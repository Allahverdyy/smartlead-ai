import re
import sqlite3
import time
from collections import defaultdict, deque

from flask import Blueprint, current_app, jsonify, render_template, request

from app.database import (lead_ekle, lead_mesajini_guncelle, lead_tamamla, lead_telefonu, sohbet_kaydet,
                          sohbet_lead_id, sohbet_olustur, sohbete_lead_bagla, sohbeti_sil, tum_leadler, tum_sohbetler)
from app.services.ai_service import ai_service, AIServiceError

# İzin verilen karakterler
ISIM_DESENI = re.compile(r"^[A-Za-zÇĞİÖŞÜçğıöşü][A-Za-zÇĞİÖŞÜçğıöşü .'-]{1,99}$")   # harf, boşluk, nokta, kesme, tire
TELEFON_DESENI = re.compile(r"^\+?[0-9 ()-]{1,20}$")                                 # rakam, boşluk, + ( ) -
ETSY_DESENI = re.compile(r"^[A-Za-z0-9]{4,20}$")                                         # Etsy mağaza adı kuralı
EPOSTA_DESENI = re.compile(r"^[A-Za-z0-9._%+-]{1,64}@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}$")

MESAJ_SINIRI = 12000  # kaydedilen sohbet dökümü (son 12.000 karakter)
OTURUM_DESENI = re.compile(r"^[A-Za-z0-9-]{8,64}$")
# Sohbete yazılan telefon: rakam, boşluk, tire, parantez; 10-13 hane
SOHBET_TELEFON_DESENI = re.compile(r"\+?\d[\d ()-]{8,18}\d")

# Blueprint 1: HTML sayfaları
sayfalar = Blueprint('sayfalar', __name__)

# Blueprint 2: JSON API (tüm adresler /api ile başlar)
api = Blueprint('api', __name__, url_prefix='/api')


# ---------------- Sayfalar ----------------

@sayfalar.route('/')
def ana_sayfa():
    """AST Digital sitesi (yerel prototip): sohbet /widget, form /api/leads, panel /dashboard."""
    return render_template('sayfalar/anasayfa.html', aktif='ana_sayfa')


# Sitenin iç sayfaları: hepsi site.html'deki ortak üst menüyü ve alt bilgiyi kullanır
@sayfalar.route('/araclar')
def araclar():
    return render_template('sayfalar/araclar.html', aktif='araclar')


@sayfalar.route('/nasil-calisir')
def nasil_calisir():
    return render_template('sayfalar/nasil.html', aktif='nasil_calisir')


@sayfalar.route('/paketler')
def paketler():
    return render_template('sayfalar/paketler.html', aktif='paketler')


@sayfalar.route('/hakkimizda')
def hakkimizda():
    return render_template('sayfalar/hakkimizda.html', aktif='hakkimizda')


@sayfalar.route('/sss')
def sss():
    return render_template('sayfalar/sss.html', aktif='sss')


@sayfalar.route('/basvuru')
def basvuru():
    return render_template('sayfalar/basvuru.html', aktif='basvuru')


@sayfalar.route('/iletisim')
def iletisim():
    """Genel iletişim: sade form (başvuru sayfasından ayrı)."""
    return render_template('sayfalar/iletisim.html', aktif='iletisim')


@sayfalar.route('/asistan')
def asistan():
    """Sohbet asistanı tam sayfa."""
    return render_template('index.html')


@sayfalar.route('/widget')
def widget():
    """Wix popup'ına gömülen sohbet penceresi (aynı arayüz, kenar boşluksuz ve tam ekran)."""
    return render_template('index.html', gomulu=True)


@sayfalar.route('/kvkk')
def kvkk():
    """KVKK Aydınlatma Metni (giriş ekranındaki onay kutusundan bağlanır)."""
    return render_template('kvkk.html')


@sayfalar.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')


# ---------------- Yardımcılar ----------------

def _hata(mesaj, kod):
    """Tüm hata cevapları aynı biçimde: {"basari": false, "hata": "..."}"""
    return jsonify(basari=False, hata=mesaj), kod


def _yonetici_mi():
    """ADMIN_KEY tanımlıysa, lead listesini yalnızca doğru anahtarı gönderen görebilir."""
    anahtar = current_app.config.get('ADMIN_KEY')
    if not anahtar:            # yerelde anahtar yoksa kontrol kapalı
        return True
    return request.headers.get('X-Admin-Key') == anahtar


# IP başına istek sınırı (bellekte; tek sunucu için yeterli)
_istekler = defaultdict(deque)
SINIRLAR = {'sohbet': (6, 60), 'lead': (3, 600)}   # (en fazla istek, saniye)


def _istemci_ip():
    """Render bir vekil sunucunun arkasında çalışır; gerçek IP X-Forwarded-For'un ilk değeridir."""
    return (request.headers.get('X-Forwarded-For', request.remote_addr or '') .split(',')[0].strip())


