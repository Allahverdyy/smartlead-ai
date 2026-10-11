import os
from dotenv import load_dotenv

# .env dosyasındaki değerleri ortam değişkeni olarak yükler
load_dotenv()


class Config:
    """Tüm ortamlarda ortak olan ayarlar."""

    SECRET_KEY = os.environ.get('SECRET_KEY', 'gelistirme-anahtari')
    DATABASE_URL = os.environ.get('DATABASE_URL', 'smartlead.db')

    GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')
    AI_PROVIDER = os.environ.get('AI_PROVIDER', 'groq')

    CORS_ORIGINS = os.environ.get(
        'CORS_ORIGINS',
        'https://astdigital.wixstudio.com,https://editor.wix.com'
    ).split(',')

    BUSINESS_CONTEXT = os.environ.get('BUSINESS_CONTEXT', (
        "Sen AST Digital'in satış asistanısın. AST Digital, Etsy satıcılarına "
        "dijital araçlar ve birebir danışmanlık sunan bir girişimdir. "
        "Hedef kitle: print-on-demand ve kişiselleştirilmiş ürün satan Etsy satıcıları. "
        "Premium üyelik aylık 39 dolardır ve web sitesindeki başvuru formuyla alınır. "
        "Kısa, samimi ve Türkçe cevap ver. Bilmediğin bir konuda uydurma; "
        "kullanıcıyı başvuru formuna veya digital.ast.tr@gmail.com adresine yönlendir. "
        "Uygun anda kullanıcının adını ve telefonunu iste."
    ))


class DevelopmentConfig(Config):
    """Yerelde (kendi bilgisayarında) çalışırken."""
    DEBUG = True


class ProductionConfig(Config):
    """Render'da canlı yayında."""
    DEBUG = False


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig,
}