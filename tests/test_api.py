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
    def hata_firlat(mesaj, gecmis=None, **_):
        raise AIServiceError('Yapay zekâ servisine bağlanılamadı.')
    monkeypatch.setattr(ai_service, 'yanit_uret', hata_firlat)
    yanit = client.post('/api/sohbet', json={'mesaj': 'Merhaba'})
    assert yanit.status_code == 503
    assert yanit.get_json()['basari'] is False


# ---------------- POST /api/leads ----------------

def test_lead_kaydi_201_ve_telefon_standart(client):
    yanit = client.post('/api/leads', json={'kvkk_onay': True, 'isim': 'Ayşe Gül', 'telefon': '0 (555) 123-45-67',
                                            'etsy_magaza': 'AyseCeramics'})
    assert yanit.status_code == 201
    lead = client.get('/api/leads').get_json()['leadler'][0]
    assert lead['telefon'] == '05551234567'
    assert lead['etsy_magaza'] == 'AyseCeramics'


def test_lead_eksik_alan_400(client):
    assert client.post('/api/leads', json={'kvkk_onay': True, 'isim': 'Elif'}).status_code == 400


def test_lead_gecersiz_isim_400(client):
    for isim in ['E', 'sada5521>£#$', '<script>alert(1)</script>']:
        assert client.post('/api/leads', json={'kvkk_onay': True, 'isim': isim, 'telefon': '05551234567'}).status_code == 400


def test_lead_gecersiz_telefon_400(client):
    for telefon in ['12345', 'asada141241', '0555-ABC-1234']:
        assert client.post('/api/leads', json={'kvkk_onay': True, 'isim': 'Elif', 'telefon': telefon}).status_code == 400


def test_lead_gecersiz_etsy_magaza_400(client):
    yanit = client.post('/api/leads', json={'kvkk_onay': True, 'isim': 'Elif', 'telefon': '05551234567', 'etsy_magaza': 'kötü mağaza!'})
    assert yanit.status_code == 400


def test_sql_enjeksiyonu_duz_metin_olarak_kalir(client):
    """? yer tutucusu sayesinde zararlı metin çalışmaz, yalnızca mesaj olarak saklanır."""
    zararli = "x'); DROP TABLE leads;--"
    client.post('/api/leads', json={'kvkk_onay': True, 'isim': 'Elif', 'telefon': '05551234567', 'mesaj': zararli})
    leadler = client.get('/api/leads').get_json()['leadler']
    assert leadler[0]['mesaj'] == zararli          # tablo hâlâ duruyor ve metin aynen kayıtlı


# ---------------- GET /api/leads ----------------

def test_leadler_en_yeniden_eskiye(client):
    client.post('/api/leads', json={'kvkk_onay': True, 'isim': 'Birinci', 'telefon': '05551111111'})
    client.post('/api/leads', json={'kvkk_onay': True, 'isim': 'Ikinci', 'telefon': '05552222222'})
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
    kodlar = [client.post('/api/leads', json={'kvkk_onay': True, 'isim': 'Elif', 'telefon': '0555123456' + str(i)}).status_code
              for i in range(4)]
    assert kodlar[:3] == [201] * 3 and kodlar[3] == 429


def test_404_json_turkce(client):
    yanit = client.get('/olmayan-adres')
    assert yanit.status_code == 404
    assert yanit.get_json()['basari'] is False


def test_405_json(client):
    assert client.get('/api/sohbet').status_code == 405


def test_lead_sohbet_dokumu_saklanir(client):
    dokum = 'Ziyaretçi: merhaba\nAsistan: Merhaba! Ne satıyorsunuz?\n' + 'x' * 13000
    client.post('/api/leads', json={'kvkk_onay': True, 'isim': 'Elif', 'telefon': '05551234567', 'mesaj': dokum})
    kayit = client.get('/api/leads').get_json()['leadler'][0]['mesaj']
    assert len(kayit) == 12000 and kayit.endswith('x')       # en son kısmı saklanır


# ---------------- Sohbet kaydı (form doldurulmasa da) ----------------

OTURUM = 'test-oturum-1234'


def test_sohbet_formsuz_da_kaydedilir(client):
    client.post('/api/sohbet', json={'mesaj': 'selam', 'gecmis': [], 'oturum': OTURUM, 'kvkk_onay': True})
    veri = client.get('/api/sohbetler').get_json()
    assert veri['adet'] == 1
    s = veri['sohbetler'][0]
    assert s['dokum'].startswith('Ziyaretçi: selam\nAsistan: ')
    assert s['lead_id'] is None


