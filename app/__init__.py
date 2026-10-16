from flask import Flask, jsonify
from flask_cors import CORS

from config import config
from app.database import init_db


def create_app(ortam='default', **ek_ayarlar):
    """Uygulama fabrikası. Sıra: ayarlar -> CORS -> veritabanı -> blueprint'ler.
    ek_ayarlar: testlerde geçici veritabanı gibi ayarları dışarıdan vermek için."""
    app = Flask(__name__)

    # 1) Ayarlar
    app.config.from_object(config[ortam])
    app.config.update(ek_ayarlar)

    # 2) CORS: API'yi yalnızca izin verilen alan adları (Wix sitemiz) çağırabilir
    CORS(app, resources={r'/api/*': {'origins': app.config['CORS_ORIGINS']}})

    # 3) Veritabanı: tablo yoksa oluştur
    with app.app_context():
        init_db(app)

    # 4) Rotalar
    from app.routes import sayfalar, api
    app.register_blueprint(sayfalar)
    app.register_blueprint(api)

    @app.after_request
    def onbellek_kapat(yanit):
        # HTML sayfaları ve API cevapları tarayıcıda saklanmasın: her push'tan sonra herkes yeni sürümü görsün
        if yanit.mimetype in ('text/html', 'application/json'):
            yanit.headers['Cache-Control'] = 'no-store'
        return yanit

    # Hata sayfaları da JSON ve Türkçe olsun (Wix tarafı her zaman aynı biçimi okur)
    @app.errorhandler(404)
    def bulunamadi(e):
        return jsonify(basari=False, hata='İstenen adres bulunamadı.'), 404

    @app.errorhandler(405)
    def yontem_yok(e):
        return jsonify(basari=False, hata='Bu adres bu istek türünü desteklemiyor.'), 405

    @app.errorhandler(500)
    def sunucu_hatasi(e):
        return jsonify(basari=False, hata='Beklenmeyen bir hata oluştu.'), 500

    # Render ve izleme araçları için sağlık kontrolü
    @app.route('/health')
    def health():
        return jsonify(durum='aktif')

    return app
