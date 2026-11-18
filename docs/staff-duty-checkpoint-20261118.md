# Web ve Android nöbet oluşturma

Personel sayfasından nöbet oluştururken şube ve öğretmen seçenekleri API'den gelir. Seçenekler sayfalanır. Yalnızca kurum ve şube kapsamındaki aktif öğretmenler seçilebilir. Kurum genelinde görev yapan öğretmenler yetkili şubelerde seçilebilir. Form seçilen günü, nöbet yerini ve saatleri mevcut nöbet API'sine gönderir. Backend öğretmenin adını kayıtlı profilden alır. Kaydetme ve liste okuma doğrulandıktan sonra form kapanır.

İstemciler her kayıt için benzersiz istek kimliği gönderir. Aynı kimlik ve içerikle yapılan tekrar tek kayıt bırakır. Kimlik farklı içerikle kullanılırsa API 409 döndürür. Sonucu belirsiz olan istekte form içeriğini koruyan istemciler listeyi tekrar okur. Salt okuma yetkisiyle nöbet listesi görüntülenebilir.

- Android 7 istemci ve 4 arayüz testi geçti. Nöbet formu 640×360 dp yatay görünüm ve 1,5 yazı ölçeğiyle çalıştırıldı. API yanıtının kaybolduğu durumda yalnızca bir POST gönderildiği ayrı istemci testiyle doğrulandı.
- Web'de 2 hedefli arayüz testi ve TypeScript kontrolü geçti. Şubeye bağlı öğretmen seçimi, salt okuma yetkisi ve kaybolan yanıtın ikinci POST olmadan doğrulanması kapsandı.
- FastAPI geçici SQLite testi geçti. Kapsam dışı şubeler 404, salt okuma isteği 403 ve geçersiz öğretmen ya da saat aralığı 422 döndürdü. Yeniden gönderim sonrası tek nöbet kaydı vardı. PostgreSQL varyantı seçilmedi.

Test kanıtları yerelde `output/native-duty-target-20261118.log`, `output/native-duty-20261118-*.xml` ve `output/native-duty-api-final-20261118.xml` altında. Fiziksel A26 ve yayın APK'sı kabulü açık. Sıradaki iş web personel ekranındaki izin oluşturma ve gerekçeli değerlendirmeyi Android ile eşitlemek.
