Native debt create real Kotlin/FastAPI temporary DB acceptance PASS: 102 real write-authorized options, committed-ACK-loss replay creates one100.01 debt, Room ledger unchanged, no payments or notification jobs. Release preflight rejects missing API and HTTP emulator endpoint; release taskgraph validates first. Full current Android regression pending. Real A26/iOS/provider/store/release acceptance remains OPEN.

<!-- native-debt-create-20261112:start -->
WIP native canonical debt create: durable actor/workspace/branch request UUID, complete write-authorized student choices, exact whitelist payload and server ACK. Legacy create pre-HTTP Room writes and fake invoice identifiers removed; both finance entry points use the canonical form. Backend12 serial/concurrent retry and branch-option cases PASS across temporary SQLite/PostgreSQL44.67s. Initial affected native7PASS; final persistence guard test, real Kotlin/FastAPI acceptance and new APK pending.
<!-- native-debt-create-20261112:end -->

Backend debt create accepts optional request_id UUID: same actor/school/student/type/amount/due/description replays existing debt, changed/deleted/colliding request rejected409; organization lock and primary key enforce uniqueness. SQLite+PostgreSQL30 targeted regression PASS, final error-response adjustment6 PASS (overlapping tests, not36 unique). Android nonce/body integration remains OPEN. Android source unchanged; last signed debug APK600e36ac remains current.

Native invoice draft UI: six targeted UI/scope tests PASS5m41s, same-source debug APK/signature PASS2m17s. Bounded native scrollable form, blank amount/date/student defaults, 48dp actions and read-only controls; actual portal dialog closes on workspace switch. Previous AlertDialog idling scenario now passes with replacement form. Backend submission DTO, create idempotency, write-authorized student options and full feature acceptance remain OPEN.

Native finance presentation scope: 14/14 affected scope/cash/receipt tests PASS1m53s; same-source debug APK/signature PASS2m46s. Actor/organization/workspace/branch/role/permission/logout changes reset finance dialogs, while refresh preserves drafts. Receipt stale-session content hides. Prior full93Android/906backend checkpoint is historical; current full Android not rerun. Invoice AlertDialog test idling remains an explicit UI test limitation.

<!-- native-receipt-20261112:start -->
Current automated acceptance: backend906 unique PASS/2 intentionally database-specific SKIP across isolated SQLite and PostgreSQL runs; Android93/93PASS; actual Kotlin/FastAPI receipt/payment linking, lost-ACK replay and server PDF PASS. Same-source signed debug APK ready locally. Frontend unchanged: prior344PASS remains applicable. Physical A26/IME/Android print service, real provider/store acceptance and unfinished native feature parity remain open.
<!-- native-receipt-20261112:end -->

<!-- native-cash-20261112:start -->
Native cash/transfer ledger checkpoint: Android full90/90 PASS (16m49s); real Kotlin/FastAPI temporary SQLite lost-ACK replay and partial payments1 PASS/1PGdeselected (107.57s); backend integrity12 PASS/12PGdeselected. Same-source debug APK/signature PASS2m43s. Physical A26, actual provider/store acceptance, other finance rows/documents and portal-local context lifecycle remain open.
<!-- native-cash-20261112:end -->

<!-- native-finance-20261112:start -->
Native recorded finance summary accepted: full Android 82/82 PASS (17m48s), real Kotlin/FastAPI temporary SQLite acceptance 1 PASS/1 PostgreSQL deselected (115.55s), same-source debug APK/signature PASS (2m48s). Debt/payment row mutations, parent flows, physical A26 and actual provider/store acceptance remain open.
<!-- native-finance-20261112:end -->

# Kaynak doğrulama durumu — 11 Kasım 2026

> Native registry kabulü (12 Kasım): tam Android74/74PASS,0skip13m5s; ardından yalnız test kaydırma/görsel kontrolleri güçlendirildi,10/10UI takip testi PASS. Aynı uygulama kaynağı gerçek FastAPI/geçiciSQLite ile CRUD,102öğrenci sayfalama,403/404/409/422, minimal yazma rolü, klinik not korunması ve Room sentinel aynılığı testini geçti. Üç gerçek pencere qualifierında sistem font2 ve48dp hedefler kontrol edildi; üç native PNG incelendi. Sınıf kaydetme rasteri senkron tutarsızlığından kanıta alınmadı; tam viewport geometri kontrolü geçti. Debug APK imzası doğrulandı; SHA256 79c6a7c512e7071453146e2c3087996955341eedef51c4517c745dfc8d24a8a1. Veli ilişkileri, özel rol native login/görünümü, diğer native işlemler ve gerçek cihaz/HTTPS/sağlayıcı/mağaza kabulü açık.


> Önceki native yoklama kabulü: gerçek FastAPI/geçiciSQLite/Kotlin HTTP senaryosu PASS; tam Android58/58PASS,0skip5m26s. Sonrasında yalnız test görsel/scroll çağrıları değişti; native render testi3pencere/2xfont ile ayrıca PASS ve görseller incelendi. Uygulama kaynağı değişmeden debug APK üretildi ve imza doğrulandı; SHA256 64f8121912246a1fc3ec82626cb20dfa24b4859389e506f81229f8a1367aa3ca. Aşağıdaki51test/APK önceki checkpointtir. Tüm native eşitleme, aylık yoklama, gerçek A26/HTTPS/ödeme kabulü tamamlanmadı.


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


## 12 November: canonical native debt creation

100/100 native regression tests passed (25 suites, no failures/errors/skips, 18m53s). Same-source debug APK signature and metadata verified. Real Kotlin/FastAPI temporary SQLite bridge passed: 102 authorized student choices, lost committed ACK retry produces one debt, no Room prewrite/payments/notification jobs. Debt create identity races passed on SQLite/PostgreSQL; selected branch ledger list/detail contract and pagination passed four cases. Release preflight rejects missing/HTTP API input and runs before release build. This is debug/internal acceptance; native finance mutations and other module parity, physical A26/iOS, real provider/HTTPS/store products and production signing remain open. See docs/acceptance/native-debt-create-20261112.json. No real payments/messages/deployment.
