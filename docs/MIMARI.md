# SmartLead AI · AST Digital
## Ortam Kurulumu ve Mimari Tasarım Envanteri

**Hazırlayan:** Abdulsamed Tanrıverdi · **Marka:** AST Digital · **Güncelleme:** 11 Ekim 2026
**Eğitim:** Python ile Ürün Geliştirme · **Revize:** salih@humanports.com
**Dayanak:** SmartLead AI Öğrenci Proje Yönergesi (Bölüm 1–7)

---

## 1. Proje Özeti

SmartLead AI, AST Digital'in web sitesinde (Wix Studio) çalışan **akıllı satış asistanıdır**. AST Digital, Etsy'de satış yapan ya da yapmak isteyen üreticilere (tişört, kupa, tumbler gibi baskılı ve kişiye özel ürün satıcıları) dijital araçlar ve birebir danışmanlık sunar.

Asistanın görevleri:

1. Ziyaretçinin Etsy, listing, mockup ve paketlerle ilgili sorularını marka diliyle yanıtlamak.
2. Ziyaretçiyi ihtiyacına uygun pakete (Freemium / Premium) yönlendirmek.
3. Ziyaretçinin iletişim bilgisini (lead) toplayıp veritabanına kaydetmek; işletme sahibinin bu kayıtları yönetim panelinde görmesini sağlamak.

Sistem iki arayüzden oluşur: ziyaretçinin sohbet edip bilgi bıraktığı **Karşılama Sayfası (B2C)** ve işletme sahibinin lead'leri gördüğü **Yönetim Paneli (B2B)**.

Yönergeye göre **mimari (klasörler, katmanlar, kurallar) sabittir; değişen tek şey konudur.** AST Digital'e özel olan kısımlar yalnızca `BUSINESS_CONTEXT` metni, `leads` tablosundaki tek ek sütun ve arayüz metinleridir.

---

## 2. Ortam Kurulumu (Yönerge Bölüm 4 — Oturum Öncesi Hazırlık)

### 2.1 Hazırım Kontrol Listesi

| # | Madde | Durum |
|---|---|---|
| 1 | `py -3.11 --version` → Python 3.11.9 | ✅ |
| 2 | `git --version` → git 2.53.0 | ✅ |
| 3 | GitHub + Render + Wix + Groq hesapları açık | ✅ |
| 4 | Groq API anahtarı (`gsk_...`) alındı ve `.env` içine kaydedildi | ✅ |
| 5 | Klasör iskeleti hazır (Bölüm 3) | ✅ |
| 6 | `venv` aktif, `pip install -r requirements.txt` hatasız tamamlandı | ✅ |
| 7 | Duman testi tarayıcıda çalıştı | ✅ |

### 2.2 Kurulum Adımları (Windows · PowerShell)

```powershell
# Proje klasörü: ...\Desktop\SMARTLEAD.AI  (TNC-PROGRAM deposunun dışında, ayrı git deposu)
mkdir app, app\templates, app\services
New-Item run.py, config.py, requirements.txt, .env, .gitignore, `
  app\__init__.py, app\database.py, app\routes.py, `
  app\templates\index.html, app\templates\dashboard.html, `
  app\services\__init__.py, app\services\ai_service.py

py -3.11 -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

**`requirements.txt`:** `flask` · `flask-cors` · `python-dotenv` · `requests` · `gunicorn`

> Bilgisayarda Python 3.14 de kurulu; bazı paketlerin henüz tam uyumlu olmaması ihtimaline karşı sanal ortam bilinçli olarak **Python 3.11** ile kuruldu.

### 2.3 Duman Testi

`hello.py` (proje dosyası değil, yalnızca ortam testi) çalıştırıldı; tarayıcıda "Ortam calisiyor!" yanıtı alındı. 5000 portu bilgisayarda başka bir uygulama tarafından kullanıldığı için test **5110** portunda yapıldı.

![Duman testi](duman-testi.png)

---

## 3. Hedef Mimari: Klasör Yapısı ve Sorumluluklar