def test_ayni_oturum_tek_kayit_olarak_guncellenir(client):
    client.post('/api/sohbet', json={'mesaj': 'selam', 'gecmis': [], 'oturum': OTURUM, 'kvkk_onay': True})
    gecmis = [{'role': 'user', 'content': 'selam'}, {'role': 'assistant', 'content': 'Merhaba'}]
    client.post('/api/sohbet', json={'mesaj': 'tişört satıyorum', 'gecmis': gecmis, 'oturum': OTURUM, 'kvkk_onay': True})
    veri = client.get('/api/sohbetler').get_json()
    assert veri['adet'] == 1 and veri['sohbetler'][0]['mesaj_sayisi'] == 4


def test_oturumsuz_sohbet_calisir_ama_kaydedilmez(client):
    assert client.post('/api/sohbet', json={'mesaj': 'selam'}).status_code == 200
    assert client.post('/api/sohbet', json={'mesaj': 'selam', 'oturum': "x'; DROP TABLE--"}).status_code == 200
    assert client.get('/api/sohbetler').get_json()['adet'] == 0


def test_sohbete_yazilan_telefon_otomatik_lead_olur(client):
    yanit = client.post('/api/sohbet', json={'mesaj': 'ahmet çakar 0553 171 622 6 ahmet@mail.co', 'oturum': OTURUM, 'kvkk_onay': True})
    assert yanit.get_json()['kaydedildi'] is True
    lead = client.get('/api/leads').get_json()['leadler'][0]
    assert lead['isim'] == 'Ahmet Çakar' and lead['telefon'] == '05531716226'
    # ikinci kez yazsa da yeni lead açılmaz
    client.post('/api/sohbet', json={'mesaj': 'tekrar 0553 171 6226', 'oturum': OTURUM, 'kvkk_onay': True})
    assert client.get('/api/leads').get_json()['adet'] == 1
    assert client.get('/api/sohbetler').get_json()['sohbetler'][0]['isim'] == 'Ahmet Çakar'


def test_kisa_sayi_lead_sayilmaz(client):
    yanit = client.post('/api/sohbet', json={'mesaj': '2026 yılında 500 satış', 'oturum': OTURUM, 'kvkk_onay': True})
    assert yanit.get_json()['kaydedildi'] is False
    assert client.get('/api/leads').get_json()['adet'] == 0


def test_form_ile_lead_sohbete_baglanir(client):
    client.post('/api/sohbet', json={'mesaj': 'selam', 'oturum': OTURUM, 'kvkk_onay': True})
    client.post('/api/leads', json={'kvkk_onay': True, 'isim': 'Elif Kaya', 'telefon': '05551112233',
                                    'mesaj': 'Ziyaretçi: selam\nAsistan: Merhaba', 'oturum': OTURUM})
    s = client.get('/api/sohbetler').get_json()['sohbetler'][0]
    assert s['isim'] == 'Elif Kaya' and s['lead_id'] is not None


def test_sohbetler_admin_anahtari_ister(tmp_path):
    from app import create_app
    istemci = create_app('development', DATABASE_URL=str(tmp_path / 'a.db'), ADMIN_KEY='gizli').test_client()
    assert istemci.get('/api/sohbetler').status_code == 401
    assert istemci.get('/api/sohbetler', headers={'X-Admin-Key': 'gizli'}).status_code == 200


# ---------------- Giriş ekranı (ad + e-posta) ve sohbet silme ----------------

def test_eposta_ile_lead_telefonsuz_kaydedilir(client):
    yanit = client.post('/api/leads', json={'kvkk_onay': True, 'isim': 'Elif Kaya', 'eposta': 'Elif@Mail.com', 'mesaj': '', 'oturum': OTURUM})
    assert yanit.status_code == 201
    lead = client.get('/api/leads').get_json()['leadler'][0]
    assert lead['eposta'] == 'elif@mail.com' and lead['telefon'] == ''


def test_gecersiz_eposta_reddedilir(client):
    yanit = client.post('/api/leads', json={'kvkk_onay': True, 'isim': 'Elif Kaya', 'eposta': 'elif@'})
    assert yanit.status_code == 400


def test_giristen_sonra_sohbet_bos_dokumu_ezmez_ve_telefon_tamamlanir(client):
    client.post('/api/leads', json={'kvkk_onay': True, 'isim': 'Elif Kaya', 'eposta': 'elif@mail.com', 'mesaj': '', 'oturum': OTURUM})
    client.post('/api/sohbet', json={'mesaj': 'selam', 'oturum': OTURUM, 'kvkk_onay': True, 'isim': 'Elif Kaya'})
    yanit = client.post('/api/sohbet', json={'mesaj': 'numaram 0555 111 22 33', 'oturum': OTURUM, 'kvkk_onay': True,
                                             'gecmis': [{'role': 'user', 'content': 'selam'}]})
    assert yanit.get_json()['kaydedildi'] is True
    leadler = client.get('/api/leads').get_json()['leadler']
    assert len(leadler) == 1 and leadler[0]['telefon'] == '05551112233'
    assert 'numaram' in leadler[0]['mesaj']


