# 19 Kasım 2026 randevu durumu ve öğretmen notu

Web ve Android aynı PATCH adresini kullanır. Durum değişikliği not alanını göndermediğinde sunucu mevcut notu korur. Eski PUT istemcilerinde de alanın bulunmaması notu korur. Yetkili personel notu düzenleyebilir veya açıkça temizleyebilir. İlişki kapsamındaki velinin iptal çağrısı öğretmen notunu değiştiremez.

Web durum ve not değişikliklerini kayıt sunucudan tekrar okunduktan sonra doğrular. Yazma yanıtı kaybolduğunda sonuç düğmesi yalnızca GET çağırır. Web ayrıntısındaki onay, red ve tamamlama işlemleri Android'le aynı durumlarda sunulur.

- Geçici SQLite'ta 2 API testi geçti. PostgreSQL varyantları seçilmedi.
- Webde 4 hedefli test ve TypeScript kontrolü geçti.
- Android'de 1 yerel HTTP sözleşme testi geçti. Fiziksel cihaz / yeni APK kabulü bu kontrolde yapılmadı.

Sırada Android genel mesajlaşmanın sohbet listesi, gerçek alıcı seçimi, sunucudan okuma ve kayıt doğrulamasını web ile eşitlemek var. Mevcut yerel örnek alıcı ve otomatik yanıtlar gerçek gönderim kabulü değildir.
