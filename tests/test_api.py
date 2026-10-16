"""Modül F: API uç noktalarının uçtan uca testleri (Groq'a bağlanmadan)."""
from app.services.ai_service import ai_service, AIServiceError


# ---------------- Genel ----------------

def test_health(client):
    yanit = client.get('/health')
    assert yanit.status_code == 200
    assert yanit.get_json() == {'durum': 'aktif'}


def test_sayfalar_aciliyor(client):
    assert client.get('/').status_code == 200
    assert client.get('/dashboard').status_code == 200
    assert client.get('/widget').status_code == 200


# ---------------- /api/sohbet ----------------

def test_sohbet_bos_mesaj_400(client):
    yanit = client.post('/api/sohbet', json={})
    assert yanit.status_code == 400
    assert yanit.get_json()['basari'] is False


def test_sohbet_cok_uzun_mesaj_400(client):
    assert client.post('/api/sohbet', json={'mesaj': 'a' * 1001}).status_code == 400


def test_sohbet_demo_modu_200(client):
    yanit = client.post('/api/sohbet', json={'mesaj': 'Fiyatlar nedir?'})
    veri = yanit.get_json()
    assert yanit.status_code == 200
    assert veri['basari'] is True
    assert 'demo' in veri['cevap'].lower()


def test_sohbet_ai_hatasi_503(client, monkeypatch):
    def hata_firlat(mesaj, gecmis=None):
        raise AIServiceError('Yapay zekâ servisine bağlanılamadı.')
    monkeypatch.setattr(ai_service, 'yanit_uret', hata_firlat)
    yanit = client.post('/api/sohbet', json={'mesaj': 'Merhaba'})
    assert yanit.status_code == 503
    assert yanit.get_json()['basari'] is False


# ---------------- POST /api/leads ----------------

def test_lead_kaydi_201_ve_telefon_standart(client):
    yanit = client.post('/api/leads', json={'isim': 'Ayşe Gül', 'telefon': '0 (555) 123-45-67',
                                            'etsy_magaza': 'AyseCeramics'})
    assert yanit.status_code == 201
    lead = client.get('/api/leads').get_json()['leadler'][0]
    assert lead['telefon'] == '05551234567'
    assert lead['etsy_magaza'] == 'AyseCeramics'


def test_lead_eksik_alan_400(client):
    assert client.post('/api/leads', json={'isim': 'Elif'}).status_code == 400


def test_lead_gecersiz_isim_400(client):
    for isim in ['E', 'sada5521>£#$', '<script>alert(1)</script>']:
        assert client.post('/api/leads', json={'isim': isim, 'telefon': '05551234567'}).status_code == 400


def test_lead_gecersiz_telefon_400(client):
    for telefon in ['12345', 'asada141241', '0555-ABC-1234']:
        assert client.post('/api/leads', json={'isim': 'Elif', 'telefon': telefon}).status_code == 400


def test_lead_gecersiz_etsy_magaza_400(client):
    yanit = client.post('/api/leads', json={'isim': 'Elif', 'telefon': '05551234567', 'etsy_magaza': 'kötü mağaza!'})
    assert yanit.status_code == 400


def test_sql_enjeksiyonu_duz_metin_olarak_kalir(client):
    """? yer tutucusu sayesinde zararlı metin çalışmaz, yalnızca mesaj olarak saklanır."""
    zararli = "x'); DROP TABLE leads;--"
    client.post('/api/leads', json={'isim': 'Elif', 'telefon': '05551234567', 'mesaj': zararli})
    leadler = client.get('/api/leads').get_json()['leadler']
    assert leadler[0]['mesaj'] == zararli          # tablo hâlâ duruyor ve metin aynen kayıtlı


# ---------------- GET /api/leads ----------------

def test_leadler_en_yeniden_eskiye(client):
    client.post('/api/leads', json={'isim': 'Birinci', 'telefon': '05551111111'})
    client.post('/api/leads', json={'isim': 'Ikinci', 'telefon': '05552222222'})
    veri = client.get('/api/leads').get_json()
    assert veri['adet'] == 2
    assert [l['isim'] for l in veri['leadler']] == ['Ikinci', 'Birinci']


def test_admin_key_korumasi(app, client):
    app.config['ADMIN_KEY'] = 'gizli-anahtar'
    assert client.get('/api/leads').status_code == 401
    assert client.get('/api/leads', headers={'X-Admin-Key': 'yanlis'}).status_code == 401
    assert client.get('/api/leads', headers={'X-Admin-Key': 'gizli-anahtar'}).status_code == 200


# ---------------- CORS ----------------

def _cors(client, kaynak):
    yanit = client.options('/api/sohbet', headers={'Origin': kaynak, 'Access-Control-Request-Method': 'POST'})
    return yanit.headers.get('Access-Control-Allow-Origin')


def test_cors_wix_izinli(client):
    assert _cors(client, 'https://astdigital.wixstudio.com') == 'https://astdigital.wixstudio.com'


def test_cors_baska_site_engelli(client):
    assert _cors(client, 'https://kotu-site.com') is None


# ---------------- Kötüye kullanım ve hata sayfaları ----------------

def test_sohbet_ip_siniri_429(client):
    kodlar = [client.post('/api/sohbet', json={'mesaj': 'merhaba'}).status_code for _ in range(7)]
    assert kodlar[:6] == [200] * 6 and kodlar[6] == 429


def test_lead_ip_siniri_429(client):
    kodlar = [client.post('/api/leads', json={'isim': 'Elif', 'telefon': '0555123456' + str(i)}).status_code
              for i in range(4)]
    assert kodlar[:3] == [201] * 3 and kodlar[3] == 429


def test_404_json_turkce(client):
    yanit = client.get('/olmayan-adres')
    assert yanit.status_code == 404
    assert yanit.get_json()['basari'] is False


def test_405_json(client):
    assert client.get('/api/sohbet').status_code == 405


def test_lead_sohbet_dokumu_saklanir(client):
    dokum = 'Ziyaretçi: merhaba\nAsistan: Merhaba! Ne satıyorsunuz?\n' + 'x' * 5000
    client.post('/api/leads', json={'isim': 'Elif', 'telefon': '05551234567', 'mesaj': dokum})
    kayit = client.get('/api/leads').get_json()['leadler'][0]['mesaj']
    assert len(kayit) == 4000 and kayit.endswith('x')       # en son kısmı saklanır
