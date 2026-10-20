import re
import time

import requests
from config import Config

GROQ_URL = 'https://api.groq.com/openai/v1/chat/completions'
MODEL = Config.GROQ_MODEL
GEMINI_URL = 'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent'

# Groq ücretsiz plan: dakikada 8.000 token. Her istekte giden metni sınırlı tutuyoruz.
GECMIS_SINIRI = 12             # geçmişten en fazla 12 mesaj (6 tur)
KULLANICI_KARAKTER_SINIRI = 500  # kullanıcının verdiği bilgiler kaybolmasın
ASISTAN_KARAKTER_SINIRI = 220    # botun eski cevapları kısaltılarak gönderilir (bağlam için yeterli)
CEVAP_TOKEN_SINIRI = 450

# Marka/telif riski taşıyan ifadeler: öneride asla kullanıcıya gitmez (listing aracındaki enforce_brand mantığı)
YASAKLI_IFADELER = ['official', 'licensed', 'authentic', 'fifa', 'world cup', 'worldcup', 'olympic', 'national team',
                    'nationalteam', 'disney', 'marvel', 'nike', 'adidas', 'nba', 'nfl', 'uefa', 'premier league']
ORNEK_ETIKET_SINIRI = 5

# Model bazen sohbetin içine boş form taklidi yazıyor ("Adınız:", "Telefon:"). Bu satırlar kullanıcıya gitmez.
SAHTE_FORM_SATIRI = re.compile(
    r"^\s*[-•*]?\s*(ad[ıi]n[ıi]z|ad soyad[ıi]?|ad[ıi]n[ıi]z soyad[ıi]n[ıi]z|isim|[ıi]sminiz|telefon(unuz| numaran[ıi]z)?|"
    r"e-?posta(n[ıi]z)?|e-?mail|mail|ilgili [üu]r[üu]n.*|mesaj[ıi]n[ıi]z|etsy ma[ğg]aza(n[ıi]z)?)\s*:\s*_*\s*$", re.I)
FORM_BASLIGI = re.compile(r"^\s*size d[öo]n[üu][şs] yapal[ıi]m\s*:?\s*$", re.I)
FORM_YONLENDIRME = ("Alttaki \"Size dönüş yapalım\" bölümüne adınızı ve telefonunuzu bırakabilirsiniz; "
                    "isterseniz buraya da yazabilirsiniz, ekibimiz mesai saatlerinde sizi arar.")


class AIServiceError(Exception):
    """Yapay zekâ servisine ulaşılamadığında fırlatılır; routes.py bunu 503 olarak döner."""
    pass


