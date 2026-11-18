# Randevularım API adresi

Öğretmenin randevu listesi için kullanılan `GET /api/appointments/my-appointments` adresi artık randevu kimliği alan detay adresinden önce tanımlanıyor. Kendi kayıtları, istenen tarih aralığı ve okulun saat dilimi mevcut kurallarla görüntüleniyor.

Geçici SQLite API testi 1/1 geçti. Başka personelin aynı günkü kaydı listede görünmedi ve mevcut detay adresi çalıştı. PostgreSQL varyantı seçilmedi. Kanıt yerelde `output/my-appointments-route-20261118.xml` altında.

Web randevu formu girilen tarihi ve saati tarayıcının saat dilimine çevirmeden API'ye gönderiyor. API bu değeri okulun saat diliminde yorumluyor. Tarayıcı UTC ile çalıştırıldığında formun girilen saati aynen taşıdığı hedefli arayüz testinde doğrulandı.

Sıradaki iş Android randevu ekranındaki yerel kayıt, durum ve bildirim işlemlerini gerçek liste, öğrenci, öğretmen ve saat seçimiyle API'ye bağlamak.
