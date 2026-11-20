# 20 Kasım 2026 · Veli ekranında günlük karne

Web, bugünkü karneyi yalnız yanıtın öğrenci kimliği seçili çocukla eşleştiğinde gösteriyor. Çocuk değişiminde önceki durum isteği iptal ediliyor. Tarihli akış, öğrenci ve tarih eşleşmesini doğruluyor. Etkinlikler virgülle ayrılmış metin olarak gösteriliyor. Tarihli karne kartında kaydedilmiş yemek, uyku, duygu durumu ve öğretmen notu okunabiliyor.

Geçici SQLite testinde öğretmen gerçek API üzerinden karne oluşturdu. Veli aynı alanları yalnız bağlı çocuğun doğru tarihindeki akışta ve bugünkü durumda gördü. Farklı gün ve kardeş boş kaldı. Yabancı öğrenci isteği 403 döndü. On üç hedefli web testi, TypeScript, hedefli ESLint ve Ruff geçti. PostgreSQL kabulü açık.

Günlük karne ayrıntısı artık aynı zaman çizelgesinde açılıyor ve seçili çocuk ile günü koruyor. Tarih değiştiğinde eski ayrıntı kapanıyor. Altı hedefli web testi karne açma, tarih geçişi, önceki çocuk yanıtının elenmesi ve yoklama bağlantısını doğruladı. TypeScript ve hedefli ESLint geçti.

Yoklama bağlantısı günün çocuğunu ve tarihini sayfa geçişinde taşıyor. Çocuk, sunucudan gelen veli ilişki listesinde doğrulanıyor. Takvim yalnız yoklama okuma yetkisiyle çağrılıyor ve seçilen ay açıkça gösteriliyor. On yedi hedefli web testi ve bir geçici SQLite API testi geçti. TypeScript, hedefli ESLint ve Ruff geçti.

Web aylık takvimi sunucudan gelen günleri gösteriyor. Tarihli akıştan gelen gün seçili açılıyor. Giriş, çıkış ve not yalnız kayıtta varsa gösteriliyor. Kayıtsız günler belirtiliyor ve ay değişiminde eski ayrıntı kapanıyor. On yedi hedefli web testi, TypeScript ve hedefli ESLint geçti.
