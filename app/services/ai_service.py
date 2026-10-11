import requests
from config import Config

GROQ_URL = 'https://api.groq.com/openai/v1/chat/completions'
MODEL = Config.GROQ_MODEL


class AIServiceError(Exception):
    """Yapay zekâ servisine ulaşılamadığında fırlatılır; routes.py bunu 503 olarak döner."""
    pass


class AIService:

    def __init__(self, api_key=None):
        # api_key verilmezse .env'deki anahtar kullanılır (test için dışarıdan verilebilir)
        self.api_key = Config.GROQ_API_KEY if api_key is None else api_key

    def _sistem_talimati(self):
        """Chatbot'un kim olduğunu ve nasıl davranacağını config'den okur."""
        return Config.BUSINESS_CONTEXT

    def _mesajlari_hazirla(self, mesaj, gecmis):
        """Sıra: sistem talimatı -> geçmiş konuşma -> yeni kullanıcı mesajı."""
        mesajlar = [{'role': 'system', 'content': self._sistem_talimati()}]
        for kayit in (gecmis or [])[-10:]:          # son 10 mesaj yeterli, maliyeti düşürür
            if kayit.get('role') in ('user', 'assistant') and kayit.get('content'):
                mesajlar.append({'role': kayit['role'], 'content': kayit['content']})
        mesajlar.append({'role': 'user', 'content': mesaj})
        return mesajlar

    def _groq_istegi(self, mesajlar):
        """Groq API'ye requests.post ile istek atar, cevap metnini döndürür."""
        try:
            yanit = requests.post(
                GROQ_URL,
                headers={'Authorization': f'Bearer {self.api_key}',
                         'Content-Type': 'application/json'},
                json={'model': MODEL, 'messages': mesajlar,
                      'temperature': 0.6, 'max_tokens': 800,
                      'reasoning_effort': 'low'},
                timeout=15
            )
        except requests.exceptions.Timeout:
            raise AIServiceError('Yapay zekâ servisi zamanında yanıt vermedi.')
        except requests.exceptions.RequestException:
            raise AIServiceError('Yapay zekâ servisine bağlanılamadı.')

        if yanit.status_code != 200:
            raise AIServiceError(f'Yapay zekâ servisi hata döndürdü (kod {yanit.status_code}).')

        metin = yanit.json()['choices'][0]['message']['content']
        return self._temizle(metin)

    def _temizle(self, metin):
        """Wix metin kutusu Markdown göstermez; model talimata uymasa bile yıldızları siler."""
        return metin.replace('**', '').replace('__', '').strip()

    def yanit_uret(self, mesaj, gecmis=None):
        """Dışarıya açık tek metot: kullanıcı mesajına cevap üretir."""
        if not self.api_key:
            return ('Şu an demo modundayım. Sorunuzu iletmek için başvuru formunu '
                    'doldurabilir veya digital.ast.tr@gmail.com adresine yazabilirsiniz.')
        return self._groq_istegi(self._mesajlari_hazirla(mesaj, gecmis))


# Uygulamanın her yerinde kullanılacak tek örnek
ai_service = AIService()