```
SMARTLEAD.AI/
├── run.py                 ← Sunucuyu başlatan giriş noktası
├── config.py              ← Tüm ayarlar ve anahtarlar (.env okur)
├── requirements.txt       ← Bağımlılık listesi
├── .env                   ← Gizli anahtarlar (Git'e EKLENMEZ)
├── .env.example           ← .env'in anahtarsız örneği (Git'e eklenir)
├── .gitignore             ← venv/, .env, __pycache__/, *.db
├── README.md
├── docs/
│   ├── MIMARI.md          ← Bu belge
│   └── duman-testi.png
└── app/
    ├── __init__.py        ← Uygulama fabrikası: create_app() + /health
    ├── database.py        ← SQLite işlemleri (SQL SADECE burada)
    ├── routes.py          ← HTTP rotaları (sadece yönlendirme)
    ├── templates/
    │   ├── index.html     ← Karşılama sayfası (yerel test arayüzü)
    │   └── dashboard.html ← Yönetim paneli (yerel test arayüzü)
    └── services/
        ├── __init__.py
        └── ai_service.py  ← Yapay zekâ çağrıları (AI SADECE burada)
```

| Dosya | Tek sorumluluğu | Kesinlikle içermez |
|---|---|---|
| `config.py` | `.env`'den ayarları okuyup `Config` sınıflarında toplamak | SQL, AI çağrısı, rota |
| `app/database.py` | Bağlantı, tablo oluşturma, lead ekleme ve listeleme | AI çağrısı, HTTP |
| `app/services/ai_service.py` | Groq'a istek atıp asistanın yanıtını döndürmek | Flask, HTTP, SQL |
| `app/routes.py` | İsteği karşılamak, doğrulamak, ilgili katmanı çağırmak, JSON döndürmek | SQL metni, Groq isteği |
| `app/__init__.py` | Ayarları yüklemek, CORS'u açmak, veritabanını başlatmak, Blueprint'leri kaydetmek | İş mantığı |
| `run.py` | `create_app()` ile uygulamayı oluşturup çalıştırmak | Her şey dışında |

**Mimari sözleşme:** `database.py` dışında hiçbir yerde SQL yoktur. `ai_service.py` dışında hiçbir yerde yapay zekâ API çağrısı yoktur. `routes.py` yalnızca bu iki katmanın fonksiyonlarını çağırır.

---

## 4. Veri Akışı

```mermaid
sequenceDiagram
    participant Z as Ziyaretçi (Wix Karşılama Sayfası)
    participant W as Wix Velo (wix-fetch)
    participant R as routes.py (Render)
    participant AI as ai_service.py
    participant G as Groq API
    participant DB as database.py (SQLite)

    Z->>W: Soru yazar, "Sor"a basar
    W->>R: POST /api/sohbet {mesaj, gecmis}
    R->>AI: ai_service.yanit_uret(mesaj, gecmis)
    AI->>G: requests.post (system + geçmiş + yeni mesaj)
    G-->>AI: yanıt
    AI-->>R: metin
    R-->>W: {basari: true, cevap}
    W-->>Z: Asistanın yanıtı

    Z->>W: İsim, telefon, Etsy mağazası, "Kaydet"
    W->>R: POST /api/leads {isim, telefon, mesaj, etsy_magaza}
    R->>DB: lead_ekle(...)
    DB-->>R: tamam
    R-->>W: 201 {basari: true}

    Note over W,R: Yönetim Paneli: GET /api/leads → Repeater
```

---

## 5. Veri Modeli (Yönerge Modül B)

Tek tablo: **`leads`** — yönergedeki zorunlu şema + AST Digital'e özel **tek ek sütun**.

| Alan | Tür | Kural | Açıklama |
|---|---|---|---|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Kayıt numarası |
| `isim` | TEXT | NOT NULL | Ad soyad |
| `telefon` | TEXT | NOT NULL | WhatsApp numarası |
| `mesaj` | TEXT | opsiyonel | Ziyaretçinin notu |
| `etsy_magaza` | TEXT | opsiyonel — **AST Digital'e özel ek sütun** | Etsy mağaza bağlantısı (başvuru değerlendirmesi için) |
| `tarih` | TIMESTAMP | `DEFAULT CURRENT_TIMESTAMP` | Kayıt zamanı |

Yönergenin izin verdiği kişiselleştirme ("restoran için `kisi_sayisi`, emlak için `butce`") AST Digital'de `etsy_magaza` olarak uygulanır; fonksiyonlar ve form bu sütuna göre güncellenir.

---

## 6. Modüllerin Fonksiyonları (Yönerge Modül A–E)

Kod öğrenci tarafından yazılacaktır; aşağıdakiler her modülün **ne içermesi gerektiğinin** tanımıdır.

