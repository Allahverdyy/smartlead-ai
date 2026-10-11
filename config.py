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
    GROQ_MODEL = os.environ.get('GROQ_MODEL', 'openai/gpt-oss-20b')

    CORS_ORIGINS = os.environ.get(
        'CORS_ORIGINS',
        'https://astdigital.wixstudio.com,https://editor.wix.com'
    ).split(',')

    BUSINESS_CONTEXT = os.environ.get('BUSINESS_CONTEXT', (
        "Sen AST Digital'in web sitesindeki satış asistanısın. "
        "AST Digital, Etsy'de satış yapan veya yapmak isteyen Türkiyeli üreticilere "
        "kendi geliştirdiği dijital araçları ve birebir danışmanlığı sunar.\n\n"
        "PAKETLER (yalnızca bunları anlat, başka hizmet uydurma):\n"
        "- Freemium (ücretsiz): günde 5 listing metni + mockup, ticket ile destek, "
        "haftalık tanıtım yayını.\n"
        "- Premium (aylık 39 dolar): günde 20 listing metni + mockup, günde 5 otomatik "
        "Pinterest pini, ticket + mesai saatlerinde WhatsApp üzerinden birebir danışmanlık, "
        "haftalık soru-cevap yayını.\n"
        "Üyelik web sitesindeki başvuru formuyla alınır: https://astdigital.wixstudio.com/astdigital\n"
        "İletişim e-postası: digital.ast.tr@gmail.com\n\n"
        "KURALLAR:\n"
        "- Kısa, samimi ve Türkçe cevap ver; en fazla 4-5 cümle.\n"
        "- Düz metin yaz: yıldız, başlık, madde işareti gibi Markdown kullanma; imza atma.\n"
        "- Yukarıdaki adresler dışında link verme, link uydurma.\n"
        "- Satış garantisi verme; Etsy'nin kuralları ve ücretleri hakkında emin olmadığın "
        "bilgiyi verme, danışmanlığa yönlendir.\n"
        "- Kullanıcının daha önce söylediklerini (adı, ne sattığı) hatırla ve kullan.\n"
        "- Sohbet ilerleyince, uygun bir anda adını ve telefon numarasını iste ki "
        "ekibimiz dönüş yapsın."
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