import sqlite3
from flask import current_app, g


def get_db():
    """Bu isteğe ait veritabanı bağlantısını verir; yoksa açar."""
    if 'db' not in g:
        g.db = sqlite3.connect(current_app.config['DATABASE_URL'])
        g.db.row_factory = sqlite3.Row   # satırlara sütun adıyla erişim: satir['isim']
    return g.db


def close_db(e=None):
    """İstek bitince bağlantıyı kapatır."""
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db(app):
    """leads tablosunu oluşturur (yoksa). create_app() içinde, app_context altında çağrılır."""
    app.teardown_appcontext(close_db)
    db = get_db()
    db.execute("""
        CREATE TABLE IF NOT EXISTS leads (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            isim        TEXT NOT NULL,
            telefon     TEXT NOT NULL,
            mesaj       TEXT,
            etsy_magaza TEXT,
            eposta      TEXT,
            tarih       TEXT DEFAULT (datetime('now', 'localtime'))
        )
    """)
    # Eski veritabanında e-posta sütunu yoksa ekle (telefonsuz lead'de telefon '' olarak saklanır)
    sutunlar = [satir[1] for satir in db.execute("PRAGMA table_info(leads)").fetchall()]
    if 'eposta' not in sutunlar:
        db.execute("ALTER TABLE leads ADD COLUMN eposta TEXT")
    # Form doldurulmasa da her sohbet kaydedilir (oturum = sayfa açılışında üretilen rastgele kimlik)
    db.execute("""
        CREATE TABLE IF NOT EXISTS sohbetler (
            oturum       TEXT PRIMARY KEY,
            dokum        TEXT NOT NULL,
            mesaj_sayisi INTEGER NOT NULL,
            lead_id      INTEGER,
            z_isim       TEXT,
            z_eposta     TEXT,
            ilk_tarih    TEXT DEFAULT (datetime('now', 'localtime')),
            son_tarih    TEXT DEFAULT (datetime('now', 'localtime'))
        )
    """)
    s_sutunlar = [satir[1] for satir in db.execute("PRAGMA table_info(sohbetler)").fetchall()]
    for sutun in ('z_isim', 'z_eposta'):                 # sabit adlar, kullanıcı girdisi değil
        if sutun not in s_sutunlar:
            db.execute(f"ALTER TABLE sohbetler ADD COLUMN {sutun} TEXT")
    db.commit()


def lead_ekle(isim, telefon, mesaj, etsy_magaza=None, eposta=None):
    """Yeni lead kaydeder, oluşan kaydın id'sini döndürür."""
    db = get_db()
    imlec = db.execute(
        "INSERT INTO leads (isim, telefon, mesaj, etsy_magaza, eposta) VALUES (?, ?, ?, ?, ?)",
        (isim, telefon or '', mesaj, etsy_magaza, eposta)
    )
    db.commit()
    return imlec.lastrowid


def tum_leadler():
    """Tüm lead'leri en yeniden eskiye, JSON'a hazır sözlük listesi olarak döndürür."""
    db = get_db()
    satirlar = db.execute("SELECT * FROM leads ORDER BY id DESC").fetchall()
    return [dict(satir) for satir in satirlar]


def sohbet_kaydet(oturum, dokum, mesaj_sayisi, isim=None, eposta=None):
    """Sohbeti ekler; aynı oturum zaten varsa dökümü ve son tarihi günceller.
    isim/eposta: ziyaretçinin girişte verdiği bilgi (aynı tarayıcıdan açılan yeni sohbetlerde de görünsün diye)."""
    db = get_db()
    db.execute("""
        INSERT INTO sohbetler (oturum, dokum, mesaj_sayisi, z_isim, z_eposta) VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(oturum) DO UPDATE SET dokum = excluded.dokum, mesaj_sayisi = excluded.mesaj_sayisi,
                                          z_isim = COALESCE(excluded.z_isim, z_isim),
                                          z_eposta = COALESCE(excluded.z_eposta, z_eposta),
                                          son_tarih = datetime('now', 'localtime')
    """, (oturum, dokum, mesaj_sayisi, isim, eposta))
    db.commit()


def sohbet_olustur(oturum):
    """Boş sohbet kaydı açar; varsa dokunmaz."""
    db = get_db()
    db.execute("INSERT OR IGNORE INTO sohbetler (oturum, dokum, mesaj_sayisi) VALUES (?, '', 0)", (oturum,))
    db.commit()


def sohbet_lead_id(oturum):
    """Bu oturumdan daha önce lead oluştuysa id'sini, yoksa None döndürür."""
    satir = get_db().execute("SELECT lead_id FROM sohbetler WHERE oturum = ?", (oturum,)).fetchone()
    return satir['lead_id'] if satir else None


def sohbete_lead_bagla(oturum, lead_id):
    db = get_db()
    db.execute("UPDATE sohbetler SET lead_id = ? WHERE oturum = ?", (lead_id, oturum))
    db.commit()


def lead_mesajini_guncelle(lead_id, mesaj):
    """Lead oluştuktan sonra sohbet devam ederse, lead'deki döküm de güncel kalsın."""
    db = get_db()
    db.execute("UPDATE leads SET mesaj = ? WHERE id = ?", (mesaj, lead_id))
    db.commit()


def lead_tamamla(lead_id, telefon=None, eposta=None, etsy_magaza=None):
    """Mevcut lead'in boş alanlarını doldurur (ör. girişte e-posta verdi, sonra telefon yazdı)."""
    db = get_db()
    db.execute("""
        UPDATE leads SET telefon = CASE WHEN ? <> '' THEN ? ELSE telefon END,
                         eposta = COALESCE(?, eposta), etsy_magaza = COALESCE(?, etsy_magaza)
        WHERE id = ?
    """, (telefon or '', telefon or '', eposta, etsy_magaza, lead_id))
    db.commit()


def lead_telefonu(lead_id):
    satir = get_db().execute("SELECT telefon FROM leads WHERE id = ?", (lead_id,)).fetchone()
    return satir['telefon'] if satir else ''


def sohbeti_sil(oturum):
    """Ziyaretçinin isteğiyle sohbet metnini siler. Bıraktığı iletişim bilgisi (lead) kalır, sohbet metni boşalır."""
    db = get_db()
    satir = db.execute("SELECT lead_id FROM sohbetler WHERE oturum = ?", (oturum,)).fetchone()
    if satir and satir['lead_id']:
        db.execute("UPDATE leads SET mesaj = '' WHERE id = ?", (satir['lead_id'],))
    db.execute("DELETE FROM sohbetler WHERE oturum = ?", (oturum,))
    db.commit()


def tum_sohbetler():
    """Tüm sohbetler, son konuşulandan eskiye; lead'e dönüştüyse isim ve telefonuyla."""
    satirlar = get_db().execute("""
        SELECT s.*, l.isim, l.telefon, l.eposta FROM sohbetler s
        LEFT JOIN leads l ON l.id = s.lead_id
        ORDER BY s.son_tarih DESC
    """).fetchall()
    return [dict(satir) for satir in satirlar]
