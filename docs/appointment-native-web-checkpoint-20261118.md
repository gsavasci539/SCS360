# 18 Kasım 2026 randevu doğrulaması

Android randevu listesi, oluşturma ve durum değişiklikleri kurum ve şube kapsamındaki randevu API'sini kullanıyor. Web ve Android formunda öğrenci ve öğretmen seçenekleri sunucudan geliyor. Veli kendi öğrencisi için uygun saati seçiyor ve kendi randevusunu iptal edebiliyor. Web ve Android aynı okul saatini ve kalıcı işlem kimliğini gönderiyor. Oluşturma yanıtı kaybolduğunda yeni istek göndermeden mevcut kayıt kontrol ediliyor.

- Geçici SQLite ile 2 API testi geçti. Erişim kapsamı, saat, yinelenen isteğin tek kayıt üretmesi, veli onayının reddi ve iptalin kalıcılığı doğrulandı. PostgreSQL varyantları seçilmedi.
- Web'de 2 form testi ve TypeScript kontrolü geçti. Saat dilimi ve oluşturma yanıtı kaybolduğunda kayıt doğrulaması kapsandı.
- Android'de 1 istemci ve 1 Compose ekran testi geçti. Yerel HTTP testinde kayıp yanıtın sunucudan doğrulanması ve durum yazımı, yatay ekran testinde yüzde 150 yazı ölçeğiyle veli iptal denetimi kapsandı.

Sırada Android'de öğretmen uygunluk saatleri yönetiminin ve personel randevu silme işleminin web ile eşitlenmesi var. A26 fiziksel cihaz kabulü açık.