class AIService:

    def __init__(self, api_key=None, gemini_key=None, saglayici=None):
        # Anahtarlar verilmezse .env'dekiler kullanılır (test için dışarıdan verilebilir)
        self.api_key = Config.GROQ_API_KEY if api_key is None else api_key
        self.gemini_key = Config.GEMINI_API_KEY if gemini_key is None else gemini_key
        self.saglayici = (saglayici or Config.AI_PROVIDER or 'groq').lower()

    def _saglayici_sirasi(self):
        """Anahtarı olan sağlayıcıları deneme sırasına dizer: seçilen önce, diğeri yedek."""
        hepsi = [('groq', self.api_key, self._groq_istegi), ('gemini', self.gemini_key, self._gemini_istegi)]
        if self.saglayici == 'gemini':
            hepsi.reverse()
        return [(ad, fonk) for ad, anahtar, fonk in hepsi if anahtar]

    def _model_istegi(self, mesajlar):
        """Sırayla sağlayıcıları dener; biri cevap verirse onu döndürür, hepsi düşerse son hatayı fırlatır."""
        son_hata = AIServiceError('Asistan şu an yanıt veremiyor, lütfen biraz sonra tekrar deneyin.')
        for ad, fonk in self._saglayici_sirasi():
            try:
                return fonk(mesajlar)
            except AIServiceError as hata:
                son_hata = hata          # yedek sağlayıcıya geç
        raise son_hata

    def _gemini_istegi(self, mesajlar):
        """Aynı mesaj listesini Gemini biçimine çevirip istek atar (system → systemInstruction, assistant → model)."""
        sistem = '\n\n'.join(m['content'] for m in mesajlar if m['role'] == 'system')
        icerik = [{'role': 'model' if m['role'] == 'assistant' else 'user', 'parts': [{'text': m['content']}]}
                  for m in mesajlar if m['role'] in ('user', 'assistant')]
        try:
            yanit = requests.post(
                GEMINI_URL.format(model=Config.GEMINI_MODEL),
                headers={'x-goog-api-key': self.gemini_key, 'Content-Type': 'application/json'},
                json={'systemInstruction': {'parts': [{'text': sistem}]}, 'contents': icerik,
                      'generationConfig': {'temperature': 0.6, 'maxOutputTokens': CEVAP_TOKEN_SINIRI}},
                timeout=15
            )
        except requests.exceptions.RequestException:
            raise AIServiceError('Yapay zekâ servisine bağlanılamadı.')
        if yanit.status_code != 200:
            raise AIServiceError('Asistan şu an yanıt veremiyor, lütfen biraz sonra tekrar deneyin.')
        try:
            return yanit.json()['candidates'][0]['content']['parts'][0]['text']
        except (KeyError, IndexError, ValueError):
            raise AIServiceError('Asistan şu an yanıt veremiyor, lütfen biraz sonra tekrar deneyin.')

    def _sistem_talimati(self):
        """Chatbot'un kim olduğunu ve nasıl davranacağını config'den okur."""
        return Config.BUSINESS_CONTEXT

    def _mesajlari_hazirla(self, mesaj, gecmis, iletisim_alindi=False, isim=None):
        """Sıra: sistem talimatı -> geçmiş konuşma -> yeni kullanıcı mesajı."""
        mesajlar = [{'role': 'system', 'content': self._sistem_talimati()}]
        for kayit in (gecmis or [])[-GECMIS_SINIRI:]:      # son mesajlar yeterli, token kotasını korur
            if kayit.get('role') in ('user', 'assistant') and kayit.get('content'):
                sinir = KULLANICI_KARAKTER_SINIRI if kayit['role'] == 'user' else ASISTAN_KARAKTER_SINIRI
                icerik = str(kayit['content'])[:sinir]
                mesajlar.append({'role': kayit['role'], 'content': icerik})
        if self._ornek_verildi_mi(gecmis):
            mesajlar.append({'role': 'system', 'content': (
                'Bu sohbette tadımlık başlık/etiket örneği zaten verildi. Yeni başlık, etiket veya '
                'varyasyon yazma; kullanıcıyı nazikçe listing aracına ve Size dönüş yapalım bölümüne yönlendir.')})
        if isim:
            mesajlar.append({'role': 'system', 'content': (
                f'Ziyaretçinin adı: {isim}. Gerekirse adıyla hitap et; cinsiyet tahmin etme (Bey/Hanım deme). '
                'Adını ve e-postasını zaten verdi, tekrar isteme.')})
        if iletisim_alindi:
            mesajlar.append({'role': 'system', 'content': (
                'Kullanıcı son mesajında adını ve telefonunu yazdı; sistem bunu kaydetti ve ekibe iletti. '
                'Tek cümleyle teşekkür et, ekibin mesai saatlerinde arayacağını söyle. Formu tekrar isteme, '
                '"kayıt yapamıyorum" deme. Sonra en fazla bir kısa soru sor.')})
        mesajlar.append({'role': 'user', 'content': mesaj})
        return mesajlar

    @staticmethod
    def _ornek_iceriyor_mu(metin):
        """Metin bir başlık/etiket örneği içeriyorsa True döner."""
        k = str(metin).lower()
        return ('etiket' in k or 'tags:' in k) and ('başlık:' in k or 'title:' in k)

    def _ornek_verildi_mi(self, gecmis):
        """Asistan bu sohbette daha önce title/tag örneği verdiyse True döner."""
        return any(kayit.get('role') == 'assistant' and self._ornek_iceriyor_mu(kayit.get('content', ''))
                   for kayit in (gecmis or []))

    def _groq_istegi(self, mesajlar, deneme=1):
        """Groq API'ye requests.post ile istek atar, cevap metnini döndürür.
        429 (istek sınırı) gelirse kısa bekleyip bir kez daha dener."""
        try:
            yanit = requests.post(
                GROQ_URL,
                headers={'Authorization': f'Bearer {self.api_key}',
                         'Content-Type': 'application/json'},
                json={'model': MODEL, 'messages': mesajlar,
                      'temperature': 0.6, 'max_tokens': CEVAP_TOKEN_SINIRI,
                      'reasoning_effort': 'low'},
                timeout=15
            )
        except requests.exceptions.Timeout:
            raise AIServiceError('Yapay zekâ servisi zamanında yanıt vermedi.')
        except requests.exceptions.RequestException:
            raise AIServiceError('Yapay zekâ servisine bağlanılamadı.')

        if yanit.status_code == 429:
            if deneme < 2:
                bekleme = min(float(yanit.headers.get('retry-after', 2) or 2), 5)
                time.sleep(bekleme)
                return self._groq_istegi(mesajlar, deneme + 1)
            raise AIServiceError('Şu an yoğunluk var, birkaç saniye sonra tekrar dener misiniz?')

        if yanit.status_code != 200:
            raise AIServiceError('Asistan şu an yanıt veremiyor, lütfen biraz sonra tekrar deneyin.')

        return yanit.json()['choices'][0]['message']['content']

    def _temizle(self, metin):
        """Wix metin kutusu Markdown göstermez; model talimata uymasa bile yıldızları siler."""
        return metin.replace('**', '').replace('__', '').strip()

    @staticmethod
    def _sahte_formu_temizle(metin):
        """'Adınız:', 'Telefon:' gibi boş form satırlarını siler; yerine tek bir yönlendirme cümlesi koyar."""
        satirlar = metin.split('\n')
        kalan = [s for s in satirlar if not SAHTE_FORM_SATIRI.match(s)]
        if len(kalan) == len(satirlar):
            return metin
        kalan = [s for s in kalan if not FORM_BASLIGI.match(s)]
        govde = re.sub(r'\n{3,}', '\n\n', '\n'.join(kalan)).strip()
        if 'size dönüş yapalım' not in govde.lower():
            govde = (govde + '\n' + FORM_YONLENDIRME).strip()
        return govde

    @staticmethod
    def _yasakli_mi(parca):
        p = parca.lower()
        return any(ifade in p for ifade in YASAKLI_IFADELER)

    def _ornegi_duzelt(self, metin):
        """Başlık/etiket örneğinde marka riskli ifadeleri siler, etiketleri 5 ile sınırlar."""
        satirlar = []
        for satir in metin.split('\n'):
            etiket = re.match(r'^(\s*(?:etiketler|etiket|tags)\s*:\s*)(.*)$', satir, re.I)
            baslik = re.match(r'^(\s*(?:başlık|baslik|title)\s*:\s*)(.*)$', satir, re.I)
            if etiket:
                parcalar = [e.strip() for e in etiket.group(2).split(',') if e.strip()]
                temiz = [e for e in parcalar if not self._yasakli_mi(e)][:ORNEK_ETIKET_SINIRI]
                satir = etiket.group(1) + ', '.join(temiz)
            elif baslik:
                ayrac = ' – ' if '–' in baslik.group(2) or ' - ' in baslik.group(2) else ', '
                parcalar = [p.strip() for p in re.split(r'\s[–|\-]\s|,\s', baslik.group(2)) if p.strip()]
                satir = baslik.group(1) + ayrac.join(p for p in parcalar if not self._yasakli_mi(p))
            satirlar.append(satir)
        return '\n'.join(satirlar)

    @staticmethod
    def _hafiza_yalani_mi(cevap, gecmis):
        """Sohbet geçmişi yokken 'hatırlıyorum' demek yalandır."""
        return not gecmis and re.search(r'(?<!ha)hatırlıyorum|hatirliyorum', cevap.lower()) is not None

    def yanit_uret(self, mesaj, gecmis=None, iletisim_alindi=False, isim=None):
        """Dışarıya açık tek metot: kullanıcı mesajına cevap üretir."""
        if not self._saglayici_sirasi():
            if iletisim_alindi:
                return 'Teşekkürler, bilgilerinizi aldım; ekibimiz mesai saatlerinde sizi arayacak.'
            return ('Şu an demo modundayım. Sorunuzu iletmek için başvuru formunu '
                    'doldurabilir veya digital.ast.tr@gmail.com adresine yazabilirsiniz.')
        cevap = self._temizle(self._model_istegi(self._mesajlari_hazirla(mesaj, gecmis, iletisim_alindi, isim)))
        cevap = self._sahte_formu_temizle(cevap)

        # Kod kapıları: kritik kurallar modelin iyi niyetine bırakılmaz
        if self._hafiza_yalani_mi(cevap, gecmis):
            return ('Önceki sohbetleri göremiyorum, o yüzden hatırlayamıyorum ama memnuniyetle yardımcı olurum. '
                    'Etsy mağazanızda ne satıyorsunuz?')
        if self._ornek_iceriyor_mu(cevap):
            cevap = self._ornegi_duzelt(cevap)

        # Son kapı: tadımlık örnek zaten verildiyse, model kurala uymasa bile ikinci örnek kullanıcıya gitmez
        if self._ornek_verildi_mi(gecmis) and self._ornek_iceriyor_mu(cevap):
            return ('Bu sohbette tadımlık örneğimizi paylaştık. Yeni ürününüz için tam başlık, 13 etiket ve '
                    'açıklamayı listing aracımız birlikte hazırlıyor; Freemium ile günde 5 listing ücretsiz. '
                    'Denemek için alttaki "Size dönüş yapalım" bölümüne adınızı ve telefonunuzu bırakabilirsiniz, '
                    'ekibimiz mesai saatlerinde sizi arar. Bu arada ürününüzle ilgili başka bir sorunuz var mı?')
        return cevap


# Uygulamanın her yerinde kullanılacak tek örnek
ai_service = AIService()