def test_ayni_oturumda_ikinci_form_yeni_lead_acmaz(client):
    client.post('/api/leads', json={'kvkk_onay': True, 'isim': 'Elif Kaya', 'eposta': 'elif@mail.com', 'oturum': OTURUM})
    client.post('/api/leads', json={'kvkk_onay': True, 'isim': 'Elif Kaya', 'telefon': '05551112233', 'mesaj': 'Ziyaretçi: selam', 'oturum': OTURUM})
    leadler = client.get('/api/leads').get_json()['leadler']
    assert len(leadler) == 1 and leadler[0]['telefon'] == '05551112233' and leadler[0]['eposta'] == 'elif@mail.com'


def test_bilgi_vermeyenin_yeni_sohbetinde_ad_gorunur(client):
    client.post('/api/sohbet', json={'mesaj': 'selam', 'oturum': OTURUM, 'kvkk_onay': True, 'isim': 'Elif Kaya', 'eposta': 'elif@mail.com'})
    s = client.get('/api/sohbetler').get_json()['sohbetler'][0]
    assert s['z_isim'] == 'Elif Kaya' and s['z_eposta'] == 'elif@mail.com'


def test_ziyaretci_sohbetini_silebilir(client):
    client.post('/api/sohbet', json={'mesaj': 'ali veli 05551112233', 'oturum': OTURUM, 'kvkk_onay': True})
    assert client.delete('/api/sohbet/' + OTURUM).status_code == 200
    assert client.get('/api/sohbetler').get_json()['adet'] == 0
    lead = client.get('/api/leads').get_json()['leadler'][0]
    assert lead['mesaj'] == '' and lead['telefon'] == '05551112233'   # iletişim kalır, sohbet metni silinir


def test_gecersiz_oturum_silinemez(client):
    assert client.delete('/api/sohbet/kisa').status_code == 400


def test_sayfalar_onbellege_alinmaz(client):
    for adres in ('/widget', '/dashboard', '/health'):
        assert client.get(adres).headers.get('Cache-Control') == 'no-store'



# ---------------- KVKK ----------------

def test_kvkk_onaysiz_lead_reddedilir(client):
    yanit = client.post('/api/leads', json={'isim': 'Elif Kaya', 'telefon': '05551112233'})
    assert yanit.status_code == 400 and 'KVKK' in yanit.get_json()['hata']


def test_kvkk_onay_zamani_saklanir(client):
    client.post('/api/leads', json={'kvkk_onay': True, 'isim': 'Elif Kaya', 'telefon': '05551112233'})
    assert client.get('/api/leads').get_json()['leadler'][0]['kvkk_onay']


def test_kvkk_onaysiz_sohbetteki_telefon_kaydedilmez(client):
    yanit = client.post('/api/sohbet', json={'mesaj': 'ali veli 05551112233', 'oturum': OTURUM})
    assert yanit.get_json()['kaydedildi'] is False
    assert client.get('/api/leads').get_json()['adet'] == 0
    assert client.get('/api/sohbetler').get_json()['adet'] == 1     # sohbet yine kaydedilir


def test_kvkk_sayfasi_acilir(client):
    yanit = client.get('/kvkk')
    assert yanit.status_code == 200 and 'Aydınlatma' in yanit.get_data(as_text=True)


def test_site_ve_asistan_sayfalari(client):
    """Ana sayfa AST Digital sitesi; sohbet /widget iframe'i, tam sayfa asistan /asistan adresinde."""
    site = client.get('/')
    assert site.status_code == 200
    html = site.get_data(as_text=True)
    assert 'AST gele gele' in html and '/widget' in html and '/api/leads' in html
    assert client.get('/asistan').status_code == 200


def test_site_ic_sayfalari(client):
    """Her bölüm kendi adresinde açılır; hepsinde aynı sabit üst menü ve aktif link işareti var."""
    adresler = {'/araclar': 'Listing Üretici', '/nasil-calisir': 'Onay al', '/paketler': 'Premium',
                '/hakkimizda': 'Abdulsamed', '/sss': 'Satış garantisi', '/basvuru': 'id="form"',
                '/iletisim': 'id="iletisimForm"'}
    for adres, metin in adresler.items():
        cevap = client.get(adres)
        assert cevap.status_code == 200, adres
        html = cevap.get_data(as_text=True)
        assert metin in html, adres
        assert 'id="siteNav"' in html and 'aria-current="page"' in html, adres
    ana = client.get('/').get_data(as_text=True)
    assert 'id="siteNav"' in ana and 'href="/basvuru"' in ana and 'href="/paketler"' in ana
