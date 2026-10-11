# SmartLead AI · AST Digital

AST Digital'in web sitesinde çalışan **akıllı satış asistanı**: Etsy satıcılarının sorularını yanıtlar, onları uygun pakete yönlendirir ve iletişim bilgilerini (lead) toplar. İşletme sahibi bu kayıtları yönetim panelinde görür.

**Teknolojiler:** Python 3.11 · Flask · SQLite · Groq (openai/gpt-oss-20b) · Wix Velo · Render

> TNC Group · Proje Uzmanı Yetiştirme Programı — Python ile Ürün Geliştirme projesi.
> Mimari tasarım ve ortam kurulumu: **[docs/MIMARI.md](docs/MIMARI.md)**

## Durum

- ✅ Ortam kurulumu ve duman testi
- ✅ Mimari tasarım
- ✅ Backend modülleri (config, database, ai_service, routes, create_app)
- ✅ 22 otomatik test (`python -m pytest -v`)
- ⬜ Wix arayüzleri ve Render yayını

## Yerelde çalıştırma

```powershell
py -3.11 -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env      # ardından GROQ_API_KEY değerini doldurun
python run.py               # http://localhost:5110
python -m pytest -v         # testler
```

## Klasör yapısı

```
run.py · config.py · requirements.txt · .env.example
app/  __init__.py · database.py · routes.py · templates/ · services/ai_service.py
docs/ MIMARI.md · duman-testi.png
```

`database.py` dışında SQL, `ai_service.py` dışında yapay zekâ çağrısı yoktur; `routes.py` yalnızca bu iki katmanı çağırır.
