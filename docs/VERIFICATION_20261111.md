Native debt create real Kotlin/FastAPI temporary DB acceptance PASS: 102 real write-authorized options, committed-ACK-loss replay creates one100.01 debt, Room ledger unchanged, no payments or notification jobs. Release preflight rejects missing API and HTTP emulator endpoint; release taskgraph validates first. Full current Android regression pending. Real A26/iOS/provider/store/release acceptance remains OPEN.
# Verification checkpoint — attendance editor

<!-- native-debt-create-20261112:start -->
WIP native canonical debt create: durable actor/workspace/branch request UUID, complete write-authorized student choices, exact whitelist payload and server ACK. Legacy create pre-HTTP Room writes and fake invoice identifiers removed; both finance entry points use the canonical form. Backend12 serial/concurrent retry and branch-option cases PASS across temporary SQLite/PostgreSQL44.67s. Initial affected native7PASS; final persistence guard test, real Kotlin/FastAPI acceptance and new APK pending.
<!-- native-debt-create-20261112:end -->
2026-11-13: Targeted acceptance only. Temporary-SQLite backend integration tests: 6 passed, 6 PostgreSQL variants skipped. Web attendance editor tests: 7 passed. TypeScript and Vite build passed. Ruff F821/F823 passed. Existing records, notes and row versions load by class/date; unrecorded students are not implicitly marked present or sent in the batch. This does not certify the complete test suite, all native modules, physical A26, iOS, payment providers or production readiness.

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


## Native ledger targeted and real API checkpoint

Two native ledger contracts PASS. Real Kotlin/FastAPI temporary SQLite acceptance PASS: 102 rows fully paged, canonical edit, paid-debt edit/cancel422, acknowledged softdelete, 101 remaining rows, unchanged Room and zero new payment/delivery records. Current full native and backend SQLite/PostgreSQL runs pending; previous full100/debug APK belong to the debt-create baseline. See docs/acceptance/native-debt-ledger-20261112.json. Remaining native modules and physical/provider/store/release acceptance remain open.


## Final native ledger regression checkpoint

Current native104/104 PASS, no failures/errors/skips. Same-source debug APK signature/package/SDK/cleartext verification PASS. Backend SQLite/PostgreSQL full union 922 unique PASS; only two documented database-specific skips remain. Frontend source tree unchanged: retained344 tests/62 files and TypeScript/Vite PASS. Native real API/tempDB debt create and ledger bridges passed; source hashes identify each accepted checkpoint. Whole-app parity and sale acceptance remain open: expenses/parents/custom roles/other native modules, physical A26/iOS, real providers/HTTPS/store products and release signing. Details docs/acceptance/native-debt-ledger-20261112.json. No user DB changes, real payments/messages or deployment.


## Expense targeted and real API checkpoint

Backend21 targeted cases PASS on temporary SQLite/PostgreSQL; native client2/UI3 PASS. Real Kotlin/FastAPI temporary SQLite bridge PASS: 100 seeded expenses plus one durable create, lost committed ACK recovery, complete101-row pagination, web110.02/category/calendar-date edit visible natively, web/native delete yields empty ledger, no payment/delivery/Room writes, foreign404/parent403. Current full native109/backend runs and matching APK still pending. Native expense edit UI, remaining modules and physical/provider/store/release acceptance remain open. See docs/acceptance/native-expense-20261112.json.


## Expense create/list/delete regression checkpoint

Native109/109 PASS, no failures/errors/skips. Same-source debug APK verified. Current backend full SQLite/PostgreSQL union 940 unique PASS with only two documented DB-specific skips. Expense API targeted21 and native client2/UI3/real API bridge accepted: numeric/string cents, scoped complete pagination, lost committed ACK creates one expense, web edits/category/date visible natively, native and web deletes yield authoritative empty ledger, zero payments/delivery jobs/Room writes. Hardcoded native expense rows and local fallback removed. Unchanged frontend344/build and Expo8/web export retained. This does not accept native expense edit UI, remaining parent/custom-role/module parity, physical A26/iOS, real provider/HTTPS/store products or production signing. See docs/acceptance/native-expense-20261112.json.

