# 19 Kasım 2026 mesaj alıcısı ve gönderim doğrulaması

Alıcı dizini aktif, aynı kuruma bağlı hesapları sayfalar. Veli kendi öğrencisine atanmış öğretmenleri, öğretmen yetkili olduğu öğrencilerin velilerini görür. Kurum geneli yetkili personel kurum içinde arar. Şube kapsamlı personel seçili veya atanmış şubelerdeki yetkili kişileri görür. Alıcı listesi ve gönderim aynı denetimi kullanır.

İstemci `POST /api/messages/send` isteğinde isteğe bağlı `request_id` gönderir. Aynı kimlik ve içerikle tekrar tek kayıt döndürür. Aynı kimlik farklı içerikle kullanılırsa 409 döner. Yanıt kaybında gönderen, `GET /api/messages/sent/{request_id}` ile kalıcı kaydı kontrol edebilir. Yanıt, kaydın oluşturulduğunu bildirir.

Geçici SQLite'ta iki API testi geçti. Kapsam dışı kurum ve şube, ilişkisiz alıcı, dizin sayfalaması, eşzamanlı tekrar, farklı içerikle çakışma ve diğer katılımcının gönderim sonucuna erişim reddi kapsandı. PostgreSQL varyantı bu kontrolde çalıştırılmadı.

Sırada sohbet listesi ve geçmişin kurum/şube kapsamı, ardından Kotlin ekranının liste, geçmiş, alıcı seçimi ve gönderim doğrulamasına bağlanması var.
