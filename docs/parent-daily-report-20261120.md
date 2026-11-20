# 20 Kasım 2026 · Veli ekranında günlük karne

Web, bugünkü karneyi yalnız yanıtın öğrenci kimliği seçili çocukla eşleştiğinde gösteriyor. Çocuk değişiminde önceki durum isteği iptal ediliyor. Tarihli akış, öğrenci ve tarih eşleşmesini doğruluyor. Etkinlikler virgülle ayrılmış metin olarak gösteriliyor. Tarihli karne kartında kaydedilmiş yemek, uyku, duygu durumu ve öğretmen notu okunabiliyor.

Geçici SQLite testinde öğretmen gerçek API üzerinden karne oluşturdu. Veli aynı alanları yalnız bağlı çocuğun doğru tarihindeki akışta ve bugünkü durumda gördü. Farklı gün ve kardeş boş kaldı. Yabancı öğrenci isteği 403 döndü. On üç hedefli web testi, TypeScript, hedefli ESLint ve Ruff geçti. PostgreSQL kabulü açık.

Günlük karne ayrıntısı artık aynı zaman çizelgesinde açılıyor ve seçili çocuk ile günü koruyor. Tarih değiştiğinde eski ayrıntı kapanıyor. Altı hedefli web testi karne açma, tarih geçişi, önceki çocuk yanıtının elenmesi ve yoklama bağlantısını doğruladı. TypeScript ve hedefli ESLint geçti.

Yoklama bağlantısı günün çocuğunu ve tarihini sayfa geçişinde taşıyor. Çocuk, sunucudan gelen veli ilişki listesinde doğrulanıyor. Takvim yalnız yoklama okuma yetkisiyle çağrılıyor ve seçilen ay açıkça gösteriliyor. On yedi hedefli web testi ve bir geçici SQLite API testi geçti. TypeScript, hedefli ESLint ve Ruff geçti.

Web aylık takvimi sunucudan gelen günleri gösteriyor. Tarihli akıştan gelen gün seçili açılıyor. Giriş, çıkış ve not yalnız kayıtta varsa gösteriliyor. Kayıtsız günler belirtiliyor ve ay değişiminde eski ayrıntı kapanıyor. On yedi hedefli web testi, TypeScript ve hedefli ESLint geçti.

Web günlük akışı, seçilen çocuğu ve günü tarayıcının ilgili geçmiş kaydında saklıyor. Yoklamaya gidip geri dönünce seçim korunuyor. Sayfa geçişinde veli ilişki listesi yeniden yükleniyor. Kaydedilen çocuk artık veliye bağlı değilse ilişkili ilk çocuk ve sunucunun bildirdiği gün açılıyor. Geri ve ileri gezinme ile ilişki kaldırma dahil 18 hedefli web testi, TypeScript ve hedefli ESLint geçti.

Web günlük akışı ilaç, doz, revir uygulaması ve teslim alan bilgisini ilgili kayıtta gösteriyor. Servis biniş ve inişleri sunucudan gelen saat ve durumla okunuyor. Bu kayıtların ayrıntıları seçili çocuk ve gün üzerinde kalıyor. Dokuz günlük akış testi, TypeScript ve hedefli ESLint geçti.

Bugünkü özet ve günlük akış, yoklama alanlarını yalnız `parent.view_attendance` izniyle döndürüyor. Bugünkü özette izin yoksa alan yanıtın dışında kalıyor. İzin varsa ve kayıt bulunamadıysa alanın değeri `null` oluyor. Karne okuma izni olan veli iki durumda da kayıtlı karneyi görebiliyor. Geçici SQLite testleri 6/6 ve hedefli web testleri 21/21 geçti. PostgreSQL varyantı ortam bulunamadığı için çalışmadı.

Web günlük özeti yalnız günlük akışı kullanan ve yetkisi olan ekranlarda istiyor. Yoklama takvimi, finans ve sağlık ekranları kendi çağrılarını kullanıyor. Panoda finans veya günlük özet isteği başarısız olduğunda diğer kart kendi yanıtını gösterebiliyor. Başarısız finans isteği sıfır borç olarak gösterilmiyor. Hedefli 23 web testi, TypeScript ve ESLint geçti.

Yalnız yoklama veya finans okuma izni olan veli, izinli modülde çocuk seçebiliyor. Seçenekler aynı kurumdaki aktif veli ilişkilerinden geliyor ve öğrenci kimliği ile adı dışında alan taşımıyor. Tam çocuk profili izni ayrı uygulanıyor. Geçici SQLite testleri 7/7, hedefli web testleri 23/23, TypeScript ve hedefli ESLint geçti. PostgreSQL ortamı mevcut değildi.
