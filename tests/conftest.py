import pytest

from app import create_app
from app.services.ai_service import ai_service


@pytest.fixture(autouse=True)
def sinirlari_sifirla():
    """Her test temiz bir istek sayacıyla başlasın."""
    from app import routes
    routes._istekler.clear()


@pytest.fixture
def app(tmp_path, monkeypatch):
    """Her test için geçici bir veritabanıyla temiz bir uygulama. Gerçek smartlead.db'ye dokunmaz."""
    monkeypatch.setattr(ai_service, 'api_key', '')      # Groq'a gitme, demo modunda çalış
    monkeypatch.setattr(ai_service, 'gemini_key', '')   # yedek sağlayıcı da kapalı
    return create_app('development', DATABASE_URL=str(tmp_path / 'test.db'), ADMIN_KEY='')


@pytest.fixture
def client(app):
    return app.test_client()