### Modül A — `config.py`
- Dosyanın başında `load_dotenv()`.
- `Config` sınıfı: `SECRET_KEY`, `DATABASE_URL` (varsayılan `smartlead.db`), `GROQ_API_KEY`, `AI_PROVIDER` (`groq`), `BUSINESS_CONTEXT`, `CORS_ORIGINS`.
- Her ayar `os.environ.get('ANAHTAR', 'varsayilan')` deseniyle okunur.
- `DevelopmentConfig` (`DEBUG = True`) ve `ProductionConfig` (`DEBUG = False`) + bunları seçen sözlük (`config = {'development': ..., 'production': ...}`).
- **Kontrol noktası:** `config.py` import edilip bir ayar yazdırılabiliyor ve `.env`'deki değer geliyor.
- ✅ 11 Ekim: tamamlandı ve test edildi. Not: `BUSINESS_CONTEXT` (chatbot'un sistem talimatı) ilk sürümdür; paket ayrıntıları ve SSS eklenerek geliştirilecek.

### Modül B — `app/database.py`

| Fonksiyon | Görevi |
|---|---|
| `get_db()` | Veritabanına bağlanır; `row_factory` ile satırlara sütun adıyla erişim sağlar |
| `init_db(app)` | `leads` tablosunu oluşturur (yoksa) |
| `lead_ekle(isim, telefon, mesaj, etsy_magaza=None)` | `?` yer tutucularıyla yeni kayıt ekler |
| `tum_leadler()` | Tüm kayıtları en yeniden eskiye getirir |

- ✅ 11 Ekim: tamamlandı. `test_modul_b.py` ile ayrı bir `test.db` üzerinde kayıt ekleme ve listeleme test edildi. SQL enjeksiyonu denemesi (`Robert'); DROP TABLE leads;--`) tablo silinmeden düz metin olarak kaydedildi; `?` yer tutucusu çalışıyor.

### Modül C — `app/services/ai_service.py`
- `AIService` sınıfı ve `yanit_uret(mesaj, gecmis)` metodu.
- `BUSINESS_CONTEXT`'i config'den okuyan yardımcı metot.
- Groq'a **`requests.post`** ile istek atan metot — model: **`openai/gpt-oss-20b`** (`GROQ_MODEL` ortam değişkeninden okunur).
- **Yönergeden bilinçli sapma:** Yönergedeki `llama-3.1-8b-instant` modeli Groq tarafından 16 Ağustos 2026'da kapatıldı (API 404 döndürüyor). Groq'un önerdiği yerine geçen model `openai/gpt-oss-20b` kullanıldı. Model adı koda gömülmek yerine config'e taşındı; ileride bir model daha kapanırsa yalnızca ortam değişkeni değişir. Kaynak: https://console.groq.com/docs/deprecations
- `messages` sırası: önce sistem talimatı (`role: system`), sonra geçmiş mesajlar, en sonda yeni kullanıcı mesajı.
- Anahtar yoksa çökmek yerine **"demo modu"** mesajı döndürür.
- Servise özel hata sınıfı `AIServiceError`; istek `try-except` ile sarılır, hata olursa `AIServiceError` fırlatılır.
- Dosya sonunda tek örnek: `ai_service = AIService()`.
- Bu dosya Flask, HTTP veya veritabanı kavramlarını bilmez; sağlayıcı değişikliği (Groq → Gemini) yalnızca burayı etkiler.
- ✅ 11 Ekim: tamamlandı. `test_modul_c.py` ile 4 test: gerçek soru, konuşma geçmişini hatırlama, anahtarsız demo modu, yanlış anahtarda `AIServiceError` (401) yakalama.
- **Test sırasında bulunan sorun ve çözümü:** İlk sürümde model olmayan bir üyelik linki uydurdu, pakette olmayan hizmetler (stok yönetimi, otomatik fiyat güncelleme) vaat etti ve Markdown kullandı. Çözüm: `BUSINESS_CONTEXT`'e gerçek paket içerikleri, izin verilen tek link/e-posta ve kurallar (uydurma yok, satış garantisi yok, düz metin, kısa cevap) eklendi; ayrıca cevaplar `_temizle()` ile Markdown yıldızlarından arındırılıyor (talimata güvenmek yerine kodda garanti).

### Modül D — `app/routes.py`
- İki Blueprint: **sayfalar** (`/`, `/dashboard`) ve **API** (`url_prefix='/api'`).
- Her API uç noktası `basari` alanı içeren JSON döndürür.
- Durum kodları: eksik veri **400**, AI hatası **503**, yeni kayıt **201**.
- `AIServiceError` yakalanıp kibar JSON hata döndürülür.

### Modül E — `app/__init__.py` + `run.py`
- `create_app()` sırası: ayarları yükle → CORS aç → `with app.app_context(): init_db(app)` → Blueprint'leri kaydet → uygulamayı döndür.
- `/health` uç noktası (canlılık kontrolü).
- `run.py`: `app = create_app()` · `if __name__ == '__main__': app.run(port=5110, debug=True)` · Render'da `gunicorn run:app`.

---

## 7. API Uç Noktaları (Yönerge Modül D)

| Metot + Yol | Görevi | Çağırdığı katman | Girdi | Başarılı çıktı |
|---|---|---|---|---|
| GET `/` | Karşılama sayfası | `render_template` | — | `index.html` |
| GET `/dashboard` | Yönetim paneli | `render_template` | — | `dashboard.html` |
| POST `/api/sohbet` | AI'a mesaj iletir | `ai_service.yanit_uret()` | `{"mesaj": str, "gecmis": [...]}` | `{"basari": true, "cevap": str}` |
| POST `/api/leads` | Yeni lead kaydeder | `database.lead_ekle()` | `{"isim", "telefon", "mesaj", "etsy_magaza"}` | 201 `{"basari": true}` |
| GET `/api/leads` | Tüm lead'leri getirir | `database.tum_leadler()` | — | `{"basari": true, "leadler": [...]}` |
| GET `/health` | Canlılık kontrolü | — | — | `{"durum": "aktif"}` |

**Hata formatı (tüm API uç noktalarında aynı):**

```json
{ "basari": false, "hata": "Kullanıcıya gösterilebilecek kısa açıklama" }
```

**Alan adları sözleşmesi (Yönerge Modül G — "Aynı Kelimeler"):** sohbet için `mesaj` / `cevap`, kayıt için `isim` / `telefon` / `mesaj` / `etsy_magaza`, liste için `leadler`. Wix tarafı bu adları birebir kullanır.

---

## 8. Asistanın Kişiliği: `BUSINESS_CONTEXT`

Kodun konuya özel tek parçası budur.

```python
BUSINESS_CONTEXT = """Sen AST Digital'in asistanisin. AST Digital, Etsy'de satis yapan
ya da yapmak isteyen ureticilere (tisort, kupa, tumbler gibi baskili ve kisiye ozel
urun saticilari) dijital araclar ve birebir danismanlik sunar.

Paketler:
- Freemium (ucretsiz): gunde 5 listing + mockup, ticket ile destek, haftalik tanitim yayini.
- Premium (aylik 39 $, 7 gun ucretsiz deneme): gunde 20 listing + mockup,
  gunde 5 otomatik Pinterest pini, mesai saatlerinde WhatsApp'tan birebir danismanlik,
  haftalik soru-cevap yayini.
Uyelik basvuruyla acilir: kisa form doldurulur, Etsy magazasi incelenir, onaylanan
saticiya hesap acilir. Premium basvurularinda 20 dakikalik tanisma gorusmesi yapilir.

Kurallar:
- Turkce, samimi, net ve cesaret veren bir dille konus. Kisa yanit ver (en fazla 4-5 cumle).
- Kesin satis vaat etme; yolu kisaltmayi vaat et.
- Bilmedigin bir konuda uydurma; "Bunu ekibimiz netlestirsin" de ve iletisim bilgisi iste.
- Konusma ilerledikce uygun paketi oner ve isim, telefon ve Etsy magaza
  baglantisini birakmasini nazikce iste.
- Etsy, e-ticaret ve AST Digital disindaki konulara girme."""
```

---

## 9. Güvenlik (Değerlendirme %10)

| Konu | Uygulama |
|---|---|
| SQL enjeksiyonu | Tüm sorgularda `?` yer tutucusu; kullanıcı verisi asla SQL metnine eklenmez. |
| Gizli anahtarlar | `GROQ_API_KEY`, `SECRET_KEY` yalnızca `.env`'de (yerel) ve Render "Environment" ayarlarında. `.env` `.gitignore`'da; depoda yalnızca `.env.example` bulunur. |
| CORS | `CORS_ORIGINS` ile yalnızca `https://astdigital.wixstudio.com` ve Wix editör/önizleme alan adlarına izin verilir; `*` kullanılmaz. |
| Girdi doğrulama | Boş mesaj, aşırı uzun mesaj (ör. 1000 karakter üstü), isim veya telefonu eksik lead → 400. |
| KVKK | Karşılama sayfasındaki formda KVKK aydınlatma metnine bağlantı ve onay kutusu bulunur (site KVKK politikasıyla uyumlu). |
| Lead listesi (ek, Belgrad aşaması) | `GET /api/leads` herkese açık kalmamalı; Wix tarafında Velo backend + Secrets Manager'da tutulan bir anahtarla çağrılması planlanır. |

---

## 10. Hata Yönetimi (Değerlendirme %10)

- Veritabanı ve Groq çağrıları `try-except` ile sarılır.
- Kullanıcıya teknik ayrıntı gösterilmez; yalnızca `{"basari": false, "hata": "..."}` döner.
- Hatanın ayrıntısı sunucu loguna yazılır (Render "Logs" ekranından izlenir).
- Groq anahtarı yoksa asistan **demo modu** yanıtı verir; Groq'a ulaşılamazsa 503 ile kibar bir mesaj döner: *"Şu an yanıt veremiyorum, bilgilerini bırakırsan ekibimiz WhatsApp'tan dönsün."*

---

## 11. Wix Bağlantısı (Yönerge Modül G)

| Arayüz | UX deseni | Bileşenler (hepsine ID verilir) | Backend |
|---|---|---|---|
| **Karşılama Sayfası (B2C)** | **Z-Pattern:** logo sol üst, sohbet sağ, form alt bölge. Sohbet kartında **Glassmorphism** (buzlu cam) | Mesaj girişi, "Sor" butonu, yanıt alanı; isim, telefon, Etsy mağazası girişleri, KVKK onayı, "Kaydet" butonu | `wix-fetch` → `POST /api/sohbet`, `POST /api/leads` |
| **Yönetim Paneli (B2B)** | **F-Pattern:** en önemli kolon (isim) solda | Repeater (isim · telefon · Etsy mağazası · tarih) | `wix-fetch` → `GET /api/leads`; her objeye `_id` eklenir, satırda `$item` kullanılır |

Ders kuralları gereği Wix "Form" öğesi kullanılmaz; tüm girişler manuel Input bileşenleridir.

---

## 12. Yayınlama (Yönerge Modül H)

1. **GitHub:** ayrı, public depo — **github.com/Allahverdyy/smartlead-ai**. `.env` ve `venv/` yüklenmez. ✅
2. **Render → New Web Service:** depo bağlanır.
   - Build: `pip install -r requirements.txt`
   - Start: `gunicorn run:app`
   - Environment: `GROQ_API_KEY`, `SECRET_KEY`, `CORS_ORIGINS`
3. `https://<servis>.onrender.com/health` → `{"durum": "aktif"}` dönünce Wix kodundaki API adresi Render adresiyle güncellenir.

**Bilinen kısıt:** Render'ın ücretsiz planında disk kalıcı değildir; yeniden yayında SQLite dosyası sıfırlanabilir ve servis 15 dakika boşta kalınca uykuya geçer. MVP ve jüri sunumu için kabul edilebilir; kalıcı kullanımda PostgreSQL'e geçilir. Mimari buna hazırdır: yalnızca `database.py` değişir.

---

## 13. Durum ve Zaman Çizelgesi (Yönerge Bölüm 6)

| Aşama | Modül | Durum |
|---|---|---|
| Ortam + hesaplar + iskelet + duman testi | Bölüm 4 | ✅ 7 Ekim |
| Mimari tasarım (bu belge) | — | ✅ 11 Ekim |
| GitHub deposu + iskelet commit | Modül H (1–2) | ✅ 7 Ekim |
| Yapılandırma | Modül A | ✅ 11 Ekim |
| Veritabanı | Modül B | ✅ 11 Ekim |
| Yapay zekâ servisi | Modül C | ✅ 11 Ekim |
| Rotalar · Fabrika + giriş | Modül D–E | ⬜ Belgrad öncesi |
| Çalıştırma + test | Modül F | ⬜ |
| Wix Karşılama Sayfası + Yönetim Paneli | Modül G | ⬜ Belgrad |
| Render'da canlı yayın | Modül H (3–5) | ⬜ Belgrad öncesi |
| README son hali, sunum/demo | Teslim | ⬜ 27 Ekim jüri |

---

*Bu belgenin yapısı ve taslak metni hazırlanırken yapay zekâ desteği (Claude) kullanılmıştır; mimari kararlar öğrenci tarafından sahiplenilmiş, kod öğrenci tarafından yazılacak ve sözlü olarak açıklanabilecek şekilde gözden geçirilecektir.*
