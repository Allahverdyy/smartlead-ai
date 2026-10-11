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
            tarih       TEXT DEFAULT (datetime('now', 'localtime'))
        )
    """)
    db.commit()


def lead_ekle(isim, telefon, mesaj, etsy_magaza=None):
    """Yeni lead kaydeder, oluşan kaydın id'sini döndürür."""
    db = get_db()
    imlec = db.execute(
        "INSERT INTO leads (isim, telefon, mesaj, etsy_magaza) VALUES (?, ?, ?, ?)",
        (isim, telefon, mesaj, etsy_magaza)
    )
    db.commit()
    return imlec.lastrowid


def tum_leadler():
    """Tüm lead'leri en yeniden eskiye, JSON'a hazır sözlük listesi olarak döndürür."""
    db = get_db()
    satirlar = db.execute("SELECT * FROM leads ORDER BY id DESC").fetchall()
    return [dict(satir) for satir in satirlar]