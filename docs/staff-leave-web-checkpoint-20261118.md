# Web personel izin işlemleri

Aktif web personel sayfasında izin listesi, kişinin kendi adına talep açması ve yetkili yöneticinin gerekçeli değerlendirmesi yer alıyor. Form tarihlerden gün sayısını hesaplıyor. Değerlendirme ekranı talebin gerekçesini gösteriyor ve yorum alanını boş açıyor. Formlar sunucudaki kayıt listeden doğrulanınca kapanıyor. Sonucu belirsiz olan işlemler ikinci yazma göndermeden listeden tekrar kontrol ediliyor.

API, yeni izinlerde isteğe bağlı benzersiz kimliği kabul ediyor. Aynı kimlik ve aynı içerik tek kayıtla sonuçlanıyor. Farklı içerikle tekrar 409 dönüyor. Şubesiyle sınırlı yönetici, yalnızca yetkili şubelerindeki veya şubeye atanmamış kurum personelinin izinlerini görebiliyor ve değerlendirebiliyor. Platform yöneticisi seçtiği kurumda değerlendirme yapabiliyor.

Web 3/3 ve TypeScript kontrolü geçti. Geçici SQLite üzerinde eski Android sözleşmesi, kurum sınırı, şube sınırı ve kimlik tekrarı dahil 3/3 API testi geçti. PostgreSQL varyantları seçilmedi. API kanıtı yerelde `output/staff-leave-web-api-20261118.xml` altında.

Sıradaki iş Android izin formuna aynı istek kimliğini ve bağlantı kesintisi sonrası sonucu kontrol etme adımını eklemek.
