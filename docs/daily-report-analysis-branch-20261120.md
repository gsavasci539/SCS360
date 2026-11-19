# 20 Kasım 2026 · Karne analizi şube filtresi

Karne analizi isteğe bağlı `branch_id` alıyor. Sunucu şubenin kurum ve erişim kapsamını doğruluyor, ardından karne sorgusuna şube koşulunu ekliyor. Yetki kapsamı dışındaki şubeler 404 dönüyor. Yanıttaki `branch_id`, uygulamanın hangi şubenin özetini aldığını doğrulamasını sağlıyor. Şube seçilmediğinde özet, kullanıcının yetkili tüm kayıtlarını kapsıyor.

Geçici SQLite üzerinde üç API testi geçti. Öğretmenin yetkili iki şubesi ile tek şube seçimi, atama kapsamı, yabancı kurum ve yetkisiz şube reddi doğrulandı. PostgreSQL kabulü açık.
