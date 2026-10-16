import re
import sqlite3
import time
from collections import defaultdict, deque

from flask import Blueprint, current_app, jsonify, render_template, request

from app.database import lead_ekle, tum_leadler
from app.services.ai_service import ai_service, AIServiceError

# İzin verilen karakterler
ISIM_DESENI = re.compile(r"^[A-Za-zÇĞİÖŞÜçğıöşü][A-Za-zÇĞİÖŞÜçğıöşü .'-]{1,99}$")   # harf, boşluk, nokta, kesme, tire
TELEFON_DESENI = re.compile(r"^\+?[0-9 ()-]{1,20}$")                                 # rakam, boşluk, + ( ) -
ETSY_DESENI = re.compile(r"^[A-Za-z0-9]{4,20}$")                                         # Etsy mağaza adı kuralı

# Blueprint 1: HTML sayfaları
sayfalar = Blueprint('sayfalar', __name__)

# Blueprint 2: JSON API (tüm adresler /api ile başlar)
api = Blueprint('api', __name__, url_prefix='/api')


# ---------------- Sayfalar ----------------

@sayfalar.route('/')
def ana_sayfa():
    return render_template('index.html')


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

    try:
        cevap = ai_service.yanit_uret(mesaj, gecmis)
    except AIServiceError as e:
        return _hata(str(e), 503)

    return jsonify(basari=True, cevap=cevap)


@api.route('/leads', methods=['POST'])
def lead_kaydet():
    if _sinir_asildi_mi('lead'):
        return _hata('Bilgileriniz zaten alındı; birkaç dakika sonra tekrar deneyebilirsiniz.', 429)
    veri = request.get_json(silent=True) or {}
    isim = str(veri.get('isim') or '').strip()
    telefon = str(veri.get('telefon') or '').strip()
    mesaj = str(veri.get('mesaj') or '').strip()
    etsy_magaza = str(veri.get('etsy_magaza') or '').strip() or None

    isim = re.sub(r'\s+', ' ', isim)            # fazla boşlukları tek boşluğa indir

    if not isim or not telefon:
        return _hata('İsim ve telefon zorunludur.', 400)
    if not ISIM_DESENI.match(isim):
        return _hata('İsim yalnızca harf içerebilir (en az 2 karakter).', 400)
    if not TELEFON_DESENI.match(telefon):
        return _hata('Telefon yalnızca rakam içerebilir.', 400)
    rakamlar = re.sub(r'\D', '', telefon)
    if not 10 <= len(rakamlar) <= 13:
        return _hata('Telefon numarası 10-13 haneli olmalıdır.', 400)
    telefon = ('+' if telefon.startswith('+') else '') + rakamlar   # standart biçimde sakla
    if etsy_magaza and not ETSY_DESENI.match(etsy_magaza):
        return _hata('Etsy mağaza adı 4-20 harf/rakam olmalıdır.', 400)

    try:
        yeni_id = lead_ekle(isim, telefon, mesaj[:1000], etsy_magaza)
    except sqlite3.Error:
        return _hata('Kayıt sırasında bir sorun oluştu.', 500)

    return jsonify(basari=True, id=yeni_id, mesaj='Bilgileriniz alındı, en kısa sürede dönüş yapacağız.'), 201


@api.route('/leads', methods=['GET'])
def leadleri_listele():
    if not _yonetici_mi():
        return _hata('Bu bilgiyi görme yetkiniz yok.', 401)
    try:
        leadler = tum_leadler()
    except sqlite3.Error:
        return _hata('Kayıtlar okunamadı.', 500)
    return jsonify(basari=True, adet=len(leadler), leadler=leadler)