## Web expense durable create checkpoint

Current frontend352/63 tests PASS, no failures/skips; TypeScript/Vite PASS. Eight targeted expense UI contracts cover lost/mismatched ACK, double click, persisted body/UUID, explicit real scope selection, incomplete branch paging, storage failure/corruption, stale permissions/scope and late editor protection. Runtime backend/native source hashes unchanged: retain940 backend PASS (two DB-specific skips),109 native PASS and the prior debug APK. This browser UI checkpoint uses mocked transport; it does not add physical/device/provider acceptance. Recovery is scoped sessionStorage in the same browser tab. See docs/acceptance/web-expense-create-20261112.json. Remaining native expense edit/note/finance-portal delete controls, parent/custom-role/module parity and device/provider/store/release acceptance stay open. No real payments/messages or deployment.

## Native finance portal expense delete checkpoint

Current native112 unique PASS, no failures/skips:6 targeted plus remaining106 in disjoint runs at identical source hashes. The Finance role portal now confirms only the explicitly selected expense; failed/stale replies cannot produce success or reload another workspace. Readonly, long text and landscape font2/48dp contracts passed. Same-source debug APK signature/package/SDK verification passed. Backend940 PASS/two DB-specific skips and frontend352/63 +TypeScript/Vite retained at unchanged source hashes. Existing actual Kotlin/FastAPI/tempDB expense API acceptance retained; these UI tests do not prove physical A26/iOS/provider acceptance. Native expense edit/reference notes, other module parity, real providers/HTTPS/store/release acceptance stay open. See docs/acceptance/native-expense-delete-20261112.json. No real payments/messages, user DB changes or deployment.

## Native uncertain expense delete recheck checkpoint

Current native113 unique PASS, no failures/skips:7 targeted plus remaining106 in disjoint runs at identical source hashes. The Finance role portal now offers an explicit list recheck after uncertain deletion without another DELETE or a false acknowledgement; failed/stale replies cannot produce success or reload another workspace. Readonly, long text and landscape font2/48dp contracts passed. Same-source debug APK signature/package/SDK verification passed. Backend940 PASS/two DB-specific skips and frontend352/63 +TypeScript/Vite retained at unchanged source hashes. Existing actual Kotlin/FastAPI/tempDB expense API acceptance retained; these UI tests do not prove physical A26/iOS/provider acceptance. Native expense edit/reference notes, other module parity, real providers/HTTPS/store/release acceptance stay open. See docs/acceptance/native-expense-recheck-20261112.json. No real payments/messages, user DB changes or deployment.

## Native expense edit targeted and real API WIP

Six targeted native contracts and actual Kotlin/FastAPI/tempSQLite edit bridge PASS; remaining113 native regressions running. See docs/acceptance/native-expense-edit-wip-20261113.json. Prior APK and physical/provider/store acceptance unchanged.

## Native expense edit reread refresh WIP

Final7 native contracts PASS. Explicit canonical reread now closes the editor and refreshes the parent ledger after an uncertain edit; no second PUT or false acknowledgement. Actual API client/model/bridge source unchanged, so its temporary DB acceptance is retained. Previous partial113 regression stopped after finding this UI gap; current113 regression is running at the corrected source. No full/APK/device acceptance claimed yet.

## Native expense edit and notes checkpoint

Current native120 unique PASS, no failures/skips:7 targeted plus remaining113 in disjoint runs at identical source hashes. Both native finance entry points now use fresh canonical expense detail, delta PUT, authoritative field acknowledgement and explicit reread recovery; failed/stale replies cannot produce success or reload another workspace. Readonly and landscape font2/48dp action contracts passed. Same-source debug APK signature/package/SDK verification passed. Backend940 PASS/two DB-specific skips and frontend352/63 +TypeScript/Vite retained at unchanged source hashes. Actual Kotlin/FastAPI/tempSQLite edit bridge also passed:120.03 and nullable-note roundtrip through the web API, same delta after lost committed ACK,0 new payments/jobs/Room writes. Injected authenticated fixture; physical A26/iOS/provider/native-login acceptance remains open. Remaining native expense create/status and concurrency policy, other module parity, real providers/HTTPS/store/release acceptance stay open. See docs/acceptance/native-expense-edit-20261113.json. No real payments/messages, user DB changes or deployment.

