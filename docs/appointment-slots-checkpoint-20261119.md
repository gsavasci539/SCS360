# 19 Kasım 2026 randevu ve uygunluk saatleri

Öğretmen webde ve Android'de kendi uygunluk saatlerini listeleyebilir, ekleyebilir ve silebilir. Aynı saat aralığı tekrar gönderildiğinde mevcut kayıt dönüyor. Çakışan farklı aralık sunucudan 409 alıyor. Yönetim listesi, bir randevu tarafından ayrılmış saatleri de içeriyor. Yanıt kaybolduğunda iki istemci de yeni yazma isteği göndermeden sonucu listeden kontrol ediyor.

Android randevu detayında yetkili personel için onaylı silme var. Sunucu silinen kaydı listeden kaldırıyor. İlişki kapsamındaki veliler kendi randevularını iptal edebiliyor ve silme isteği 403 dönüyor.

- Geçici SQLite'ta 3 API testi geçti. PostgreSQL varyantları seçilmedi.
- Webde 3 hedefli test ve TypeScript kontrolü geçti.
- Android'de 1 yerel HTTP sözleşme testi ve 1 sentetik Compose testi geçti. Compose testi geniş yatay ekranda büyük yazıyla veli randevu kartını kapsıyor. Yeni uygunluk diyaloğunun fiziksel ekran kabulü açık.

Sırada web randevu durum işlemlerinin Android ile eşitlenmesi ve mevcut öğretmen notunun korunup sunucudan doğrulanması var. Yeni APK üretilmedi.
