from flask import Flask
from config import config
from app.database import init_db, lead_ekle, tum_leadler

app = Flask(__name__)
app.config.from_object(config['development'])
app.config['DATABASE_URL'] = 'test.db'   # gerçek veritabanına dokunmasın

with app.app_context():
    init_db(app)
    yeni_id = lead_ekle('Elif Test', '05551234567', 'Fiyat bilgisi istiyorum', 'ElifTeeShop')
    print('Eklenen kayit id:', yeni_id)

    # Guvenlik testi: SQL enjeksiyonu denemesi duz metin olarak kaydedilmeli
    lead_ekle("Robert'); DROP TABLE leads;--", '0000', 'enjeksiyon denemesi')

    for lead in tum_leadler():
        print(lead)