## Native create notes and readonly status WIP

Targeted7 contracts and actual Kotlin/FastAPI/tempSQLite notes bridge PASS. Old pending six-field requests keep the exact body/UUID; creation notes reach web notes through the existing receipt_url text alias, status is readonly server data. Wrong note ACK is not success. Create/edit lost ACK recovery leaves101 ledger rows and0 new payment/jobs/Room writes. Remaining115 native regressions running; prior120/APK are for the previous source. See docs/acceptance/native-expense-notes-wip-20261113.json.

## Cash ACK scroll correction WIP

Original115 regression had114 PASS/1FAIL: cash_done could not be found while ACK semantics retained the old form scroll range. Production cash UI now binds content/semantics to one composition snapshot and resets confirmation scroll with stable keys. Original assertions unchanged; final10 targets PASS. Remaining112 native regression running, prior failed run archived. Actual notes API client/model/bridge source unchanged; its temporary DB acceptance retained. No full/APK/device acceptance claimed yet.

## Shared confirmation visibility correction WIP

Second112 regression exposed an expense-delete ACK outside the viewport after the old form offset persisted (111PASS/1FAIL). Expense delete now uses the same composition snapshot/fresh confirmation scroll binding as cash. Final14 targets PASS with original assertions unchanged; remaining108 native regressions running. Both failed attempts archived and excluded from final acceptance. Actual notes API client/model/bridge unchanged; temporary DB acceptance retained.

## Native creation notes and readonly expense status checkpoint

Current native122 unique PASS, no failures/skips:14 targeted plus remaining108 in disjoint runs at identical source hashes. Native creation notes now persist and recover with the same durable UUID/body, including exact old six-field requests. Expense status is readonly server data, matching the web form. Dead legacy PAN callback removed; hosted checkout remains authoritative; failed/stale replies cannot produce success or reload another workspace. Readonly and landscape font2/48dp action contracts passed. Initial runs exposed cash confirmation scroll and expense delete acknowledgement visibility failures. Both production dialogs now capture confirmation in composition and start confirmation with fresh scroll state and stable keys; original test assertions preserved. Same-source debug APK signature/package/SDK verification passed. Backend940 PASS/two DB-specific skips and frontend352/63 +TypeScript/Vite retained at unchanged source hashes. Actual Kotlin/FastAPI/tempSQLite edit bridge also passed:120.03 and nullable-note roundtrip through the web API, same delta after lost committed ACK,0 new payments/jobs/Room writes. Injected authenticated fixture; physical A26/iOS/provider/native-login acceptance remains open. Expense concurrency policy and other module parity, real providers/HTTPS/store/release acceptance stay open. See docs/acceptance/native-expense-notes-20261113.json. No real payments/messages, user DB changes or deployment.

## WIP native parent/custom-role/payment parity 20261113

Work in progress, not full acceptance. Native parent management now has canonical paged contact CRUD, explicit login-account and student links. Parent portal uses authorized my-children/debt DTOs; name/phone inference and legacy manual-payment callbacks removed. Custom server roles retain their real slugs and permissions in a distinct native portal; initial loaders and navigation use permission gates. Hosted payment close/recheck reloads authoritative lists without creating a manual payment. First targeted run:27 PASS/2 UI failures across29 cases; both hosted AlertDialog large-font cases did not idle. The dialog was replaced with a bounded lazy native layout and fresh confirmation scroll state; verification is pending. Actual native login/FastAPI/tempDB bridge has been added but not yet accepted. Remaining operational modules still require individual real API and payload audits. No production data, provider transaction or deployment.

## Accepted native parent/custom-role/payment parity checkpoint