def _sinir_asildi_mi(tur):
    adet, sure = SINIRLAR[tur]
    simdi = time.time()
    kuyruk = _istekler[(tur, _istemci_ip())]
    while kuyruk and simdi - kuyruk[0] > sure:
        kuyruk.popleft()
    if len(kuyruk) >= adet:
        return True
    kuyruk.append(simdi)
    return False


def _dokum(gecmis, mesaj=None, cevap=None):
    """Sohbeti panelde okunacak düz metne çevirir: her satır 'Ziyaretçi:' veya 'Asistan:' ile başlar."""
    satirlar = []
    for kayit in gecmis:
        if isinstance(kayit, dict) and kayit.get('role') in ('user', 'assistant') and kayit.get('content'):
            satirlar.append(('Ziyaretçi: ' if kayit['role'] == 'user' else 'Asistan: ') + str(kayit['content'])[:1000])
    if mesaj:
        satirlar.append('Ziyaretçi: ' + mesaj)
    if cevap:
        satirlar.append('Asistan: ' + cevap)
    return '\n'.join(satirlar)[-MESAJ_SINIRI:], len(satirlar)


def _buyuk_harfle(kelime):
    """Türkçe kurala göre ilk harfi büyütür: ismail -> İsmail, ılgaz -> Ilgaz."""
    ilk = {'i': 'İ', 'ı': 'I'}.get(kelime[0], kelime[0].upper())
    return ilk + kelime[1:].lower()


def _sohbetteki_iletisim(mesaj):
    """Ziyaretçi adını ve telefonunu sohbete yazdıysa (isim, telefon) döner, yoksa None."""
    eslesme = SOHBET_TELEFON_DESENI.search(mesaj)
    if not eslesme:
        return None
    rakamlar = re.sub(r'\D', '', eslesme.group())
    if not 10 <= len(rakamlar) <= 13:
        return None
    telefon = ('+' if eslesme.group().startswith('+') else '') + rakamlar
    # Telefondan önce yazılan ilk 1-4 kelime isim kabul edilir (yalnızca harf)
    oncesi = re.sub(r'\s+', ' ', mesaj[:eslesme.start()]).strip(' ,.:;-')
    kelimeler = [k for k in oncesi.split(' ') if k][-4:]
    isim = ' '.join(_buyuk_harfle(k) for k in kelimeler)
    if not ISIM_DESENI.match(isim):
        isim = 'Sohbetten gelen'
    return isim, telefon


# ---------------- API ----------------

@api.route('/sohbet', methods=['POST'])
def sohbet():
    if _sinir_asildi_mi('sohbet'):
        return _hata('Çok hızlı mesaj gönderiyorsunuz, lütfen bir dakika sonra tekrar deneyin.', 429)
    veri = request.get_json(silent=True) or {}
    mesaj = str(veri.get('mesaj') or '').strip()
    gecmis = veri.get('gecmis') or []

    if not mesaj:
        return _hata('Mesaj boş olamaz.', 400)
    if len(mesaj) > 1000:
        return _hata('Mesaj en fazla 1000 karakter olabilir.', 400)
    if not isinstance(gecmis, list):
        gecmis = []

    oturum = str(veri.get('oturum') or '')
    if not OTURUM_DESENI.match(oturum):
        oturum = None                       # eski widget veya bozuk kimlik: sohbet yine çalışır, kaydedilmez

    isim = re.sub(r'\s+', ' ', str(veri.get('isim') or '')).strip()
    isim = isim if ISIM_DESENI.match(isim) else None    # giriş ekranında verilen ad; yalnızca harf
    eposta = str(veri.get('eposta') or '').strip().lower()
    eposta = eposta if len(eposta) <= 120 and EPOSTA_DESENI.match(eposta) else None

    kvkk_onay = veri.get('kvkk_onay') is True
    # Sohbete yazılan telefon yalnızca KVKK onayı verildiyse kaydedilir; kaydedemeyeceksek 'aldım' dedirtmeyiz
    iletisim = _sohbetteki_iletisim(mesaj) if (oturum and kvkk_onay) else None
    try:
        cevap = ai_service.yanit_uret(mesaj, gecmis, iletisim_alindi=bool(iletisim), isim=isim)
    except AIServiceError as e:
        return _hata(str(e), 503)

    kaydedildi = False
    if oturum:
        dokum, adet = _dokum(gecmis, mesaj, cevap)
        try:
            sohbet_kaydet(oturum, dokum, adet, isim, eposta)
            lead_id = sohbet_lead_id(oturum)
            if iletisim and not lead_id:            # sohbete yazılan bilgiyle otomatik lead
                lead_id = lead_ekle(iletisim[0], iletisim[1], dokum)
                sohbete_lead_bagla(oturum, lead_id)
                kaydedildi = True
            elif lead_id:
                if iletisim and not lead_telefonu(lead_id):      # girişte e-posta vermişti, şimdi telefon yazdı
                    lead_tamamla(lead_id, telefon=iletisim[1])
                    kaydedildi = True
                lead_mesajini_guncelle(lead_id, dokum)
        except sqlite3.Error:
            current_app.logger.exception('Sohbet kaydedilemedi')   # kayıt hatası sohbeti bozmasın

    return jsonify(basari=True, cevap=cevap, kaydedildi=kaydedildi)


