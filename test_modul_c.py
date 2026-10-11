from app.services.ai_service import ai_service, AIService, AIServiceError

print('--- Test 1: Gercek soru ---')
print(ai_service.yanit_uret('Merhaba, Etsy magazam var ama satis yapamiyorum. Bana nasil yardimci olursunuz?'))

print('\n--- Test 2: Gecmisi hatirliyor mu? ---')
gecmis = [
    {'role': 'user', 'content': 'Benim adim Mehmet, sublimasyonla kupa satiyorum.'},
    {'role': 'assistant', 'content': 'Merhaba Mehmet, memnun oldum!'},
]
print(ai_service.yanit_uret('Adimi ve ne sattigimi hatirliyor musun?', gecmis))

print('\n--- Test 3: Anahtar yoksa demo modu ---')
print(AIService(api_key='').yanit_uret('Fiyat nedir?'))

print('\n--- Test 4: Yanlis anahtar -> AIServiceError ---')
try:
    AIService(api_key='gsk_yanlis').yanit_uret('Merhaba')
except AIServiceError as hata:
    print('Hata yakalandi:', hata)