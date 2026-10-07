# hello.py — sadece ortam testi (proje dosyası DEĞİL)
from flask import Flask #Venv'e kurduğumuz Flask kütüphanesinden ana sınıfı alır.

app = Flask(__name__)  #Web uygulamasını oluşturur.

@app.route('/') #Sitenin ana adresine (/) bir istek gelince altındaki fonksiyonun çalışacağını söyler.
def merhaba():
    return 'Ortam calisiyor!'  #Tarayıcıya gönderilecek cevap.

if __name__ == '__main__': #Dosya doğrudan çalıştırıldığında sunucuyu başlatır.
    app.run(port=5110) #Sunucuyu başlatır ve 5110 portunu dinler. (localhost:5110)