@api.route('/leads', methods=['POST'])
def lead_kaydet():
    if _sinir_asildi_mi('lead'):
        return _hata('Bilgileriniz zaten alındı; birkaç dakika sonra tekrar deneyebilirsiniz.', 429)
    veri = request.get_json(silent=True) or {}
    isim = str(veri.get('isim') or '').strip()
    telefon = str(veri.get('telefon') or '').strip()
    mesaj = str(veri.get('mesaj') or '').strip()
    etsy_magaza = str(veri.get('etsy_magaza') or '').strip() or None

    eposta = str(veri.get('eposta') or '').strip().lower() or None
    oturum = str(veri.get('oturum') or '')
    isim = re.sub(r'\s+', ' ', isim)            # fazla boşlukları tek boşluğa indir

    if veri.get('kvkk_onay') is not True:
        return _hata('Devam etmek için KVKK Aydınlatma Metni onayı gereklidir.', 400)
    if not isim or not (telefon or eposta):
        return _hata('İsim ve telefon (veya e-posta) zorunludur.', 400)
    if not ISIM_DESENI.match(isim):
        return _hata('İsim yalnızca harf içerebilir (en az 2 karakter).', 400)
    if telefon:
        if not TELEFON_DESENI.match(telefon):
            return _hata('Telefon yalnızca rakam içerebilir.', 400)
        rakamlar = re.sub(r'\D', '', telefon)
        if not 10 <= len(rakamlar) <= 13:
            return _hata('Telefon numarası 10-13 haneli olmalıdır.', 400)
        telefon = ('+' if telefon.startswith('+') else '') + rakamlar   # standart biçimde sakla
    if eposta and (len(eposta) > 120 or not EPOSTA_DESENI.match(eposta)):
        return _hata('Geçerli bir e-posta adresi yazın.', 400)
    if etsy_magaza and not ETSY_DESENI.match(etsy_magaza):
        return _hata('Etsy mağaza adı 4-20 harf/rakam olmalıdır.', 400)

    gecerli_oturum = bool(OTURUM_DESENI.match(oturum))
    try:
        mevcut = sohbet_lead_id(oturum) if gecerli_oturum else None
        if mevcut:                                   # aynı sohbette ikinci form: yeni kayıt açma, eksikleri tamamla
            lead_tamamla(mevcut, telefon=telefon, eposta=eposta, etsy_magaza=etsy_magaza)
            if mesaj:
                lead_mesajini_guncelle(mevcut, mesaj[-MESAJ_SINIRI:])
            yeni_id = mevcut
        else:
            yeni_id = lead_ekle(isim, telefon, mesaj[-MESAJ_SINIRI:], etsy_magaza, eposta)
            if gecerli_oturum:
                if mesaj:
                    sohbet_kaydet(oturum, mesaj[-MESAJ_SINIRI:], mesaj.count('\n') + 1)
                else:
                    sohbet_olustur(oturum)               # giriş ekranı: sohbet henüz başlamadı
                sohbete_lead_bagla(oturum, yeni_id)
    except sqlite3.Error:
        return _hata('Kayıt sırasında bir sorun oluştu.', 500)

    return jsonify(basari=True, id=yeni_id, mesaj='Bilgileriniz alındı, en kısa sürede dönüş yapacağız.'), 201


@api.route('/leads', methods=['GET'])
def leadleri_listele():
     #if not _yonetici_mi():
      #   return _hata('Bu bilgiyi görme yetkiniz yok.', 401)
    try:
        leadler = tum_leadler()
    except sqlite3.Error:
        return _hata('Kayıtlar okunamadı.', 500)
    return jsonify(basari=True, adet=len(leadler), leadler=leadler)



@api.route('/sohbetler', methods=['GET'])
def sohbetleri_listele():
    if not _yonetici_mi():
        return _hata('Bu bilgiyi görme yetkiniz yok.', 401)
    try:
        sohbetler = tum_sohbetler()
    except sqlite3.Error:
        return _hata('Sohbetler okunamadı.', 500)
    return jsonify(basari=True, adet=len(sohbetler), sohbetler=sohbetler)


@api.route('/sohbet/<oturum>', methods=['DELETE'])
def sohbet_sil(oturum):
    """Ziyaretçi kendi sohbetini siler. Oturum kimliği yalnızca ziyaretçinin tarayıcısında bulunur."""
    if _sinir_asildi_mi('sohbet'):
        return _hata('Çok hızlı istek gönderiyorsunuz, lütfen biraz sonra tekrar deneyin.', 429)
    if not OTURUM_DESENI.match(oturum):
        return _hata('Geçersiz sohbet kimliği.', 400)
    try:
        sohbeti_sil(oturum)
    except sqlite3.Error:
        return _hata('Sohbet silinemedi.', 500)
    return jsonify(basari=True, mesaj='Sohbet silindi.')
