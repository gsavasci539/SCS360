# 19 Kasım 2026 · Günlük karnede eşzamanlı yazma koruması

Günlük karne API’si kayıt sürümünü `version` alanında dönüyor. Web düzenleme ve silme sırasında ekrandaki sürümü `If-Match` başlığında gönderiyor. Sürüm artık güncel değilse API HTTP 412 dönüyor ve güncel içerik korunuyor. Web taslağı açık kalıyor. Öğrenci, tarih ve kayıtlı Android gözlemleri web düzenleme formunda korunuyor.

Veritabanı yazmadan önceki koşulu ve kaydın güncelliğini aynı SQL ifadesinde kontrol ediyor. Eski istemciler başlıksız istek gönderebiliyor. Bu isteklerde de API kendi okuması ile yazması arasındaki değişikliği kontrol ediyor. Yeni web ve Android yazma akışları sunucudan alınan sürümü gerektiriyor.

Üç geçici SQLite API testi ve iki web testi geçti. Yarış testinde ilk istek kaydı okuduktan sonra ikinci istek güncel gözlemi yazdı. İlk isteğin yazması ve sonraki eski sürümlü silme reddedildi. TypeScript ve hedefli Ruff kontrolleri geçti. PostgreSQL kabulü açık.