138 unique native tests passed in disjoint15+123 runs. Actual native custom-role and parent login/FastAPI/tempSQLite acceptance passed for101-contact paging, contact CRUD, account/student links, own-child finance, pending medicine/excuse requests, missing daily report and one synthetic stored teacher chat with zero real delivery/payments/notification jobs. Hosted close/recheck reloads current-scope data without manual-payment callbacks. Legacy sample child matching, invoices, meals, health, scores, phone and IBAN content removed from the parent portal. Missing data and denied scopes remain explicit. Same-source signed debug APK verified. Unchanged backend940 PASS/two DB-specific skips and frontend352/63 +TypeScript/Vite retained. Earlier failed tests/fixture validation are historical, not final acceptance. Remaining operational modules/legacy role administration are still open; test totals do not prove all-module parity. External acceptance is separate at user request and was not performed. See docs/acceptance/native-parent-parity-20261113.json.

## Accepted branch-limited native parent creation

21 affected/native tests passed (six new and15 rechecked); actual native branch-limited custom-role and class-scoped teacher login/FastAPI/tempSQLite acceptance passed. Actual student options retain each actor scope. New contacts use one atomic student-parent creation and server contact/link readback; scoped users without student permissions cannot create invisible standalone contacts. Foreign organization and other-class students are rejected.101 unlinked contacts stay hidden. Zero payment/notification rows or real deliveries. The prior unchanged123-case regression was retained, not rerun or counted twice. Same-source debug APK signature verified. Prior parent-checkpoint duration metadata now explicitly separates its six-contract and nine-UI runs; counts/outcomes did not change. Remaining operational modules are open; physical/provider/store/release acceptance was not performed. See docs/acceptance/native-parent-branch-20261113.json.

## WIP native library core: targeted/API pass, full regression pending

10 new native contract/UI tests and actual native custom writer/reader authentication/FastAPI/tempSQLite acceptance passed for catalog create/list,real student options,borrow/readback/PUT return,stock restoration,foreign student denial,readonly403 and duplicate-return409. Full other-native regression is running; a same-source APK has not yet been accepted. This is WIP,not full library parity. Correction:Book/BookLoan are aliases of LibraryBook/LibraryLoan,so there is no different store or migration requirement. The earlier WIP inference was incorrect. Web stock mapping,durable reminder delivery and native detail/edit/delete remain open. Native local loan/stock writes and false SMS claims removed. No real payments/messages/deploy. See docs/acceptance/native-library-wip-20261113.json.

## Accepted native library core checkpoint; library parity remains open

154 distinct native cases passed (10 new target and144 other regression). Actual native custom writer/reader authentication/FastAPI/tempSQLite acceptance passed for canonical catalog creation/listing,real student options,borrow/readback and PUT return,stock2-to1-to2,foreign student denial,readonly403 and duplicate-return409. No local loan/stock writes,fake default records or SMS delivery claims. Zero Payment/NotificationJob/real delivery. Same-source debug APK signature verified. Backend940/two DB-specific skips and352 other frontend tests/63 files retained. Web stock row/summary now use available_copies; two new frontend render tests and current TypeScript/Vite build passed. The retained frontend suite was not rerun. **Library is not complete:** native detail/edit/delete is pending; web stock mapping is fixed; reminder route still claims delivery without a queue and is not offered by native. Book/BookLoan are aliases of LibraryBook/LibraryLoan; the earlier WIP different-store inference was incorrect and is corrected. No migration is needed. Remaining modules are open. Physical/provider/store/release acceptance was not performed. See docs/acceptance/native-library-core-20261113.json.

## Book catalogue API stock/history guards

Five real API/tempSQLite tests passed; five PostgreSQL variants deselected. Book edits preserve active-loan inventory, reject stale snapshots and invalid copy overrides. Active or returned loan history blocks deletion,including history outside a teacher student scope. Readonly/foreign/null guards and unused-book deletion passed. SQLite timestamp CAS formatting failure corrected; original assertions retained. No full backend-suite rerun or new Android build claimed. Native CRUD UI and real reminder queue are still pending. See docs/acceptance/library-catalog-guards-20261113.json.

## 2026-11-13 attendance editor

Targeted only: temporary SQLite backend 6 passed, 6 PostgreSQL variants skipped; web UI 7 passed; TypeScript/Vite build passed. Unrecorded students are not implicitly marked present. Does not certify the full suite or physical device acceptance. See `docs/native-attendance-editor-checkpoint-20261113.md`.
Details: `docs/native-attendance-editor-checkpoint-20261113.md`.
