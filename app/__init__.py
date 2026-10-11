from flask import Flask, jsonify
from flask_cors import CORS

from config import config
from app.database import init_db


def create_app(ortam='default'):
    """Uygulama fabrikası. Sıra: ayarlar -> CORS -> veritabanı -> blueprint'ler."""
    app = Flask(__name__)

    # 1) Ayarlar
    app.config.from_object(config[ortam])

    # 2) CORS: API'yi yalnızca izin verilen alan adları (Wix sitemiz) çağırabilir
    CORS(app, resources={r'/api/*': {'origins': app.config['CORS_ORIGINS']}})

    # 3) Veritabanı: tablo yoksa oluştur
    with app.app_context():
        init_db(app)

    # 4) Rotalar
    from app.routes import sayfalar, api
    app.register_blueprint(sayfalar)
    app.register_blueprint(api)

    # Render ve izleme araçları için sağlık kontrolü
    @app.route('/health')
    def health():
        return jsonify(durum='aktif')

    return app
