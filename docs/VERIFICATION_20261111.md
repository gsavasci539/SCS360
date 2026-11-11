# Kaynak doğrulama durumu — 11 Kasım 2026

> Yeni native yoklama checkpoint: gerçek FastAPI + geçici SQLite + Kotlin HTTP istemcisi kabulü geçti. 102 öğrenci/101 mevcut satır sayfalı yüklendi; mevcut not/HALF_DAY/sürüm korundu; kayıp yanıta aynı PUT gövdesi tek audit ile tekrarlandı; eski sürüm409, salt-okuma403, kurum dışı404, bildirim işi0. Tam yeni Android58 test paketi şu anda çalışıyor; aşağıdaki51PASS ve APK önceki kaynağa aittir. Güncel APK henüz üretilmedi. Aylık/derse ait native yoklama API bağlantısı açık; sahte takvim gösterilmez.

Bu dal geliştirme checkpoint'idir. Üretim veya tam web/native eşitliği kabulü değildir.

## Android / mobil

- Güncel Kotlin kaynak: **51/51PASS,0fail/0error/0skip,11m49s**, JDK23. `native-api-bound-scope-accepted-20261111.json`145Kotlin dosyasının SHA ve test XML sayımlarını içerir (SCS360Mobile deposunun docs klasöründedir).
- Tüm Retrofit servis tanımları eager validate edildi; anket gövdesinin JVM wildcard hatası giderildi. Sentetik HTTP hataları yerel kayıt veya örnek izin başarısı üretmez.
- Immutable operasyon kapsamı coroutine → Call.Factory → Request.tag → interceptor ile aktarılır. Hesap/kurum/şube/izin/API değişiminde eski yanıt ve henüz gönderilmemiş eski istek yeni aktöre taşınmaz. Aynı tokenla logout/login eski SaaS işlemini canlandırmaz. Regresyonlarda eski POST'un sunucuya hiç ulaşmadığı doğrulandı.
- Rol politikası4 ve AES-GCM token kasası2 testi de bu tam51koşudadır. Kripto testleri gerçek JCE ile test anahtarı kullanır; AndroidKeyStore donanımı gerçek cihazda ayrıca kabul edilecek.
- Responsive kapsam:8pencere ×3yazı ölçeğinde iki test toplam48konfigürasyon adımı; Students/Platform20gerçek ekran senaryosu ve büyük yazıda Root kritik düğmesine erişim. Dört sentetik görsel önceki görsel kabulün SHA'larıyla aynıdır. Bu bütün sayfaların cihaz kabulü değildir.
- Önceki47koşu46PASS/1wildcardFAIL idi; JDK17 koşusu Android36 sandbox başlangıcında durdu. Bunlar başarı sayılmaz. Son51koşu bu hatayı gideren kaynaktır.
- Resmî Gradle9.3.1 wrapper SHA256 ile pinlendi; wrapper sürüm kontrolü geçti. Tek-worker JVM ayarları testte kullanılan yapılandırmayla eşitlendi. Aynı145Kotlin dosyası değişmeden debug APK BUILD SUCCESSFUL3m16s; imza ve aapt metadata doğrulandı. Paket com.aistudio.okul360.hdtcca, min24/target36, 37296299byte, SHA256 `2844d7d8333b2509310912c127ba29a6e15f89db1a595f286d36ebe3d75526bd`. APK yalnız yerel debug artifact olarak tutulur; üretim veya cihaz kabulü değildir.
- Expo birim testleri8/8PASS; Android/iOS Hermes ve web export geçti. Bu yerel iOS veya gerçek cihaz kabulü değildir.
- Tam canonical API/payload/DTO işlev eşitliği henüz tamamlanmadı. Eski aktör/kurum bilgisi taşımayan disk kayıtları korunur fakat gösterilmez; kapsamlı offline cache açık.
- Gerçek A26 bağlı değil. Gerçek sağlayıcı anahtarları/HTTPS ve mağaza ürünleri sağlanmadı. Sentetik HTTP testleri gerçek ödeme kabulü değildir.

## Backend / web

Son native aşamasından önce değişmeyen web/API kaynağı için:

- Backend904PASS/2DB'ye özgüSKIP; geçici SQLite/PostgreSQL kullanıldı. Skiplerin karşı DB'deki sürümleri çalıştı.
- Frontend62dosya/344PASS; TypeScript ve Vite build geçti.
- Web E2E32PASS/3SKIP; izole memory-provider ayarıyla eksik3vaka ayrıca geçti.35benzersiz vaka iki ayrı koşudadır.
- Gerçek yerel veritabanı yalnız okunarak17/17 kontrol geçti; veri hücreleri değişmedi. Gerçek veri veya veritabanı bu kaynak checkpoint'ine eklenmedi.

SaaS üyelik hesabı ve kurum tahsilat hesapları ayrıdır. İyzico/PayTR/Craftgate/Sipay adapterleri ve Craftgate'e bağlı banka POS yolu vardır; her bankanın doğrudan protokolü uygulanmış değildir. Üretim dağıtımı veya gerçek ödeme/mesaj yapılmadı.
