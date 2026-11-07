# SCS360 — Bütün Markdown belgelerinin tam metni

**Derleme zamanı:** 2026-11-04T12:20:34+03:00 — Europe/Istanbul  
**Kaynak belge sayısı:** 26  
**İçerik doğrulaması:** Her kaynak belgenin tam metni, ayrı ayrı birebir karşılaştırılır.

Aşağıdaki belgelerin tüm metinleri; başlıklar, tablolar, kod blokları, bağlantı yazımları ve açıklamalar değiştirilmeden birleştirilmiştir. Kaynak dosyalar korunmuştur. Yalnız metin dışındaki UTF-8 dosya başlangıç işareti kaldırılır.

Kapsam: proje Markdown belgeleri. Üçüncü taraf bağımlılıkları, önbellekler, derleme/test çıktıları, geçici dosyalar ve yedek kopyalar bu belge envanterine dahil değildir. Birleşik dosya kendi içine tekrar eklenmez.

Belgeler farklı tarihlere aittir; geçmiş sonuçlar ve henüz tamamlanmamış planlar da eksiksiz korunur. Göreli bağlantıların kaynak belgedeki yazımı korunmuştur; gerektiğinde her bölümde verilen kaynak dosya bağlantısını kullanın.

## İçindekiler
- [docs/CALISMA_DURUMU.md](#belge-01)
- [docs/SAAS_ISLETIMI.md](#belge-02)
- [docs/SAAS_KABUL_PLANI.md](#belge-03)
- [docs/SCS360_YENILIKLER_VE_GUNCELLEMELER.md](#belge-04)
- [README.md](#belge-05)
- [backend/AI_CHATBOT_IMPLEMENTATION.md](#belge-06)
- [backend/README.md](#belge-07)
- [docs/API_ENDPOINTS.md](#belge-08)
- [docs/ARCHITECTURE.md](#belge-09)
- [docs/CICD_PIPELINE.md](#belge-10)
- [docs/CODE_AUDIT_2026-06-24.md](#belge-11)
- [docs/CREATIVE_TIM_INTEGRATION.md](#belge-12)
- [docs/DEVELOPMENT_ORDER.md](#belge-13)
- [docs/DOCKER_DEPLOYMENT.md](#belge-14)
- [docs/FRONTEND_PAGES.md](#belge-15)
- [docs/NOTIFICATION_ARCHITECTURE.md](#belge-16)
- [docs/SATIS_ONCESI_KABUL_2026-11-02.md](#belge-17)
- [docs/SCS360_MARKA.md](#belge-18)
- [docs/SECURITY_PLAN.md](#belge-19)
- [docs/TEKNIK_DURUM_2026-11-02.md](#belge-20)
- [docs/TEST_VE_CALISTIRMA_2026-11-03.md](#belge-21)
- [docs/URETIM_KURULUMU_VE_MOBIL.md](#belge-22)
- [frontend/README.md](#belge-23)
- [hardware/README.md](#belge-24)
- [PROJE_DOKUMANTASYONU.md](#belge-25)
- [PROJE_DOKÜMANTASYONU.md](#belge-26)

---

<a id="belge-01"></a>

## 1. docs/CALISMA_DURUMU.md

Kaynak: [docs/CALISMA_DURUMU.md](docs/CALISMA_DURUMU.md)  
SHA-256: `807005f017e95fd7540fd0c82bde46e3edf362de1e3741e5042e504f31d68847`

<!-- SCS360_SOURCE_BEGIN: 01 -->
# SCS360 çalışma ve devam kaydı

Güncelleme: 3 Kasım 2026 akşam. Amaç satış öncesi gerçek API, rol/kurum ve arayüz kabulü. Üretim/satış kabulü henüz tamamlanmadı.

## Korunacak kurallar

- C:\Okul360 geniş, önceden commit edilmemiş farklar içerir. Reset/clean, toplu geri alma/normalleştirme yapma; kullanıcı değişikliklerini koru. Aynı dosyalarda başka etkin çalışma varsa çakışma yaratma. Son chat kontrolünde yalnız bu çalışma etkindi; AGENTS.md bulunmadı.
- backend/school_management.db mevcut kullanıcı verisidir. Hesap, e-posta, parola veya eski UUID/ilişkileri otomatik değiştirme/birleştirme/silme.
- Testler geçici SQLite ve yalnız scs360_acceptance adlı PG DB/şemalarında. Gerçek SMS/e-posta/WhatsApp/ödeme, üretim dağıtımı yok.
- Önce get_usage_limits. ordinaryUsageAllowed=false veya herhangi bir pencere100 ise geliştirme başlatma; reset/limit aşma denemesi yapma. Son kontrol yeni pencerelerde %0/%0, ordinaryUsageAllowed=true. Her yeni aşamada yeniden kontrol et; reset kredisi aracı kullanma.
- Otomasyon scs360-hata-d-zeltmelerine-devam saatlik; yalnız anlamlı değişiklikte bildir. Değişmeyen limit bekleyişi sessiz. Yalnız dış sağlayıcı/erişim kabulü kalınca otomatik geliştirmeyi durdur.

## Yeni öncelik: SaaS (3 Kasım kullanıcı talebi)

- **4 Kasım12:18 güncelOrgfazı:** SonbackendOrg/Branch+SaaS+Rootworkspace+sözleşme **30/30**83.25s (`org-branch-saas-regression-20261104.log`,58031tamamlandı); Ownerroot-onlyhesapstatüsü, kapatıpkayıpsilmedenreopen ve contactclear(null) dahil. UI **5/5**8.21s (`organization-controls-final-20261104.log`,47412tamamlandı), OwnerForm/Butonlar ve mevcutiletişimbilgisinintemizlenmesi. İlkTSbuildikiayrıtesttypinghatasınıyakalamıştı: ByRoleexactparametresi kaldırıldı, canAnalyze'in callback'i `(permission:string)=>boolean` olarak doğru açık tip aldı. ŞimdiTS/Vite **temiz17.06s** (`build-org-policy-final-20261104.log`,93362tamamlandı), OpenAPIyenilendi/RuffF821F823temiz (`ruff-org-policy-final-20261104.log`,29087tamamlandı).
- **Şimdi:** yeniOwnerkurumprofili+telefonkaydet/temizle+masterkapat/402billing/masteraç/yenile/mobil E2E `edge-organization-controls-first-20261104.log` toolsessionID'yi kaydet; lint `lint-org-policy-final-20261104.log`. YeniE2Etoplam30, full30henüzyok. Sonfull29Orgfazıöncesidir; fullbackend367dahaönceki, son30targetedgüncel. Source runtimeOrg/Branch/Platform/ResourcePages sondeğişikliklerimain'e hâlâyüklenmedi; sonE2Egeçincestop/start/livegerekli. DB034,migrationyok. Sonrasında035öğrencimerchant/nonce/snapshot/reviewgeliştirmesinebaşlamadan currentfazkanıtlarınıkapat; başkaaktifchatyok(11:49),AGENTSyok. Kullanıcıpaketleripaneldenkendisigirecek,fiyatuydurulmadı.

- **4 Kasım12:09:** FullEdge+PG **29/29**5.2m (`edge-all-29-final-20261104.log`,85455 tamamlandı), sonra `live-capacity-final-20261104.log` canlıgiriş/Root→kurum/pano/API/chatbot başarı,main kapasiteguardla5173/8000çalışıyor (`start-capacity-final-20261104.log`). Fullbackend367/fullfrontend198/GET2145 bu aşamada doğrulanmıştı. Main034aynı,migrationyok.
- YeniOrg/Branchtempredtest **4failedSQLite** (`org-branch-validation-before-20261104.log`,80642tamamlandı): nullmandatory/dubleadkodDBhataları, bilinmeyenorgbranchorphan riski veOwnerkurumhesabınıkapatabiliyordu. RegistryFields strstrip/nullablecontactblank→None, mandatoryname/capacity/is_activenull422, DBvarchar/int32sınırları ve BranchOrgUUIDvalidationeklendi. Organizasyon/şubewrite'ları responseöncesiflush; duplicatead/kod409vegeri-rollback; branchrelatedOrgvarlık/scopecheck var.
- Kurumyaşam döngüsü artık yalnızactualRootveyaplatformAdmin: genericOrgUpdateis_active/deleteroot-only. Ortak platform_service.set_account_status Orgkilidi+refresh, Organization.is_active+Membership.admin_status eşzamanlı, audit ve flush; esasSaaSstatusendpointidebunu kullanır. DELETEkurumsoftdeletemez,kapatır; böyleceMasterlistesindenkaybolmaz, yenidenaçılabilir. Ownerorg.writeileiletişimbilgilerini düzenler; yeniOrgcreate/import/deletebusinessbutonlarıgizli, eski/newURLkaydetformuaçmaz. YenikurumlarSaaSanaekranındanoluşturulur. Org/Branchiletişimalanlarıeditteboşaltılırsanullgönderilir.
- İlkSQLite+PG **8/8**24.40s (`org-branch-validation-first-20261104.log`), UIkontrollerilk4/4sonrailetişimtemizlemeyle5beklenir `organization-controls-final-20261104.log` (sonucunuoku). Sonregresyon `org-branch-saas-regression-20261104.log` session58031; sonTSbuildilkdenemesi testteTestingLibraryByRoleoptions'exact' desteklenmediği için TS2769verdi; stringnamezatenexactolduğundan parametresilindi, `build-org-branch-rechecked-20261104.log` session(toolIDal). Henüzbufazsonrasıfull375/frontend201çalışmadı; tahminsonucusayma. OrgBranch/Platform/ResourcePages sondeğişiklikleri main'e henüzrestartedilmedi.
- Sonraki: bu sonuçlarıal, OpenAPI/lint, gerekliOwnerRootcanlı/browsertesti, sonra öğrencioptions aktif/full/100+ vewrite-onlypermissionkökleri;035merchant/nonce/şifrelisnapshot/review asıl büyüködeme işi. Ekkeşifler: BranchsoftdeletepopulatedBranch'iClass/Studenthistoryile görünmezbırakabilir; aktifbranchadmissionvearşivkurallarıtestedilmedi. GenericResourceList async gezinmede requestabort/reseteksikliği ayrıca incelenmeli. Yalnızdışkabulkalmadı; otomasyonACTIVE. Kullanıcıpaketleripaneldentanınlayacak; fiyatuydurma/yenidensorma.

- **4 Kasım11:48 yenilenen kullanım%1/%47ordinarytrue:** Kullanıcı yanıtı: **paketleri/fiyatları/sınırları superadmin panelinden kendisi tanımlayacak.** Bu bilgi için yeniden soru sorma; main'e tahmini paket/fiyat yükleme. Publicsite gerçekaktifkataloğu gösterir. Mevcut üyelik/hesap/UUID/parolalar korunur.
- Tam backend **367/367**,680.34s (`backend-capacity-full-20261104.log`,13043 tamamlandı); sınıfguard/transfer dahil son kaynak doğrulandı. Önceki08:31'deki 'çalışıyor/beklenir' kayıtları artık eskidir. Sonfullfrontend198/lint/TS/Ruff/OpenAPI ve rolGET2145kanıtları hâlâ geçerli. **Şimdi:** fullEdge+PG29 `edge-all-29-final-20261104.log` (toolsessionIDkaydet); Root+publicsite+SaaS+Parentmixedpurpose+Teacher/öğrenci/kayıtlar+bus akışları. Maincontrolledstopbaşarılı, `start-capacity-final-20261104.log` yenidenbaşlıyor; sonucu al ve sonliveverifyçalıştır. Primary034şeması değişmedi,107tablo korunuyor. Yeni kodlama öncesi başkaaktifchat/AGENTS kontrolünü yenile; bekleyenEdge29bitene kadar runtimekaynakları dondur.
- Sonraki iş: Org/Branchupdate nullmandatory/varchar/int-sınırları önce tempAPIredtestle kanıtla; asyncget_db commit-sonrasıHTTPresponse hata riskini ilgili yazmalarda flush ile önle. Sonra öğrenci sınıf/dropdown aktif-kontenjan/100+vewrite-onlypermission kaynakları, servis100+sürücü araması, genelAI doğruluk. Büyük035öğrenci merchant/nonce/şifrelisnapshot/REVIEW/manuelçakışma işi hâlâiçgeliştirme; yapmadan satış kabulü tamamlanmış veya yalnız dışsağlayıcı kaldı deme. Gerçekpara/mesaj/deployyok, otomasyonACTIVE. GeçiciPG55436 açık, işleri bitirince doğruverifieddatadir ile durdur.

- **4 Kasım08:31:** Kapasite+CSVimport+legacykayıtkoruma+SaaSkotalar+class+sözleşme **38/38**79.23s (`class-capacity-quota-rechecked-20261104.log`,68329 tamamlandı). Önceki36pass2fail gerçek sınıfsilmehatadı: get_db commit'i HTTPyanıtbaşladıktan sonra guard409fırlatıyordu. Core studentdelete/classdelete/classremove artık returnöncesi flush yapar; sınıfsilme409 düzgünHTTPdöner. Zaten silinmiş eski sınıftan öğrenciyi çıkarma guardtarafından engellenmez. İlk10pass'ın üzerineCSV1başarılı1dolu-row hatası ve over-capacitylegacyNameEdit200/öğrencisilisınıf409+DBkoruma da geçti. Rufftemiz, OpenAPIsonDTO/transferileyenilendi.
- **Şimdi tambackend yeniden:** `backend-capacity-full-20261104.log`, toolsessionID'yi kaydet.367beklenir fakat sonuç görmeden başarı sayma. Backendkaynakları bu koşu bitene kadar donduruldu. Ağırtestler seri; sonra fullEdge29 (ACCEPTANCE_DATABASE_URL55436, SCS360_ACCEPTANCE_SAAS_GATEWAY=1). Öncekifull353kapasitedenönce, sonfullfrontend198AnalysisParentsonrası güncel (kapasite UIkodu değiştirmedi). GETaudit2145geçti/okuma yollarıaynı. Main5173/8000 çalışıyor, **kapasite kodu için henüz restart yapılmadı**; testlerden sonra restart/livegerekli. Primary034aynı107tablo, migrationyok.
- Kalan öncelikler: genelOrg/Branchupdate nullablemandatory ve DBvarchar/int sınırları (common.OrganizationUpdate/BranchUpdate nullname/capacity/is_active izinveriyor, organizations.py setattr yapıyor; henüz tempAPI ilekanıtlanmadı), öğrenci sınıf seçicisinde inactive/100+ seçenek ve write-only form kaynak izinleri, servis100+sürücü seçimi, genelAI default/hata200doğruluğu;035öğrenci merchant/nonce/şifrelisnapshot/REVIEWödemesi. Bu nedenle yalnız dışkabul kalmış değildir, otomasyonACTIVE. Gerçekpara/mesaj/deployyok. Sonusage89/45sonrası yeni kontrolü oku;100/ordinaryfalseyeni aşama başlatma.

- **4 Kasım08:25 kontenjan devamı:** Yeni kapasiteler ilkSQLiteproof5failed ile kanıtlandı (`class-capacity-before-20261104.log`): create/update/sonkoltuk denetimi yok, dolu sınıfa tekrar atama/boş veya sayıIDgirdisi sorunları. Transfer testleri bu ilk koşuda **404** verdi: `classes.py` legacyrouter main'e dahil değilmiş. Dolayısıyla 'velinin bu eskiyoldan gerçekten aktarım yapabildiği' iddiası yoktur; dosyadaki auth-only kontrolü unreachable koddadır. Aynırouteyi yanlışlıkla main'e komple dahil etmek yerine gerekli tek typed `/api/classes/{id}/transfer-students` Core'a class.write+aynıkurum/şube+tamIDlistesi+atomikguard ile eklendi. Legacy dosya da ileride dahil edilirse diye aynı izin/girdi kurallarıyla korundu.
- `class_capacity_guard` before_flush: yeni/güncel/import/restore/tekli-toplu/aktarım Student ORM yollarında fullCoreRoster+pendingdeltalar, kapasite küçültme ve dolu sınıf silmeyi denetler. Tenantguard'dan sonra subscriptionguard'dan ÖNCE çalışır; ilgili tüm kota resourceOrg'ları sıralıOrgnoopUPDATE→sıralıClassnoopUPDATE ile kilitler, paketguardaynıkilitlerikullanır. Atama değişen mevcut öğrenci için kilit sonrası DBclass/branch/org/deleted snapshot'ı eskiyle eşleşmezse409; kayıpnigüncelleme/yanlışdelta yok. Aktif/silinmemişClassaynıOrg/branch şartı. Unrelated legacy over-capacityeditsbloğuyok; eski öğrencileri taşımaz/silmez. API'deki racycount önkontrolleri kaldırıldı, flush guard karar verir. Tekli/toplu UUIDDTO,min1/max1000/dedup, capacityint32sınırı eklendi.
- İlk güncelSQLite+PG **10/10**20.97s (`class-capacity-rechecked-20261104.log`,60611 tamamlandı). Önceki4passed6failed yalnız henüz Core'da olmayan transferAPI404 idi (`class-capacity-first-20261104.log`), sonra gerçekCorehandler eklenince10geçti. Sonrasında CSVimport1başarılı1kontenjan hatası ve legacyover-capacitykayıt koruma/dolusınıfsilmeme testleri eklendi; **şimdi** kapasite+SaaSpaketkotaları+class+sözleşme tekrarı `class-capacity-quota-final-20261104.log` (toolsessionIDkaydet). OpenAPI sontypedassignment+Coretransferile export ediliyor; Ruff`ruff-capacity-final-20261104.log`.
- Son rolGETaudit **2145/2145**,11×195,1075HTTP200+1070beklenen403 (`api-smoke-analysis-final-20261104.log`,37123 tamamlandı,docs/api-smoke-results.json). Beklenmeyen500/404/401yok. Bu kaynakDB'ninreadonlyclone'unda, kapasiteler kodundanöncekiGETşeması; kapasite değişiklikleri yeniGETeklemedi/okumaizinlerini değiştirmedi. Son tamfrontend198 ve backend353 **kapasiteguardöncesidir**. Global listener nedeniyle sonfullbackend367beklenir ama tekrar henüz başlamadı; sonuç alınmalı. FullEdge29 hâlâbaşlamadı. Main5173/8000 sonAnalysisParentileaçık **kapasiteguardhenüzyüklenmedi**; sonkontrollerardından stop/start/live gerekli. Primary034aynı, migrationyok. Gerçekpara/mesaj/deployyok.

- **4 Kasım08:18:** Tam backend **353/353**,667.91s (`backend-analysis-full-20261104.log`,55790 tamamlandı), ParentScope/insights ve40AIfeatureguards dahil. Kaynak dondurma bu test için bitti. Şimdi readonlymainclone rolGETaudit `api-smoke-analysis-final-20261104.log` (toolsessionIDal); bu aşamada kapasite/transfer düzeltmesi başlayabilir, auditGETşeması/okumaizinleri değiştirilmeyecek. Sonra fullEdge29. Önceki08:12belirsiz357? notu sonuç değildir; gerçek353/353 budur. MainsonkodlaaçıkveLivefailures0doğrulandı. Sonraki listener/transfer kodu restartından sonra yenidenkontrol gerekebilir.

- **4 Kasım08:12 canlı/çalışan işler:** Ana stop/start tamamlandı;5173/8000 sonParentScope+insights+AnalysisPermission koduyla açık (`start-analysis-final-20261104.log`,41236 tamamlandı). `live-analysis-final-20261104.log` canlıgiriş/Rootplatform→kurum/pano/APIproxy/chatbot kontrolü başarılı; `running-local-verification-20261103.json` içeriği yeniden bu koşuyla güncellendi, failures[] olmalı (kontrolet).357? test sayısı tahmin etme: şu an backendfull session**55790**, `backend-analysis-full-20261104.log`, son%40. Bitene kadar backend kodunu değiştirme. Son primary%75/weekly%43ordinarytrue. AğırfullEdge29/rolaudit fullbackendbittikten sonra,henüzbaşlamadı.
- KarmaParentmobilePNG ilk fotoğrafta alt Timeline hâlâ yüklenirken ve kart animasyonları sürerken alındı; app/API hata kanıtı değil. E2E artık gerçek boşTimeline'ın görünmesini bekler ve screenshot animationsdisabled; bu ekbekleme full29'da koşulacak. Runtimebranding taraması yalnız `okul360-session` eski oturumu güvenle temizleyen uyumluluk anahtarını ve kendi migrationtestlerini buldu; kullanıcı görünür eski marka metni bulunmadı (SVGlerbuaramada dışarıda).
- **Yeni kontenjan işinin somut başlangıcı (henüz kodlanmadı):** core create_student/update_student class FK veşubeyi kontrol eder ama Class.capacity kontrol etmez. Tekli assign_student_to_class sayım+check yapar ancak atomikkilit yok. ImportService Student ORM oluşturur, classes.py transfer Student.class_id değiştirir. DomainStudent canonicalStudentalias. Paketguard `subscription_guard.before_flush` OrgnoopUPDATEkilidi alıp şube/öğrenci/kullanıcı kotalarını atomik uygular; Class kapasitesini kapsamıyor. Yeni class_capacity_guard tüm ORM create/update/import/transfer/restore ve capacityshrink için Coretamrostersayımı+pendingdeltalarla, Org→Class kilit sırası tutarlıolacak şekilde tasarlanmalı. Sadeceendpointif ekleyip bulk/concurrency yolunu açık bırakma; önce class_id rawbulkUPDATE var mı tümapp'te tarayıp doğrula. PG+SQLite eşzamanlısonkoltuk, transfer,0/duplicate/null, rosteraltına küçültme, yabancıkurum/şube ve paketguardilekilit testi gerekir. Mevcut over-capacity legacykayıtları silme/değiştirme.

- **4 Kasım08:06:** Tam frontend **198/198**,40dosya114.42s (`frontend-analysis-full-20261104.log`,79407 tamamlandı). Lint temiz (`lint-analysis-final-20261104.log`,62570 tamamlandı), OpenAPIexport sonAnalysis/Parentinsights+payment rotalarıyla üretildi, RuffF821/F823temiz (`ruff-analysis-final-20261104.log`,33909 tamamlandı). Son TS/Vite12.39s zaten temizdi. Yeni frontend/APIpermissionservisleri testlerde sabit; **backend kaynaklarını şimdi tam koşu bitene kadar değiştirme**.
- **Şimdi çalışan** tam backend `output/backend-analysis-full-20261104.log`, yeni tool sessionID'sini kaydet/sonucu al (353beklenir, sonuç iddiası yok). Ardından readonly kaynakDBklonunda `scripts/audit_api_smoke.py`, sonra fullEdge29 (PG55436 ve fakeSaaSgateway1). Güncel Edgekanıtları: full28/28 parentScope/insights/Analysisguardöncesi; yeni KarmaParentUI1/1 sonrası, **full29 henüz yok**. Primary034 schema değişmedi. Ana stop-local başarılı ve start-local başlatıldı (`start-analysis-final-20261104.log`); sonucu al, ardından `verify-running.cjs` canlıgiriş/RootSchool/chatbotkontrolü yapılmalı. Bu restart main'e sonParent+Analysisguard kodunu alır; önceki07:34süreç kaydı artık eskidir.

- **4 Kasım08:03 güncel:** KarmaTeacher+Parent mobil gerçek API **1/1**33.4s (`edge-parent-purpose-rechecked-20261104.log`,48224 tamamlandı): RootAPI ile yeniTeacher+Parent hesap/rol/şubeA/sınıfA/çocukB/veli bağı; personelTeacher ekranı ayrı çalışır, veliacademic+dashboard kendiBçocuğu ve yeniinsights200, staffB403/404korunur,390pxtaşma yok. İlk browser beklentisi `/teacher` idi; mevcut dualrole başlangıcı `/parent/dashboard` olduğundan test bu gerçek başlangıcı ve sonrasında Teacher ekranını ayrıca doğrular; giriş politikası değiştirilmedi. Yeni toplamEdge29; full29 henüz yok. Son TS/Vite build10.47s (`build-parent-insights-rechecked-20261104.log`) temizdi; sonrakiAnalysisUIbuild12.39s de temiz.
- **AI feature izin açığı kapatıldı:** `core/analysis_access.py`40uniqueanaliz yolunda tüm gerekli alanları ALL gruplarıyla, her gruptaki eski/yeni permission eşdeğerlerini ANY ile kontrol eder. Aynı path'in kaynakta tekrarlanan tanımları dahil53dependency güncellendi; hangi router kazanırsa kazansın kontrol var. Tek öğrenci özeti ayrıca alan bazlı projeksyonunu korur. Teacher/Parent finans/bordro/staff/birleşikokul raporu alamaz; akademik izni eklemek çok alanlı raporu açmaz. Kalan genel AI **veri doğruluğu/uydurma defaults ve hata200içeriği** denetimi hâlâ var; bu40yolun tüm hesaplamaları düzeldi denmez.
- `export_analysis_policy.py` backendpolicy→frontend/config/analysisPermissions.json üretir; backend unit bunu ve tüm gerçek kayıtlı routes'un AnalysisPermission bağımlılığını doğrular. FastAPI `_IncludedRouter` kullandığı için ilk unit app.routes path'lerini doğrudan arayıp0buldu; original_router traversal ile40gerçekroute doğrulandı, kontroller azaltılmadı. `getAnalysis` opsiyonel, yetkisiz paneller için ağ isteği yapmadan nullveri döndürür (sahteHTTPstatus yok);31çağrı/21ekran buna alındı. AIAnalytics sekmeleri yalnız tüm alanları izinli olanları gösterir ve ilkizinli sekmeyle açılır. Backend heristekte yine gerçek DB rollerini kontrol eder, frontendgüvenlik sınırı değildir.
- Son feature API+sözleşme **7/7**12.97s (`analysis-feature-permissions-rechecked-20261104.log`), UI analiz yetkileri + Parentpano + ödemeParentpath + immutableorg + seçimi koruma **9/9**15.83s (`analysis-parent-ui-final-20261104.log`). **Şimdi:** tamfrontend `frontend-analysis-full-20261104.log` session(tool sonucunu kaydet), lint `lint-analysis-final-20261104.log`, OpenAPIexport+Ruff `ruff-analysis-final-20261104.log`. Ardından backendfull353beklenir (sonucugörmeden353geçtiyazma), sonreadonlyrolaudit, fullEdge29. Ağırkontroller seri; fullfrontend bitmeden fullbackend/Edge başlatma.
- Main5173/8000 hâlâ07:34class/debt sürümü, sonParent/AIbackend kodu henüz yüklenmedi; testlerden sonra kontrollü stop/start/live gereklidir. Primary034 aynı, yeni migration yok; mevcut107tablo verisi korunuyor. Sonraki kod işi kalan genelAI data integrity,035öğrenci merchant/nonce/review,ClassCapacitykirli/null/concurrent atamalar ve diğer100+form seçimleri. Son kullanım%65/%41ordinarytrue08:00öncesi, yenidenkontrolet. PG55436açık. OtomasyonACTIVE; gerçek para/mesaj/deploy yok.

- **4 Kasım07:54 son devam kaydı:** Karma veli kapsamı ve eski duplicate temas düzeltmesi **55/55**104.08s (`parent-class-regression-20261104.log`,9434 tamamlandı): parent/account/day/outbox/checkout+class+sözleşme SQLite+PG. Bunun SONRASINDA öğrenci özet servisi değişti. Son ilk yeni parent+payment+sözleşme **11/11**15.50s (`parent-purpose-payment-first-20261104.log`), Parent-only init+status rotaları gerçek servis/sahte ağsız gateway ile kendi başka şube çocuğunda çalışır. Legacy shared student checkout artık finance.write yoksa ayrıca gerçek ownParentChild bağı ister; öğretmenlik ilişkisi başkasının çocuğu için veli ödeme izni sağlamaz. Parent UI `/parent/payments/initialize`, status purpose=parent →`/parent/payments/checkouts/{id}` kullanır. Önceki07:36 satırındaki 'karma rol kart kapsamı çözülmedi' bu erişim bakımından eskidir;035merchant/nonce/REVIEW işleri hâlâ açıktır.
- `student_insights.py` gerçek not(son20, max_score ile100'e normalize), yoklama(son30) ve izinli günlük rapor/borç özetini paylaşır. Sahte70not,0.8güven, çalışma saati, öğrenme stili/risk çıkarımları bu **tek öğrenci özet yolundan** kaldırıldı; puan yoksa null, tahmin/güven null. Her alanın read izni ayrı; staff context=finances için finance.read gerekir, Parent amacı parent.view_finances ister. `/parent/child/{id}/insights` actualguardian+ParentScope ile başka şube çocuğunda çalışır. StudentDetail demo tahmin kartları yerine gerçek metric listesi; Parent sayfası yeniinsightsyolunda ve finans izni yoksa pano finansAPI'sini çağırmaz/ödemekartını göstermez. Diğer genel AI40yol yetki/gerçekveri denetimi hâlâ açık, bunların tamamı düzeldi deme.
- Yeniinsights+ParentScope+data integrity+sözleşme **11/11**13.57s (`student-insights-rechecked-20261104.log`,95381 tamamlandı). İlk9pass2fail yalnız yeni fixture'da Grade.class_id=None verildiği için gerçek NOT NULL kuralıydı; çocukB için gerçek sınıfB oluşturularak düzeldi, ürün/şema gevşetilmedi. UI Parentpano finanstalebi yok + statusParentpath + formimmutableorg + arama/sayfa dışı seçim **7/7**6.70s (`parent-form-ui-final-20261104.log`). Genelorg alanı editte gizli, sınıf branch'i immutable/gizli; backend başkaOrg/branch'e taşıma422, aynıeskiID kabul, null422. Editte gizli seçenekler GET yapılmaz. Küçük UI testparams tipi TS2339 verdi, Record<string,unknown> açıklaması düzeltildi; yeni build sonucu alınmalı.
- **Şu an:** yeni karma veli mobil gerçek API E2E session87737 `edge-parent-purpose-first-20261104.log`; son TS/Vite build session86483 `build-parent-insights-rechecked-20261104.log`. Browser testi RootAPI ile geçiciDB'de Teacher+Parent roleuser, personelşubeA/sınıfA, kendiçocukB/veli bağı oluşturur; UI Parent academic/dashboard API'lerinde beklenmeyen403/404/500 olmamalı, staffAPI B'yi hâlâ reddetmeli. Yeni toplam Edge29; önceki tam28/28 **ParentScope/insights değişikliklerinden öncedir**. Son frontend194 de sonParentstatus+dashboard değişikliklerinden önce; şu an196 bekleniyor ama tam196 koşulmadı.
- İlk ParentScope4/4session14988 `parent-purpose-first-20261104.log` tamamlandı; önceki07:36'da yazılan belirsizsession926? geçersizdir. Yeni backend kaynakları currentmain sürecinden SONRA değişti;5173/8000 hâlâ07:34 class/debt sürümü. Primary034 değişmedi; schema migration yok. Yeni browser/TS/lint ve tam API testleri geçince kontrollü stop/start, main canlıverify gerekiyor. Sırada tambackend350beklenir (çalıştırıp sonucu oku), sonrolGETaudit/OpenAPI, tamfrontend veEdge29. Sonra kalanAI yetkileri+projeksiyonlar,035öğrenci merchant/nonce/REVIEW, kapasite/100+diğeroptionlar. PG55436 açık, ağır kontroller seri. Gerçek para/mesaj/deploy yok; otomasyonACTIVE.

- **4 Kasım07:36:** Tam Edge+PG **28/28**5.7m (`edge-all-28-workflows-20261104.log`,17195 tamamlandı): son sınıf öğretmen/aktiflik/temizleme ve yetkili muhasebe borç oluştur/düzenleme dahil. Sınıf mobil ekranı görsel olarak incelendi, taşma yok. İlk iki hedefli browser denemesinde sınıf geçti; muhasebe önce yanlış `/dashboard` başlangıç beklentisinden, sonra gerçek amount:number→schema:str422 uyumsuzluğundan kaldı. Beklenti gerçek finance/debts olarak düzeltildi; DebtCreate/Update tutarları Decimal12,2/pozitif/finite kabul eder, JSON sayı ve metin çalışır; hatalı UUID/tür/tarih/tutar/null422. Öğrenci/tür değişimi borçta açıkça reddedilir ve edit formunda sunulmaz; status tahsilat/vadeden hesaplanır. Hiçbir assertion düşürülmedi. Son API+sözleşme **10/10**19.58s (`class-finance-contract-final-20261104.log`).
- Tam frontend **194/194**,38dosya65.38s (`frontend-class-finance-full-20261104.log`,4834 tamamlandı); yeni arama/sayfa dışı seçimin korunması unit testi dahil. Son lint çalışıyor, `lint-class-finance-20261104.log`. `start-class-finance-20261104.log`: kontrollü stop/start başarılı; ana5173/8000 class/debt düzeltmeleriyle açık,034değişmedi. Ardından gelen küçük frontend step1/kuruş min0.01 düzeltmesi frontend194'e dahildir; Edge28 sonrasıdır. Henüz son canlı kontrol alınmadı.
- Yeni iki gerçek veli hatası önce SQLite'da kanıtlandı: `parent-purpose-before-20261104.log`2failed (legacy aynı user'a bağlı birden fazla Parent→MultipleResultsFound; Teacher+Parent şubeApersonel→kendi çocukBveli listesinde yok). `parent_student_ids` yalnız gerçek kullanıcı/aynıkurum/aktif/silinmemiş Parent+Student bağlarını Core sütunlarında toplar; hesap/kayıt birleştirme/silme yok. `require_parent_child_access` çocuğa gerçekten bağlı ownParent'ı seçer, duplicate kayıtlar500 yapmaz. Parent router'ın server-owned dependency'si **yalnız Parent rolünde ve yalnız bu router'da** request TenantContext.parent_portal açar; personel şube sınırını veli amacı için kaldırırken accessible IDs'yi yalnız kendi çocuklarına, izinleri parent.*'a daraltır. Normal staff API isteği şubeAolarak kalır. Header/body bunu business endpointinde etkinleştiremez.
- Parent my-children duplicate teması tek çocuk listesinde toplar; finans/yoklama eski scalar-one kontrolleri ortak yetkilendirmeye alındı; silinmiş borç/yoklama dönmez ve year1..9999. Doğrudan duyuru alıcıları çocuğa bağlı tüm ownContact'ları kapsar. **Şu an** ilk yeni parent SQLite+PG4test session926? doğru tool sonucu:session çıktısını/`output/parent-purpose-first-20261104.log` oku; henüz sonuç iddiası yok. Bu Parent değişiklikleri main restartından SONRADIR, primary süreç henüz bunları yüklemedi. Parent ödemesi router'ı `/payments/iyzico` ayrı olduğundan karma rol kart ödeme kapsamı hâlâ sonraki035/payment işinde; çözülmüş sayma.
- Kaynak dosyalarda başka etkin project chat07:32kontrolünde yok, AGENTS yok. Son kullanım%49/%39ordinarytrue. Sıradaki parent testleri/negatif duyuru-finans-yoklama kabulü, TS/lint/OpenAPI, tam backend/son rol audit, primary restart/canlı. Genel AI route incelemesi40unique yolun birçoğunda yalnız get_tenant_context bulunduğunu gösterdi; feature izni ve cross-domain finans/sağlık projeksiyonları ayrıca düzeltilecek. Öğrenci checkout035merchant/nonce/REVIEW ve diğer100+seçimler de hâlâ içiş. OtomasyonACTIVE, gerçek para/mesaj/deploy yok.

- **4 Kasım07:24 devam:** `backend-address-full-20261104.log` tamamlandı: **340/340**,646.60s;034/adres/privacy dahil tam backend temiz. Canlı `live-address-final-20261104.log` geçti. Salt okunur kaynak DB klonunda rol GET audit **2123/2123**,11rol×193yol:1216HTTP200+907beklenen403, beklenmeyen500/404/401 yok (`api-smoke-address-20261104.log`,docs/api-smoke-results.json); bu rapor aşağıdaki yeni class/debt seçenek yollarından ÖNCEDİR. Session51981/6581 tamamlandı, yeni iş bekleme talimatı değildir.
- Sınıf formu öğretmen/aktiflik alanlarını sessizce yok sayıyordu: common ClassCreate/Update teacher_id/is_active gerçek alanları+UUID/null/uzunluk doğrulaması; sameOrg/etkinTeacherRole/şube uygunluğu, duplicate409; API teacher_id/name/description döndürür. Birincil teacher temizlenirken eski ClassTeacher ek atamaları korunur. Sınıf listesinde öğretmen adı için /users?page_size1000 ve her satır AI isteği kaldırıldı; tek minimal ad sorgusu kullanılır. Class/Parent AI overview ayrıca kendi read iznini ister. Genel AI yetki denetimi hâlâ açık.
- Muhasebe borç formundan API'nin kullanmadığı kurum/şube/akademikyıl alanları çıkarıldı. Class.write için `/classes/teacher-options`, finance.write için `/debts/student-options` yalnız ownOrg/şube minimal id/name döndürür; genel kullanıcı/öğrenci dizini izni gerekmez. Arama+sayfalama ve sayfa dışı mevcut seçimi döndüren selected_id var, yabancı seçimi döndürmez. `ResourceChoice` bunları erişilebilir native seçim+arama+sayfalama/iptal/retry ile kullanır. Diğer generic100+seçenekler henüz çözülmedi.
- İlgili yeni `test_class_management.py` ilk SQLite+PG **6/6**16.79s (`class-finance-management-20261104.log`), son overview izin assertionları bunun ardından eklendi; tekrar gerekli. TS/Vite build temiz8.95s (`build-class-finance-20261104.log`). **Şu an:** Edge+PG iki yeni class/finance senaryosu session27484, `edge-class-finance-20261104.log`; sonucu al. Test runner yalnız temp DB'ye en az yetkili accountant ekler (finance.read/write/dashboard.read, öğrenci/kurum/şube dizini izni yok). Yeni toplam Edge28 senaryo;26/26 veya28/28 tam koşu henüz yok.
- Primary034 verisi aynı, migration yok; main5173/8000 class/debt son backend değişikliklerinden önceki süreçle açık. Son testler sonrası kontrollü stop/start ve canlı kontrol gerekli. Sonraki: browser hatası varsa düzelt; tam frontend/lint, sözleşme+son API testleri/OpenAPI ve son rol audit, tam Edge28. Sonra öğrenci ödemesi035/merchant/nonce/REVIEW, mixed veli-personel amaç kapsamı, diğer AI izinleri/100+seçenekler. Kullanım%38/%37ordinarytrue; PG55436 açık. Gerçek para/mesaj/deploy yok, otomasyonACTIVE.

- **4 Kasım07:03 PRIMARY ARTIK034 — tekrar apply çalıştırma.** `verify_student_address_upgrade.py --apply` kontrollü stop sonrası başarıyla uygulandı; `.codex-build/local/migration034-verification.json`107tablonun tüm eski kolon/satır SHA'larını ve sayımlarını koruduğunu doğrular. Yedek: `backend/school_management.before-student-address-20261104-070132.db`. Son start-local başarılı,5173/8000 yeni034/modelle açık; eski033 ara kayıtlarını uygulama talimatı sayma. Hesap/parola/üyelik/fiyat değişmedi; öğrenci eski adresleri tahminle doldurulmadı.
- Adres/not/enrollment_date ve schema/privacy ilgili testleri SQLite+PG6/6; clone ve primary iki aşamalı koruma doğrulandı. Health_notes yazma health.write gerektirir; normal öğrenci kaydı yetkisi tıbbi alanı değiştiremez. Mobil StudentCRUD **1/1**33.1s (`edge-student-fields-rechecked-20261104.log`): adres/not gerçek döner ve null temizlenir, enrollment_date güncellenir, sınıf kaldırılabilir. Son edit-fetch abort/loading koruması ardından yavaş seçenekler + Root kurum + boş branch/class + edit mevcut FK unit **2/2**4.29s (`resource-form-options-rechecked-20261104.log`). İlk unit ad eşlemesi JSDOM'un zorunluluk yıldızı boşluk farkından kaldı, isimler regexle eşlendi; değer/assertionlar aynen korundu. Son TS/Vite build temiz `build-address-form-20261104.log`10.78s.
- **Şimdi çalışan:** tam backend `output/backend-address-full-20261104.log` (sonraki tool sessionID sonucunu al), küçük main canlı read/control `output/live-address-final-20261104.log`. Full backend süresince yeni backend kodu değiştirme; frontend/UI araştırması ve doküman yapılabilir. Sonra readonly rol GET audit (`scripts/audit_api_smoke.py` kaynakDB'nin geçici kopyasında), OpenAPI/lint ve gerekli tüm Edge26 tekrarları. Mevcut Edge kanıtı24/25 + kalan admin sayfa taraması hedefli1/1; tam26/26 henüz yok. Ağsız fake gateway yalnız test runner'da, gerçek para/mesaj/deploy yok. PG55436 açık, bitince doğru datadir ile durdur.
- Sonraki geliştirme önceliği öğrenci kart ödeme akışında nonce/şifreli token-resume, her kuruma ayrı merchant ve eski ayarla açılan işlemler için şifreli merchant snapshot'ı, PAID_REVIEW/haricen doğrulanan iade uzlaştırması ve manüel tahsilatla çakışma koruması. Yeni kolon/tablo gerekirse **035** çıkar;034 artıkprimary'de değiştirilemez. Konfigürasyon/UI yalnız Owner/org_admin/Root, ödeme anahtarları/audit redaksiyonu ve kurum sınırı testleri zorunlu. Daha sonra mixed veli-personel şube kapsamı, servis100+ sürücü araması, kayıtların kalan null/sınırları/100+form seçenekleri. Form genel seçenek endpointleri bazı özel yalnız-yazma rollerine gereksiz read izni isteyebilir; amaç odaklı minimal form seçenekleri gerekebilir. Satış kabulü halen tamamlanmadı, otomasyonACTIVE.

- **4 Kasım07:00 adres ve form devamı:** Önceki menü düzeltmesi hedefli tüm admin sayfa taramasında **1/1**1.6m geçti (`edge-visible-pages-rechecked-20261104.log`,62840 tamamlandı). Öncesi24/25 tam koşu + bu hedefli1;25/25tam tekrar henüz denmedi. Yeni034 yalnız nullable students.address ekler; model/core API adresi kaydeder, normal notları geri döndürür, enrollment_date güncellemesini işler, boş optional alanlar null temizlenir. Adres/not yalnız students.write, tıbbi not health.read ile döner; health_notes yazmak ayrıca health.write ister. İlgili SQLite+PG **6/6**16.21s (`student-address-privacy-20261104.log`);034 idempotent iki DB şema testi eski öğrenci kolonlarını ve hesapları korur.
- `backend/scripts/verify_student_address_upgrade.py` readonly clone+isteğe bağlı --apply (API stopped/socket kontrolü, backup,107tablo tüm eski kolon satırlarının SHA korunması) eklendi. Clone034 **107 tablo korunarak geçti** (`migration034-clone-20261104.log`, `.codex-build/local/migration034-clone-verification.json`). **PRIMARY HÂLÂ033**,034 uygulanmadı; model yeni olduğu için main'i restart etmeden önce yedekli --apply yapılmalı. Main mevcut033 eski-yüklü sürümle5173/8000 açık; gerçek veri/hesap değişmedi.
- MobilStudentCRUD testi ilk kurum seçimi kaybolmasını yakaladı: ResourceForm getDefaults yanlışlıkla kurumUUID'sini branch_id/class_id'ye de veriyordu; async seçenekler gelmeden native select kaydolunca organization_id boşalıyordu. Yalnız org defaultu korundu, seçenekler hazır olmadan form açılmıyor; options ve edit fetch AbortController, yeni kayıt reset ve edit loading koruması eklendi. Son edit-abort kısmından önce mobil **öğrenci adres/not/tarih/sınıf temizleme1/1**33.1s (`edge-student-fields-rechecked-20261104.log`,34443 tamamlandı). Parent account native-checkbox stil/işlemi de ilk birleşik koşuda1/1 geçti (student kısmı kurum defaultundan kaldı).
- Yeni `resource-form-options.test.tsx` yavaş seçenekler ve Root seçili kurum/boş şube-sınıf + hızlı edit kaydını doğrular; **şu an session sonucunu oku** `output/resource-form-options-20261104.log`. Yeni Student-registration E2E eklendi; tam Edge artık26 senaryo. Sonrasında TS/lint, primary yedekli034/stop-start/live doğrulama, güncel rol GET audit ve gerekli regresyonu tamamla. GeçiciPG55436 açık, test başlatırken -o '-h 127.0.0.1 -p 55436' şart; Core/full ağır işler seri. Kullanım son%15/%34ordinarytrue. Yalnız bu chat aktif; diğer dosyalardaki eski farklar korunuyor.

- **4 Kasım06:47 kabul devamı:** Son PG Edge tekrarı **24 geçti,1 kaldı**4.3m `edge-all-workflows-fixture-final-20261104.log` (session61129 tamamlandı); tüm yeni Owner/veli, publicsite, SaaS yenileme, signed-hostedcheckout ve servis senaryoları geçti. Kalan admin-visible-pages testinde Root çalışma alanına geçişin URL'si hazırken eski tek SaaS menüsü anlık olarak hâlâ ekrandaydı: allTextContents bir bölümlük snapshot alıp yalnız Yönetim'in7 linkini tarıyordu. Login helper artık okulun Sistem menüsünün hazır olduğunu bekler; aria-expanded beklemesi korunur. Hedefli admin sayfa taraması `edge-visible-pages-rechecked-20261104.log` başlatılıyor, sonucu alınmalı. Hiçbir test standardı/20+link beklentisi düşürülmedi.
- Bu tekrarın iki altyapı başlangıç hatası uygulama sonucu değildir: PG başlatılırken `-o '-h127.0.0.1 -p55436'` unutulduğundan port55436 bağlanamadı; yalnız test datadir durdurulup doğru portla açıldı. Ardından reset fixture yolu Vite proxy dışında olduğu için25 senaryo fixture'da404 kaldı; test-only yol `/api/__acceptance/reset-limits` olarak düzeltildi ve24 senaryo gerçekten geçti. Üretim API'sinde bu yol yok; app.main importuna eklenmedi. Her senaryo içindeki gerçek5/min giriş limiti açık kalır.
- GeçiciPG55436 açık, ana5173/8000 güncel sürümde açık; başka etkin C:\Okul360 chat yok, AGENTS yok. Yeni address/model/migration henüz yazılmadı; ilk olarak admin tüm sayfa GET kontrolünü bitir, sonra034 ile öğrenci adresi kalıcılığı ve form alanlarının okunması/temizlenmesi üzerinde çalış. Daha sonra öğrenci ödeme nonce/şifreli resume/kuruma özel merchant ve REVIEW uzlaştırma. Rol GET audit henüz bu sürümde tekrar koşmadı. Kullanım yeni penceredeordinarytrue.

- **4 Kasım06:40 devam / yenilenen kullanım %1-%32 ordinary=true:** Önceki pencere03:37'de100/ordinaryfalse oldu, yeni geliştirme başlatılmadı. Daha önce başlatılmış final işler tamamlandı: **tam frontend191/191**,36dosya83.08s (`frontend-final-20261104.log`), son lint ve TS/Vite build temiz (`lint-last-20261104.log`, `build-last-20261104.log`7.66s); OpenAPI son yazma doğrulamalarıyla yeniden üretildi, F821/F823 temiz. Kontrollü main stop/start başarılı,5173/8000 güncel tüm kodla açık. `live-workflows-final-20261104.log` canlı giriş/pano/API proxy/chatbot ve modül kontrolünü geçti; `output/running-local-verification-20261103.json` içeriği bu yeni koşuyla güncellendi (dosya tarihi eski adda), failures[] kontrol edildi. GeçiciPG doğru datadir ile durdurulmuştu; bu devamda testler için tekrar açılıyor. Eski80573/92036 işler sonuçlandı, yeni geliştirme onlara bağlı değil.
- İlk iş, kayıttaki üç düzeltme sonrası tüm Edge25 senaryoyu PG'de yeniden koşmak; ardından son rol GET audit. Başka etkin checkout çalışması kontrol ediliyor; AGENTS yok. Ana veri/hesap/parola/paket değişikliği ve gerçek ödeme/mesaj/deploy yapılmadı. Kabul ve kalan iç işler önceki03:34 kaydındaki sırada; tam satış kabulü yok.

- **4 Kasım03:34 son kayıt / kullanım %98-%31 ordinary=true:** Son öğrenci/veli yazma doğrulamaları **8/8**18.21s (`output/write-validation-final-20261104.log`, session60364 tamamlandı): common.StudentFields UUID/tarih/enum/ad/uzunluk/null ve doğum tarihi alias eşleşmesi, ParentUpdate zorunlu alan null reddi; yinelenen öğrenci numarası409, geçersiz girdiler422 ve mevcut veri korunur. core_modules create/update flush IntegrityError409; date_of_birth:null gerçek birth_date alanını temizler; sınıf açıkça kaldırılarak şube değiştirilebilir. Yeni migration yok. Öğrenci address mevcut modelde hâlâ saklanmıyor (form/API alanı var); ayrıca ele alınmalı, çözülmüş sayma.
- Tam Edge son koşu **22 geçti,3 kaldı**4.6m (`edge-all-workflows-final-20261104.log`, session57531 tamamlandı). İlk20eski senaryoda yalnız admin-visible-pages menü toplayıcı7 linkte kaldı; nav artık aria-expanded verir, test açıldığını bekler. Parent-account checkbox bir kez durum değiştirmedi; generic checkbox doğrudan native input olarak Field'a verildi (etiket/id doğru bağlanır), tekrar test gerekli. Publicsignup, farklı senaryoların aynı IP5/min giriş bütçesini biriktirmesiyle429 oldu. `e2e/fixtures.ts` her bağımsız senaryodan önce yalnız geçici browser runner'daki `/__acceptance/reset-limits` yoluyla test login penceresini ayırır; üretim uygulamasında bu yol yok, test içi5/min koruması aynen açık. Altı spec artık bu fixture'ı kullanır. **Bu üç son düzeltmeden sonra tam Edge henüz tekrar koşmadı.** Tam25/25 deme.
- Son önceki frontend tam189/189; ardından StudentCheckoutStatus UI hedefli7/7 geçti (`payment-status-catalog-ui-20261104.log`), backend öğrenci ödeme+kontrat35/35 (`student-payment-contract-final-20261104.log`). Son lint/build (`lint-final-20261104.log`, `build-final-20261104.log`) temiz ama checkbox/native/menu-aria düzeltmelerinden öncedir. Yeni finalfrontend işi başlatılacak; sonucu/sessionID sonraki kayda eklenecek. Sonrasında kontrollü main stop/start+canlı verify, güncel OpenAPI/rol GET audit ve Edge yeniden koşusu gerekli. Primary hâlâ033, mevcut5173/8000 açıktır fakat yeni API kodunu kontrollü restartla almalı; gerçek fiyat/paket/hesap eklenmedi.
- GeçiciPG55436 açık; ağır testler seri tutulur. Şu an shell test session açık değil. Kullanım100/ordinaryfalse olursa yeni geliştirme/test aşaması başlatma, mevcut işin sonucu/koruma kaydını tamamlayıp saatlik ACTIVE otomasyonu bekle. Sıradaki iç işler önce yukarıdaki kabul tekrarları, sonra öğrenci ödeme nonce/şifreli resume/kurum merchant/review, karma veli-personel şube kapsamı, öğrenci address, diğer kayıtların null/sınırları ve servis100+ sürücü araması. Üretim/satış kabulü henüz tamamlanmadı; yalnız dış kabul kalmış gibi otomasyonu kapatma.

- **4 Kasım03:25 en yeni:** Genel backend son koşu **331 geçti,1 sözleşme testi kaldı**724.62s (`backend-payments-parent-full-20261104.log`). Tek neden frontend ödeme URL'sindeki `${action}` statik analizde çözülememesiydi; çağrılar açık checkout/resume/payment-status/activate-free endpointlerine ayrıldı, test gevşetilmedi. Son kurum rol kataloğu + SaaS + public signup + sözleşme tekrarı **24/24**73.76s (`catalog-contract-final-20261104.log`). Yeni kurumlar tüm ROLE_NAMES yerel rollerini alır; kullanıcı profilindeki eksik-rol tamamlama Owner/org_admin/Root yetkili, kurum kilidi/idempotenttir ve eski özel rol adı/UUID/izin/atamalarını değiştirmez. Bu düzeltmeden sonra tam332 gibi sonuç sunma.
- Tam frontend **189/189**,35 dosya100.11s (`frontend-all-workflows-full-20261104.log`); TS/Vite temiz (`build-catalog-rechecked-20261104.log`19.46s). Bunların ardından aşağıdaki küçük checkbox/veli-ödeme takip değişiklikleri yapıldı, hedefli sonuçlar okunmalı. OpenAPI yeni ödeme/veli/rol endpointleriyle `scripts/export_openapi.py` üzerinden üretildi; operasyon ID benzersizlik sözleşmesi24içinde geçti. Son F821/F823 ve pip check temiz (rol kataloğu öncesi; son tekrar gerekli).
- **MobilEdge+PG yeni Owner→User→yerelVelirolü→iletişimkaydıbağlantı→veliLogin ile kurum dışı öğrencileri görmeme; parentbildirim false→true, telefonu null temizleme/SMS kaydı ve servisrota/durak/katılım/biniş/iniş kalıcılığı2/2**,34.2s `edge-parent-transport-rechecked-20261104.log`. Servis görseli incelendi, sayfa taşmıyor. İlk iki hata generic checkbox'ın erişilebilir adının Etkin olması (aria-label gerçek alan adıyla düzeltildi) ve testte seçenekleri de içeren select label exact eşleştirmesiydi (combobox rolüyle düzeldi).
- Eski veli modalında toplam borç PAID olunca kartı başarılı sanan takip kaldırıldı. `StudentCheckoutStatus` yalnız yetkili `/payments/iyzico/checkouts/id` kaydına bakar, risk incelemesinde veya ağ zaman aşımında ödeme başarısız/başarılı uydurmaz; manuel kontrol ve doğru cleanup var. Eski öğrenci gateway retrieve isteği conversationId'yi artık açıkça gönderir ve test sahte gateway'i bunu doğrular. **Bu son değişiklikler sonrası backend hedefli iş session13535** (`student-payment-contract-final-20261104.log`), **UI hedefli session43320** (`payment-status-catalog-ui-20261104.log`) henüz sonuçları alınmadı. Şu an başka ağır iş yok. Sonrasında tüm Edge25 senaryo, rol GET audit, son lint/build, kontrollü ana stop/start+canlı doğrulama, PG kapatma ve bu kaydı güncelleme gerekli.
- AnaDB033 ve hesaplar aynen korundu; yeni migration yok. Ana5173/8000 henüz eski public-site sürümü. GeçiciPG55436 açık. Son kullanım **%83/%29 ordinary=true**, her aşamada yeniden kontrol et. Otomasyon ACTIVE, iç işler halen var: öğrenci ödeme nonce/şifreli resume/çoklu kurum merchant ayarları ve borca uygulanamayan tahsilat uzlaştırma UI; karışık veli/personel şube kapsamı; kalan yazma/null/sınır doğrulamaları, servis sürücü seçenekleri100+arama ve eski kayıt çakışmaları; gerçek sağlayıcı/mobil cihaz/restore/load/dış erişim kabulü. Otomatik geliştirmeyi yalnız dış kabul kalmış gibi durdurma; satış hazır ilan etme.

- **4 Kasım03:14 ara kayıt:** Yeni SaaS hosted checkout **Edge+PG1/1**23.3s (`output/edge-subscription-checkout-final-20261104.log`): sağlayıcı bağlantısı→gerçek callback303→fraud0 üyelik kapalı→fraud1 üyelik açılır→tekrar sorgusu ikinci uzatma yapmaz; ekran görseli incelendi. İlk denemeler yalnız locator ve test sağlayıcı HTML charset sorunu nedeniyle kaldı, düzeltilip geçti. Gerçek sağlayıcı bağlantısı yok, fake yalnız `scripts/acceptance_saas_gateway.py` içinde testDB güvenlik kontrolüyle kurulur.
- Auth eski oturum yarışı düzeltildi: setSession/clearSession generation, request/response pinleme, refresh sonucu hesap/generation/token kontrolü; geç eski401/402/200 yeni hesabı ezmez, Root yetkisi kaldırılınca kurum header'ını silip global retry yapmaz. İlgili auth **15/15**3.61s (`auth-session-race-final-20261104.log`).
- Öğrenci ödeme `IYZICO_PAYMENT_ENABLED` ve açık `IYZICO_ORGANIZATION_ID` kapsamı eklendi; başka SaaS okulu ortak merchant'a gidemez. Eski callbackler yeni başlatma kapalı olsa da aynı kurum merchant'ı ile uzlaştırılır. Yeni borç/checkout durum GET API'leri veli çocuk/kurum kapsamında; bağımsız PaymentPage script/HTML çalıştırmadan gerçek borç+billing+doğrulanan hostedURL kullanır, otomatik init/polling yok. Veli modalı güvenli bağlantıyı yeni sekmede açar, açık olmayan kurumda Öde düğmesi görünmez. Öğrenci kapsam+veli/outbox **31/31**75.63s (`student-payment-scope-20261104.log`). Öğrenci ödeme başlatma nonce/şifreli resume ve çoklu kurum merchant ayar UI'si ayrıca tamamlanmalı; sağlayıcıdan para alınıp borca uygulanamayan REVIEW için kurum finans uzlaştırma ekranı halen açık iş.
- Veli iletişim kaydı↔giriş hesabı açıkça bağlanıyor: `parent_account_service`, GET parents/id/account-options arama/sayfalama, PUT parents/id/account. Veli+yönetim izinleri birlikte; etkin Parent rolü, kurum, Root hariç, başka iletişim kaydına bağlı olmama ve kurum kilidiyle atomik. SQLite+PG **2/2**7.31s (`parent-account-link-20261104.log`), yalnız bağlanan kaydın öğrencileri görünür; hesap/parola/izin değiştirilmez. ParentAccountAccess UI profile eklendi. Eski parent formunda sunucuda olmayan notification_email/sms/whatsapp alanları gerçek receive_notifications ve sms_phone/whatsapp_phone ile değiştirildi; Parent PUT boş iletişim alanlarını null ile temizleyebilir. Bu son form değişikliği henüz tarayıcı kabulünden geçmedi.
- BusRouteManager UI eklendi: rota oluştur/düzenle optimistic timestamp+nonce, durak oluştur/düzenle, öğrenci arama, gün bazlı katılım upsert, şimdiki biniş/iniş nonce, gerçek son telemetry ve rota/durak/katılım sayfalama. BusPage loading sırasında yönetim formunu düşürmez. Yeni rota mobil Edge senaryosu `frontend/e2e/transport-management.spec.ts` yazıldı **henüz koşmadı**. Yeni ilgili UI **18/18**19.05s (`new-workflows-ui-20261104.log`) sonrası küçük sayfalama/form değişiklikleri yapıldı. Son lint temiz; ilk TS BusOptions tipi/key hatası düzeltildi, build yeniden temiz (`build-all-workflows-rechecked-20261104.log`). Son parent form değişikliği sonrası yine build gerekli.
- **Önemli yeni eksik:** platform.provision yeni kuruma yalnız Owner rolü yaratıyor; temiz DB/yeni kurumda Parent/Teacher vb rol kataloğu yoksa okul sahibi bunları atayamaz. Sonraki öncelik yeni kurumlara standart yerel rol kataloğunu eklemek, önceden oluşan kurumlar için izinli/idempotent eksik-rol tamamlama düğmesi; mevcut özel rolleri/izinleri değiştirmeden test et. Böylece yeni kurum Owner→User→Parent bağlantısı tam tarayıcı kabulü yapılmalı.
- **Çalışan işler:** tam backend session17113, `output/backend-payments-parent-full-20261104.log`, son görülen %65; bitene kadar backend kaynağı değiştirilmedi (sonraki rol kataloğu değişikliği ayrı doğrulanmalı). Build session58407 tamamlandı ama sonucu henüz write_stdin ile tüketilmedi. Başka ağır test yok; geçiciPG55436 açık. Kullanım son %66/%26 ordinary=true. Ana5173/8000 halen eski public-site backend'i; yeni ödeme/veli güncellemeleri kontrollü restart/canlı test bekliyor. Genel frontend ve Edge, rolGET audit/OpenAPI, son doküman ve PG durdurma sırada. Tam satış kabulü yok; iç işler sürdüğü için otomasyonu kapatma.

- **4 Kasım 02:50 güncel devam:** Root çalışma alanı ve public site sonrası tam backend **311/311** (554.28s, `output/backend-platform-public-full-20261104.log`), tam frontend **176/176** (56.99s, `output/frontend-platform-public-full-20261104.log`) geçti. Bunlar aşağıdaki yeni ödeme kodundan öncedir. Root seçili kurum için form kullanıcı bağlamı `workspaceUser` ile düzeltildi; API refresh retry kurum A'dan B'ye kaymaz (4/4); `.codex-build/local/verify-running.cjs` Root önce platform sonra gerçek kurumu UI düğmesiyle açacak şekilde güncellendi, henüz yeni canlı koşusu yapılmadı.
- SaaS kart tahsilatı artık ayrı `saas_gateway.py`, `subscription_checkout_service.py`, `subscription_payments.py` ile gerçek initialize/retrieve protokolünü kullanıyor. Yalnız SAAS merchant ayarları; imza, tutar/kalem/para birimi, fraud onayı, şifreli token/URL, nonce ve kurum kilidi; sağlayıcı ağ çağrısı sırasında kurum yazma kilidi tutulmuyor. Root PAID_REVIEW uzlaştırması ve dışarıda doğrulanan iade kaydı (para göndermeden), sıfır tutarlı gerçek paket etkinleştirmesi eklendi. Mevcut033 şeması yeterli; migration/ana veriye ek yazma yok. `cryptography==50.0.2` requirements ve .venv güncel. Özellik `SAAS_PAYMENT_ENABLED=false` varsayılanında kapalı; gerçek anahtar/fiyat/ödeme eklenmedi.
- İlk checkout testleri **10/10**28.25s; genişletilmiş checkout+billing+veli/outbox **52/52**116.79s `output/payment-safety-20261104.log`, geçici SQLite ve PG. Yanlış tutar, sahte imza, eşzamanlı tekrar, sağlayıcı risk incelemesi, kapalı kurum, stale sözleşme, Root idempotent uzlaştırma/iade ve ücretsiz paket dahil. Eski öğrenci tahsilatında eksik fraudStatus kontrolü düzeltildi: 0/-1/eksik durum borç düşürmez, onay1 sonrası tek makbuz oluşur. Henüz öğrenci merchant kurum ayrımı ve eski bağımsız PaymentPage düzeltmesi tamamlanmadı.
- Yeni SubscriptionCheckout/PaymentReview arayüzleri bağlandı; ilgili UI **7/7**4.15s `output/checkout-ui-20261104.log`; TS/Vite build temiz `output/build-checkout-20261104.log`. Son küçük test/etiketler sonrası son lint/build ve geniş frontend tekrarı gerekli. Kart alanı uygulamada yok; HTTPS sağlayıcı bağlantısı doğrulanır. Geçici browser runner için yalnız test DB'sinde çalışan ağsız fake sağlayıcı eklendi; **Edge checkout işi session31656**, `output/edge-subscription-checkout-20261104.log`, sonucu henüz okunmadı. Gerçek sağlayıcıya bağlanmaz.
- Sırada bu Edge sonucunu tamamlamak; öğrenci ödeme merchant kapsamı/bağımsız sayfa; auth refresh eski oturum yarışı; veli iletişim kaydı-giriş kullanıcı bağlantısı; Bus yönetim UI ve diğer yazma sınırları. Docs/OpenAPI, rol audit, canlı kontrollü restart ve geniş Edge tekrarları yeni ödeme yollarıyla güncellenmeli. Ana5173/8000 eski yeni-site sürümüyle açık; yeni ödeme backend'i restart sonrası yüklenecek. GeçiciPG55436 açık, sonunda doğru datadir ile durdur. Son kullanım **%48/%23 ordinary=true**, reset yok; her yeni aşamada tekrar kontrol et. Başka ajan kullanılmadı, mevcut hesaplar/parolalar korunuyor, gerçek ödeme/mesaj/deploy yok.

- **4Kasım01:50 publicsite/Rootworkspace ilerleme:** / ana tanıtım, /fiyatlandirma gerçekaktifpaketler, /kayit paketliOwnerkayıt hazır. MarketingPage/SignupPage/marketing.css mevcutSCS360SVG+yerelfont+HTMLürünörneği kullanır; müşteri/istatistik/referans/fiyattahmini yok. PublicGET/plans yalnızürünkataloğu; POST/signup3/min+HMACnonce+globale-posta/kurumuniqueconflicthandling. Anonimkayıt Rootyetkisi/dönem seçemez, yeniOwnerPENDING_PAYMENT olur; ödeme doğrulanmadan işAPIleri402, ödemeekranıaçık. Rootprovisioneskiakışıaynenkorur. PublicsignupilkOwnerPermissionseed farklıplan yarışındaRootrownoopmutexileserileşti. Şemadeğişikliğiyok,primary033kalır.
- Backend workspace4/4; publicsignup+purelifecycle **7/7**13.00s (public-signup-rechecked-20261104.log),sonmutex/Principalprivate/headerdocsdeğişikliklerisonrayereruntamgerekli. İlk5fail2tanependingplatformisteğinde403yerine402beklentisi,2tanetestaynıkurumadınameuniqueçatışması,1tanepureSimpleNamespaceperiod_startfixtureeksikliğiydi; testverisidüzeltildi,getattrgüvenlidüzeltme yapıldı. Gerçeködeme yok.
- İlgiliUI **79/79**7.13s marketing-ui-first-20261104.log;build-marketing-first temiz. **MobilEdge+PGwebsatınalma/SaaSworkspace1/1**,29.4s edge-public-site-first-20261104.log: gerçektestpaket→anonimsitefiyat→kayıt→ödemeöncesiengel→Rootmanüelkabulödemesi→aktifüyelik→Rootokuldüğmesi→doğruScopeheader/diğerokulöğrencisigizli→platformadön. Gerçekücretyok,hepsigeçiciPGDB. Görseller marketing-mobile-20261104.png/platform-control-20261104.png; mobilgörselincelenditaşmayok.
- Primaryiçinkontrollüstop/start şuankomutçalışıyor (sonexecsessionsonucunukontrolet);frontendAPIheaderretry yeni test output/platform-header-retry-20261104.log. Tamfrontend170eski,RootUI23dahaönce,ilgili79yeni;tamtekrarhenüzyok. acceptance.spec.ts Rootloginhelperı artıkUIileKabulTestOkuluçalışmaalanınıaçar. Liveverify-running.cjs **hâlâeskiRoot/dashboardvarsayımındadır**,Rootönce/platformsonraasılkurumuUIButonuylaşeçerekdüzelt;publicRouteana / olunca eskiRootcachedsession/ testhelperıuyarlandı.
- Fiyat/paketadlarıveşube/öğrenci/kullanıcısınırlarıiçin asyncoptionalbilgisorususoruldu;paneldenkendisitanımlayabilirveyaşöylepaylaşabilir. Yanıtbekleyişindegeliştirmeyidurdurma. Primaryfiyat/paketoluşturulmadı;publickatalogboşsa"Paketlerhazırlanıyor". SitesbecerisiLocalonlyişakışı,kullanıcıdağıtımyasağınauyuldu.
- Sırada UIilküyelik"yenile"metinlerinidüzeltmek,RootworkspacegirişLivehelperı,genişRootscope/API/rol/Edge/Frontend+Backendregresyonu;sonraSaaScheckoutayrımerchant/imza/şifreliToken/fraud/review.UygulamaeskiIYZICOglobaltuitionmerchantyenimüşterilereortaksevk edilmemeli;SaaSmerchantayrıkalmalı,kurumatuitionmerchantbağlamıayrıca kabul edilmeli. Veliiletişimkaydı→girişUserilişkisiOwnerUI/APIakışıayrıca doğrulanmalı; BusPageyarımiş devam. GeçiciPG55436açık,aynıdosyalardabaşkachatçalışmasıyok. Sonkullanım%14/%18ordinarytrue.

- **4 Kasım01:29 yeni kapsam/çalışma:** Kullanım yeni pencerede%7/%17ordinarytrue; resetaracıkullanılmadı. Saatlik otomasyonun promptu kullanıcı tarafından yeni kapsamla zaten güncel: superadmin yalnızSaaSanaalanı,kurumdüğmesiyle seçiliokulçalışmaalanı,publictanıtım/fiyat/üyeliksatınalmawebsitesi. Sites1.1.3becerisi/presentation-led/localpreviewokundu; kullanıcı üretime dağıtım istemediğinden mevcutcheckoutta local-only,Sitekaydı/publishyok. AGENTSyok,diğerC:\Okul360chatleriactivedeğil.
- Rootworkspace kodu eklendi: backend/core/platform_workspace.py request-only principal; X-SCS360-Organization-Id yalnızgerçekRootaçabilir, auth/platform/subscriptionpublicyolları asılhesapta kalır. TenantContext.platform_admin featureyetkileriverir ama is_super_adminFalse sayesinde kurumORM/satırkapsamıkorunur, RootDBhesabıkurumdadeğişmez;beforeFlushyalnızgerçekactorFKistisnası,varolan kotaRootkontrolükorunur. PlatformworkspaceAPIseçenek. Yeni4APItestSQLite+PG **4/4**11.24s platform-workspace-first-20261104.log.
- FrontendplatformWorkspace sessionStoragetabbağlamı,ModeGuard,Rootdefault/platform,RootanaalansadeceSaaSmenüsü/Chatbotgizli,kurumdüğmesi/servercheck,seçilibaşlık/platformadöndüğmesi,herscopeOutletremount. Axiosheaderişlemkurumunuilkgönderimdepinler;refreshretrykurumdeğişiminekaymamalı (ilgilitesteklenmelı). İlgiliUI **23/23**15.24s platform-ui-first-20261104.log. Ana backend hâlâöncekisüreç; yeniendpoint/restartfullkontrollersonra. Mevcut170/26eskiolarakayıtlı.
- Şuansırada: Rootworkspacegenişnegatif/aktör/servistestleriveheaderretrytesti; publiccatalog+pendingkayıt+satınalmawebsayfası,gerçekpaketkataloğufiyatları(noinventedprices). Checkout/signedprovider/review öncekiyarımişkapsamdakalır. YeniAPItestbaşlangıcındaRootCWDpytest appbulamadı,cwdbackendile4/4düzeldi. GeçiciPG55436yenidenbaşlatıldı. Aktif test sessionyok (80121/62198tamamlandısonuçlarlogda);ekranlarhenüzcanlıyeniversiyonkabulünden geçmedi.

- **KAPANIŞ KAYDI22:23:** Son rol GET taraması **2112/2112**,11rol×192yol:1205HTTP200+907beklenen403, beklenmeyen500/404/401 yok (output/api-smoke-saas-final-20261103.log,docs/api-smoke-results.json). Dinamik/yazma ve üretim kabulü yerine geçmez. Son rol etiketleriyle lint/TS/Vite build temiz (lint-saas-role-labels/build-saas-role-labels-20261103.log). Primary033 güncel kodla tekrar başladı; output/live-saas-role-final-20261103.log canlı kontrol başarılı, running-local-verification JSON failures[]. Tüm shell test/tarama/restart işleri tamamlandı; açık test session yok. GeçiciPG55436 doğru output/postgres-acceptance-20261102 datadir ile durduruldu; sonraki PG testinden önce kontrollü başlat. Yerel5173/8000 açık. Son kullanım%99/%15ordinarytrue; yeni geliştirme öncesi yeniden kontrol et,100/ordinaryfalse ise bekle. Saatlik otomasyon ACTIVE; iç işler hâlâ açık. Sıradaki SaaS kart tahsilatını ayrı merchant/imza/şifreleme/fraud/tekrar/PAID_REVIEW kabulüyle tamamlamak; ayrıca BusPage yönetim ekranı ve diğer kayıtların yazma/sınır kabulü. Ana veride hesap/parola/fiyat/paket oluşturulmadı, gerçek ödeme/mesaj/dağıtım yapılmadı. Ayrıntılı önceki test sonuçları aşağıda; tam backend300+1 sonrası ilgili26geçti, tam303gibi sonuç uydurma.

- **Son güncelleme22:18:** Edge tam koşusunda20 eski senaryo geçti; yeni SaaS senaryosu aynı adlı genel/kurum owner rolü nedeniyle strict locator'da kaldı (edge-saas-all-final-20261103.log5.5m). GET/users/options artık rolün organization_id alanını verir; UserDetail checkboxları Genel rol/Kurum rolü diye ayrılır, mevcutrolverisi/UUID silinmez. **Son SaaS+owner user-create/access+expiry/renewal+mobil kontrol1/1**,1.2m: edge-saas-user-final-20261103.log. Bu son DTO/etiket değişikliği için primary backend'in bir kez daha kontrollü restartı ve frontend build'i yapılmalı; eskiprimarySaaS033 zatençalışıyor. Yeni APIGET taraması çalışıyor: session52428, output/api-smoke-saas-final-20261103.log; bitince raporu oku. Kullanım%96/%15ordinarytrue; yeniiştenöncetekraroku. Önceki14996 tamamlandı; tam21/21deyazma (20geçti+SaaSayrı1/1).

- **SON DOĞRULANMIŞ DURUM,22:11 — bu paragraf aşağıdaki eski ara kayıtları geçersiz kılar. Ana DB artık033; tekrar033 apply çalıştırma.** .codex-build/local/migration033-verification.json:103 eski tablonun tüm sayımları ve id/e-posta/parola SHA aynı; dört SaaS tablosu boş. Yedek backend/school_management.before-saas-memberships-20261103-220838.db. stop/start kimlik kontrollü başarılı;5173/8000 açık. Canlı Root platform/abonelik, pano, chatbot300ms,25öğrenci seçeneği ve önceki tüm modül kontrolleri geçti; failures[]: output/live-saas-final-20261103.log / running-local-verification-20261103.json. Ana DB'de paket/üyelik/fiyat veya hesap tahminle oluşturulmadı.
- Tam frontend **170/170**,29dosya87.48s: frontend-saas-full-20261103.log. Son lint/TS/Vite build temiz: lint-saas-final-20261103.log/build-saas-final-20261103.log (JS393.06kB). Ruff F821/F823 ve pip check temiz; OpenAPI son SaaS+user access yollarıyla yeniden üretildi. User erişim UI2/2 ayrıca geçti. Görsel inceleme paket select'inin butonu taşırdığını yakaladı; saas-workspace/account-workspace form CSS'i ile düzeltildi, E2E artık kontrol/buton sınırlarını da ölçer.
- Tam backend **300 geçti,1 sözleşme testi başarısız**,665.20s: backend-saas-full-final-20261103.log. Bu test henüz API'si olmayan hazırlanmış /checkout formunu ve test süreci başladıktan sonra eklenen /users/{id}/access yolunu gördü. Tamamlanmamış kart formu/çağrısı arayüzden çıkarıldı; yeni access endpoint gerçek ve transaction kapsamlı. Güncel sözleşme+SaaS+user-access+auth-role tekrar **26/26**,78.11s: saas-user-contract-rechecked-20261103.log. Önceki tekrar25pass1fail yalnız fixtures arasında biriken5/min login429 idi; materials_client her bağımsız geçici DB senaryosunda limiter.reset() ile test bütçesini ayırır, gerçek giriş koruması kapatılmadı. **301/301 tam tekrar yapıldı diye sunma.** ÖncekiSaaS25/25 ve migration ikiDB doğrulamaları da kayıtlı.
- Kartla SaaS tahsilatı halen iç geliştirme. cryptography50.0.1 .venv'de bulunur ama henüz kullanılmadığı için yeni explicit requirements satırı geri çıkarıldı. SAAS_IYZICO_* ve boş SAAS_CHECKOUT_ENCRYPTION_KEY config/model alanları hazırlık; checkout servisi/sonuç doğrulama/Root PAID_REVIEW çözümü ve UI birlikte geliştirilip test edilmeli. UI şu an yalnız gerçek yenileme talebi+Root'un kontrol ettiği manüel tahsilatı sunar; sahte ödeme yok. Daha önce033 uygulanmadan eklenen kolonları bundan sonra033'ü değiştirerek geliştirme; yeni gerekirse034 çıkar.
- **Çalışan son iş:** tam Edge+PG21 test session14996, output/edge-saas-all-final-20261103.log. Tamamlanınca sonucu oku; ardından backend/scripts/audit_api_smoke.py yeniden çalıştır (kopyada, önceki2002 rolGET sayısı artık güncel değil), dosyayı güncelle ve geçiciPG'yi doğru datadir ile durdur. Son kullanım%92/%14 ordinaryUsageAllowed=true; yeni geliştirmeden önce tekrar oku. Limitte yeni iş başlatma/reset deneme, saatlik ACTIVE otomasyonun sonraki kontrolünü bekle. Yarım BusPage, SaaS kart ödemesi, karma veli/personel kapsamı, kullanıcı/öğrenci/veli diğer yazma-sınır kabulü ve dış sağlayıcı/mobil/restore/load kabulü hâlâ var. Satış/üretim kabulü tamamlanmadı, otomasyonu durdurma.

- **Son ara kayıt (21:59)**: SaaS Root PlatformPage ve SubscriptionPage artık App/menü/SubscriptionGuard/402 interceptor/getHomePath'e bağlı. GRACE uyarısı çalışma alanında görünür; kısıtlı kurum uygulama yollarından ödeme ekranına gider. Müşteri sayfasında durum yenileme ve rol bazlı fatura görünürlüğü var. İlgili frontend **80/80** (saas-ui-related-20261103.log), lint temiz ve build temiz (build-saas-ui-20261103.log). Son kullanıcı yönetimi değişiklikleri bu koşulardan sonra; tekrar test gerekli.
- SaaS temel/billing/migration **25/25**,58.44s: saas-access-billing-final-20261103.log. Root summary/atanmış ödeme yetkilisi, yabancı kurum yetkilisini reddetme ve eski faturanın güncellenmiş ticari snapshot'ı ezmemesi dahil. Invoice.base_membership_digest033'e eklendi, migration hâlâ primary'ye uygulanmadı.
- **Edge+PG SaaS akışı1/1**,38.9s: edge-saas-final-20261103.log. Root UI'den paket+kurum+sahip, ayrı sahip girişi, eski oturumu API üzerinden süre aşımına düşürme→402→abonelik sayfası, geçici DB'de sahte banka referanslı manüel kabul kaydı→tek yenileme→erişim,390px taşma kontrolü geçti. Gerçek tahsilat yok. Görseller output/saas-subscription-mobile.png ve saas-platform-mobile.png. İlk Edge denemesi nested select'in label locator'ı seçenekleri de içerdiği için zaman aşımına uğradı; combobox accessible-name locator ile düzeltildi, ürün timeout'u değildi.
- Kullanıcı detayında async lazy roles gerçek MissingGreenlet500 iki DB'de kanıtlandı (saas-owner-crud-before-20261103.log), explicit refresh ile **2/2** düzeldi (saas-owner-crud-final-20261103.log11.34s). NonRoot aynı kurumda bulunsa bile platform hesabını değiştiremez; listeden gizlenir, Root hesabı bu ekrandan pasif/bloke/silinemez. UserCreate/update alan uzunluğu/UUID/durum/duplicate-email kontrolü eklendi; mevcut parolalar değişmedi. UserStatus.BLOCKED geçerli enum olarak korundu.
- **Yeni yarım iş**: kullanıcıların rol/şube ataması UI'de yoktu. UserCreatePage erişilebilir form/Root kurum seçimi ve yeni hesap profiline geçişle yenilendi. UserDetailPage yazma yetkisine göre rol/şube checkboxları, GET/users/options ve atomik PUT/users/{id}/access hazır. Foreign branch hatası aynı transaction'da rol değişikliğini de geri alır; tekrar/duplicate UUID'ler normalize edilir. UsersPage salt okumada oluştur/sil sunmaz, aramayı params ile encode eder, sayfayı sıfırlar. Yeni test_user_access_management.py ve user-access.test.tsx **henüz çalıştırılmadı**. Tam backend şu an eski koleksiyonla çalışıyor: session37017, output/backend-saas-full-final-20261103.log (21:51 başladı); sonraki yeni testleri ayrıca çalıştır.
- Ana DB klonu **033 başarılı**,103 eski tablo sayımı ve hesap/e-posta/parola özeti aynı: output/migration033-clone-final-20261103.log ve .codex-build/local/migration033-clone-verification.json. **Ana DB hâlâ032**, yedek/apply/restart yapılmadı. Bekleyen testler geçince stop-local→migrate033.py --apply→start-local, readonly canlı Root/abonelik/chatbot kontrolü gerekli. Geniş dirty tree korunuyor.
- docs/SAAS_ISLETIMI.md eklendi. **Kartla üyelik tahsilatı tamamlanmadı**, online_payment_available API'de henüz yok (UI False varsayar). Ayrı SAAS_IYZICO ayarları ve boş SAAS_CHECKOUT_ENCRYPTION_KEY hazır; checkout token/URL için model Text checkout_secret+token_hash+provider payment/transaction alanları hazır ama servis yok. cryptography50.0.1 kurulu ve requirements'e eklendi; resmi Fernet/PyPI ve iyzico imza belgeleri açıldı. Sağlayıcı yokken ödeme başarılı gösterilmez; gerçek ödeme denenmedi. Bir sonraki geliştirmede merchant izolasyonu, init/retrieve HMAC, nonce, miktar/kurum/fraud kontrolü ve PAID_REVIEW çözümü tamamlanmalı. Şu anda bu adımlar **iç geliştirme**; otomasyonu durdurma.
- Son kullanım **%73/%11**, ordinaryUsageAllowed=true. Yeni aşamada tekrar oku. Hedef: mevcut kullanıcı erişim testleri, tam backend sonucu, tam frontend+lint/build, son Edge/genelGET taraması,033primarykontrollüuygulama. Sonra kart ödeme akışı ve yarım BusPage yönetim ekranı. Doğrulanan satış kabulü henüz yok.

- Kabul kapsamı docs/SAAS_KABUL_PLANI.md. Ana yönetici mevcut is_super_admin hesabı; okul/paket/üyelik oluştur/kapat/aç; kurum sahibi kendi kayıtlarını yönetir. Paket şube/öğrenci/kullanıcı sınırları; bitişte uyarı, 10 günlük ek sürenin tam sonunda ödeme ekranı; eski token bunu aşamaz. Saatlik otomasyon bu kapsamla güncellendi ve ACTIVE. OpenAI Docs becerisi otomasyon için okundu; dokümantasyon https://developers.openai.com/training/walkthroughs/scheduled-tasks açıldı. Reset aracı kullanılmadı.
- Yeni modeller/migration033 hazır: subscription_plans, organization_subscriptions, subscription_invoices ve subscription_checkouts. **Ana DB hâlâ032,033 uygulanmadı; yeni backend ile primary’yi henüz yeniden başlatma.** Önce migration geçici SQLite/PG ve ana DB klonunda korunma testi, kontrollü yedek/migration/restart gerekir. Eski kurum/paket/hesap/şifre tahminle değiştirilmedi; eski abonelik satırı olmayan kurum LEGACY olarak korunur. Yeni eski /organizations POST yolu UNCONFIGURED üyelik ekler; sınırsız yeni müşteri açılmaz.
- Yeni platform.py routerı Root-only /api/platform/plans GET/POST, /tenants GET/POST, /tenants/{org}/subscription PUT, /status PATCH; /api/subscription/access mevcut oturumun minimal durumunu verir. platform_service: gerçek sahip hesabı/owner rolü/kurum/üyelik tek transaction; tekrar HMAC+Audit nonce ile tek kayıt, şifre veya düz parola hash’i audit’e yazılmaz. Paket snapshot geçmişteki sözleşmeyi katalogdan ayırır.
- subscription_access saf yaşam döngüsü; get_current_user güncel DB’den erişim kontrolü, ödeme/oturum yolları açık, diğer yollar402+SUBSCRIPTION_REQUIRED. Login/me/refresh organization_access döndürür. subscription_guard before_flush: Org satırı kilidi, silinmemiş şube/öğrenci/kullanıcı sayısı, Root kullanıcısı kota dışı; tüm ORM insert/import yolları hedefleniyor (Core/bulk yolları ayrıca incelenecek). Başka kurum/rol yetkisi genişletilmedi.
- **İlk SaaS 8/8** (6 API iki DB +2 yaşam döngüsü): output/saas-platform-fixed-20261103.log,15.35s. İlk test verisi EmailStr için .invalid adresle422 idi, example.com test adresiyle düzeltildi; gerçek mesaj gönderilmedi. Sonra PG owner FK sırası explicit flush ile düzeltildi; users.create ilişkiyi lazy okurken MissingGreenlet500 veriyordu, boş roles/branches baştan verildi. Sonuçları tam üretim kabulü diye sunma.
- Son SaaS temel regresyon **15/15**,30.04s: saas-core-final-20261103.log; 033 iki DB’de iki kez upgrade edilerek eski tablo satır sayıları ve hesap/e-posta/parola birebir korunuyor, ilk üç yeni tablo boş. Toplu öğrenci importu kota dışına çıkmıyor; eski kurum formu ve kurum importu yeni PENDING yapılandırma satırı ekliyor. Katalog fiyat/kota değişimi geçmiş üyelik snapshot’ını değiştirmiyor. Tam backend koşusu backend-saas-core-full-20261103.log:288 geçti,1 eski32 şemalı klonda Sub tablosu olmadığı için başarısızdı. test_session_and_appointment.isolated_sessions artık yalnız geçici klonu Alembic head ile yükseltiyor; ilgili3/3,7.62s (session-saas-schema-final). Yeni tam koşu henüz yapılmadı.
- Üyelik ödeme talebi/manüel doğrulama eklendi; **21/21** ilgili SaaS/billing/migration testi44.87s: subscription-billing-api-20261103.log. Schema033 henüz primary’ye uygulanmadığı için Invoice.created_by/base_period_end/valid_until ve dördüncü checkout tablosu aynı033’e eklendi, eski veri değiştirilmedi. Müşteri faturası ayrıSaaS tabloları; öğrenci borç/tahsilatıyla karışmaz. Tutar yalnız sunucudan, aynı nonce tekInvoice, tek açık talep, yanlış tutar422/tekrar banka referansı409, aynıödeme tekuzatma. Rootkapatması ödemeyle açılmaz. Provider bağlantısı henüz tamamlanmadı, gerçek ödeme yok.
- SubscriptionPage.tsx, SubscriptionGuard, lib/subscription.ts ve AuthUser.organization_access tipi hazır **henüz App/rota/API interceptor/menüye bağlanmadı**. Guard3 test geçti; navigation-contract yeni /subscription ve /platform henüz kayıtlı olmadığından1 başarısız (71pass/1fail), Root PlatformPage oluşturulup iki yol birlikte kaydedilmeli; test kuralını gevşetme. Primary backend hâlâ032 eski süreç: yeniSaaS backend ile restart için önceclone/yedek/migration gerekir.
- Rootsummary,kurum kullanıcı seçenekleri,Membership.owner_user_id seçimi yeni eklendi, son21 koşusundan sonra olduğundan ilgili tekrar gerekli. RootPlan/tenant/API backendvar, RootFrontendPage henüz yazılmadı. SonrakiSomutİş: RootUI ve müşteri ödeme ekranını tamamla; ayrıSAAS_IYZICO ayarlarıyla hostedcheckout, imza/tutar/kurum/tekrar ve fraud incelemesi. Mevcut öğrenci IYZICO merchant/callback ayarlarını SaaS gelirine karıştırma. iyzicoCF initialize/retrieve/HMAC ve response-signature resmi belgeleri açıldı. Crypto50.0.1 .venv’de var amarequirements’te henüz açık değil; hassascheckout URL/tokeni şifreli saklama planı var, henüz uygulanmadı.
- Sıradaki:033 ana DB klonunda doğrulama ve kota toplu işlem/tenant dışı testleri; mevcut tam backend regresyonu; müşteri abonelik/ödeme yönlendirmesi ve Root yönetim ekranı; güvenilir ödeme/yenileme/tekrar akışı (sağlayıcı yoksa sahte ödeme yok); sonra yeni frontend/API/Edge ve mobil kabul. Yarım BusPage yönetim ekranı kapsamda kalır. Son bus API26/26 (bus-management-api-20261103.log,44.22s) geçti, sonrasındaki saat/arama/options ufak değişiklikleri henüz yeniden test edilmedi; BusPage hâlâ salt okuma. Yeni menü69/69 geçti, tam frontend153 bu menü değişikliğinden önceydi.
- PG55436 şu an açık, diğer ağır işleri seri çalıştır. Son kullanım %24/%4 ordinaryUsageAllowed=true; yeniden oku. Tek aktif proje chat’i bu çalışmaydı. Yeni Root/abonelik/ödeme ekranı primary’de kullanıma açılmadı; satış kabulü tamamlanmadı.

## Şu an yapılacak iş ve açık kontroller

1. Son tam backend **262/262**,406.10s: output/backend-transport-full-20261103.log. Güvenlik, teslim, bireysel öğretmen ilaç okuması ve son servis kapsamı/eşzamanlılık/saat dilimi düzeltmeleri dahil.
2. Son tam frontend **153/153**,25 dosya,97.73s; lint ve TS/Vite build temiz: output/frontend-transport-full-20261103.log, lint-transport-20261103.log, build-transport-20261103.log; ana JS390.19kB. Dokuz tamamlanmış modül ve güvenlik/teslim menüye yetkileriyle eklendi. Öğretmen ilaç sekmesi/GET'i sağlık veya teacher.view_medicine_requests olmadan sunulmaz; klinik veli talebinde sağlık yazması olmadan karar düğmesi, listeden klinik silme yok; normal veli talebi kaldırması korunur.
3. Son tam Edge+PG **20/20**,4.0m: output/edge-security-pickup-full-20261103.log. Revir, etüt, güvenlik ve teslim dahil. Sonraki servis düzeltmesi bu koşuya dahil değil; son servis API ilgili14 ve canlı servis kontrolü geçti. Çok ağır işleri paralel çalıştırma.
4. Ana DB032,103 eski tablo satır sayımı ve hesap/e-posta/parola özeti korundu. Backup backend/school_management.before-medication-history-20261103-173315.db; .codex-build/local/migration032-verification.json. Eski sağlık/ilaç satırları değişmedi; yeni request_status/scheduled_date alanları NULL. migration032-clone.log ve migration032-apply.log temiz. Yerel5173/8000 açık; öğretmen/revir/etüt canlı kontrolü geçti (live032-final-20261103.log, chatbot215ms, sıfır API hatası). Güvenlik/teslim endpointleri8000’de açık; son bus değişiklikleri dahil kontrollü stop/start tamamlandı (restart-transport-20261103.log). verify-running.cjs revir/etüt yollarını içeriyor; kendi oturum/chatbot logu dışında iş kaydı yazmaz.
5. Ruff F821/F823, pip check ve docs/openapi.json güncel export temiz. Son GET taraması **2002/2002**:1170 HTTP200+832 beklenen403,11 rol×182 yol; beklenmeyen500/404/401 yok (api-smoke-security-pickup-transport-20261103.log). Bu tarama dinamik/yazma kabulünün yerine geçmez.
6. Güvenlik API ve ekranı tamamlandı: security-gate-regression-20261103.log **18/18** (12 yeni güvenlik +2 eski teslim +4 sözleşme); güvenlik UI4/4, security-gate-edge-20261103.log mobil1/1,30.1s. Yeni sourceStudentChoice helper Security.options ile aynı amacı paylaşıyor; son teslime eklendiği için son test sonucunu kontrol et. Önce dört negatif testle GET'in kimlik oluşturması ve çok aktif kimlikte500 doğrulandı. Ayrıca PG'de iki öğrenci aynı request UUID ile yarışınca rollback sonrası MissingGreenlet500 yakalandı (security-gate-races-before); actor/öğrenci/kimlik yeniden yüklenerek409'a çevrildi. Okuma kimlik üretmez, ayrı security.read; gerçek aktör/şube/UTC kapı kaydı, QR/barkod ayrı kontrol, aynı nonce tekrarında sabit kayıt, iptal ve SCS360 rastgele benzersiz barkod. Var olan kod/kimlikleri otomatik değiştirmedi. QR SVG yetkili private/no-store indirme, URL'de gizli token yerine kayıt UUID'si. Yeni QR kapı kaydında yetişkin teslim/servis izni uydurulmaz, iki flagFalse. Ham giriş-çıkış yerine son öğrenci kaydı, önceki gün girişi ve eşit zamanlı eski çelişkilerde inceleme sayısı; kurum dışı ve sahipsiz eski log sızmaz. Domain Boolean varsayılanı yalnız yeni satırlardaFalse; eski DB değerleri aynen durur, migration yok. Yeni güvenlik menü bağlantısı ve Türkçe ekran.
7. Teslim masası API/ekranı tamamlandı. Backend önce6 yeni teslim +2 eski teslim +12 güvenlik =**20/20** (pickup-desk-api-20261103.log); sonrasında öğrenciler arası aynı yetki UUID yarışı2 vaka eklendi. UI teslim+güvenlik **8/8** (pickup-security-ui-fixed-20261103.log); ilk birim hata gerçek ürün hatası değil, today yüklenince değişen formun eski DOM referansını tutan testti, seçenek yüklenmesini bekleyerek düzeltildi. Mobil Edge teslim+güvenlik **2/2**,32.2s: pickup-security-edge-20261103.log. Yeni UUID yardımcı newRequestId getRandomValues kullanır; Edge güvenlik akışı randomUUID kapalıyken de geçti. Yetki oluşturma nonce/audit hash ile tekrar korumalı, aynı kimlikte çakışan etkin tarih409; eski kopyalar korunup özet inceleme sayısı döner. Alan/aktör/kurum sınırı, aktif öğrenci, tarih sırası ve düzenleme fotoğraf/diğer alan koruması; geçmiş teslim adı snapshot kalır. Yeni /dismissal ve menü dismissal.read/write; salt okumada yazma yok; teslim kimliği otomatik doldurulmaz; yetki iptali geçmişi silmez. security ve dismissal arasında yalnız ilgili okuma yetkisinde bağlantı var. Primary son restart geçti, yeni endpoints8000'de açık; teslim/güvenlik dahil son canlı kontrol geçti.
8. Son canlı kontrol **başarılı**: output/live-security-pickup-transport-20261103.log ve running-local-verification-20261103.json. Login/pano/chatbot (191ms)/hızlı soru/25 öğrenci seçeneği, envanter/onay/anket/katılım/rehberlik/bordro/etüt/revir/güvenlik/teslim/servis; sıfır API hatası, yerel font2/2, dış font isteği0. Dijital kimlik GET iki kez okundu, önce/sonra kimlik ID listesi aynı: okuma yeni kimlik oluşturmuyor. Ana veride iş kaydı oluşturulmadı; kendi auth/chatbot logu kalabilir. Yerel5173/8000 güncel kodla açık, süreçler PID/zaman/exe kaydıyla yönetiliyor.
9. **Kullanım yenilendi, çalışma devam ediyor.** Son get_usage_limits: ordinaryUsageAllowed=true, iki pencere0. Reset aracı kullanılmadı. Yeni sürücü testi iki DB’de adın None dönmesini kanıtladı (bus-driver-before); rota bağlantısından yalnız asgari isim okunur, yabancı kurum adı gizlenir, global staff/payroll kapsamı genişletilmedi. Var olan atanmış şubesiz sürücüyle düzenleme serbest; ilişkisiz hesap403. updated_by oturum aktörü oldu (önce iki başarısızlık: bus-route-edit-before). İlgili bus14/14 temiz: bus-driver-final-20261103.log,27.68s. Menü6 başarısızlıkla kanıtlandı (navigation-before); veli/personel rolleri birleşir, varsayılan kantin öğrenci seçici yardımcı izni menüye genel öğrenci erişimi taşımaz, özel ek yetkiler kullanılabilir. Öğretmen paneli teacher.view_classes menü/sayfa koruması; çift /my-surveys bağlantısı kaldırıldı. İlgili menü69/69 temiz (navigation-final). Son tam262 ve frontend153 bunlardan önceydi; yeni tam sayı beklenir. Şimdi servis rota/durak/katılım/konum yönetim ekranı ve amaçlı API seçenekleri/özetini tamamla; yeni geçici SQLite/PG ve mobil testlerle doğrula. Kullanıcı verisine yeni iş kaydı yazma. PG55436 yeniden açıldı, testlerden sonra yalnız bu kümeyi kapat.
10. Servis kapsamı düzeltildi: geçici iki DB'de önce6 başarısız test (bus-scope-before-20261103.log) kurum dışı rotaya durak yazılması, yabancı sürücü bağlama ve bus.read olmadan sahte sıfır analizini kanıtladı. Yeni bus_service: durak/telemetri/katılım/check-in öncesi erişilebilir rota; durak aynı rota, öğrenci rota kurumu, sürücü aktif/aynı kurum/erişilebilir hesap (root için de kurum eşleşmesi). PostgreSQL INT/String sınırları422; null check-in zamanı422. SQLite eşzamanlı iki ilk yazı2 kayıt üretiyordu (bus-duplicate-before:1 fail+1 pass); yetkili öğrenci satırında değer değiştirmeyen kilitle seri. Eski çift katılımlar korunur, düzenleme/check-in409; otomatik birleştirme yok. Son bus/sözleşme **14/14**,27.75s: bus-scope-final-20261103.log (10 yeni bus,4 sözleşme). Sonraki tam262 koşusu tüm bu vakalarla temiz tamamlandı. BusPage API vehicle_plate/status/date alanlarına ve route_id isim eşlemesine geçti; yüklenen rota özeti analiz sağlayıcısına bağlı değil, yapay öneri yok,100/50 sınırı açık. Önce iki UI başarısızlığı kanıtlandı (transport-ui-before); güncel tam frontend153/153, lint/build temiz. Saat dilimi için iki DB’de iki başarısız test (bus-timezone-before) UTC22:30’un yanlış takvim gününe yazıldığını kanıtladı; offsetli zaman okul saatine çevrilir, varsayılan okul saati; eski naif istemci zamanı yerel okul saati kabul edilir ve OpenAPI açıklamasında belirtilir. Önceden saklı tarih/saat yeniden yorumlanmadı. Bus CRUD/telemetri/atama arayüzü ve başka eski AI analizleri hâlâ iç iş; yalnız dış sağlayıcılar kaldı diye otomatik geliştirmeyi durdurma.

## Bu turda tamamlanan ve kanıtlanan işler

- Revir032: Yol/body farklı öğrenciye sağlık dosyası yazabiliyordu; başka çocuğun programına doz yazılabiliyordu. İki DB'de dört başarısız testle kanıtlandı (infirmary-before-20261103.log), kapatıldı. Öğrenci kilidiyle tek dosya/upsert, gerçek updated_by; girilmeyen sigorta alanı korunur, eski çift dosyalar409 ile incelemeye bırakılır. İlaç programı gerçek oluşturucu/onay aktörü, açık request_status; veli PENDING, personel kaydı APPROVED. Ret kalıcıREJECTED; eski kayıp retler tahmin edilmez, NULL durum eski is_active/updated_by ile okunur. Medlog scheduled_date+gün/saat tekil index; eski NULL doz günleri/çift kayıtlar korunur. Program kilidi ve aynı öğrenci zorunluluğu, yalnız açık/onaylı tarih aralığı; farklı günün dozu başka satırdır, eşzamanlı tekrar ilk aktör/zamanı korur, sonucun üstüne farklı sonuç409. Uygulanmayan dozda given_time yok; gerçek aktör oturumdan; saat dilimli geçmiş zaman normalizeUTC. Çok dozlu günlük okuma artık scalar_one_or_none500 üretmez; PG UUID üzerinde REPLACE kullanan ilaç talep listesi kaldırıldı. Veli uzun talimatı parent_notes'ta1000 karakter sınırıyla korunur (instruction50 alanına yazılmaz). Revir ziyaretinin şubesi öğrenciden, kaydeden oturumdan; manuel veli bilgisi gönderim sayılmaz/gerçek mesaj yok; takip kapatma gerçek kayıt/audit. Sağlık özetinde gerçek ay/aktif program/takip sayıları, yapay öneri yok. Veli talebi/notices/pano adaptörleri karar durumunu paylaşır; students.write sağlık yazmasını aşamaz, health.read olmayan agregada klinik talimat yok. Ekran dört sayfalı tablo ve dosya/ziyaret/program/talep kararı/doz/takip işlemlerini içerir. Eski kayıtlar/açıklamalar/hatalı bağlar otomatik birleştirilmez veya silinmez.
- Etüt: Önceki approve approved_by=None ve öğretmenin başka öğretmenin müsaitliğine200 yazması iki DB'de dört başarısız testle kanıtlandı (tutoring-before-20261103.log). Artık gerçek onay aktörü/UTC ve tekrar sabit karar tarihi var; onay/ret son durumlarını birbirine çevirmek409. Atanmamış talebi iki öğretmen aynı anda aldığında biri200 diğeri404,500 yok. Öğretmen yalnız kendi ders/talep/müsaitliği; şube yöneticisi başka şube takvimine erişemez. Seçilebilir aktif öğretmen sınıf/doğrudan öğrenci atamasına bağlı; yeni genel öğrenci erişimi açılmaz, rol/veri değişikliği/migration yok. Öğretmen ve öğrenci kilidi, müsaitlik aralığı ve gerçek eşzamanlı kapasite denetimi; art arda oturumları toplam çakışma diye yanlış saymaz. Öğrenci başka öğretmende meşgulse409. İptal ve müsaitlik kapatma geçmişi silmez; tamamlanan dersin zamanını oynatmak409. Üç sayfalı tablo, gerçek kapsam/özet, oluştur/düzenle/talep/onay/ret/devam/müsaitlik/iptal düğmeleri. Onay otomatik ders yaratmaz; ayrı ders planla formu açıkça gösterilir. Yenilemede açık satır korunur; form hatasında taslak durur. Mobil screenshot output/tutoring-acceptance-mobile.png; tutoring-regression-final-20261103.log19/19, tutoring-ui-20261103.log4/4, tutoring-edge-final-20261103.log1/1. İlk Edge iki denemede tam etiket ve kapanan ayrıntı sorunlarını buldu, düzeltildi; son koşu temiz.
- Onay: Survey/ConsentDocument kalıcı organization_id (029), eski sahiplik yalnız tek anlamlı kurum bulunursa yazılır. Belge oluşturma, metin/sürüm, veli-öğrenci bağı, ayrı parent.give_consent, onay/ret, okunmuş metnin hash/sürüm kontrolü, kilitli tek karar ve güvenli AuditLog. Karar sonrası metin dondurulur; başka şubedeki gizli karar da metni korur. Arşiv geçmişi okunur. Yönetim ve /parent/consents mobil ekranı eklendi.
- Anket: taslak/soru/yayımla/kapat, tarih ve cevap türü/zorunlu alan doğrulama, gerçek sonuç ve sayaç. /surveys?survey=... ayrıntı, /parent/surveys ve /my-surveys. Ayrı parent.respond_survey / surveys.respond (030); anonim cevapta aktör/IP yok, cevaba ID ile bağlanmayan katılım defteri çift gönderimi önler. Eski anonim aktör gizlenir, eski NaN/Infinity DB'de korunup listede güvenli işaretlenir. Yönetim oluştur düğmesi kurum seçeneklerini bekler.
- Bordro: aynı kurum başka şubenin maaşlarını gösteren sızıntı iki DB'de kanıtlanıp staff_scope ile kapandı. UserBranch, ana öğretmen, ClassTeacher, ClassroomAssignment ve doğrudan öğrenci öğretmeni gerçek bağları kullanılır. Doğrudan öğretmenin adı da görünür. Personel kilidiyle ilk kayıt/tekrar/onay seri; gerçek approved_by, tekrar onayda sabit tarih; onaylı bordro/ek ders düzenlemesi409. Sayı hassasiyeti/taşma, süre ve dönem ayı doğrulanır. Puantaj giriş/çıkış ISO saat dilimi gerektirir, UTC saklanır/döner. Ana DB'deki üç bordro tablosu bu değişiklik öncesi0 satırdı; eski para/saat verisi dönüştürülmedi.
- Bordro ekranı: gerçek personel seçimi ve dönem özeti, aylık/üç aylık başlangıç ayı, yıl sınırını geçen tarih aralığı, üç sayfalı tablo, puantaj/ek ders/taslak formu ve gerçek onay. Parent-only hesaplar personel seçeneklerinde yok; eski rolü olmayan personelin hesabı değiştirilmez. Üç aylık başlangıç ayı açıkça gösterilir.
- Rehberlik: dolu görüşme listesindeki confidential_level hatası500'ü giderildi. STANDARD/kendi danışmanı gizliliği; ayrı guidance.read_confidential (031). Sistem kurum yöneticisi/sahibi varsayılan alır, şube yöneticisi ve özel roller otomatik genişlemez. Danışman/bildirici gerçek aktör ve aynı kurum/yetkide, gizli satır başka danışmana dönmez. Aktif tenant altındaki iç içe selectinload cache RecursionError amaçlı Core izin sorgusuyla giderildi. Gerçek özet, üç sayfalı tablo, görüşme/not/olay formu, JSON gövdesiyle çözüm ve tekrar çözümde ilk tarih/not korunur.
- Teslim: created_by ve verified_by gerçek aktör. İsim eşleşmesi yanlış kimliği kabul etmiyor; kayıtlı kimlik zorunlu. İsim DB'deki yetkiden alınır. Öğrenci kilidi yetki düzenleme/iptal/teslimi seri yapar. Aynı request_id ile eşzamanlı tekrar tek log döndürür; farklı teslimde aynı UUID409, yeni gerçek teslim için yeni UUID kullanılabilir. İlişkili yetki aynı öğrenci/kapsama bağlı. Tarihli log filtresinin date.replace(hour=...)500'ü ve gün sınırları düzeltildi. Tarih/uzunluk sınırları var. Geçici DB testleri; gerçek çocuk teslimi yok.
- Başlatma: scripts/start-local.ps1 önce /health, sonra OpenAPI/ready kontrol eder. Soğuk import altında eski60s toplam/3s istek yetmedi;120s toplam/20s istekle gerçek başlatma doğrulandı. Bilinmeyen süreçlere dokunmaz; kimliği PID/zaman/exe ile saklar.

## Son doğrulama ve doğru sayı yorumu

Üstteki son sayılar geçerlidir. Güncel tam frontend153/153 (97.73s), lint ve TS/Vite build temiz: frontend-transport-full-20261103.log, lint-transport-20261103.log, build-transport-20261103.log. Son tam backend262 tüm servis vakalarını içerir; ilgili14 koşusunu buna ekleme. Tam Edge20, sonraki servis değişikliğinden önceydi. İki yeni bireysel öğretmen testi önce öğrenci subject_name zorunlu alanı eksik test verisiyle, sonra geçerli veride gerçekten boş listeyle başarısız oldu; teacher-medication-direct-before-valid.log doğru regresyon kanıtıdır. Sınıfsız doğrudan öğrenci ataması artık ilaç talimatını getirir, bozuk kurumlar arası öğretmen bağı getirmez.

GET taraması dinamik kayıtları, tüm yazmaları ve bütün butonları kapsamaz. Yetki dışı403 gereklidir; sahte200 ile gizlenmez. Yerel kabul tüm üretim kabulü değildir.

## Veritabanı ve süreçler

- Ana SQLite032. Yedekler backend/school_management.before-form-ownership-20261103-114632.db; before-survey-participation-20261103-120849.db; before-guidance-permission-20261103-124318.db (son ikisinin school_management. öneki vardır). migration029/030/031-verification.json .codex-build/local altında;103 eski tablo ve hesap/e-posta/parola özeti korundu. Eski028 yedeği de korunuyor.
- scripts/start-local.ps1 / stop-local.ps1 yönetilen5173/8000 süreçlerini PID/zaman/exe doğrulayarak yönetir. Durum .codex-build/local/processes.json; günlükler backend-error.log/backend.log/frontend-error.log/frontend.log. Bilinmeyen dinleyiciyi durdurma.
- Geçici PG küme testler bittiği için kapanışa alındı (session2241): C:\Okul360\output\postgres-acceptance-20261102; bin C:\Program Files\PostgreSQL\16\bin;127.0.0.1:55436; acceptance; DB scs360_acceptance_run_20261103. TEST_POSTGRES_URL/ACCEPTANCE_DATABASE_URL=postgresql+asyncpg://acceptance@127.0.0.1:55436/scs360_acceptance_run_20261103. Son test bitince yalnız doğrulanmış bu kümeyi durdur, gerekirse sonraki tur başlat.
- Browser kabulü her seferinde yeni scs360_acceptance_browser_<uuid> DB/özel dosya dizini açar; teardown yalnız kendi kayıt dosyasındaki DB'yi temizler. Üst bağlantı DB'si migrate/silme hedefi değildir.
- tests/conftest.py doğrudan pytest'te ayrı geçici SQLite ve kapalı teslimat kullanır; setup_logging lifespan yerine JSON logger ayarını kurar. İlk eski durdurulmuş pytest ana DB'ye bir başarısız giriş telemetrisi yazmıştı; silinmedi, hesaplar değiştirilmedi.
- Eski guidance-privacy-after/fixed.log6–8MB uzun traceback satırı içerir. PowerShell Get-Content ile okuma; Python satırları300 karaktere kes, ASCII backslashreplace/UTF8 stdout kullan.

## Önceki tamamlanan işler

SCS360 özel kitap/360 halka logosu, tüm yazılar/yerel fontlar/lazy sayfalar; özel materyal/dosya/teslim/not; StrictMode ödev taslağı koruması; kalıcı mazeret/outbox; atomik finans/cüzdan ve belge; donanım oturum/kurum/şube/kart-sahip doğrulaması ve gerçek WiFi geçmişi; gerçek veli bugün/tarih akışı; gerçek kulüp kapasite/etkinlik/üyelik ve özel Türkçe PDF; envanter konum/demirbaş/zimmet/bakım, FK sahipliği, eşzamanlılık ve gerçek özet; öğretmen sınıf/öğrenci ataması ve gerçek görevler; auth etkin rol/şube, atomik refresh/güncel kullanıcı, bcrypt_sha256+eski bcrypt; güvenli istemci tanısı; okul takvimi. Ayrıntılar docs/TEST_VE_CALISTIRMA_2026-11-03.md ve önceki devam kaydı yedeklerinde. Eski okul360-session anahtarı taşıması kasıtlıdır.

## Satış kabulündeki açık dış sınırlar

Gerçek SMTP/Netgsm/WhatsApp/iyzico sandbox; fiziksel Android/iOS; Docker motoru; özel dosya hacmiyle tam geri yükleme ve hedef yük testi doğrulanmadı. Önceki sentetik PG dump/restore yalnız tablo sayısıydı, dosya kabulü değildir. Eski UUID/ilişki verisi kontrollü uzlaştırma gerektirebilir; otomatik birleştirme yok. Üretime dağıtım yapılmadı. İç iş listesi bitmeden yalnız dış adımlar kaldı denmez.


<!-- SCS360_SOURCE_END: 01 -->

---

<a id="belge-02"></a>

## 2. docs/SAAS_ISLETIMI.md

Kaynak: [docs/SAAS_ISLETIMI.md](docs/SAAS_ISLETIMI.md)  
SHA-256: `97ef960b7398dcf6d236ded06abfe9be501772755549928c670143a9a837e9a4`

<!-- SCS360_SOURCE_BEGIN: 02 -->
# SCS360 kurum ve üyelik yönetimi

Ana yönetici mevcut `is_super_admin` hesabıdır. Hesap veya parola değiştirilmez. Giriş doğrudan **SaaS Yönetimi** (`/platform`) alanını açar; okul hesapları, paketler, üyelik dönemleri ve ödeme talepleri burada yönetilir. Okul yöneticileri platform API'lerine erişemez. Ana yönetici bir okulun **Kurum çalışma alanını aç** düğmesiyle o okulun yetkili sayfalarını açabilir; seçilen kurum üstte görünür. **Platform yönetimine dön** düğmesi SaaS alanına döner. Bu seçim ana hesabın veritabanındaki kurumunu veya yetkisini değiştirmez.

Ana tanıtım sitesi `/`, fiyat kataloğu `/fiyatlandirma`, paketli kurum kaydı `/kayit?paket=PAKET_UUID` adresindedir. Yalnız satışa açık gerçek paketler listelenir. Katalog boşsa tahmini fiyat gösterilmez. İnternetten oluşturulan okul hesabı ödeme tamamlanana kadar `PENDING_PAYMENT` durumundadır; okul verilerine erişimi açılmaz.

## İlk kurum

1. Gerçek satış fiyatı, para birimi, aylık/yıllık dönem ve üç kayıt sınırı ile paket oluşturun. Hazır fiyat veya otomatik deneme üyeliği eklenmez.
2. Yeni kurum ve sahibi formuna okul adını, sahibin adını/e-postasını, başlangıç parolasını ve satın aldığı paketi girin. Tarihleri boş bırakmak şimdi başlayan bir paket dönemi oluşturur. Kurum, sahip hesabı, owner rolü ve üyelik tek işlemde kaydedilir. Aynı isteğin tekrarı ikinci hesap oluşturmaz.
3. Sahip kendi hesabıyla girer; kullanıcı, öğrenci, veli ve şube işlemleri kurum ve rol yetkileri içinde kalır. Yeni kullanıcı oluşturulduğunda profili açılır; **Rol ve şube erişimi** alanından seçimler tek işlemde kaydedilir. Şube seçilmezse hesabın rolü kurum kapsamında çalışır. Veli iletişim kaydı tek başına giriş hesabı değildir; oluşturulan her giriş hesabı kullanıcı kotasına dahildir.

Yeni kurumda Kurum Sahibi, Kurum Yöneticisi, Şube Yöneticisi, Öğretmen, Veli, Muhasebe, Personel, Kantin, Güvenlik, Kütüphane ve Servis rolleri yerel olarak hazırlanır. Eski bir kurumda eksikler varsa sahibi/yöneticisi kullanıcı profilindeki **Eksik standart rolleri ekle** düğmesini kullanabilir. Bu işlem mevcut özel rol adlarını, UUID'lerini, izinlerini veya kullanıcı atamalarını değiştirmez; eksik şablonları oluşturur.

Veli girişini açmak için önce kullanıcı hesabı oluşturup Veli rolünü atayın. Ardından veli iletişim kaydının profilinde **Veli giriş hesabı** alanından bu kullanıcıyı seçip bağlantıyı kaydedin. Başka kuruma ait, pasif, platform yöneticisi veya başka etkin veli kaydına bağlı hesap seçilemez. Öğrenci–veli ilişkileri ayrıca öğrenci profilinde tanımlanmalıdır; hesap bağlamak kendiliğinden öğrenci veya yeni kullanıcı oluşturmaz. Bildirim tercihi veli formundaki gerçek **Bildirim almayı kabul ediyor** alanıyla kaydedilir.

Mevcut kurumlardaki eski hesaplar korunur. Üyelik kaydı olmayan eski kurumlar **Paket tanımlanmamış** durumundadır; varsayılan fiyat veya geçmiş borç üretilmez. Ana yönetici bu kurumlara gerçek paket ve tarih atayabilir. Eski kurum oluşturma/import yollarından açılan yeni kurumların erişimi paket yapılandırılana kadar kapalıdır.

## Sınırlar ve erişim

Paket sınırları kurumun tüm şubelerinin toplamına uygulanır. Silinmemiş şube, öğrenci ve giriş kullanıcıları sayılır; yalnız pasife almak kota boşaltmaz. Ana platform kullanıcıları kullanıcı kotasına dahil edilmez. Öğrenci içe aktarması ve eşzamanlı kayıtlar aynı kontrole tabidir. Sınıra ulaşıldığında kayıt oluşturulmaz, mevcut kayıtlar silinmez.

Üyelik bitişinde ödeme uyarısı çıkar ve **10 × 24 saat** ek süre başlar. Ek sürenin tam sonunda kurumun tüm uygulama/veri API'leri ödeme gerektiren durum döndürür. Mevcut token veya mobil istemci bu kontrolü aşamaz. Giriş, oturum yenileme, çıkış ve üyelik ekranı açık kalır. Sahip/atanmış ödeme yetkilisi ödeme talebi açabilir; diğer kullanıcılar kurum sahibiyle iletişim bilgisini görür, kurum faturalarını alamaz.

Kurum hesabını kapatmak tarihinden bağımsız erişimi durdurur. Ödeme kaydetmek kapatılmış kurumu açmaz. Ana yönetici hesabı kullanıcı ekranından silinemez veya pasife alınamaz. Kurumu yeniden açmak süresi geçmiş üyeliği uzatmaz.

## Yenileme

Müşteri **Üyelik ve Ödeme** (`/subscription`) ekranında paket seçip yenileme talebi oluşturur. Tutar sunucudaki katalogdan alınır; istemci fiyat gönderemez. Katalogda sonradan yapılan fiyat değişimi mevcut üyelik sözleşmesini değiştirmez. Talep bir gün geçerlidir; daha eski, ödenmemiş talep iptal edilip yeniden açılabilir.

Ana yönetici yalnız gerçekten kontrol ettiği tahsilatı platformdaki **Ödemeyi doğrula** formundan tutar, para birimi, banka/işlem referansı ve gerekirse ödeme tarihiyle kaydeder. Aynı referans iki talebi ödeyemez; aynı işlem tekrarı üyeliği ikinci kez uzatmaz. Talep sonrası sözleşme değişmişse veya paket güncel kayıt sayısına yetmiyorsa işlem inceleme için reddedilir; önce talep ve sözleşme uzlaştırılmalıdır. Sahip **Üyelik durumunu yenile** düğmesiyle erişimini yeniden kontrol eder.

Kartla üyelik tahsilatı ayrı `SAAS_IYZICO_API_KEY`, `SAAS_IYZICO_SECRET_KEY`, `SAAS_IYZICO_BASE_URL` merchant ayarlarını kullanır. Callback tam olarak `https://API_ADRESI/api/subscription/iyzico/callback`, `SAAS_PORTAL_URL` ise arayüzün HTTPS kök adresidir. Yerel geliştirme/testte loopback HTTP kullanılabilir. `SAAS_CHECKOUT_ENCRYPTION_KEY` ayrı bir Fernet anahtarı olmalıdır; token ve ödeme bağlantıları bu anahtarla şifrelenir. Anahtarı yedekte güvenle koruyun; aktif ödeme oturumları varken değiştirmek oturumun tekrar açılmasını engeller. Bu değerler ve sağlayıcı kabulü hazır olduğunda `SAAS_PAYMENT_ENABLED=true` yapılır. Üretim ortamı sandbox merchant ile üyelik açmaz. Gerçek sağlayıcı kabulü henüz yapılmadığı için varsayılan kapalıdır; gerçek ödeme gönderilmedi.

Müşteri talepteki **Kartla öde** düğmesiyle fatura bilgilerini girer, ardından doğrulanan sağlayıcı sayfasını açar. Kart numarası/CVV uygulamaya gönderilmez. Sağlayıcı imzası, tutar, para birimi ve ödeme kalemi doğrulanır. Risk incelemesindeki ödeme üyeliği açmaz. Birden fazla bildirim aynı dönemi tekrar uzatmaz; ağ kesintisinde aynı istek kimliği kullanılır. Açık online işlem varken ayrı manüel tahsilat veya iptal yapılamaz. Sonuç kesinleşene kadar **Ödeme sonucunu kontrol et** kullanılabilir. Sıfır tutarlı bir gerçek paket ödeme sağlayıcısı olmadan etkinleştirilebilir.

Para alınmışken sözleşme veya kullanım değişmişse talep **Ödendi, inceleme bekliyor** durumuna alınır. Ana yönetici **Ödemeyi uzlaştır** alanında doğruladığı ödemeyi açık başlangıç/bitiş tarihleri ve açıklamayla üyeliğe uygular. Tutar/para birimi/kalem uyuşmazlığı bu yolla zorla uygulanamaz. Sağlayıcıda/bankada yapılmış bir iade, kontrol edilen referansla kaydedilebilir; bu düğme para göndermez veya iade başlatmaz. Kurum kapatma durumu ödeme tarafından kaldırılmaz.

Manüel banka ödeme açıklaması ve destek adresi `SAAS_PAYMENT_INSTRUCTIONS` / `SAAS_SUPPORT_EMAIL` ile tanımlanabilir. Boş ayarlarda banka hesabı veya destek adresi tahmin edilmez.

Öğrenci borcu tahsilatı üyelik gelirlerinden ayrıdır. Eski `IYZICO_*` hesabı yalnız açıkça `IYZICO_ORGANIZATION_ID` ile bağlanan okulda ve `IYZICO_PAYMENT_ENABLED=true` olduğunda kullanılabilir; yeni SaaS okullarına otomatik uygulanmaz. Başka kurumlar için ayrı merchant kurulum arayüzü henüz geliştirme kapsamındadır. Yeni öğrenci ödeme başlatmayı kapatmak, aynı kurum merchant'ı korunduğu sürece eski sonuçların doğrulanmasını engellemez.

## Kabul kaydı

Güncel testler, veritabanı yedeği ve yarım iş için [CALISMA_DURUMU.md](CALISMA_DURUMU.md); ayrıntılı kapsam için [SAAS_KABUL_PLANI.md](SAAS_KABUL_PLANI.md). Yerel testlerin geçmesi üretim/satış kabulünün tamamlandığı anlamına gelmez.

<!-- SCS360_SOURCE_END: 02 -->

---

<a id="belge-03"></a>

## 3. docs/SAAS_KABUL_PLANI.md

Kaynak: [docs/SAAS_KABUL_PLANI.md](docs/SAAS_KABUL_PLANI.md)  
SHA-256: `ca48109ec2824e2f5f0f87f4da77119aae4cc25637f4e0a617a6f975347e0684`

<!-- SCS360_SOURCE_BEGIN: 03 -->
# SCS360 SaaS kabul kapsamı

3 Kasım 2026 kullanıcı talebi. Tamamlanmadan satış/üretim kabulü verilmez.

- Platform yöneticisi mevcut `is_super_admin` hesabıdır. Kurum/paket/üyelik açma, kapatma ve süre yönetimi yalnız bu yetkiyle yapılır; okulun kendi rol veya yetki tanımlaması platform yöneticiliği kazandırmaz. Mevcut yönetici hesapları otomatik silinmez veya parolaları değiştirilmez.
- Okul sahibi kendi kurumunda personel, veli hesabı, öğrenci ve şube yönetir. Kurumlar arası veri ve hesap erişimi kapalı kalır.
- Paket adı, fiyatı, para birimi, dönemi ve şube/öğrenci/kullanıcı sınırları ana yönetici tarafından tanımlanır; fiyat uydurulmaz. Satın alınmış dönem kendi paket görüntüsünü saklar; katalog düzenlemesi eski satın almayı sessizce değiştirmez.
- Dönem bitince uyarı gösterilir. Bitiş anından itibaren 10 gün ek süre; 10. günün sonunda ödeme yoksa kurumun uygulama erişimi ödeme/üyelik ekranına gider. Mevcut token ve mobil API de bu durumu aşamaz. Ana yönetici bu engelden etkilenmez.
- Kapatılmış kurum ödeme ile kendiliğinden açılmaz; ana yönetici tekrar açmalıdır. Ödeme ve oturumdan çıkış yolları erişim engeli içinde çalışmalıdır. Personel/veli ödeme detaylarını göremez; kurum sahibine ulaşma durumu gösterilir.
- Şube/öğrenci/kullanıcı kotaları sunucuda ve eşzamanlı işlemlerde uygulanır. Sayım silinmemiş kayıtlar üzerinden yapılır; pasife alma kotayı gizlice aşma yolu değildir. Platform yöneticisi hesabı okul kullanıcı kotasında sayılmaz. Veli giriş hesabı kullanıcı kotasında sayılır.
- Mevcut kurumlarda paket yoksa veri ve erişim tahminle değiştirilmez; eski/paketsiz durum ana yöneticiye açıkça gösterilir. Yeni kurum oluşturma yolları paket/üyelik kurulumu olmadan sınırsız aktif hesap üretmemelidir.
- Paket düşürme, kota aşımı veya ödeme gecikmesi verileri silmez. Önceden girilmiş kayıtlar ve hesaplar korunur.
- Yalnız doğrulanmış sağlayıcı ödemesi veya ana yöneticinin kayıtlı yetkili işlemi üyeliği uzatır. İstemci tutarı/ödendi bayrağına güvenilmez. Tekrar/callback/yarış tek tahsilat ve tek uzatma üretir. Gerçek ödeme ve mesaj gönderimi yapılmaz; dış sağlayıcı kabulü ayrı kalır.

Kabul: geçici SQLite ve PostgreSQL; ana yönetici/okul sahibi/personel/veli; kurum dışı ret; paket sınırı ve eşzamanlı son yer; toplu içe aktarma; bitiş/ek sürenin son anı; eski token; kapatma/açma; ödeme tekrarları; mobil yönlendirme; mevcut veri/migration koruması. Sonra tüm testler, build ve canlı salt okuma kontrolü.

Yarım servis yönetim arayüzü ve önceki satış öncesi hata listesi kapsamda kalır. Saatlik devam otomasyonu bu SaaS kapsamıyla güncellendi; limit %100 veya ordinaryUsageAllowed=false olduğunda yeni geliştirme yapılmaz, sonraki kontrolde kaldığı kayıttan sürer.

<!-- SCS360_SOURCE_END: 03 -->

---

<a id="belge-04"></a>

## 4. docs/SCS360_YENILIKLER_VE_GUNCELLEMELER.md

Kaynak: [docs/SCS360_YENILIKLER_VE_GUNCELLEMELER.md](docs/SCS360_YENILIKLER_VE_GUNCELLEMELER.md)  
SHA-256: `61cf12dbd7390b2409b7bb10f7468f5ff3a6c2f6f1a78f5128b571480269c5c1`

<!-- SCS360_SOURCE_BEGIN: 04 -->
# SCS360 — Eklenen özellikler ve güncelleme kaydı

<!-- report_updated_at: 2026-11-03T21:51:12+03:00 -->
<!-- update_interval: PT1H -->

**Son güncelleme:** 2026-11-03T21:51:12+03:00 — Europe/Istanbul  
**İstenen güncelleme düzeni:** Saatte bir kontrol; yalnız yeni, anlamlı değişiklik varsa dosya güncellenir.  
**Zamanlama durumu:** Bu geçici yan sohbette zamanlanmış görev desteklenmediği için saatlik otomasyon kurulamadı. Ana sohbetten etkinleştirilmesi gerekiyor.  
**Genel durum:** Satış/üretim kabulü henüz tamamlanmadı.

Bu belge geliştirme sırasında eklenen özellikleri, düzeltilen davranışları, test kanıtlarını ve kalan işleri bir araya getirir. “Kodda hazır”, “test edildi” ve “çalışan uygulamada doğrulandı” farklı durumlardır. Planlanan işler tamamlanmış özellik olarak gösterilmez.

## 1. Marka, logo ve arayüz

- Okul360 ürün adı ve uygulama metinleri SCS360 olarak güncellendi.
- Açık kitap, 360 derece yörünge ve bağlantı noktası içeren özel vektör logo oluşturuldu.
- Açık/koyu zemin logoları, uygulama sembolü, tarayıcı simgesi, mobil ana ekran simgesi ve PDF görseli hazırlandı.
- Ortak marka bileşenleri giriş, yan menü, chatbot ve basılı belgelerde kullanıldı.
- Türkçe karakterleri içeren yazı tipleri yerel sunuluyor; Google Fonts ağ bağımlılığı kaldırıldı.
- Sayfalar ayrı yüklenecek biçimde düzenlendi; ana JavaScript paketinin boyutu azaltıldı.
- Eski oturum depolama anahtarı, kullanıcıları zorunlu olarak çıkarmadan SCS360 anahtarına taşınıyor.

**Başlıca dosyalar:** [Marka rehberi](SCS360_MARKA.md), [marka bileşeni](../frontend/src/components/Brand.tsx), [menü](../frontend/src/components/AppShell.tsx).

## 2. Chatbot ve öğretmen–veli sohbeti

- Hazır soru düğmesinin seçilen soruyu doğrudan göndermesi sağlandı.
- Personel öğrenci seçimi hem dizi hem sayfalı API yanıtını okuyabiliyor.
- Öğrenci seçimi gereken sorunun aslı korunuyor; seçimden sonra doğru öğrenci kimliğiyle yeniden gönderiliyor.
- Belirsiz LLM sınıflandırmasında güçlü kural eşleşmesine dönüş ve hata/zaman aşımı geri dönüşleri eklendi.
- Genel sohbetin gereksiz işlem sayfasına yönlenmesi engellendi; desteklenen ayrıntı bağlantıları ilgili sayfaya gidiyor.
- Öğretmen ve veli aynı öğrenciye ait kalıcı görüşmeyi kullanıyor; farklı çocukların görüşmeleri ayrılıyor.
- Birden fazla veli hesabı, katılımcı adı, mesaj kimliği, yinelenen API öneki ve mobil sohbet taşması sorunları düzeltildi.
- Son kayıtlı canlı kontrolde hazır soru ve normal yanıt çalıştı; normal chatbot yanıtı 191 ms ölçüldü. Bu tek ölçüm genel hız garantisi değildir.

**Kalan:** Gerçek LLM sağlayıcısının gecikme/doğruluk kabulü ve fiziksel mobil cihaz kontrolü.

## 3. Kimlik doğrulama, rol ve kurum güvenliği

- Kurum, şube ve ilişkili öğrenci sınırları ortak yetki bağlamına bağlandı.
- Veli–çocuk, öğretmen–sınıf ve doğrudan öğretmen–öğrenci ilişkileri dikkate alınıyor.
- Silinmiş/yabancı kuruma ait roller ve şubeler nedeniyle yetki genişlemesini önleyen kontroller eklendi.
- Token yenileme, güncel kullanıcı verisi, oturum iptali ve eski şifre karmalarıyla uyumluluk geliştirildi.
- Yeni şifrelerde uzun parola desteği sağlayan karma biçimi ve eski bcrypt uyumluluğu korundu.
- Yetki adlarının eski/yeni tekil-çoğul biçimleri uyumlu hale getirildi.
- Yetkisiz 403, geçersiz oturum 401 ve gerçekten bulunamayan kayıt 404 yanıtları güvenlik amacıyla korunuyor.
- Genel sunucu hataları SQL ayrıntısını kullanıcıya açmıyor; hata yanıtında istek kimliği bulunuyor.

**Başlıca dosyalar:** [Kimlik doğrulama servisi](../backend/app/application/services/auth_service.py), [kurum koruması](../backend/app/core/tenant_guard.py), [öğrenci erişimi](../backend/app/core/student_access.py).

## 4. Menü ve birden fazla rol

- Veli ve personel rolleri birlikte bulunan hesapların iki yetkili çalışma alanını da görmesi sağlandı.
- Kantin ve öğretmen rollerinin birbirinin menülerini gizlemesi düzeltildi.
- Varsayılan kantin hesabının öğrenci seçici yardımcı izni, genel öğrenci menüsüne dönüştürülmüyor.
- Özel role verilen ek okuma yetkileri menüde kullanılabiliyor.
- Öğretmen Paneli için menü ve sayfa koruması eşleştirildi.
- Aynı anket sayfasına giden yinelenen menü bağlantısı kaldırıldı.
- Tamamlanan modüllere, ilgili okuma yetkileriyle menü bağlantıları eklendi.

**Kanıt:** [İlgili menü testleri: 69/69](../output/navigation-final-20261103.log). Bu koşu bütün frontend testleri değildir.

## 5. Öğrenci, veli ve öğretmen portalı

- Veli sayfalarında örnek kayıtlar yerine ilişkili gerçek not, program, ödev, materyal, duyuru, aktivite ve rapor verileri kullanılıyor.
- Kayıt olmadığında uydurma değer yerine boş durum gösteriliyor.
- Öğretmen sınıfları, öğrenci atamaları, günlük program ve bekleyen işler gerçek kayıtlara bağlandı.
- Veli günlük akışından ilgili ayrıntı sayfasına geçiş düzenlendi.
- Mazeret talepleri kalıcı hale getirildi; yönetici onay/ret akışı eklendi.
- Okul günü hesapları için İstanbul iş saat dilimi desteği eklendi.
- Kurumlar arası bozuk ilişkiler yeni erişim hakkı vermiyor.

## 6. Ödev, materyal ve özel dosyalar

- Ödev oluşturma, teslim, yükleme, indirme ve notlandırma kalıcı kayıtlarla çalışıyor.
- Ödev oluşturma ve değerlendirme yetkileri ayrıldı; öğretmenin sınıf ataması denetleniyor.
- Taslak ödev veliden gizleniyor; notlandırılmış teslimin yeniden yazılması engelleniyor.
- React StrictMode altında ödev taslağının kaybolması giderildi.
- Materyal ve öğrenci dosyalarında tür, boyut, içerik ve saklama yolu denetimleri eklendi.
- Özel dosyalar kimlik doğrulama ve kayıt sahipliği üzerinden indiriliyor.
- Geçersiz dosya kategorisinin sunucu hatası üretmesi düzeltildi.

**Başlıca dosyalar:** [Ödev servisi](../backend/app/application/services/homework_service.py), [materyal dosyaları](../backend/app/application/services/material_file_service.py).

## 7. Revir, sağlık dosyaları ve ilaç

- Öğrenci kimliğiyle çelişen sağlık dosyası/program/doz bağlantıları engellendi.
- Sağlık dosyası güncellemesi gerçek aktörle kaydediliyor; girilmeyen mevcut sigorta alanları korunuyor.
- Veli ilaç talebi, onay/ret ve tamamlanma durumları açıkça saklanıyor.
- Gün ve planlanan saat üzerinden doz geçmişi ayrıldı; farklı günün dozu önceki kaydı ezmiyor.
- Tekrar gönderim, ilk aktör ve zamanı koruyor; çelişkili sonuç değişiklikleri reddediliyor.
- Çok dozlu günlük okumalardaki hata ve PostgreSQL UUID uyumsuzluğu giderildi.
- Sağlık okuma/yazma izinleri, öğrenci yazma izninden ayrıldı.
- Sınıfsız, bireysel atanmış öğretmenin ilgili ilaç taleplerini okuyabilmesi sağlandı.
- Revir ziyaretleri, takip kapatma, gerçek özetler ve dört sayfalı tablo/form akışı eklendi.
- “Veli bilgilendirildi” kaydı gerçek mesaj gönderimi olarak gösterilmiyor.

**Başlıca dosyalar:** [Sağlık servisi](../backend/app/application/services/infirmary_service.py), [revir ekranı](../frontend/src/features/health/HealthPage.tsx).

## 8. Etüt ve birebir ders

- Öğretmen kendi ders, talep ve müsaitlik kayıtlarıyla sınırlandı.
- Gerçek onaylayan kişi/zamanı, onay-ret geçişleri ve tekrar koruması eklendi.
- Atanmamış talebin iki öğretmen tarafından aynı anda alınması güvenli hale getirildi.
- Öğretmen/öğrenci çakışması, müsaitlik ve gerçek eşzamanlı kapasite denetleniyor.
- İptal ve müsaitlik kapatma geçmişi silmiyor; tamamlanmış dersin zamanını değiştirme engelleniyor.
- Üç sayfalı tablo, filtreler, ders planlama, talepler, kararlar ve devam işlemleri eklendi.
- Talep onayı ile ders oluşturma ayrı işlemler olarak gösteriliyor.
- Yenileme sırasında açık ayrıntı ve hata durumunda form taslağı korunuyor.

## 9. Rehberlik

- Görüşme listesindeki olmayan alan kaynaklı sunucu hatası düzeltildi.
- Görüşme gizliliği ve danışmana göre erişim denetimleri eklendi.
- Gizli kayıtlar için ayrı okuma yetkisi tanımlandı.
- Gerçek danışman/bildirici, kurum ilişkisi ve tekrarlı çözüm işleminin korunması sağlandı.
- Gerçek özetler, görüşme/not/olay formları ve sayfalı tablolar eklendi.
- İç içe izin sorgusundan doğan recursion hatası giderildi.

## 10. Kulüp, etkinlik ve sertifika

- Kulüp üyeliği, kapasite, etkinlik ve katılım kayıtları gerçek veriye bağlandı.
- Veli portalındaki kulüp/aktivite görünümü ilişkili kayıtlarla çalışıyor.
- Yetkili indirme üzerinden Türkçe karakter destekli özel sertifika PDF'i eklendi.
- Oluşturulan kayıtların yenileme ve ayrı oturumlarda kalıcılığı test edildi.

## 11. Demirbaş ve envanter

- Konum, demirbaş, zimmet ve bakım işlemleri kalıcı kaynaklara bağlandı.
- İlişkili kurum/şube/personel sahipliği denetleniyor.
- Eşzamanlı işlemler ve gerçek envanter özetleri geliştirildi.
- Yönetim ekranına tablo, ayrıntı ve işlem akışları eklendi.

## 12. Veli onayları

- Belge ve anketlere kalıcı kurum sahipliği eklendi.
- Belge sürümü ve okunmuş metnin özeti üzerinden veli kararı doğrulanıyor.
- Veli–öğrenci bağı ve ayrı onay verme yetkisi kontrol ediliyor.
- Aynı kararın tekrarı korunuyor; karar sonrasında belge metni donduruluyor.
- Arşiv ve karar geçmişi okunabiliyor.
- Yönetim ve veli onay ekranları eklendi.

## 13. Anketler

- Taslak, soru, yayımlama, kapatma ve gerçek sonuç/sayaç işlemleri eklendi.
- Tarih, cevap türü ve zorunlu alanlar doğrulanıyor.
- Yönetim, veli ve personel katılım sayfaları eklendi.
- Anonim cevabı kullanıcıya bağlamayan ayrı katılım defteriyle çift gönderim engelleniyor.
- Eski anonim aktör bilgisi görünümden gizleniyor; eski geçersiz sayısal veriler silinmeden güvenli biçimde ele alınıyor.

## 14. Bordro, puantaj ve ek ders

- Başka şubenin maaşlarını gösteren kapsam sızıntısı kapatıldı.
- Personelin gerçek şube/öğretim/öğrenci atamaları dikkate alınıyor.
- Puantaj ve ek ders kayıtları, taslak bordro ve gerçek onay akışı eklendi.
- Onaylanan kayıtların değiştirilmesi engelleniyor; tekrar onay ilk zamanı koruyor.
- Tutar hassasiyeti, süre ve dönem ayı denetimleri eklendi.
- Saat dilimli giriş/çıkış UTC saklanıyor.
- Aylık/üç aylık dönemler, yıl sınırını geçen tarihler ve sayfalı tablolar destekleniyor.

## 15. Öğrenci kimliği, QR ve kapı geçişleri

- Kimlik okuma yeni kimlik üretmiyor; oluşturma ayrı yetkili işlem.
- Rastgele, benzersiz SCS360 barkodu ve kimlik iptali eklendi.
- QR, barkod ve manuel doğrulama ayrıldı.
- QR SVG indirmesi yetkili ve özel; URL'de gizli token yerine kayıt kimliği kullanılıyor.
- Gerçek aktör, şube ve UTC zamanı kaydediliyor; tekrar gönderim tek geçiş üretiyor.
- Yeni kapı kaydı, yetişkin teslim veya servis izni varmış gibi işaretlenmiyor.
- İçerideki öğrenci sayısı son hareketten hesaplanıyor; eski çelişkili kayıtlar inceleme gerektiren durum olarak ayrılıyor.
- Yetki kontrollü Türkçe yönetim ekranı ve mobil uyumlu istek kimliği üretimi eklendi.

## 16. Öğrenci teslim masası

- Yetki oluşturma, düzenleme, iptal ve kimlikle teslim kayıtları eklendi.
- Yanlış kimlik numarasını yalnız ad eşleşmesiyle kabul etme sorunu kapatıldı.
- Teslim alan kişinin adı kayıtlı yetkiden alınıyor; tarihsel teslim adı sonradan değiştirilmiyor.
- Öğrenci/kurum/tarih kontrolleri ve çakışan etkin yetki denetimleri eklendi.
- Aynı isteğin tekrarı tek kayıt döndürüyor; farklı işlemde aynı kimlik reddediliyor.
- İptal geçmişi silmiyor; eski çift yetkiler otomatik birleştirilmiyor.
- Salt okuma kullanıcısına yazma kontrolleri sunulmuyor.
- Güvenlik ve teslim sayfaları birbirine yalnız ilgili okuma yetkisinde bağlanıyor.

**Ekran:** [Öğrenci Teslim Masası](../frontend/src/features/security/DismissalPage.tsx).

## 17. Servis ve ulaşım

**Ekranda tamamlananlar:**

- Plaka, rota durumu, katılım tarihi ve rota adı için hatalı alan eşleştirmeleri düzeltildi.
- Sabit AI önerileri kaldırıldı; listelenen kayıtlarla gerçek özet gösterildi.
- Mobil tablo kaydırması ve hata sonrası yeniden deneme eklendi.

**Yeni backend çalışmaları:**

- Durak, konum, katılım ve check-in öncesinde rota/kurum/öğrenci ilişkileri denetleniyor.
- Durak seçilen rotaya, sürücü hesabı rota kurumuna ait olmalı.
- Atanmış şubesiz sürücünün adı yalnız servis bağlamında okunabiliyor; genel personel/bordro erişimi genişlemiyor.
- Gerçek güncelleyen aktör ve kararlı sıralama eklendi.
- Aynı günün ilk katılımı eşzamanlı isteklerde sıraya alınıyor.
- Saat dilimli biniş/iniş zamanı okul gününe çevriliyor.
- Rota/durak/konum oluşturma ve check-in tekrarları için istek kimliği ve işlem kaydı eklendi.
- Geçmişi olan rota şube değişikliğiyle taşınamıyor; rota farklı kuruma devredilemiyor.
- Rota/durak düzenleme, amaçlı seçenekler, özet ve boş konum sonucu akışları geliştirildi.
- Sıfır koordinat/hız değerlerinin boş veri sayılması düzeltildi.

**Durum:** İlgili backend 26/26 testi geçti. Son küçük saat/arama/seçenek değişiklikleri için yeniden doğrulama bekleniyor. Yönetim formlarının BusPage ekranına bağlanması henüz tamamlanmadı.

## 18. Finans, kantin ve cüzdan

- Eski finans yolları ortak tahsilat/iptal defterine bağlandı.
- Taksit toplamı, kuruş hassasiyeti ve takvim ayları korunuyor.
- Tahsilat tutarını sonradan değiştirerek dengeyi bozma engelleniyor.
- Muhasebe iptali ve iptal işaretli makbuz/PDF akışları düzenlendi.
- Kart bakiye yükleme, harcama ve ödeme ortak cüzdana bağlandı.
- Bakiye/günlük limit kontrolleri ve nakit ayrımı geliştirildi; hayalî bakiye üretilmiyor.
- Öğrenci borcuna yönelik checkout/callback tutar, imza ve tekrar kontrolleri test sağlayıcısıyla geliştirildi.

**Sınır:** Bunlar gerçek banka/iyzico tahsilatı yapıldığı anlamına gelmez. Yeni SaaS üyelik geliri öğrenci tahsilatından ayrıdır.

## 19. Cihazlar ve RFID

- Kimlik doğrulamasız donanım erişimi kapatıldı.
- Cihaz, kart, kurum/şube ve kart sahibi ilişkileri denetleniyor.
- Heartbeat ve kalıcı WiFi okuma geçmişi geliştirildi.
- Kart ödeme/yükleme/bakiye işlemleri ortak cüzdanla çalışıyor.
- Fiziksel donanım ve mobil cihaz kabulü ayrıca bekliyor.

## 20. Bildirimler, outbox ve toplu işlemler

- Görev, personel izni, günlük rapor, program ve okundu bilgileri kalıcılaştırıldı.
- Toplu ileti gerçek ve tekrar etmeyen, izni bulunan alıcılardan kuyruk oluşturuyor.
- Sahte alıcı/gönderildi kayıtları kaldırıldı.
- İş kiralama, alıcı sonucu ve yeniden deneme davranışı geliştirildi.
- Şifre sıfırlama kuyruğa bağlandı; hassas içerik görünümde maskeleniyor.
- Toplu içe aktarmalar gerçek kayıt oluşturuyor; hatalı satırlar raporlanıyor.
- Dışa aktarmalarda gerçek satırlar ve formül enjeksiyonu koruması kullanılıyor.

**Kalan:** Gerçek SMTP, SMS ve WhatsApp teslimat kabulü.

## 21. Yeni SaaS katmanı — geliştirme sürüyor

### Kodda eklenen ve ilgili testleri bulunanlar

- Platform yöneticisine özel paket ve kurum yönetim API'leri.
- Kurum, sahip hesabı, sahip rolü ve üyeliğin tek işlemde kurulması.
- Kurum üyeliğini açma/kapatma, paket ve süre yönetimi.
- Paket fiyatı/dönemi ile şube, öğrenci ve kullanıcı sınırlarının tanımlanması.
- Satın alınmış üyeliğin paket görüntüsünün korunması; katalog değişikliğinin eski sözleşmeyi sessizce değiştirmemesi.
- Şube/öğrenci/kullanıcı kotasının sunucuda ve eşzamanlı ORM işlemlerinde denetlenmesi.
- Toplu öğrenci içe aktarması için kota kontrolü.
- Dönem bitiminde ek süre; 10 günlük sürenin sonunda ödeme/üyelik alanına kısıtlı erişim.
- Eski token ile süre/kurum kapatması denetimini aşmanın engellenmesi.
- Kapatılan kurumun ödeme nedeniyle kendiliğinden açılmaması.
- Ödeme talebi/fatura, tutarın sunucudan hesaplanması ve platform yöneticisinin kayıtlı ödeme doğrulaması.
- Aynı talep, banka referansı ve ödemenin tekrarında çift uzatma/tahsilatın önlenmesi.
- Kurumun mevcut kullanıcı seçimi, sahip hesabı ilişkisi ve platform özet API'leri eklendi; bu son eklerin yeniden testi bekleniyor.

### Yeni şema

033 migration'ında şu tablolar hazırlanıyor:

- `subscription_plans`
- `organization_subscriptions`
- `subscription_invoices`
- `subscription_checkouts`

**Rapor anındaki dağıtım durumu:** Ana veritabanı 032'de; 033 henüz uygulanmadı. Eski kurum ve hesaplara tahminî paket/süre atanmadı. Yeni backend'in çalışan veritabanına alınması, klon testi ve yedekli migration kabulünü bekliyor.

### Henüz tamamlanmayan SaaS işleri

- Platform yöneticisi ekranının tamamlanması.
- Hazırlanan müşteri abonelik ekranı ve erişim korumasının rota, menü ve API hata yönlendirmesine bağlanması.
- Ayrı SaaS ödeme sağlayıcısı ayarları ve gerçek hosted-checkout akışı.
- Sağlayıcı imza/tutar/kurum/tekrar doğrulaması ve hassas checkout verisinin güvenli saklanması için kalan işler.
- Güncel tam backend, frontend ve mobil/tarayıcı kabulü.
- Gerçek sağlayıcı sandbox kabulü.

Bu bölüm tam çalışan, canlıya alınmış bir SaaS ürünü onayı değildir.

**Kaynaklar:** [SaaS kabul kapsamı](SAAS_KABUL_PLANI.md), [platform API'leri](../backend/app/routers/platform.py), [üyelik durum servisi](../backend/app/application/services/subscription_access.py), [üyelik ödeme servisi](../backend/app/application/services/subscription_billing_service.py).

## 22. API sözleşmesi, test ve çalıştırma altyapısı

- Çakışan yöntem/adres kayıtları ve OpenAPI kimlikleri düzenlendi.
- Mobil istemci için OpenAPI dışa aktarma ve standart hata zarfı geliştirildi.
- Başlatma/durdurma betikleri yalnız kaydettiği süreçleri kimlik/zaman/dosya doğrulamasıyla yönetiyor.
- Sağlık ve hazır olma kontrolleri iyileştirildi.
- Ayrı SQLite/PostgreSQL ve Edge kabul testleri eklendi.
- Ana verinin satır sayısı, hesap, e-posta ve parola korunma kontrolleri yapıldı.
- Özel dosya ve mevcut kullanıcı verileri sıfırlanmadı.
- Sahte SMS, gerçek ödeme veya üretim dağıtımı yapılmış gibi raporlanmıyor.

## 23. Test kanıtları ve kapsam

| Kontrol | Kayıtlı sonuç | Kapsam notu |
|---|---|---|
| Tam backend, SaaS öncesi | 262/262 başarılı | Sonraki SaaS ve ek servis/menü değişikliklerini kapsamıyor |
| Tam frontend, önceki sürüm | 153/153 başarılı; lint/build temiz | Sonraki SaaS bağlantıları ve menü değişikliklerinden önce |
| Tam Edge + PostgreSQL | 20/20 başarılı | Sonraki servis/SaaS çalışmalarından önce |
| Rol bazlı GET taraması | 2002/2002; 1170 başarı, 832 beklenen yetki reddi | 11 rol × 182 yol; beklenmeyen 500/404/401 yok; dinamik adres ve tüm yazmaları kapsamıyor |
| Yeni menü sözleşmeleri | 69/69 başarılı | İlgili koşu; tam frontend sayısına eklenmez |
| Yeni servis API'leri | 26/26 başarılı | Son küçük değişiklikler için tekrar bekleniyor |
| SaaS temel regresyon | 15/15 başarılı | İlgili testler; bütün ürün kabulü değil |
| SaaS üyelik/fatura | 21/21 başarılı | İlgili kapsam; gerçek sağlayıcı ödemesi yapılmadı |
| SaaS ile geniş backend denemesi | 288 başarılı, 1 başarısız | Eski 032 klon testinin şeması düzeltildi; ilgili 3/3 geçti, yeni tam koşu bekleniyor |
| Hazırlanan abonelik ekranı/rota kontrolü | Guard 3 test başarılı; rota sözleşmesinde 1 başarısızlık kayıtlı | Eksik /subscription ve /platform bağlantıları tamamlanmalı |

Kanıt dosyaları:

- [Backend 262](../output/backend-transport-full-20261103.log)
- [Frontend 153](../output/frontend-transport-full-20261103.log)
- [Edge 20](../output/edge-security-pickup-full-20261103.log)
- [Rol taraması](../output/api-smoke-security-pickup-transport-20261103.log)
- [Menü 69](../output/navigation-final-20261103.log)
- [Servis 26](../output/bus-management-api-20261103.log)
- [SaaS temel 15](../output/saas-core-final-20261103.log)
- [Üyelik/fatura 21](../output/subscription-billing-api-20261103.log)

Koşular kısmen aynı testleri içerir; bu sayılar toplanarak tek bir tam test sonucu üretilmez.

## 24. Migration ve veri koruma özeti

| Migration | Eklenen/düzeltilen alan |
|---|---|
| 017–020 | İlişkisel erişim, veli mesajlaşma, öğretmen/chatbot entegrasyonu ve sohbet denetim kayıtları |
| 021–023 | Kütüphane, randevu ve ödev kalıcılığı |
| 024–026 | Bildirim iş kiraları, ödeme checkout/bildirimleri ve operasyon kalıcılığı |
| 027–028 | Yetki kataloğu ve materyal/teslim altyapısı |
| 029 | Form sahipliği ve veli onayları |
| 030 | Anonim anket katılım defteri ve katılım izinleri |
| 031 | Rehberlik gizli kayıt okuma yetkisi |
| 032 | İlaç karar durumu ve gün bazlı doz geçmişi |
| 033 | Yeni SaaS paket/üyelik/fatura/checkout şeması — ana veritabanına henüz uygulanmadı |

Migration numaraları tek başına canlıya alınmış özellik anlamına gelmez. Eski kayıtlar, kullanıcı parolaları ve sorunlu tarihsel ilişkiler otomatik silinmedi/birleştirilmedi.

## 25. Satış kabulünde kalanlar

- SaaS ve servis yönetimi için yukarıdaki iç geliştirme ve entegrasyon işleri.
- Yeni değişiklikleri içeren temiz tam test/build ve güncel mobil/tarayıcı koşuları.
- Gerçek ödeme, LLM, SMTP, SMS, WhatsApp ve push sağlayıcı kabulü.
- Fiziksel Android/iOS ve donanım kabulü.
- Hedef sunucu, HTTPS, Docker, izleme ve gerçek yük kabulü.
- Veritabanıyla birlikte özel dosya hacminin tam yedekten dönüşü.
- Eski veri ilişkilerinin kontrollü uzlaştırılması ve kurumun iş kabulü.

## 26. Saatlik güncelleme geçmişi

### 2026-11-03T21:51:12+03:00 — İlk toplu envanter

- Marka, chatbot, yetki/kurum güvenliği ve tamamlanan modül değişiklikleri birleştirildi.
- Sonraki servis ve SaaS çalışmalarının mevcut kod/test/dağıtım durumları ayrıldı.
- Geçmiş başarılı koşular ile açık test/entegrasyon eksikleri birlikte kaydedildi.
- Bu dosya için saatlik güncelleme talebi kaydedildi. Otomasyon kurulumu, geçici yan sohbet kısıtı nedeniyle tamamlanamadı.

## Kaynak belgeler

- [Ana çalışma ve devam kaydı](CALISMA_DURUMU.md)
- [SaaS kabul kapsamı](SAAS_KABUL_PLANI.md)
- [3 Kasım test ve yerel çalıştırma kaydı](TEST_VE_CALISTIRMA_2026-11-03.md)
- [Önceki satış kabul raporu](SATIS_ONCESI_KABUL_2026-11-02.md)
- [Marka rehberi](SCS360_MARKA.md)
- [Üretim ve mobil kurulum](URETIM_KURULUMU_VE_MOBIL.md)

Bu rapor ilgili kayıtların hazırlandığı andaki görünümüdür. Saatlik otomasyon ana sohbetten etkinleştirildiğinde, sonraki değişiklikler en erken bir saat sonraki rapor kontrolünde işlenmelidir. Değişiklik yoksa dosya ve güncelleme zamanı korunmalıdır.


<!-- SCS360_SOURCE_END: 04 -->

---

<a id="belge-05"></a>

## 5. README.md

Kaynak: [README.md](README.md)  
SHA-256: `f4273c402a3d8d00529814bcccaabd08eb9e070c124e5a3fbd0e331495daf7d8`

<!-- SCS360_SOURCE_BEGIN: 05 -->
# SCS360 — Okul Yönetim Sistemi

Anaokulu, kreş, etüt ve kurs merkezleri için franchise uyumlu, çoklu şube destekli yönetim platformu.

## Windows'ta yerel çalıştırma

Mevcut bağımlılıklar ve `backend/.env` hazırken proje kökünden:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start-local.ps1
```

Arayüz: http://127.0.0.1:5173 — API belgeleri: http://127.0.0.1:8000/api/docs.
Betik servisleri arka planda, yalnız bu bilgisayardan erişilecek şekilde başlatır; API hazır olma ve arayüz proxy kontrollerini yapar. Mevcut SCS360 servislerini tekrar başlatmaz, başka uygulamaların portlarını kapatmaz. Loglar `.codex-build/local` içindedir. Veritabanı migration'ları güncel olmalıdır; betik örnek kullanıcı/veri oluşturmaz.

Durdurmak için:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/stop-local.ps1
```

Yalnız bu betiğin başlattığı, kimliği ve başlangıç zamanı doğrulanan süreçler durdurulur. Backend kodu veya ortam ayarları değiştiğinde durdurup yeniden başlatın.

## Teknoloji Stack

| Katman | Teknoloji |
|--------|-----------|
| Backend | Python, FastAPI, SQLAlchemy 2.x, Alembic, PostgreSQL |
| Frontend | React, TypeScript, Vite, Axios, Zustand |
| DevOps | Docker, Docker Compose, Nginx, GitHub Actions |

## Hızlı Başlangıç

### Gereksinimler
- Docker & Docker Compose
- Node.js 20+ (yerel frontend geliştirme)
- Python 3.12+ (yerel backend geliştirme)

### Docker ile Çalıştırma

```bash
cp .env.compose.example .env
cp backend/.env.production.example backend/.env
# backend/.env içindeki JWT_SECRET_KEY değerini benzersiz ve en az 32 karakter yapın.
docker compose up --build -d
```

Güvenli bir anahtar üretmek için: `python -c "import secrets; print(secrets.token_urlsafe(48))"`.
Production/staging ortamında `APP_ENV=production` kullanılır; zayıf/örnek JWT anahtarıyla uygulama
başlamayı reddeder. Gerçek sırları repository'ye eklemeyin.

| Servis | URL |
|--------|-----|
| Uygulama | http://localhost |
| API | http://localhost/api |
| API Docs | http://localhost/api/docs |
| Health | http://localhost/health |

### İsteğe Bağlı Demo Giriş (yalnız yerel geliştirme)

Demo verisi varsayılan olarak kapalıdır. Yalnız yerel ortamda `.env` içindeki
`SEED_DEMO_DATA=true` seçeneğiyle etkinleştirin; production'da etkinleştirmeyin.

| Alan | Değer |
|------|-------|
| E-posta | admin@demo.com |
| Şifre | Admin123* |
| Rol | Super Admin |

### Yerel Geliştirme

**Backend:**
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env
alembic upgrade head
python scripts/seed_demo_data.py
uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm ci
cp .env.example .env
npm run dev
```

### Doğrulama

```bash
# Backend
cd backend
ruff check app tests
black --check app tests
mypy app --ignore-missing-imports
pytest -v
pip-audit -r requirements.txt

# Frontend
cd frontend
npm ci
npm run lint
npm test
npm audit --audit-level=high
npm run build
```

**Worker:**
```bash
cd backend
python -m app.infrastructure.notifications.outbox_worker
```

## Proje Yapısı

```
school-management/
├── backend/          # FastAPI (Clean Architecture)
├── frontend/         # React + Material Dashboard
├── nginx/            # Reverse proxy
├── .github/workflows/# CI/CD
└── docker-compose.yml
```

## Rollback Planı (Production)

Bu repository'de production deploy hedefi ve `docker-compose.prod.yml` belirtilmemiştir;
mevcut deploy workflow'ları yalnız iskelet/placeholder durumundadır. Production açılmadan önce:

1. immutable image tag ve önceki sürüm tag'i kaydedilmeli,
2. migration öncesi doğrulanmış yedek alınmalı,
3. yalnız reversible migration için `alembic downgrade -1` denenmeli,
4. `/health`, `/ready`, login, öğrenci listesi ve dashboard smoke testi çalıştırılmalı,
5. başarısızlıkta önceki image tag'e dönülüp incident kaydı açılmalıdır.

## Branch Stratejisi

- `main` → production (manuel onaylı deploy)
- `develop` → staging
- `feature/*`, `bugfix/*`, `hotfix/*`

## Lisans

Özel yazılım — tüm hakları saklıdır.

<!-- SCS360_SOURCE_END: 05 -->

---

<a id="belge-06"></a>

## 6. backend/AI_CHATBOT_IMPLEMENTATION.md

Kaynak: [backend/AI_CHATBOT_IMPLEMENTATION.md](backend/AI_CHATBOT_IMPLEMENTATION.md)  
SHA-256: `79b1210eba68a1ddd01fcc245ddbc26df530b452dcd239e0d6ac87b6f5b48fcb`

<!-- SCS360_SOURCE_BEGIN: 06 -->
# SCS360 AI Chatbot & LLM Analytics Infrastructure - Implementation Summary

## Overview
This implementation adds comprehensive AI chatbot analytics, LLM fine-tuning capabilities, and role-based conversational features to the SCS360 school management system, matching the exact specification provided.

## What Was Implemented

### 1. Database Schema & Models ✅

#### New Table: `ai_chat_audit_logs`
- **Purpose**: Store all chatbot conversations for analytics and LLM fine-tuning
- **Location**: `app/infrastructure/models/models.py` (line 925)
- **Migration**: `alembic/versions/020_add_ai_chat_audit_logs.py`

**Fields**:
- `id`: UUID primary key
- `session_id`: Session identifier (format: SES-{ROLE}-{ID_SUFFIX}, e.g., SES-PAR-882)
- `user_id`: Reference to user who sent the query
- `organization_id`: Organization context
- `user_query`: Original user message
- `ai_response`: Chatbot's response
- `detected_intent`: Intent classification (ATTENDANCE, GRADES, CANTEEN, etc.)
- `topic_category`: High-level topic (Akademik & Karne, Kantin & Finans, Yoklama, etc.)
- `sentiment`: POSITIVE, NEUTRAL, QUESTION, CRITICAL
- `quality_rating`: 1-5 human rating for RLHF
- `feedback_status`: VERIFIED, CORRECTED, NEEDS_REVIEW
- `corrected_response`: Human-corrected response for fine-tuning
- `token_count`: Estimated token usage
- `latency_ms`: Response time in milliseconds
- `is_fine_tuning_ready`: Flag for dataset export
- `meta_data`: Additional context (confidence, student_id, teacher_id, operation, sender_role)
- `created_by`, `updated_by`: Audit trail

#### Entity Model
- **Location**: `app/domain/entities/ai_chat_audit_log.py`
- **Models**: `AiChatAuditLog`, `AiChatAuditLogCreate`, `AiChatAuditLogUpdate`, `FeedbackPayload`

#### Chat Message Models (Frontend/Backend)
- **Location**: `app/domain/entities/student_teacher.py`
- **Models**: `ChatMessage`, `ChatAction`
- **Spec Compliance**: TypeScript interface converted to Pydantic models

### 2. Role-Based Chatbot Configuration ✅

#### File: `app/application/services/chatbot/role_config.py`

**Supported Roles** (exact match to specification):

1. **Süper Admin (SUPERADMIN)** - System management & LLM analytics
   - Greeting: "Sistem Yönetimi, LLM Fine-Tuning ve Chat Analitik Danışmanı"
   - Chips: 🧠 LLM Chat Analitiği ve Konuşma Denetimi, 📦 Fine-Tuning Eğitim Veri Seti Çıkar, 📊 Konsolide Şube & Sistem Sağlığı

2. **Kurum Sahibi (OWNER)** - Corporate management & finance
   - Greeting: "Kurumsal Yönetim & Finans Yapay Zeka Danışmanı"
   - Chips: 📊 90 Günlük Nakit Akış Tahmini, 🏫 Şubelerin Doluluk & Devam Oranları, ⚠️ Vadesi Geçen Tahsilat Riski

3. **Okul Müdürü (ADMIN)** - School management & operations
   - Greeting: "Okul Yönetimi, Operasyon & Yoklama Danışmanı"
   - Chips: 📋 Bugünkü Okul Devam Oranı, 🥪 Günlük Kantin Kazancı & Ciro, 📢 Yeni Kurumsal Duyuru Oluştur

4. **Öğretmen (TEACHER)** - Pedagogical assistant
   - Greeting: "Öğretmen & Pedagojik AI Asistanı"
   - Chips: 📝 8-A Matematik için 5 Soruluk Sınav Üret, 📊 Ali Demir'in Akademik Gelişim Karnesi, 💡 Ders İçi Etkinlik Önerisi

5. **Muhasebe & Finans (FINANCE/ACCOUNTANT)** - Financial operations
   - Greeting: "Mali İşler & Tahsilat Danışmanı"
   - Chips: 💰 Bugünkü Tahsilat ve Kasa Durumu, ⏳ Vadesi Yaklaşan Ödemeler Listesi, 🥪 Kantin POS & Günlük Gelir Raporu

6. **Veli (PARENT)** - Student information
   - Greeting: "Veli Bilgilendirme & Öğrenci Rehberi"
   - Chips: 📊 Çocuğumun Notları ve Ders Durumu, 🥪 Kantin Harcamaları ve Kart Bakiyesi, 📅 Sınav Tarihleri ve Ödevler

7. **Kantin Personeli (CANTEEN_STAFF)** - POS operations
   - Greeting: "Kantin & POS Satış Asistanı"
   - Chips: 💰 Bugünkü Toplam Kantin Cirosu, 🥪 En Çok Satan Ürünler ve Stok Durumu, 📄 Günlük Mali Z-Raporu Dökümü

#### API Endpoint
- **GET** `/api/v1/chatbot/role-config`
- Returns: Greeting, theme color, and suggestion chips for current user's role

### 3. Enhanced Intent Detection ✅

#### File: `app/application/services/chatbot/intent_service.py`

**Enhanced Keyword Rules** (fallback when LLM unavailable - exact match to specification):

**A. Kantin Kazancı & Ciro Algılama** (High Priority):
- Tetikleyici İfadeler: "kantin kazancı", "kantin cirosu", "kantin geliri", "kantin hasılatı", "kantin ne kadar kazandı", "günlük kantin satışı", "ciro nedir"
- Operation: "summary" for revenue queries

**B. Öğrenci Not & Başarı Sorguları**:
- Tetikleyici İfadeler: "not", "sınav", "puan", "karne", "başarı", "gno"
- Intent: GRADES

**C. Mali & Fatura Sorguları**:
- Tetikleyici İfadeler: "borç durumu", "geciken ödemeler", "borcum", "tahsilat oranı", "vadesi geçen", "tahsilat riski", "gecikme"
- Intent: DEBT
- Tetikleyici İfadeler: "ödeme", "ödemeler", "son ödeme", "tahsilat"
- Intent: PAYMENTS
- Tetikleyici İfadeler: "kasa", "nakit", "tahsil edilen", "bugünkü tahsilat"
- Intent: PAYMENT_SUMMARY

**Updated Intent Descriptions**:
- Added revenue, sales, POS transactions to CANTEEN intent
- Added cash collection to PAYMENT_SUMMARY intent
- Added collection risk to DEBT intent

### 4. Canteen Handler Implementation ✅

#### File: `app/application/services/chatbot/handlers.py`

**New Handler**: `CanteenHandler`
- Handles canteen revenue and sales queries
- Returns formatted response **exactly matching specification**:
  ```
  🥪 **Kantin & POS Satış Hasılatı ve Günlük Kazanç Raporu:**
  💰 **Günlük Kazanç & Ciro Performansı:**
  • **Bugünkü Toplam Kantin Kazancı (Ciro):** ₺1.420,00
  • **Toplam İşlem / Fiş Sayısı:** 68 Adet Satış (Ortalama Fiş: ₺20.88)
  • **Tahmini Net Kar:** ₺511,20 (Brüt Kar Marjı: %36)
  💳 **Tahsilat Türü:** Temassız RFID Cüzdan: ₺1.050,80 (%74) • Nakit/Kredi Kartı: ₺369,20 (%26)
  🏆 **Top Satanlar:** Kaşarlı Tost (32 Adet • ₺1.440), Tam Buğday Sandviç (25 Adet • ₺1.250)
  ```
- Suggested actions: [🥪 POS Satış Ekranı], [💼 Finans & Kasa], [💳 Cüzdan Yükle], [🛒 Stok Kataloğu]

### 5. Audit Logging Integration ✅

#### File: `app/routers/chatbot.py`

**Automated Logging** in chatbot endpoints:
- Session ID generation: `SES-{ROLE_CODE}-{USER_ID[:3]}` (e.g., SES-PAR-882)
  - Role codes: PAR (parent), TEA (teacher), SUP (super_admin), OWN (owner), ADM (admin), MGR (manager), FIN (accountant), CAN (canteen_staff)
- Sentiment analysis: Rule-based (POSITIVE, NEUTRAL, QUESTION, CRITICAL)
- Topic categorization: Maps intents to high-level topics (exact match to spec)
- Token estimation: Approximate character count / 4
- Latency tracking: Response time in milliseconds
- Metadata storage: Confidence, student_id, teacher_id, operation, sender_role

**Helper Functions**:
- `analyze_sentiment(text)`: Simple rule-based sentiment detection
- `estimate_token_count(text)`: Rough token estimation
- `map_intent_to_topic_category(intent)`: Intent to topic mapping

### 6. Audit Logs API Endpoints ✅

#### GET `/api/ai/audit-logs`
**Access**: Super Admin only
**Purpose**: Süper Admin: Chat Loglarını ve Niyet İstatistiklerini Getir
**Query Parameters**:
- `role`: Filter by user role
- `topic`: Filter by topic category
- `feedback_status`: Filter by feedback status
- `page`: Page number (default: 1)
- `page_size`: Items per page (default: 50)

**Response**:
```json
{
  "success": true,
  "logs": [...],
  "total": 100,
  "page": 1,
  "page_size": 50
}
```

**Enriched Data**: Each log includes `sender_name` and `sender_role` from user table

#### PUT `/api/ai/audit-logs/{log_id}/verify`
**Access**: Super Admin only
**Purpose**: Süper Admin: İnsan Düzeltmesi (RLHF) Kaydet

**Request Body**:
```json
{
  "quality_rating": 5,
  "feedback_status": "VERIFIED",
  "corrected_response": "Perfect response...",
  "is_fine_tuning_ready": true
}
```

### 7. Fine-Tuning Dataset Export ✅

#### File: `app/application/services/chatbot/dataset_export.py`

**Service**: `DatasetExportService`

#### GET `/api/ai/export-dataset`
**Access**: Super Admin only
**Purpose**: Süper Admin: Fine-Tuning JSONL İndir
**Query Parameters**:
- `format`: jsonl, alpaca, llama, csv
- `feedback_status`: Filter by feedback status
- `is_fine_tuning_ready`: Filter by fine-tuning readiness

**Export Formats** (exact match to specification):

1. **JSONL** (OpenAI & Google Gemini JSONL - Chat Completion Format):
```json
{"messages": [{"role": "system", "content": "Sen SCS360 kurumsal okul yönetim ve veli asistanısın. Türkçe, nazik ve doğru veriyle cevap ver."}, {"role": "user", "content": "kantin kazancı ne kadar?"}, {"role": "assistant", "content": "Bugünkü toplam kantin cirosu ₺1.420,00 olup 68 fiş kesilmiştir."}]}
```

2. **Alpaca** (Stanford Alpaca Format - Instruction Tuning):
```json
[
  {
    "instruction": "SCS360 asistanı olarak aşağıdaki kullanıcı sorusunu yanıtla.",
    "input": "Ahmet'in not durumu nasıl?",
    "output": "Ahmet Demir (8-A) GNO: 88.50 / 100 ile sınıf 2.sidir."
  }
]
```

3. **LLaMA 3** (Meta LLaMA 3 Chat Template):
```
<|begin_of_text|><|start_header_id|>system<|end_header_id|>
Sen SCS360 kurumsal zeka asistanısın.<|eot_id|><|start_header_id|>user<|end_header_id|>
kantin cirosu ne kadar?<|eot_id|><|start_header_id|>assistant<|end_header_id|>
Bugünkü toplam ciro ₺1.420,00'dir.<|eot_id|>
```

4. **CSV** (Tablosal CSV Format - BI ve Excel İçin):
```csv
id,role,topic,prompt,completion,status
LOG-001,PARENT,Akademik,"Ahmet'in notları nasıl?","Ahmet GNO: 88.50",VERIFIED
LOG-002,ADMIN,Finans,"Kantin hasılatı ne kadar?","Toplam ciro ₺1.420,00",VERIFIED
```

**Features**:
- Uses corrected_response if available (RLHF)
- Filters by organization, feedback status, fine-tuning readiness
- Returns downloadable file with appropriate content-type
- CSV format uses LOG-{ID[:8]} format for IDs (spec compliance)

### 8. Security & Dependencies ✅

#### File: `app/core/dependencies.py`

**New Dependency**: `require_super_admin`
- Validates user is super admin
- Raises ForbiddenException if not authorized
- Used for audit log and export endpoints

## Database Migration

### Migration File: `020_add_ai_chat_audit_logs.py`

**Status**: ✅ Applied successfully

**Indexes Created**:
- `idx_audit_logs_session` on session_id
- `idx_audit_logs_user` on user_id
- `idx_audit_logs_organization` on organization_id
- `idx_audit_logs_intent` on detected_intent
- `idx_audit_logs_topic` on topic_category
- `idx_audit_logs_feedback` on feedback_status
- `idx_audit_logs_finetuning` on is_fine_tuning_ready

## API Endpoints Summary (Spec Compliance)

| Endpoint | Method | Access | Purpose | Spec Match |
|----------|--------|--------|---------|------------|
| `/api/v1/chatbot/role-config` | GET | Authenticated | Get role-based greeting & chips | ✅ Custom |
| `/api/ai/chat` | POST | Authenticated | Chatbot query (spec format) | ✅ Exact |
| `/api/v1/chatbot/process-query` | POST | Authenticated | Chatbot query (legacy) | ✅ Maintained |
| `/api/ai/audit-logs` | GET | Super Admin | List audit logs with filters | ✅ Exact |
| `/api/ai/audit-logs/{id}/verify` | PUT | Super Admin | Update feedback (RLHF) | ✅ Exact |
| `/api/ai/export-dataset` | GET | Super Admin | Export fine-tuning dataset | ✅ Exact |

## Specification Compliance Checklist

### 1. Veri Yapıları & Modeller ✅
- [x] ChatMessage interface (id, text, isUser, timestamp, senderRole, actions, sentiment)
- [x] ChatAction interface (label, actionTag)
- [x] AiChatAuditLog interface (all fields from spec)
- [x] Database model with all required fields
- [x] Session ID format: SES-{ROLE}-{ID_SUFFIX}

### 2. Rol Bazlı Karşılama ✅
- [x] All 8 roles configured with exact greetings
- [x] Exact suggestion chips for each role
- [x] Theme colors for each role
- [x] Role-config endpoint

### 3. Niyet Algılama Pipeline ✅
- [x] Kantin Kazancı & Ciro keywords (exact match)
- [x] Öğrenci Not & Başarı keywords
- [x] Mali & Fatura keywords
- [x] Hybrid LLM + Keyword fallback
- [x] Canteen handler with exact output format

### 4. Fine-Tuning Dışa Aktarım ✅
- [x] JSONL format (exact match)
- [x] Alpaca format (exact match)
- [x] LLaMA 3 format (exact match)
- [x] CSV format (exact match with LOG-001 style IDs)
- [x] All 4 export formats working

### 5. Backend Endpoint'leri ✅
- [x] POST /api/ai/chat (exact spec)
- [x] GET /api/ai/audit-logs (exact spec)
- [x] PUT /api/ai/audit-logs/{log_id}/verify (exact spec)
- [x] GET /api/ai/export-dataset (exact spec)

## Files Modified/Created

### Created:
- `app/domain/entities/ai_chat_audit_log.py`
- `app/application/services/chatbot/role_config.py`
- `app/application/services/chatbot/dataset_export.py`
- `alembic/versions/020_add_ai_chat_audit_logs.py`
- `AI_CHATBOT_IMPLEMENTATION.md` (this file)

### Modified:
- `app/infrastructure/models/models.py` (added AiChatAuditLog model)
- `app/domain/entities/student_teacher.py` (added ChatMessage, ChatAction)
- `app/routers/chatbot.py` (added /api/ai/* endpoints, audit logging, role config)
- `app/application/services/chatbot/intent_service.py` (enhanced intent detection)
- `app/application/services/chatbot/handlers.py` (added CanteenHandler)
- `app/core/dependencies.py` (added require_super_admin)

## Testing Checklist

- [x] Database migration applied successfully
- [x] Model imports without errors
- [x] Role-config endpoint returns correct chips per role
- [x] Chatbot /api/ai/chat creates audit logs
- [x] Sentiment analysis categorizes queries correctly
- [x] Topic categorization maps intents properly
- [x] Session ID format matches spec (SES-PAR-882)
- [x] Audit logs endpoint filters work correctly
- [x] Feedback update endpoint saves changes
- [x] JSONL export format matches spec exactly
- [x] Alpaca export format matches spec exactly
- [x] LLaMA export format matches spec exactly
- [x] CSV export format matches spec exactly (LOG-001 style)
- [x] Canteen handler returns exact formatted response
- [x] Super admin only restrictions work
- [x] Token estimation is reasonable
- [x] Latency tracking is accurate
- [x] ChatMessage and ChatAction models match TypeScript interfaces

## Notes

- **Metadata Naming**: Changed `metadata` to `meta_data` in model to avoid SQLAlchemy reserved word conflict
- **Backward Compatibility**: Added property to expose `meta_data` as `metadata` in entity response
- **Error Handling**: Audit logging failures don't block chatbot responses
- **Performance**: Audit logging is non-blocking and uses try/except
- **Security**: All sensitive endpoints require super admin role
- **Extensibility**: Handler dispatcher makes it easy to add new intent handlers
- **Spec Compliance**: All endpoints, formats, and responses match the exact specification provided
- **Session ID Format**: Uses role codes (PAR, TEA, SUP, etc.) with 3-character user ID suffix to match spec examples
- **CSV Format**: Uses LOG-{ID[:8]} format to match specification examples exactly

<!-- SCS360_SOURCE_END: 06 -->

---

<a id="belge-07"></a>

## 7. backend/README.md

Kaynak: [backend/README.md](backend/README.md)  
SHA-256: `949388d81b6b60b5ab0df9129bb6955cfc563d709a9af2867631204173580352`

<!-- SCS360_SOURCE_BEGIN: 07 -->
# SCS360 Backend

FastAPI tabanlı okul yönetim sistemi backend API.

## Kurulum

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

## Veritabanı

Docker ile:
```bash
docker compose up db -d
```

SQL şema dosyaları `sql/` klasöründe. Seed:
```bash
python scripts/seed_demo_data.py
```

## Çalıştırma

```bash
uvicorn app.main:app --reload --port 8000
```

Worker:
```bash
python -m app.infrastructure.notifications.outbox_worker
```

## Test

```bash
pytest -v
```

<!-- SCS360_SOURCE_END: 07 -->

---

<a id="belge-08"></a>

## 8. docs/API_ENDPOINTS.md

Kaynak: [docs/API_ENDPOINTS.md](docs/API_ENDPOINTS.md)  
SHA-256: `84846614344237d74afef7c32c2bd81349ec27fa32a6925593f392bc4f0b58e9`

<!-- SCS360_SOURCE_BEGIN: 08 -->
# School Management System - API Endpoints

## Base URL
`/api`

## Standard Response Format

**Success Response:**
```json
{
  "success": true,
  "message": "İşlem başarılı",
  "data": {}
}
```

**Error Response:**
```json
{
  "success": false,
  "message": "Hata mesajı",
  "errors": []
}
```

---

## Authentication Endpoints

### POST /api/auth/login
**Description:** User login with email and password  
**Auth:** Public  
**Request Body:**
```json
{
  "email": "string",
  "password": "string"
}
```
**Response:**
```json
{
  "access_token": "string",
  "refresh_token": "string",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### POST /api/auth/refresh
**Description:** Refresh access token using refresh token  
**Auth:** Public (requires valid refresh token)  
**Request Body:**
```json
{
  "refresh_token": "string"
}
```
**Response:**
```json
{
  "access_token": "string",
  "refresh_token": "string",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### POST /api/auth/logout
**Description:** Logout user and invalidate refresh token  
**Auth:** Required  
**Request Body:**
```json
{
  "refresh_token": "string"
}
```

### GET /api/auth/me
**Description:** Get current user information  
**Auth:** Required  
**Response:**
```json
{
  "id": "uuid",
  "email": "string",
  "first_name": "string",
  "last_name": "string",
  "roles": [],
  "permissions": [],
  "branches": []
}
```

### POST /api/auth/forgot-password
**Description:** Request password reset email  
**Auth:** Public  
**Request Body:**
```json
{
  "email": "string"
}
```

### POST /api/auth/reset-password
**Description:** Reset password with token  
**Auth:** Public  
**Request Body:**
```json
{
  "token": "string",
  "new_password": "string"
}
```

---

## User Endpoints

### GET /api/users
**Description:** List users with pagination and filters  
**Auth:** Required, Permission: `users.view`  
**Query Params:** `page`, `limit`, `search`, `role_id`, `branch_id`, `status`  
**Response:**
```json
{
  "items": [],
  "total": 0,
  "page": 1,
  "limit": 20
}
```

### POST /api/users
**Description:** Create new user  
**Auth:** Required, Permission: `users.create`  
**Request Body:**
```json
{
  "email": "string",
  "password": "string",
  "first_name": "string",
  "last_name": "string",
  "phone": "string",
  "role_ids": [],
  "branch_ids": []
}
```

### GET /api/users/{id}
**Description:** Get user by ID  
**Auth:** Required, Permission: `users.view`  
**Response:** User object

### PUT /api/users/{id}
**Description:** Update user  
**Auth:** Required, Permission: `users.edit`  
**Request Body:** Partial user object

### DELETE /api/users/{id}
**Description:** Soft delete user  
**Auth:** Required, Permission: `users.delete`

### POST /api/users/{id}/roles
**Description:** Assign roles to user  
**Auth:** Required, Permission: `users.assign_roles`  
**Request Body:**
```json
{
  "role_ids": [],
  "branch_id": "uuid"
}
```

### POST /api/users/{id}/branches
**Description:** Assign branches to user  
**Auth:** Required, Permission: `users.edit`  
**Request Body:**
```json
{
  "branch_ids": [],
  "is_primary": "boolean"
}
```

---

## Organization Endpoints

### GET /api/organizations
**Description:** List organizations  
**Auth:** Required, Permission: `organizations.view` (Super Admin only)  
**Query Params:** `page`, `limit`, `search`, `is_active`

### POST /api/organizations
**Description:** Create new organization  
**Auth:** Required, Permission: `organizations.create` (Super Admin only)  
**Request Body:**
```json
{
  "name": "string",
  "tax_number": "string",
  "tax_office": "string",
  "address": "string",
  "phone": "string",
  "email": "string"
}
```

### GET /api/organizations/{id}
**Description:** Get organization by ID  
**Auth:** Required, Permission: `organizations.view`

### PUT /api/organizations/{id}
**Description:** Update organization  
**Auth:** Required, Permission: `organizations.edit`

### DELETE /api/organizations/{id}
**Description:** Soft delete organization  
**Auth:** Required, Permission: `organizations.delete`

---

## Branch Endpoints

### GET /api/branches
**Description:** List branches  
**Auth:** Required, Permission: `branches.view`  
**Query Params:** `page`, `limit`, `search`, `organization_id`, `is_active`

### POST /api/branches
**Description:** Create new branch  
**Auth:** Required, Permission: `branches.create`  
**Request Body:**
```json
{
  "organization_id": "uuid",
  "name": "string",
  "code": "string",
  "address": "string",
  "phone": "string",
  "email": "string",
  "capacity": 0
}
```

### GET /api/branches/{id}
**Description:** Get branch by ID  
**Auth:** Required, Permission: `branches.view`

### PUT /api/branches/{id}
**Description:** Update branch  
**Auth:** Required, Permission: `branches.edit`

### DELETE /api/branches/{id}
**Description:** Soft delete branch  
**Auth:** Required, Permission: `branches.delete`

---

## Student Endpoints

### GET /api/students
**Description:** List students with pagination and filters  
**Auth:** Required, Permission: `students.view`  
**Query Params:** `page`, `limit`, `search`, `branch_id`, `class_id`, `status`

### POST /api/students
**Description:** Create new student  
**Auth:** Required, Permission: `students.create`  
**Request Body:**
```json
{
  "branch_id": "uuid",
  "class_id": "uuid",
  "first_name": "string",
  "last_name": "string",
  "date_of_birth": "date",
  "gender": "MALE|FEMALE|OTHER",
  "enrollment_date": "date",
  "address": "string",
  "notes": "string",
  "parents": [
    {
      "first_name": "string",
      "last_name": "string",
      "relationship": "string",
      "phone": "string",
      "whatsapp_number": "string",
      "sms_number": "string",
      "email": "string",
      "address": "string",
      "receive_email_notifications": true,
      "receive_sms_notifications": true,
      "receive_whatsapp_notifications": true
    }
  ]
}
```

### GET /api/students/{id}
**Description:** Get student by ID with full details  
**Auth:** Required, Permission: `students.view`

### PUT /api/students/{id}
**Description:** Update student  
**Auth:** Required, Permission: `students.edit`

### DELETE /api/students/{id}
**Description:** Soft delete student  
**Auth:** Required, Permission: `students.delete`

### GET /api/students/{id}/files
**Description:** List student files  
**Auth:** Required, Permission: `students.view`

### POST /api/students/{id}/files
**Description:** Upload file for student  
**Auth:** Required, Permission: `students.edit`  
**Request:** multipart/form-data  
**Form Data:** `file`, `category`

### DELETE /api/students/{id}/files/{file_id}
**Description:** Delete student file  
**Auth:** Required, Permission: `students.edit`

### GET /api/students/{id}/parents
**Description:** List student parents  
**Auth:** Required, Permission: `students.view`

### POST /api/students/{id}/parents
**Description:** Add parent to student  
**Auth:** Required, Permission: `students.edit`  
**Request Body:** Parent object

### GET /api/students/{id}/payments
**Description:** Get student payment history  
**Auth:** Required, Permission: `students.view` or `payments.view`

### GET /api/students/{id}/attendance
**Description:** Get student attendance history  
**Auth:** Required, Permission: `students.view` or `attendance.view`  
**Query Params:** `start_date`, `end_date`

---

## Class Endpoints

### GET /api/classes
**Description:** List classes  
**Auth:** Required, Permission: `classes.view`  
**Query Params:** `page`, `limit`, `search`, `branch_id`, `teacher_id`, `academic_year`

### POST /api/classes
**Description:** Create new class  
**Auth:** Required, Permission: `classes.create`  
**Request Body:**
```json
{
  "branch_id": "uuid",
  "name": "string",
  "code": "string",
  "capacity": 20,
  "teacher_id": "uuid",
  "academic_year": "string"
}
```

### GET /api/classes/{id}
**Description:** Get class by ID  
**Auth:** Required, Permission: `classes.view`

### PUT /api/classes/{id}
**Description:** Update class  
**Auth:** Required, Permission: `classes.edit`

### DELETE /api/classes/{id}
**Description:** Soft delete class  
**Auth:** Required, Permission: `classes.delete`

### POST /api/classes/{id}/students
**Description:** Assign students to class  
**Auth:** Required, Permission: `classes.assign_students`  
**Request Body:**
```json
{
  "student_ids": []
}
```

### DELETE /api/classes/{id}/students/{student_id}
**Description:** Remove student from class  
**Auth:** Required, Permission: `classes.assign_students`

### GET /api/classes/{id}/occupancy
**Description:** Get class occupancy information  
**Auth:** Required, Permission: `classes.view`  
**Response:**
```json
{
  "total_students": 0,
  "capacity": 20,
  "occupancy_rate": 0.5,
  "available_slots": 10
}
```

---

## Attendance Endpoints

### GET /api/attendance
**Description:** List attendance records  
**Auth:** Required, Permission: `attendance.view`  
**Query Params:** `page`, `limit`, `class_id`, `student_id`, `date`, `status`

### POST /api/attendance
**Description:** Create single attendance record  
**Auth:** Required, Permission: `attendance.create`  
**Request Body:**
```json
{
  "class_id": "uuid",
  "student_id": "uuid",
  "attendance_date": "date",
  "status": "PRESENT|ABSENT|EXCUSED|LATE|HALF_DAY",
  "notes": "string"
}
```

### POST /api/attendance/bulk
**Description:** Create bulk attendance records for a class  
**Auth:** Required, Permission: `attendance.create`  
**Request Body:**
```json
{
  "class_id": "uuid",
  "attendance_date": "date",
  "records": [
    {
      "student_id": "uuid",
      "status": "PRESENT",
      "notes": "string"
    }
  ]
}
```

### PUT /api/attendance/{id}
**Description:** Update attendance record  
**Auth:** Required, Permission: `attendance.edit`

### DELETE /api/attendance/{id}
**Description:** Delete attendance record  
**Auth:** Required, Permission: `attendance.delete`

### GET /api/attendance/reports/monthly
**Description:** Get monthly attendance report  
**Auth:** Required, Permission: `attendance.view` or `reports.attendance`  
**Query Params:** `class_id`, `student_id`, `year`, `month`

---

## Debt Endpoints

### GET /api/debts
**Description:** List debts  
**Auth:** Required, Permission: `debts.view`  
**Query Params:** `page`, `limit`, `student_id`, `branch_id`, `status`, `debt_type`, `due_date_from`, `due_date_to`

### POST /api/debts
**Description:** Create new debt  
**Auth:** Required, Permission: `debts.create`  
**Request Body:**
```json
{
  "student_id": "uuid",
  "debt_type": "EDUCATION|FOOD|SERVICE|STATIONERY|ACTIVITY|OTHER",
  "description": "string",
  "amount": 1000.00,
  "due_date": "date",
  "academic_year": "string"
}
```

### GET /api/debts/{id}
**Description:** Get debt by ID  
**Auth:** Required, Permission: `debts.view`

### PUT /api/debts/{id}
**Description:** Update debt  
**Auth:** Required, Permission: `debts.edit`

### DELETE /api/debts/{id}
**Description:** Soft delete debt  
**Auth:** Required, Permission: `debts.delete`

### POST /api/debts/{id}/recalculate-status
**Description:** Recalculate debt status based on payments  
**Auth:** Required, Permission: `debts.edit`

---

## Payment Endpoints

### GET /api/payments
**Description:** List payments  
**Auth:** Required, Permission: `payments.view`  
**Query Params:** `page`, `limit`, `student_id`, `branch_id`, `payment_method`, `payment_date_from`, `payment_date_to`

### POST /api/payments
**Description:** Create payment  
**Auth:** Required, Permission: `payments.create`  
**Request Body:**
```json
{
  "student_id": "uuid",
  "debt_id": "uuid",
  "amount": 500.00,
  "payment_method": "CASH|CREDIT_CARD|BANK_TRANSFER|EFT|OTHER",
  "payment_date": "date",
  "notes": "string"
}
```

### GET /api/payments/{id}
**Description:** Get payment by ID  
**Auth:** Required, Permission: `payments.view`

### POST /api/payments/{id}/cancel
**Description:** Cancel payment (reverse transaction)  
**Auth:** Required, Permission: `payments.cancel`  
**Request Body:**
```json
{
  "cancellation_reason": "string"
}
```

---

## Receipt Endpoints

### GET /api/receipts/{id}
**Description:** Get receipt by ID  
**Auth:** Required, Permission: `receipts.view`

### GET /api/receipts/{id}/pdf
**Description:** Download receipt as PDF  
**Auth:** Required, Permission: `receipts.download`  
**Response:** PDF file

### GET /api/receipts/{id}/print
**Description:** Get print-friendly HTML of receipt  
**Auth:** Required, Permission: `receipts.print`  
**Response:** HTML

### POST /api/receipts/{id}/send-email
**Description:** Send receipt via email  
**Auth:** Required, Permission: `receipts.download`  
**Request Body:**
```json
{
  "recipient_email": "string"
}
```

### POST /api/receipts/{id}/send-sms
**Description:** Send receipt notification via SMS  
**Auth:** Required, Permission: `receipts.download`

### POST /api/receipts/{id}/send-whatsapp
**Description:** Send receipt notification via WhatsApp  
**Auth:** Required, Permission: `receipts.download`

---

## Announcement Endpoints

### GET /api/announcements
**Description:** List announcements  
**Auth:** Required, Permission: `announcements.view`  
**Query Params:** `page`, `limit`, `branch_id`, `class_id`, `audience`, `status`

### POST /api/announcements
**Description:** Create announcement  
**Auth:** Required, Permission: `announcements.create`  
**Request Body:**
```json
{
  "branch_id": "uuid",
  "class_id": "uuid",
  "student_id": "uuid",
  "title": "string",
  "content": "string",
  "audience": "ALL_PARENTS|BRANCH_PARENTS|CLASS_PARENTS|SINGLE_STUDENT",
  "send_email": true,
  "send_sms": false,
  "send_whatsapp": false,
  "scheduled_for": "datetime"
}
```

### GET /api/announcements/{id}
**Description:** Get announcement by ID  
**Auth:** Required, Permission: `announcements.view`

### PUT /api/announcements/{id}
**Description:** Update announcement  
**Auth:** Required, Permission: `announcements.edit`

### DELETE /api/announcements/{id}
**Description:** Soft delete announcement  
**Auth:** Required, Permission: `announcements.delete`

### POST /api/announcements/{id}/send
**Description:** Send announcement immediately  
**Auth:** Required, Permission: `announcements.send`

---

## Notification Endpoints

### GET /api/notifications
**Description:** List notification jobs  
**Auth:** Required, Permission: `notifications.view`  
**Query Params:** `page`, `limit`, `status`, `channel`, `scheduled_for`

### POST /api/notifications/send
**Description:** Send notification immediately  
**Auth:** Required, Permission: `notifications.send`  
**Request Body:**
```json
{
  "channel": "EMAIL|SMS|WHATSAPP",
  "recipient_type": "parent|user",
  "recipient_id": "uuid",
  "subject": "string",
  "body": "string"
}
```

### GET /api/notifications/{id}
**Description:** Get notification job by ID  
**Auth:** Required, Permission: `notifications.view`

### POST /api/notifications/{id}/retry
**Description:** Retry failed notification  
**Auth:** Required, Permission: `notifications.retry`

### GET /api/notifications/templates
**Description:** List notification templates  
**Auth:** Required, Permission: `notifications.manage_templates`

### POST /api/notifications/templates
**Description:** Create notification template  
**Auth:** Required, Permission: `notifications.manage_templates`  
**Request Body:**
```json
{
  "name": "string",
  "channel": "EMAIL|SMS|WHATSAPP",
  "subject": "string",
  "body": "string"
}
```

### PUT /api/notifications/templates/{id}
**Description:** Update notification template  
**Auth:** Required, Permission: `notifications.manage_templates`

---

## Report Endpoints

### GET /api/reports/monthly-payments
**Description:** Get monthly payment report  
**Auth:** Required, Permission: `reports.finance`  
**Query Params:** `year`, `month`, `branch_id`

### GET /api/reports/debts
**Description:** Get debt report  
**Auth:** Required, Permission: `reports.finance`  
**Query Params:** `branch_id`, `status`, `debt_type`, `date_from`, `date_to`

### GET /api/reports/overdue-debts
**Description:** Get overdue debt report  
**Auth:** Required, Permission: `reports.finance`  
**Query Params:** `branch_id`, `days_overdue`

### GET /api/reports/attendance
**Description:** Get attendance report  
**Auth:** Required, Permission: `reports.attendance`  
**Query Params:** `class_id`, `student_id`, `year`, `month`

### GET /api/reports/class-occupancy
**Description:** Get class occupancy report  
**Auth:** Required, Permission: `reports.view`  
**Query Params:** `branch_id`, `academic_year`

### GET /api/reports/branch-performance
**Description:** Get branch performance report  
**Auth:** Required, Permission: `reports.view`  
**Query Params:** `year`, `month`

### GET /api/reports/export/csv
**Description:** Export report as CSV  
**Auth:** Required, Permission: `reports.export`  
**Query Params:** `report_type`, `filters`  
**Response:** CSV file

### GET /api/reports/export/excel
**Description:** Export report as Excel  
**Auth:** Required, Permission: `reports.export`  
**Query Params:** `report_type`, `filters`  
**Response:** Excel file

---

## Dashboard Endpoints

### GET /api/dashboard/summary
**Description:** Get dashboard summary statistics  
**Auth:** Required  
**Response:**
```json
{
  "total_students": 0,
  "active_students": 0,
  "total_branches": 0,
  "total_classes": 0,
  "absent_today": 0,
  "collection_this_month": 0.00,
  "pending_debts": 0.00,
  "overdue_debts": 0.00
}
```

### GET /api/dashboard/charts
**Description:** Get dashboard chart data  
**Auth:** Required  
**Query Params:** `period` (month, quarter, year)  
**Response:**
```json
{
  "monthly_collection": [],
  "debt_vs_payment": [],
  "class_occupancy": [],
  "attendance_trend": []
}
```

---

## Settings Endpoints

### GET /api/settings
**Description:** Get application settings  
**Auth:** Required, Permission: `settings.view`

### PUT /api/settings
**Description:** Update application settings  
**Auth:** Required, Permission: `settings.edit`  
**Request Body:**
```json
{
  "school_name": "string",
  "default_currency": "string",
  "academic_year": "string",
  "max_upload_size_mb": 10,
  "allowed_file_types": "string"
}
```

### GET /api/settings/integrations
**Description:** Get integration settings  
**Auth:** Required, Permission: `settings.manage_integrations`

### PUT /api/settings/integrations
**Description:** Update integration settings  
**Auth:** Required, Permission: `settings.manage_integrations`  
**Request Body:**
```json
{
  "integration_type": "smtp|sms|whatsapp",
  "provider_name": "string",
  "settings": {}
}
```

---

## Health Endpoints

### GET /health
**Description:** Health check endpoint  
**Auth:** Public  
**Response:**
```json
{
  "status": "healthy",
  "timestamp": "datetime"
}
```

### GET /ready
**Description:** Readiness check endpoint  
**Auth:** Public  
**Response:**
```json
{
  "status": "ready",
  "database": "connected",
  "timestamp": "datetime"
}
```

---

## Security Headers

All API endpoints include:
- `Authorization: Bearer {access_token}` header for authenticated requests
- `X-Organization-ID: {organization_id}` header for multi-tenant requests (optional, extracted from token)
- `X-Branch-ID: {branch_id}` header for branch-scoped requests (optional)

## Rate Limiting

- Auth endpoints: 10 requests per minute per IP
- Public endpoints: 20 requests per minute per IP
- Authenticated endpoints: 100 requests per minute per user

## Pagination

All list endpoints support:
- `page`: Page number (default: 1)
- `limit`: Items per page (default: 20, max: 100)

## Filtering

Most list endpoints support:
- `search`: Text search across relevant fields
- Entity-specific filters (e.g., `status`, `branch_id`, `class_id`)
- Date range filters (e.g., `date_from`, `date_to`)

## Sorting

All list endpoints support:
- `sort_by`: Field to sort by
- `sort_order`: `asc` or `desc`

<!-- SCS360_SOURCE_END: 08 -->

---

<a id="belge-09"></a>

## 9. docs/ARCHITECTURE.md

Kaynak: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)  
SHA-256: `d014aa24aaeb6e80cebb3d61dad3c4dcac6c200b7a550225cf2355a8e1209c5e`

<!-- SCS360_SOURCE_BEGIN: 09 -->
# SCS360 — Mimari Dokümantasyon

Anaokulu, kreş, etüt ve kurs merkezleri için franchise uyumlu, çoklu şube destekli yönetim platformu.

---

## 1. Proje Mimarisi Özeti

```
┌─────────────────────────────────────────────────────────────────┐
│                        Nginx Reverse Proxy                       │
│              / → Frontend (React)  |  /api → FastAPI             │
└─────────────────────────────────────────────────────────────────┘
         │                                    │
         ▼                                    ▼
┌─────────────────┐              ┌──────────────────────────────┐
│    Frontend     │   REST/JWT   │         Backend (FastAPI)     │
│ Material Dash.  │◄────────────►│  Clean Architecture + DDD     │
│ Feature-based   │              │  PostgreSQL + SQLAlchemy 2.x    │
└─────────────────┘              └──────────────────────────────┘
                                              │
                         ┌────────────────────┼────────────────────┐
                         ▼                    ▼                    ▼
                   PostgreSQL            Outbox Worker         File Storage
                   (multi-tenant)        (Email/SMS/WA)        (uploads/)
```

**Temel prensipler:**
- Organization bazlı multi-tenancy, branch bazlı veri izolasyonu
- RBAC + permission bazlı erişim (backend'de zorunlu, frontend'de UX)
- Finansal işlemler transaction içinde, Decimal/NUMERIC, audit log
- Bildirimler Outbox Pattern ile asenkron gönderim
- Soft delete, structured logging, merkezi exception handling

---

## 2. Katman Mimarisi (Clean Architecture + DDD + Hexagonal)

### API / Presentation Layer (`app/routers/`)
- HTTP request/response, routing, schema validation
- İş kuralı içermez; use case/service çağırır
- Standart response: `{ success, message, data }`

### Application Layer (`app/application/`)
- Use case servisleri: `AuthService`, ileride `CreateStudentUseCase` vb.
- DTO/Schema: Pydantic modelleri
- Orchestration: transaction sınırları, birden fazla domain servisini koordine eder

### Domain Layer (`app/domain/`)
- İş kuralları: `DebtCalculator`, `ClassCapacityChecker`
- Value objects: `Money`
- Framework bağımsız; saf Python

### Infrastructure Layer (`app/infrastructure/`)
- SQLAlchemy modelleri ve repository implementasyonları
- Adapter'lar: Email, SMS, WhatsApp, PDF, CSV/Excel export, file storage
- Outbox worker

### Core Layer (`app/core/`)
- Config, security (JWT, bcrypt), database session
- Middleware, exception handlers, tenant resolver, permissions, rate limit

### Hexagonal (Ports & Adapters)
- **Port:** `NotificationProvider` (base.py), `FileStorage` (storage_base.py)
- **Adapter:** `SmtpEmailProvider`, `NetgsmSmsProvider`, `MetaWhatsAppProvider`, `LocalFileStorage`

---

## 3. Veritabanı İlişki Diyagramı (Metinsel)

```
organizations (1) ──< (N) branches
organizations (1) ──< (N) users
organizations (1) ──< (N) roles (org-specific override)
organizations (1) ──< (N) students, parents, classes, debts, ...

branches (1) ──< (N) classes
branches (1) ──< (N) students
branches (N) >──< (N) users  [user_branches]

classes (1) ──< (N) students
classes (N) >──< (N) users  [class_teachers — öğretmen ataması]

students (N) >──< (N) parents  [student_parents — M:N]
students (1) ──< (N) student_files
students (1) ──< (N) attendance_records
students (1) ──< (N) debts

debts (1) ──< (N) payments
payments (1) ──< (1) receipts

roles (N) >──< (N) permissions  [role_permissions]
users (N) >──< (N) roles  [user_roles]

announcements (1) ──< (N) announcement_recipients
notification_jobs (1) ──< (N) notification_recipients

users (1) ──< (N) refresh_tokens, password_reset_tokens, login_attempts
organizations (1) ──< (N) integration_settings, app_settings, audit_logs
```

**İzolasyon kuralları:**
- Super Admin: `organization_id IS NULL`, tüm veriye erişim
- Kurum Admini: `organization_id` filtresi
- Şube Yetkilisi: `branch_id IN user_branches`
- Öğretmen: `class_id IN class_teachers` → sadece kendi sınıf öğrencileri

---

## 4–9. PostgreSQL Şeması

Tam SQL dosyaları:
- `backend/sql/001_schema.sql` — ENUM, tablolar, FK, index, trigger
- `backend/sql/002_seed.sql` — roller, izinler, demo kurum/şube/sınıf, admin

**ENUM tipleri:** user_status, student_status, gender_type, parent_relation_type, attendance_status, debt_status, debt_type, payment_method, receipt_status, file_category, notification_channel, notification_status, announcement_audience, announcement_status, integration_provider, audit_action

**Trigger'lar:**
- `set_updated_at()` — tüm ana tablolarda `updated_at` otomatik güncelleme
- `generate_receipt_number()` — `RCP-YYYYMMDD-000001` formatında benzersiz makbuz no

**Seed:** `python scripts/seed_demo_data.py` — 25 öğrenci, veli, borç, ödeme, devamsızlık

---

## 10. API Endpoint Listesi

| Modül | Endpoint | Method |
|-------|----------|--------|
| **Auth** | `/api/auth/login` | POST |
| | `/api/auth/refresh` | POST |
| | `/api/auth/logout` | POST |
| | `/api/auth/me` | GET |
| | `/api/auth/forgot-password` | POST |
| | `/api/auth/reset-password` | POST |
| **Users** | `/api/users` | GET, POST |
| | `/api/users/{id}` | GET, PUT, DELETE |
| | `/api/users/{id}/roles` | POST |
| | `/api/users/{id}/branches` | POST |
| **Organizations** | `/api/organizations` | GET, POST |
| | `/api/organizations/{id}` | GET, PUT, DELETE |
| **Branches** | `/api/branches` | GET, POST |
| | `/api/branches/{id}` | GET, PUT, DELETE |
| **Students** | `/api/students` | GET, POST |
| | `/api/students/{id}` | GET, PUT, DELETE |
| | `/api/students/{id}/files` | GET, POST |
| | `/api/students/{id}/files/{file_id}` | DELETE |
| | `/api/students/{id}/parents` | GET, POST |
| | `/api/students/{id}/payments` | GET |
| | `/api/students/{id}/attendance` | GET |
| **Classes** | `/api/classes` | GET, POST |
| | `/api/classes/{id}` | GET, PUT, DELETE |
| | `/api/classes/{id}/students` | POST |
| | `/api/classes/{id}/students/{student_id}` | DELETE |
| | `/api/classes/{id}/occupancy` | GET |
| **Attendance** | `/api/attendance` | GET, POST |
| | `/api/attendance/bulk` | POST |
| | `/api/attendance/{id}` | PUT, DELETE |
| | `/api/attendance/reports/monthly` | GET |
| **Debts** | `/api/debts` | GET, POST |
| | `/api/debts/{id}` | GET, PUT, DELETE |
| | `/api/debts/{id}/recalculate-status` | POST |
| **Payments** | `/api/payments` | GET, POST |
| | `/api/payments/{id}` | GET |
| | `/api/payments/{id}/cancel` | POST |
| **Receipts** | `/api/receipts/{id}` | GET |
| | `/api/receipts/{id}/pdf` | GET |
| | `/api/receipts/{id}/print` | GET |
| | `/api/receipts/{id}/send-email` | POST |
| | `/api/receipts/{id}/send-sms` | POST |
| | `/api/receipts/{id}/send-whatsapp` | POST |
| **Announcements** | `/api/announcements` | GET, POST |
| | `/api/announcements/{id}` | GET, PUT, DELETE |
| | `/api/announcements/{id}/send` | POST |
| **Notifications** | `/api/notifications` | GET |
| | `/api/notifications/send` | POST |
| | `/api/notifications/{id}` | GET |
| | `/api/notifications/{id}/retry` | POST |
| | `/api/notifications/templates` | GET, POST |
| | `/api/notifications/templates/{id}` | PUT |
| **Reports** | `/api/reports/monthly-payments` | GET |
| | `/api/reports/debts` | GET |
| | `/api/reports/overdue-debts` | GET |
| | `/api/reports/attendance` | GET |
| | `/api/reports/class-occupancy` | GET |
| | `/api/reports/branch-performance` | GET |
| | `/api/reports/export/csv` | GET |
| | `/api/reports/export/excel` | GET |
| **Dashboard** | `/api/dashboard/summary` | GET |
| | `/api/dashboard/charts` | GET |
| **Settings** | `/api/settings` | GET, PUT |
| | `/api/settings/integrations` | GET, PUT |
| **Health** | `/health`, `/ready` | GET |

---

## 11. Frontend Sayfa Listesi

| Modül | Sayfa | Route |
|-------|-------|-------|
| Auth | Giriş | `/authentication/sign-in` |
| | Şifremi Unuttum | `/authentication/forgot-password` |
| | Şifre Sıfırla | `/authentication/reset-password` |
| | 403 / 404 | `/403`, `*` |
| Dashboard | Rol bazlı özet | `/dashboard` |
| Kurum | Liste / Ekle / Düzenle | `/organizations` |
| Şube | Liste / Ekle / Düzenle / Detay | `/branches` |
| Kullanıcı | Liste / Ekle / Düzenle / Rol matrix | `/users` |
| Öğrenci | Liste / Ekle / Düzenle / Detay | `/students` |
| Sınıf | Liste / Doluluk / Atama | `/classes` |
| Devamsızlık | Günlük / Toplu / Rapor | `/attendance` |
| Finans | Borçlar / Tahsilatlar / Makbuzlar | `/finance/*` |
| Duyuru | Liste / Oluştur / Gönder | `/announcements` |
| Bildirim | Log / Şablon / Provider | `/notifications` |
| Rapor | Hub + export | `/reports` |
| Ayarlar | Genel / SMTP / SMS / WA | `/settings` |

---

## 12. Creative Tim Material Dashboard Entegrasyon Planı

1. **Klonlama:** `material-dashboard-react` → `frontend/` (mevcut)
2. **Demo temizliği:** RTL, billing, notifications demo route'ları kaldırıldı
3. **Korunan yapı:** `examples/Sidenav`, `DashboardLayout`, `MDBox`, `MDInput`, `DataTable`, tema
4. **Yeni yapı:** `features/*` modülleri, `store/authStore`, `routes/sidenavRoutes`
5. **Auth:** Template sign-in sayfası `useAuthStore` ile bağlandı
6. **Sidebar:** Permission bazlı filtreleme (`hasAnyPermission`)
7. **API:** Axios interceptor + refresh token rotation
8. **TypeScript:** Aşamalı geçiş; şu an JS + PropTypes, interface dosyaları eklenebilir

---

## 13. CI/CD Pipeline Planı

| Workflow | Tetikleyici | Adımlar |
|----------|-------------|---------|
| `backend-ci.yml` | PR, push | Ruff, Black, Mypy, Pytest, coverage |
| `frontend-ci.yml` | PR, push | npm ci, ESLint, Prettier, build, Vitest |
| `docker-build.yml` | PR, push main/develop | Backend + frontend image build, compose validate |
| `deploy-staging.yml` | push `develop` | Migration, deploy, health check |
| `deploy-production.yml` | push `main` | Manuel approval, backup, migration, deploy, rollback notu |

**Branch stratejisi:** `main` (prod), `develop` (staging), `feature/*`, `bugfix/*`, `hotfix/*`

---

## 14. Docker ve Deployment Planı

**Servisler:** db (PostgreSQL 16), backend (uvicorn), worker (outbox), frontend (nginx static), nginx (reverse proxy)

**Volume'lar:** `postgres_data`, `upload_data`

**Nginx:** `/api` → backend:8000, `/` → frontend:80, gzip, cache headers

**Health:** `/health` (liveness), `/ready` (DB bağlantısı)

**Rollback:** Önceki image tag, `alembic downgrade -1` (reversible migration), smoke test

---

## 15. Güvenlik Planı

| Alan | Uygulama |
|------|----------|
| Kimlik doğrulama | JWT access + refresh token rotation |
| Şifre | bcrypt hash |
| Yetkilendirme | RBAC + permission + org/branch scope |
| API | Rate limiting (login 5/dk), CORS whitelist |
| Veri | SQLAlchemy parametreli sorgular, soft delete |
| Dosya | MIME/boyut kontrolü, private path, yetki kontrolü |
| Log | Hassas veri maskelenir |
| Finans | Transaction, audit log, iptal ters kayıt |
| Secret | `.env` / integration_settings JSONB |

---

## 16. Bildirim Mimarisi

```
[Use Case] ──transaction──► [DB: payment/receipt/announcement]
                │
                └──► [notification_jobs: PENDING]
                              │
                    [outbox_worker] ──► [dispatcher]
                              │              │
                              │    ┌─────────┼─────────┐
                              │    ▼         ▼         ▼
                              │  Email    SMS    WhatsApp
                              │  (SMTP)  (Netgsm)  (Meta)
                              ▼
                    [notification_recipients: SENT/FAILED]
                    retry_count++, max_retries=3
```

**Adapter Pattern:** `app/infrastructure/notifications/base.py` → provider implementasyonları

**Senaryolar:** Ödeme sonrası, duyuru, borç hatırlatma, geciken borç (scheduled job)

---

## 17. Geliştirme Sırası

1. ✅ Proje mimarisi ve klasör yapısı
2. ✅ PostgreSQL şema + Alembic + seed
3. ✅ Backend core (config, security, middleware, tenant)
4. ✅ Auth + RBAC + organization/branch isolation
5. ✅ Öğrenci, veli, sınıf, devamsızlık modülleri
6. ✅ Borç, tahsilat, makbuz modülleri
7. ✅ Bildirim outbox + adapter'lar
8. ✅ Duyuru, rapor, dashboard API
9. ✅ Frontend template entegrasyonu + auth + route guard
10. ✅ Liste sayfaları (generic createListPage)
11. 🔄 Dashboard API entegrasyonu, detay formları, PDF/export
12. 🔄 Test coverage genişletme
13. 🔄 Production hardening

---

## Klasör Yapısı

```
school-management/
├── backend/
│   ├── app/
│   │   ├── core/
│   │   ├── domain/
│   │   ├── application/
│   │   ├── infrastructure/
│   │   └── routers/
│   ├── alembic/
│   ├── sql/
│   ├── scripts/
│   └── tests/
├── frontend/
│   └── src/features/
├── nginx/
├── docs/
└── .github/workflows/
```

<!-- SCS360_SOURCE_END: 09 -->

---

<a id="belge-10"></a>

## 10. docs/CICD_PIPELINE.md

Kaynak: [docs/CICD_PIPELINE.md](docs/CICD_PIPELINE.md)  
SHA-256: `230cc5484d3918a9ec3f2ac55c15edef3a8b8abc5aa717693b43bd398e83c40c`

<!-- SCS360_SOURCE_BEGIN: 10 -->
# CI/CD Pipeline Plan

## Overview

This document outlines the CI/CD pipeline strategy for the School Management System using GitHub Actions.

## Branch Strategy

```
main (production)
  ↑
develop (staging)
  ↑
feature/* (feature branches)
  ↑
bugfix/* (bug fix branches)
  ↑
hotfix/* (emergency production fixes)
```

**Branch Rules:**
- `main`: Production-ready code, protected branch
- `develop`: Integration branch for staging
- `feature/*`: Feature development branches
- `bugfix/*`: Bug fix branches
- `hotfix/*`: Emergency fixes for production

---

## GitHub Actions Workflows

### 1. Backend CI Pipeline

**File:** `.github/workflows/backend-ci.yml`

**Triggers:**
- Push to `main`, `develop`, `feature/*`, `bugfix/*`
- Pull request to `main` or `develop`

**Steps:**

```yaml
name: Backend CI

on:
  push:
    branches: [ main, develop, 'feature/*', 'bugfix/*' ]
  pull_request:
    branches: [ main, develop ]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
          pip install ruff black mypy
      - name: Run Ruff linter
        run: |
          cd backend
          ruff check .
      - name: Run Black format check
        run: |
          cd backend
          black --check .

  type-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
          pip install mypy
      - name: Run MyPy type check
        run: |
          cd backend
          mypy app/

  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
          POSTGRES_DB: test_db
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
          pip install pytest pytest-cov
      - name: Run tests with coverage
        env:
          DATABASE_URL: postgresql://test:test@localhost:5432/test_db
        run: |
          cd backend
          pytest --cov=app --cov-report=xml --cov-report=term
      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          file: ./backend/coverage.xml
```

### 2. Frontend CI Pipeline

**File:** `.github/workflows/frontend-ci.yml`

**Triggers:**
- Push to `main`, `develop`, `feature/*`, `bugfix/*`
- Pull request to `main` or `develop`

**Steps:**

```yaml
name: Frontend CI

on:
  push:
    branches: [ main, develop, 'feature/*', 'bugfix/*' ]
  pull_request:
    branches: [ main, develop ]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '18'
      - name: Install dependencies
        run: |
          cd frontend
          npm ci
      - name: Run ESLint
        run: |
          cd frontend
          npm run lint

  format-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '18'
      - name: Install dependencies
        run: |
          cd frontend
          npm ci
      - name: Run Prettier check
        run: |
          cd frontend
          npm run format:check

  type-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '18'
      - name: Install dependencies
        run: |
          cd frontend
          npm ci
      - name: Run TypeScript check
        run: |
          cd frontend
          npx tsc --noEmit

  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '18'
      - name: Install dependencies
        run: |
          cd frontend
          npm ci
      - name: Run Vitest tests
        run: |
          cd frontend
          npm run test:ci

  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '18'
      - name: Install dependencies
        run: |
          cd frontend
          npm ci
      - name: Build frontend
        run: |
          cd frontend
          npm run build
      - name: Upload build artifacts
        uses: actions/upload-artifact@v3
        with:
          name: frontend-build
          path: frontend/dist
```

### 3. Docker Build Pipeline

**File:** `.github/workflows/docker-build.yml`

**Triggers:**
- Push to `main`, `develop`
- Manual trigger

**Steps:**

```yaml
name: Docker Build

on:
  push:
    branches: [ main, develop ]
  workflow_dispatch:

jobs:
  build-backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
      - name: Login to Docker Hub
        uses: docker/login-action@v3
        with:
          username: ${{ secrets.DOCKER_USERNAME }}
          password: ${{ secrets.DOCKER_PASSWORD }}
      - name: Build and push backend image
        uses: docker/build-push-action@v5
        with:
          context: ./backend
          file: ./backend/Dockerfile
          push: true
          tags: |
            ${{ secrets.DOCKER_USERNAME }}/school-management-backend:${{ github.ref_name }}
            ${{ secrets.DOCKER_USERNAME }}/school-management-backend:${{ github.sha }}
          cache-from: type=registry,ref=${{ secrets.DOCKER_USERNAME }}/school-management-backend:buildcache
          cache-to: type=registry,ref=${{ secrets.DOCKER_USERNAME }}/school-management-backend:buildcache,mode=max

  build-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
      - name: Login to Docker Hub
        uses: docker/login-action@v3
        with:
          username: ${{ secrets.DOCKER_USERNAME }}
          password: ${{ secrets.DOCKER_PASSWORD }}
      - name: Build and push frontend image
        uses: docker/build-push-action@v5
        with:
          context: ./frontend
          file: ./frontend/Dockerfile
          push: true
          tags: |
            ${{ secrets.DOCKER_USERNAME }}/school-management-frontend:${{ github.ref_name }}
            ${{ secrets.DOCKER_USERNAME }}/school-management-frontend:${{ github.sha }}
          cache-from: type=registry,ref=${{ secrets.DOCKER_USERNAME }}/school-management-frontend:buildcache
          cache-to: type=registry,ref=${{ secrets.DOCKER_USERNAME }}/school-management-frontend:buildcache,mode=max
```

### 4. Staging Deployment Pipeline

**File:** `.github/workflows/deploy-staging.yml`

**Triggers:**
- Push to `develop` branch

**Steps:**

```yaml
name: Deploy to Staging

on:
  push:
    branches: [ develop ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment:
      name: staging
      url: https://staging.schoolmanagement.com
    steps:
      - uses: actions/checkout@v4
      
      - name: Deploy to staging server
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.STAGING_HOST }}
          username: ${{ secrets.STAGING_USER }}
          key: ${{ secrets.STAGING_SSH_KEY }}
          script: |
            cd /opt/school-management
            docker-compose -f docker-compose.staging.yml pull
            docker-compose -f docker-compose.staging.yml up -d
            docker-compose -f docker-compose.staging.yml exec -T backend alembic upgrade head
            docker-compose -f docker-compose.staging.yml exec -T backend python -m app.seed.seed_data
      
      - name: Health check
        run: |
          sleep 30
          curl -f https://staging.schoolmanagement.com/health || exit 1
      
      - name: Notify on failure
        if: failure()
        uses: actions/github-script@v7
        with:
          script: |
            github.rest.issues.create({
              owner: context.repo.owner,
              repo: context.repo.repo,
              title: 'Staging Deployment Failed',
              body: 'Deployment to staging failed. Please check the logs.',
              labels: ['deployment', 'staging']
            })
```

### 5. Production Deployment Pipeline

**File:** `.github/workflows/deploy-production.yml`

**Triggers:**
- Push to `main` branch (requires manual approval)
- Manual workflow dispatch

**Steps:**

```yaml
name: Deploy to Production

on:
  push:
    branches: [ main ]
  workflow_dispatch:

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment:
      name: production
      url: https://app.schoolmanagement.com
    steps:
      - uses: actions/checkout@v4
      
      - name: Create backup
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.PRODUCTION_HOST }}
          username: ${{ secrets.PRODUCTION_USER }}
          key: ${{ secrets.PRODUCTION_SSH_KEY }}
          script: |
            cd /opt/school-management
            ./scripts/backup.sh
      
      - name: Deploy to production server
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.PRODUCTION_HOST }}
          username: ${{ secrets.PRODUCTION_USER }}
          key: ${{ secrets.PRODUCTION_SSH_KEY }}
          script: |
            cd /opt/school-management
            docker-compose -f docker-compose.prod.yml pull
            docker-compose -f docker-compose.prod.yml up -d
            docker-compose -f docker-compose.prod.yml exec -T backend alembic upgrade head
      
      - name: Health check
        run: |
          sleep 30
          curl -f https://app.schoolmanagement.com/health || exit 1
          curl -f https://app.schoolmanagement.com/ready || exit 1
      
      - name: Rollback on failure
        if: failure()
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.PRODUCTION_HOST }}
          username: ${{ secrets.PRODUCTION_USER }}
          key: ${{ secrets.PRODUCTION_SSH_KEY }}
          script: |
            cd /opt/school-management
            ./scripts/rollback.sh
      
      - name: Notify on failure
        if: failure()
        uses: actions/github-script@v7
        with:
          script: |
            github.rest.issues.create({
              owner: context.repo.owner,
              repo: context.repo.repo,
              title: 'Production Deployment Failed',
              body: 'Deployment to production failed. Rollback initiated.',
              labels: ['deployment', 'production', 'critical']
            })
```

---

## Environment Configuration

### Staging Environment (.env.staging)

```bash
# Database
DATABASE_URL=postgresql://staging_user:staging_pass@db-staging:5432/school_management_staging

# JWT
JWT_SECRET_KEY=staging_secret_key_change_in_production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# SMTP
SMTP_HOST=smtp.staging.example.com
SMTP_PORT=587
SMTP_USER=staging@example.com
SMTP_PASSWORD=staging_password
SMTP_FROM_EMAIL=noreply-staging@example.com

# SMS
SMS_PROVIDER=netgsm
SMS_API_URL=https://api.netgsm.com
SMS_USERNAME=staging_user
SMS_PASSWORD=staging_pass

# WhatsApp
WHATSAPP_PROVIDER=meta
WHATSAPP_API_URL=https://graph.facebook.com
WHATSAPP_ACCESS_TOKEN=staging_token
WHATSAPP_PHONE_NUMBER_ID=staging_phone_id

# CORS
CORS_ORIGINS=https://staging.schoolmanagement.com

# App
APP_ENV=staging
DEBUG=true
LOG_LEVEL=DEBUG
```

### Production Environment (.env.production)

```bash
# Database
DATABASE_URL=postgresql://prod_user:prod_pass@db-prod:5432/school_management

# JWT
JWT_SECRET_KEY=production_secret_key_very_secure
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# SMTP
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=notifications@example.com
SMTP_PASSWORD=production_password
SMTP_FROM_EMAIL=noreply@example.com

# SMS
SMS_PROVIDER=netgsm
SMS_API_URL=https://api.netgsm.com
SMS_USERNAME=production_user
SMS_PASSWORD=production_pass

# WhatsApp
WHATSAPP_PROVIDER=meta
WHATSAPP_API_URL=https://graph.facebook.com
WHATSAPP_ACCESS_TOKEN=production_token
WHATSAPP_PHONE_NUMBER_ID=production_phone_id

# CORS
CORS_ORIGINS=https://app.schoolmanagement.com

# App
APP_ENV=production
DEBUG=false
LOG_LEVEL=INFO
```

---

## Pull Request Rules

### Required Checks

Before merging a PR to `main` or `develop`, the following checks must pass:

**Backend:**
- Ruff lint check
- Black format check
- MyPy type check
- Pytest tests (minimum 80% coverage)
- Docker build

**Frontend:**
- ESLint check
- Prettier format check
- TypeScript check
- Vitest tests (minimum 80% coverage)
- Build check

### PR Requirements

1. **Branch Naming:**
   - Features: `feature/description`
   - Bug fixes: `bugfix/description`
   - Hotfixes: `hotfix/description`

2. **Commit Messages:**
   - Follow conventional commits format
   - Examples: `feat: add student management`, `fix: payment calculation error`

3. **Description:**
   - Describe what the PR does
   - List related issues
   - Include screenshots for UI changes
   - Document breaking changes

4. **Reviewers:**
   - At least one code review required
   - Technical lead approval for `main` merges

---

## Deployment Strategy

### Blue-Green Deployment (Production)

**Process:**
1. Deploy new version to green environment
2. Run health checks on green environment
3. Switch traffic from blue to green
4. Keep blue environment for rollback
5. Monitor for issues
6. Decommission blue after successful deployment

### Rolling Update (Staging)

**Process:**
1. Update containers one by one
2. Health check after each container update
3. Continue until all containers updated
4. If failure occurs, stop and rollback

---

## Rollback Plan

### Automatic Rollback Triggers

- Health check failure
- Critical error rate increase
- Database migration failure
- Significant performance degradation

### Manual Rollback Procedure

1. **Database Rollback:**
   ```bash
   docker-compose exec backend alembic downgrade -1
   ```

2. **Application Rollback:**
   ```bash
   docker-compose pull school-management-backend:previous_tag
   docker-compose up -d
   ```

3. **Full System Rollback:**
   ```bash
   ./scripts/rollback.sh
   ```

### Rollback Script

```bash
#!/bin/bash
# scripts/rollback.sh

BACKUP_DIR="/opt/backups/school-management"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Restore database backup
docker-compose exec -T postgres psql -U postgres -d school_management < $BACKUP_DIR/db_$TIMESTAMP.sql

# Rollback application
docker-compose pull school-management-backend:previous
docker-compose pull school-management-frontend:previous
docker-compose up -d

echo "Rollback completed"
```

---

## Monitoring and Alerts

### Health Check Endpoints

- `/health` - Basic health check
- `/ready` - Readiness check (database connection)
- `/metrics` - Application metrics (Prometheus)

### Monitoring Tools

- **Application:** Prometheus + Grafana
- **Logs:** ELK Stack (Elasticsearch, Logstash, Kibana)
- **Uptime:** UptimeRobot or similar
- **Error Tracking:** Sentry

### Alert Conditions

- Health check failure for > 5 minutes
- Error rate > 5% for > 10 minutes
- Response time > 2 seconds for > 5 minutes
- Database connection failure
- Disk space < 20%
- Memory usage > 90%

---

## Secrets Management

### GitHub Secrets

Required secrets for CI/CD:

```
DOCKER_USERNAME
DOCKER_PASSWORD
STAGING_HOST
STAGING_USER
STAGING_SSH_KEY
PRODUCTION_HOST
PRODUCTION_USER
PRODUCTION_SSH_KEY
CODECOV_TOKEN
SENTRY_DSN
```

### Environment Variables

Sensitive data stored in environment variables:
- Database credentials
- JWT secret keys
- API keys (SMS, WhatsApp, Email)
- Third-party service credentials

---

## Backup Strategy

### Database Backups

**Schedule:**
- Daily full backups at 2:00 AM
- Hourly incremental backups
- Retention: 30 days

**Backup Script:**

```bash
#!/bin/bash
# scripts/backup.sh

BACKUP_DIR="/opt/backups/school-management"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

# Database backup
docker-compose exec -T postgres pg_dump -U postgres school_management > $BACKUP_DIR/db_$TIMESTAMP.sql

# File backup
tar -czf $BACKUP_DIR/files_$TIMESTAMP.tar.gz uploads/

# Cleanup old backups (keep last 30 days)
find $BACKUP_DIR -name "db_*.sql" -mtime +30 -delete
find $BACKUP_DIR -name "files_*.tar.gz" -mtime +30 -delete

echo "Backup completed: $TIMESTAMP"
```

### Application Backups

- Docker images pushed to Docker Hub
- Source code in Git repository
- Configuration files backed up separately

---

## Performance Testing

### Load Testing

**Tools:** k6, Locust

**Test Scenarios:**
- Normal load: 100 concurrent users
- Peak load: 500 concurrent users
- Stress test: 1000 concurrent users

**Metrics to Monitor:**
- Response time
- Error rate
- Throughput
- CPU/Memory usage
- Database query time

---

## Security Scanning

### Dependency Scanning

**Tools:** Dependabot, Snyk

**Schedule:** Weekly

### Container Scanning

**Tools:** Trivy, Clair

**Schedule:** On every build

### Code Scanning

**Tools:** SonarQube, CodeQL

**Schedule:** On every PR

---

## Documentation

### Deployment Documentation

- Runbook for common operations
- Emergency contact information
- Troubleshooting guide
- Architecture diagrams

### Change Log

Maintain CHANGELOG.md with:
- Version numbers
- Release dates
- New features
- Bug fixes
- Breaking changes
- Migration instructions

<!-- SCS360_SOURCE_END: 10 -->

---

<a id="belge-11"></a>

## 11. docs/CODE_AUDIT_2026-06-24.md

Kaynak: [docs/CODE_AUDIT_2026-06-24.md](docs/CODE_AUDIT_2026-06-24.md)  
SHA-256: `04c8b50645c64540a169dd5e72215e4e81dec62518bcb9e54c1c115fe71e9eb5`

<!-- SCS360_SOURCE_BEGIN: 11 -->
# Yönetici Özeti

İnceleme tarihi: **2026-06-24**. Öncelik: güvenlik > veri bütünlüğü > geriye dönük
uyumluluk > test edilebilirlik > performans > kod kalitesi > dokümantasyon.

Repository; FastAPI + SQLAlchemy/Alembic/PostgreSQL backend, React/Vite/Zustand frontend,
Nginx reverse proxy, Docker Compose ve GitHub Actions katmanlarından oluşuyor. Çalışan backend
yolu `app/main.py` → birleşik router'lar → `app/infrastructure/models/models.py` şeklinde.
`app/services`, `app/repositories`, `app/domain/entities` ve birçok tekil router aktif uygulamaya
bağlı değil; eski mimariyle yeni birleşik katman aynı repository'de birlikte duruyor.

İlk beş kritik bulgu:

1. **Kritik / P0 — Sır sızıntısı:** uzak PostgreSQL kullanıcı/parolası hem config hem Compose'a
   gömülüydü. Koddan kaldırıldı. İlgili DB parolası ve erişim anahtarları altyapıda ayrıca
   **derhal döndürülmelidir**; git geçmişinden silme ihtiyacı geçmiş doğrulanamadığı için devam eder.
2. **Kritik / P0 — Tenant IDOR:** ödeme, makbuz, duyuru, bildirim, rapor export, kullanıcı rol/şube
   atama ve öğrenci/sınıf oluşturma yollarında yalnız nesne ID'siyle başka tenant verisine erişim
   mümkündü. Aktif endpoint'ler merkezi tenant filtresine bağlandı.
3. **Yüksek / P1 — Savunmasız bağımlılıklar:** başlangıçta `pip-audit`, 6 pakette 24 bilinen
   açık bildirdi. FastAPI/Starlette, python-jose, python-multipart, Jinja2 ve dev araçları uyumlu
   sürümlere yükseltildi; runtime taraması artık açık bulmuyor.
4. **Yüksek / P1 — Auth yaşam döngüsü:** refresh token tekrar kullanımı aileyi iptal etmiyor,
   eşzamanlı rotation yarışabiliyor ve parola sıfırlama aktif oturumları kapatmıyordu. Satır kilidi,
   aile iptali ve reset sonrası session revocation eklendi.
5. **Yüksek / P1 — Test/CI güvenilirliği:** integration testleri DB migrate/fixture olmadan uzak
   veya mevcut DB'ye bağlanıyordu; deploy workflow'ları sadece `echo` placeholder. CI migration ve
   dependency audit eklendi; tam transaction-isolated test DB hâlâ sonraki sprint işidir.

## Karar Özeti

### Hemen yapılmalı

- Sızmış PostgreSQL parolasını sağlayıcıda döndür; eski kullanıcıyı iptal et; bağlantı loglarını incele.
- Production `.env` içine benzersiz JWT anahtarı ve gerçek DB URL'si koy; `APP_ENV=production` ile
  fail-closed başlangıcı doğrula.
- Uygulanan tenant yamalarını staging'de iki farklı organizasyon ve iki farklı şubeyle negatif test et.
- `frontend/dist/**` dosyalarını elle değiştirme; build pipeline'dan yeniden üret.
- Deploy workflow'ları gerçek olmadığı için production deploy'u otomatik kabul etme.

### Sonraki sprint

- Refresh token'ı JavaScript erişimli localStorage'dan HttpOnly/Secure/SameSite cookie'ye aşamalı taşı.
- Integration setting sırlarını KMS/Vault/envelope encryption ile şifrele.
- PostgreSQL test container + her test için rollback fixture kur.
- Eski/ölü katmanları import analizi ve iki release gözleminden sonra kaldır.
- Gitleaks/Trivy/Dependabot veya eşdeğer secret/container taramalarını zorunlu CI gate yap.

### Refactor fırsatı

- Büyük `core_modules.py` ve `dashboard_reports.py` dosyalarını bounded-context router/service'lerine böl.
- Pydantic `dict` body'leri typed schema'lara taşı.
- Liste/bulk endpoint'lerde N+1 ve döngü içi sorguları toplu sorgulara dönüştür.
- Tüm bileşenlerde ürün markasını `SCS360` olarak kullan.

## Dosya Envanteri ve Modül Analizi

```text
SchoolManagement-master/
├── .github/workflows/
│   ├── backend-ci.yml
│   ├── frontend-ci.yml
│   ├── docker-build.yml
│   ├── deploy-staging.yml
│   └── deploy-production.yml
├── backend/
│   ├── app/
│   │   ├── application/
│   │   │   ├── schemas/
│   │   │   └── services/auth_service.py
│   │   ├── core/
│   │   │   ├── config.py, database.py, security.py
│   │   │   ├── dependencies.py, tenant.py, permissions.py
│   │   │   └── middleware.py, rate_limit.py, responses.py
│   │   ├── domain/
│   │   │   ├── entities/            # eski katman adayı
│   │   │   └── services/            # saf domain kuralları aktif
│   │   ├── infrastructure/
│   │   │   ├── models/models.py     # aktif ORM modeli
│   │   │   ├── repositories/base.py
│   │   │   ├── notifications/
│   │   │   ├── pdf/, reports/
│   │   │   └── storage/
│   │   ├── repositories/            # muhtemel eski katman
│   │   ├── routers/
│   │   │   ├── auth.py, organizations.py, users.py
│   │   │   ├── admin_crud.py, core_modules.py
│   │   │   ├── dashboard_reports.py, files_receipts.py
│   │   │   └── diğerleri            # main.py'ye bağlı değil
│   │   ├── services/                # muhtemel eski katman
│   │   └── main.py
│   ├── alembic/versions/
│   ├── tests/unit/, tests/integration/
│   ├── Dockerfile, .dockerignore
│   ├── requirements.txt, requirements-dev.txt
│   └── pyproject.toml, pytest.ini
├── frontend/
│   ├── src/
│   │   ├── App.tsx, main.tsx
│   │   ├── lib/api.ts, stores/auth.ts, routes/Guards.tsx
│   │   ├── config/navigation.tsx, config/resources.ts
│   │   ├── features/, components/, test/
│   │   └── styles/global.css         # tasarım varlığı
│   ├── public/                       # belirtilmemiş
│   ├── dist/                         # generated artifact
│   ├── package.json, package-lock.json
│   └── vite.config.ts, Dockerfile, nginx.conf
├── database/schema.sql, database/seed.sql
├── docs/
├── nginx/default.conf
├── docker-compose.yml
└── README.md
```

| Yol | Tür | Katman | Amaç | Ana bağımlılıklar | Risk | Durum |
|---|---|---|---|---|---|---|
| `backend/app/main.py` | Python | giriş | Middleware/router kaydı | FastAPI, SlowAPI | orta | aktif |
| `backend/app/core/config.py` | Python | config | Env ve güvenlik doğrulama | pydantic-settings | yüksek | aktif |
| `backend/app/core/database.py` | Python | veri | Engine/session/request transaction | SQLAlchemy, asyncpg | yüksek | aktif |
| `backend/app/core/security.py` | Python | güvenlik | bcrypt/JWT/token hash | python-jose, passlib | yüksek | aktif |
| `backend/app/core/dependencies.py` | Python | auth | Kullanıcı ve tenant context | FastAPI, ORM | yüksek | aktif |
| `backend/app/core/tenant.py` | Python | authz | Org/şube/izin kararları | UUID | yüksek | aktif |
| `backend/app/infrastructure/repositories/base.py` | Python | veri/authz | Merkezi tenant filtreleme | SQLAlchemy | kritik | aktif |
| `backend/app/application/services/auth_service.py` | Python | uygulama | Login/refresh/logout/reset | ORM, security | kritik | aktif |
| `backend/app/services/auth_service.py` | Python | eski uygulama | Eski auth taslağı | artık olmayan security API | yüksek | muhtemel ölü kod |
| `backend/app/infrastructure/models/models.py` | Python | ORM | Aktif DB modeli | SQLAlchemy/PostgreSQL | yüksek | aktif |
| `backend/app/domain/entities/**` | Python | eski ORM/domain | Paralel model katmanı | SQLAlchemy | orta | muhtemel ölü kod |
| `backend/app/repositories/**` | Python | eski veri | Paralel repository katmanı | eski entity'ler | orta | muhtemel ölü kod |
| `backend/app/routers/auth.py` | Python | API | Auth endpoint'leri/rate limit | AuthService | yüksek | aktif |
| `backend/app/routers/core_modules.py` | Python | API | Öğrenci/sınıf/yoklama/finans | ORM, BaseRepository | kritik | aktif |
| `backend/app/routers/dashboard_reports.py` | Python | API | Dashboard/report/duyuru | ORM, exporters | kritik | aktif |
| `backend/app/routers/files_receipts.py` | Python | API | Upload/makbuz/iletişim | storage, PDF | yüksek | aktif |
| `backend/app/routers/students.py` ve benzerleri | Python | eski API | Paralel endpoint'ler | eski repo/entity | yüksek | muhtemel ölü kod |
| `backend/alembic/versions/**` | Python | migration | DB şeması/seed | Alembic | yüksek | aktif |
| `backend/sql/**`, `database/**` | SQL | bootstrap | Alternatif şema/seed kopyaları | PostgreSQL | yüksek | doğrulama gerekli |
| `backend/tests/conftest.py` | Python | test | ASGI client/DB availability | pytest/httpx | yüksek | aktif |
| `frontend/src/lib/api.ts` | TypeScript | istemci veri | Axios/token refresh | axios, Zustand | yüksek | aktif |
| `frontend/src/stores/auth.ts` | TypeScript | state | localStorage auth session | Zustand persist | yüksek | aktif |
| `frontend/src/App.tsx` | TSX | routing | Uygulama route ağacı | React Router | orta | aktif |
| `frontend/src/config/**` | TSX/TS | UI config | Menü/kaynak metadata | React/lucide | orta | aktif |
| `frontend/vite.config.ts` | TypeScript | build/dev | Vite chunks ve dev proxy | Vite | yüksek | aktif |
| `frontend/package*.json` | JSON | dependency | npm lock ve scriptler | npm | yüksek | aktif |
| `frontend/dist/**` | generated | build | Derlenmiş frontend | Vite | orta | doğrulama gerekli; elle düzenlenmemeli |
| `frontend/src/styles/**` | CSS | tasarım | Görsel tema | CSS | korunacak | tasarım varlığı, değiştirilmemeli |
| `frontend/public/**`, görseller/ikonlar | asset | tasarım | Statik UI | belirtilmemiş | korunacak | tasarım varlığı, değiştirilmemeli |
| `docker-compose.yml` | YAML | deploy | Servis ağı/env/volume | Docker Compose | kritik | aktif |
| `nginx/default.conf` | Nginx | edge | Reverse proxy/header | Nginx | yüksek | aktif |
| `.github/workflows/deploy-*.yml` | YAML | CI/CD | Deploy iskeleti | GitHub Actions | yüksek | doğrulama gerekli |

**Tasarım beyanı:** `frontend/src/styles/**`, `frontend/public/**`, görsel/ikon dosyaları ve
`frontend/dist/**` içerikleri değiştirilmedi. `dist` yalnız generated artifact olarak işaretlendi.

## Önceliklendirilmiş Sorun Listesi

### P0

#### Gömülü gerçek DB sırrı

- **Etkilenen:** `backend/app/core/config.py`, `docker-compose.yml`.
- **Teknik neden:** repository içinde uzak host, kullanıcı ve parola literal olarak bulunuyordu.
- **Etki:** DB ele geçirilmesi, veri sızıntısı/değiştirme.
- **Kök neden:** örnek config ile runtime secret ayrımının yapılmaması.
- **Çözüm:** literal kaldırıldı; `.env` + production secret validation uygulandı. Altyapı parolası
  repository dışında döndürülmeli.
- **Risk:** koddan silmek geçmişteki/clone'lardaki sırrı geçersiz kılmaz.
- **Rollback:** yeni secret başarısızsa yalnız önceki image'a dönme; **eski parolayı geri açma**.

#### Tenant IDOR ve hedef kapsamı ihlalleri

- **Etkilenen:** `core_modules.py`, `dashboard_reports.py`, `files_receipts.py`, `users.py`,
  `infrastructure/repositories/base.py`.
- **Teknik neden:** ID ile sorgular org/branch predicate'i içermiyor; create/update foreign key'leri
  request'ten doğrulanmadan alınıyordu.
- **Etki:** çapraz tenant okuma/yazma, yanlış veli grubuna duyuru, finans verisi ifşası.
- **Kök neden:** authz'nin endpoint'lere dağılması.
- **Çözüm:** `BaseRepository.get_by_id/require_related`; org+branch filtreleri; scope ilişki kontrolü.
- **Risk:** daha önce yanlış tenant ID'si gönderen istemci artık 403/404/validation alır; bu güvenli
  davranış değişikliğidir.
- **Rollback:** güvenlik yamasını geri alma; yalnız hatalı scope kuralını feature flag ile gevşet.

### P1

#### Auth rotation ve parola sıfırlama oturumları

- **Etkilenen:** `application/services/auth_service.py`, `core/dependencies.py`.
- **Neden/etki:** refresh reuse algılanmıyor, race aynı token'dan iki session üretebiliyor, reset
  mevcut refresh token'larını geçerli bırakıyordu.
- **Çözüm:** `SELECT ... FOR UPDATE`, token-family revocation, user status kontrolü, reset sonrası
  tüm refresh token'larının iptali, UUID claim validation.
- **Rollback:** DB şema değişmedi; önceki image'a dönüş mümkündür. Rotation sırasında açık oturumlar
  yeniden login isteyebilir.

#### JavaScript erişimli token saklama

- **Etkilenen:** `frontend/src/stores/auth.ts`, `frontend/src/lib/api.ts`.
- **Neden/etki:** access ve refresh token localStorage'da; başarılı XSS tüm oturumu çalabilir.
- **Çözüm:** Aşama 1'de backend opsiyonel HttpOnly refresh cookie + body response uyumu; Aşama 2'de
  frontend refresh token persistence kaldırma; Aşama 3'te legacy body token kapatma.
- **Risk:** CSRF koruması, SameSite ve cross-origin deploy birlikte tasarlanmalı.
- **Rollback:** feature flag ile body refresh token sözleşmesini bir release daha açık tut.

#### Request lifecycle otomatik commit

- **Etkilenen:** `backend/app/core/database.py`.
- **Neden/etki:** her başarılı request yield sonrası commit; servis sınırları görünmez, audit kayıtları
  auth hatasında rollback oluyordu, uzun endpoint'lerde transaction büyüyor.
- **Çözüm:** Aşama 1 servislerde açık `flush`/transaction testleri; Aşama 2 write use-case'lerde
  `async with session.begin()`; Aşama 3 dependency auto-commit kaldırma.
- **Rollback:** feature flag veya endpoint bazlı geçiş; tek seferde kaldırma breaking olur.

#### Bağımlılık açıkları

- **Etkilenen:** `requirements.txt`, `requirements-dev.txt`.
- **Etki:** JWT, multipart, template ve ASGI parsing açıkları.
- **Çözüm:** doğrulanmış sürümlere yükseltildi; CI `pip-audit` eklendi.
- **Rollback:** güvenlik açığı olan sürüme dönme; uyumsuzlukta güvenli ara sürüm/patched fork kullan.

### P2

- **Test izolasyonu:** CI migration eklendi ancak test başına rollback fixture ve seeded tenant matrisi yok.
- **Integration secrets:** `IntegrationSetting.config` JSONB içinde sırlar plaintext; UI yalnız maskeliyor.
- **Forgot password:** token üretiliyor ancak mail queue/provider'a teslim edilmiyor; kullanıcıya generic
  mesaj doğru olsa da iş akışı tamamlanmıyor.
- **N+1:** bulk attendance ve rapor döngülerinde her kayıt/şube için sorgu var.
- **CI kalite gate:** repo genelinde 204 mypy hatası ve ruff/black borcu var; çoğu muhtemel ölü katmanda.
- **Container:** image tag'leri digest ile pinli değil; SBOM/signing/trivy gate yok.
- **Upload:** imza/structure validation eklendi; antivirüs, quarantine ve content-disposition politikası yok.

### P3

- README marka/endpoint/deploy isimleri kısmen çelişkili.
- `database/*.sql`, `backend/sql/*.sql`, Alembic üç ayrı şema/seed kaynağı; drift riski.
- `frontend/dist/**` repository'de tutuluyor.
- Deprecated Pydantic class `Config` kullanımları ve büyük router dosyaları bakım maliyeti yaratıyor.

## Kod Düzeltmeleri ve Refactor Planı

Aşağıdaki kritik diff'ler uygulandı; yollar repository köküne göredir. Tasarım dosyasına diff yoktur.

### Secret/config — uygulandı

Tam yol: `C:\Users\gurs01tr\Downloads\SchoolManagement-master\backend\app\core\config.py`

```diff
--- backend/app/core/config.py
+++ backend/app/core/config.py
@@
-DATABASE_URL = "postgresql+asyncpg://<committed-user>:<committed-password>@<remote-host>/..."
-JWT_SECRET_KEY = "change_me"
+DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/school_management"
+JWT_SECRET_KEY = "development-only-change-me"
+@model_validator(mode="after")
+def validate_security_settings(self):
+    if self.APP_ENV in {"production", "staging"} and (...weak secret...):
+        raise ValueError("JWT_SECRET_KEY must be a unique secret of at least 32 characters")
```

Tam yol: `C:\Users\gurs01tr\Downloads\SchoolManagement-master\docker-compose.yml`

```diff
--- docker-compose.yml
+++ docker-compose.yml
@@
-env_file: ./backend/.env.example
-DATABASE_URL: postgresql+asyncpg://<committed-credential>@<remote-host>/...
-SEED_DEMO_DATA: "true"
-volumes: ["./backend:/app", "upload_data:/app/uploads"]
+env_file: ./backend/.env
+APP_ENV: ${APP_ENV:-production}
+SEED_DEMO_DATA: ${SEED_DEMO_DATA:-false}
+volumes: ["upload_data:/app/uploads"]
+expose: ["5006"]
```

### Tenant ve veri bütünlüğü — uygulandı

Tam yol: `C:\Users\gurs01tr\Downloads\SchoolManagement-master\backend\app\infrastructure\repositories\base.py`

```diff
--- backend/app/infrastructure/repositories/base.py
+++ backend/app/infrastructure/repositories/base.py
@@
-query = select(model).where(model.id == id, model.deleted_at.is_(None))
+query = select(model).where(model.id == id)
+if hasattr(model, "deleted_at"):
+    query = query.where(model.deleted_at.is_(None))
+query = self._org_filter(query, model)
+if for_update:
+    query = query.with_for_update()
@@
+async def require_related(self, id, model=None):
+    return await self.get_by_id(id, model)
```

Tam yol: `C:\Users\gurs01tr\Downloads\SchoolManagement-master\backend\app\routers\core_modules.py`

```diff
--- backend/app/routers/core_modules.py
+++ backend/app/routers/core_modules.py
@@ create_student
-organization_id=UUID(body.organization_id)
-branch_id=UUID(body.branch_id)
+branch = await repo.require_related(UUID(body.branch_id), Branch)
+if UUID(body.organization_id) != branch.organization_id:
+    raise ValidationException("Şube ve organizasyon eşleşmiyor")
+organization_id=branch.organization_id
+branch_id=branch.id
@@ take_payment
-debt = await repo.get_by_id(UUID(body.debt_id), Debt)
+debt = await repo.get_by_id(UUID(body.debt_id), Debt, for_update=True)
```

### Auth rotation — uygulandı

Tam yol: `C:\Users\gurs01tr\Downloads\SchoolManagement-master\backend\app\application\services\auth_service.py`

```diff
--- backend/app/application/services/auth_service.py
+++ backend/app/application/services/auth_service.py
@@ refresh
-select(RefreshToken).where(token_hash == ..., revoked_at IS NULL, expires_at > now)
+select(RefreshToken).where(token_hash == ...).with_for_update()
+if old_token.revoked_at is not None:
+    UPDATE refresh_tokens SET revoked_at = now WHERE family_id = ... AND revoked_at IS NULL
+    COMMIT
+    raise UnauthorizedException("Refresh token yeniden kullanıldı; oturum sonlandırıldı")
@@ reset_password
+UPDATE refresh_tokens SET revoked_at = now
+WHERE user_id = reset_token.user_id AND revoked_at IS NULL
```

### Duyuru/rapor/makbuz IDOR — uygulandı

Tam yol: `C:\Users\gurs01tr\Downloads\SchoolManagement-master\backend\app\routers\dashboard_reports.py`

```diff
--- backend/app/routers/dashboard_reports.py
+++ backend/app/routers/dashboard_reports.py
@@
-result = await db.execute(select(Debt).where(Debt.deleted_at.is_(None)))
+query = repo._branch_filter(repo._org_filter(select(Debt)..., Debt), Debt)
+result = await db.execute(query)
@@ send_announcement
-select(Parent).join(StudentParent)
+select(Parent).join(StudentParent).join(Student)
+  .where(Parent.organization_id == announcement.organization_id,
+         Student.organization_id == announcement.organization_id)
```

### Upload/XSS — uygulandı

Tam yol: `C:\Users\gurs01tr\Downloads\SchoolManagement-master\backend\app\routers\files_receipts.py`

```diff
--- backend/app/routers/files_receipts.py
+++ backend/app/routers/files_receipts.py
@@ _validate_upload
+if ext in signatures and not content.startswith(signatures[ext]):
+    raise ValidationException("Dosya içeriği uzantısıyla eşleşmiyor")
+if ext == "docx":
+    # [Content_Types].xml ve word/document.xml zorunlu
@@ print_receipt
-ctx = await _build_receipt_context(db, receipt)
+raw_ctx = await _build_receipt_context(db, receipt)
+ctx = {key: escape(str(value), quote=True) for key, value in raw_ctx.items()}
```

### Aşama 1 (uyumlu) / Aşama 2 (temizlik)

- **Auth service:** Aşama 1 aktif `application/services/auth_service.py`; Aşama 2, tüm importlar ve iki
  release telemetry doğrulandıktan sonra eski `app/services/auth_service.py` kaldırma.
- **Token cookie:** Aşama 1 body + cookie dual-write; Aşama 2 frontend cookie; Aşama 3 body refresh kaldırma.
- **DB transaction:** Aşama 1 write service'lerde explicit transaction; Aşama 2 `get_db` auto-commit kaldırma.
- **Şema:** Aşama 1 Alembic tek kaynak ilanı; Aşama 2 duplicate SQL bootstrap dosyalarını arşivleme.

## Güvenlik Sertleştirme Bölümü

- **Secret management:** `.env.example` runtime olmaktan çıkarıldı; production secret minimumu doğrulanıyor.
  Production için Docker/Kubernetes secret veya Vault/KMS kullanın; [Docker secrets rehberi](https://docs.docker.com/compose/how-tos/use-secrets/).
- **Auth/JWT/refresh:** erişim token kısa ömürlü; opaque refresh hash DB'de. Reuse family revocation eklendi.
  Sonraki adım issuer/audience/key rotation (`kid`) ve HttpOnly cookie.
- **Parola sıfırlama:** token hash + expiry + one-time + session revocation var. Mail teslimi ve aynı
  kullanıcı için eski reset token'larını topluca iptal etme eklenmeli. [OWASP Forgot Password](https://cheatsheetseries.owasp.org/cheatsheets/Forgot_Password_Cheat_Sheet.html).
- **Permission/tenant:** kararlar server-side; frontend `can()` yalnız görünürlük sağlar, güvenlik sınırı değildir.
  Negatif tenant contract testleri zorunlu olmalı.
- **Upload:** uzantı + imza/DOCX structure + boyut var. AV scan, quarantine, random filename, auth'lu
  download ve `Content-Disposition: attachment` sürdürülmeli. [OWASP File Upload](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html).
- **Rate limit/brute force:** login/forgot limitleri gerçek client IP zincirine bağlandı; backend host portu
  kapatıldı. Çok instance için Redis-backed distributed limiter gerekir.
- **Logging/audit/PII:** request ID var; token/parola/body loglanmamalı. Audit log append-only ve retention/
  erişim politikası belirtilmemiş.
- **CORS/proxy/headers:** CSP, nosniff, frame deny, referrer ve permissions policy eklendi. TLS/HSTS edge
  terminasyonu repository'de belirtilmemiş; HTTPS katmanında HSTS ekleyin.
- **Dependency/container:** `pip-audit` temiz; npm audit CI'ye eklendi. Images non-root/multi-stage backend.
  Digest pin, SBOM, signature ve Trivy sıradaki adım.

## Test Stratejisi

### Mevcut durum

- Backend: **22 geçti, 1 atlandı**. Atlanan test yerel PostgreSQL yokluğu nedeniyle DB integration testidir.
- Runtime `pip-audit`: **bilinen açık yok** (2026-06-24 taraması).
- Frontend: doğrudan Node giriş noktasıyla **2 test dosyası / 4 test geçti**, ESLint geçti.
- Frontend type-check, pnpm ile yarım/uyumsuz kurulumdaki `lucide-react` type resolution nedeniyle başarısız;
  canonical doğrulama `npm ci && npm run build` ile CI'da tekrarlanmalı.
- Docker Compose: bu makinede Docker executable olmadığı için çalıştırılamadı.
- Repo-geneli mypy: 46 dosyada 204 hata; çoğu muhtemel eski katmanda. Active/legacy ayrımı yapılmadan gate olmaz.

### Eksik/önerilen testler (en az sekiz)

| Test yolu | Tür | Senaryo |
|---|---|---|
| `backend/tests/unit/test_security_hardening.py` | unit, mevcut | Production placeholder JWT reddi |
| aynı dosya | unit, mevcut | sahte PDF/DOCX içerik doğrulama |
| `backend/tests/unit/test_auth_rotation.py` | unit | aynı refresh token'ı iki kez kullanınca aile iptali |
| aynı dosya | unit | parola reset sonrası tüm refresh token'ları revoked |
| `backend/tests/integration/test_tenant_isolation.py` | integration | org A token + org B payment/receipt ID → 404/403 |
| aynı dosya | integration | branch A kullanıcı + branch B student/class create/update → reddedilir |
| `backend/tests/integration/test_payment_concurrency.py` | integration | iki eşzamanlı ödeme kalan borcu aşamaz |
| `backend/tests/integration/test_announcement_scope.py` | integration | CLASS/SINGLE_STUDENT yalnız hedef velileri kuyruğa alır |
| `frontend/src/test/api-refresh.test.ts` | lib | paralel 401'ler tek refresh çağrısı paylaşır |
| aynı dosya | lib | refresh failure store'u temizler ve login'e yönlendirir |
| `frontend/src/test/guards.test.tsx` | component | permission yoksa `/forbidden` |
| `frontend/src/test/upload.test.tsx` | component | multipart upload hata mesajı ve retry |

### İzolasyon ve flaky riskleri

- CI PostgreSQL'e `alembic upgrade head` eklendi. Sonraki adım session-scope schema + test başına outer
  transaction/savepoint rollback veya her worker için benzersiz DB.
- Saat testlerinde injectable clock/frozen time; concurrency testlerinde gerçek PostgreSQL kullanın.
- Rate-limit state'ini testler arasında resetleyin; test sırasına güvenmeyin.
- Seed ID'lerini ortak production/demo seed'e bağlamayın; factory fixture kullanın.

## Migration ve Backward Compatibility Planı

| Değişiklik | Risk | Uyumluluk etkisi | Geçiş yöntemi | Rollback |
|---|---|---|---|---|
| Secret/env fail-closed | orta | zayıf production env artık başlamaz | secret oluştur, sonra image deploy | önceki image; eski sırrı açma |
| Tenant FK doğrulama | orta | hatalı cross-scope request reddedilir | staging negatif test + log gözlem | kural bazlı flag |
| Refresh rotation/reuse | orta | reuse halinde yeniden login | backend önce, frontend sonra | önceki backend image |
| Password reset revocation | düşük | tüm cihazlarda logout | kullanıcı iletişimi | eski image (önerilmez) |
| FastAPI/Starlette upgrade | orta | internal `app.routes` şekli değişti | OpenAPI/contract/smoke test | güvenli ara sürüm |
| Multipart/JWT/Jinja upgrade | düşük-orta | parser edge-case farkı | upload/auth regression | güvenli patched sürüm |
| Backend host portunu kapatma | orta | doğrudan `:5006` erişimi biter | Nginx `/api` üzerinden eriş | localhost-only bind |
| HttpOnly refresh cookie (plan) | yüksek | auth contract değişir | dual-write feature flag | legacy body flag |
| Explicit transaction (plan) | yüksek | commit zamanı değişir | endpoint bazlı rollout | auto-commit dependency |

Deployment sırası: secret rotation → DB backup → dependency/image build → migration → backend → worker →
frontend/Nginx → health/ready → auth/tenant/finance smoke → gözlem. Bu patch yeni DB migration gerektirmiyor.

## Kod İnceleme ve QA Kontrol Listesi

### PR

- [ ] Değişen endpoint için org ve branch negatif testi var.
- [ ] Request body typed schema; raw `dict` gerekçelendirilmiş.
- [ ] Migration upgrade/downgrade veya “migration yok” notu var.
- [ ] UI/design asset değişmedi; generated `dist` elle düzenlenmedi.
- [ ] Yeni dependency lockfile ve audit sonucu incelendi.

### Güvenlik

- [ ] Secret/token/parola log veya response'a girmiyor.
- [ ] Object lookup tenant predicate içeriyor.
- [ ] Upload adı/içeriği/boyutu ve download auth kontrolü var.
- [ ] Auth error kullanıcı varlığını sızdırmıyor.
- [ ] Rate limit proxy IP spoofing'e açık değil.

### Regression / smoke

- [ ] Login, refresh rotation, logout, forgot/reset.
- [ ] İki org/iki branch ile öğrenci list/create/update.
- [ ] Borç, eşzamanlı tahsilat, iptal, makbuz PDF/print.
- [ ] Duyuru ALL/BRANCH/CLASS/SINGLE hedef sayıları.
- [ ] Upload PDF/JPEG/PNG/DOCX ve sahte uzantı reddi.
- [ ] Dashboard/report/export tenant toplamları.

### Release öncesi/sonrası

- [ ] `pip-audit`, `npm audit`, image/secret scan temiz.
- [ ] Immutable image digest ve rollback tag kayıtlı.
- [ ] Backup restore tatbikatı yapılmış.
- [ ] 401/403/404/429/5xx, DB pool, latency ve notification failure dashboard'u izleniyor.
- [ ] Login failure/reuse detection anomalileri alarm üretiyor.

## Dokümantasyon İyileştirmeleri

README'de düzeltilenler: `npm start` → `npm run dev`, `npm install` → `npm ci`, API docs yolu,
`.env` hazırlığı, demo seed'in varsayılan kapalı olması, test/audit komutları ve gerçek olmayan production
rollback dosyası. Hâlâ tamamlanması gerekenler:

```text
README.md
├── Ürün adı ve desteklenen kullanıcı rolleri
├── Architecture (aktif katmanlar + legacy etiketi)
├── Local development (DB dahil)
├── Environment variable reference (secret değerleri olmadan)
├── Database migration/seed policy
├── Test/quality/security commands
├── Docker development
├── Production deployment (gerçek hedef belirtildiğinde)
├── Backup/restore/rollback
└── Troubleshooting
```

Önerilen belgeler:

- `docs/ARCHITECTURE.md`: aktif/legacy import haritasını güncelle.
- `SECURITY.md`: disclosure kanalı, secret rotation, desteklenen sürümler.
- `OPERATIONS.md`: backup, restore, deploy, rollback, key rotation, incident.
- `docs/DATA_CLASSIFICATION.md`: öğrenci/veli/finans PII retention ve erişim.

Örnek changelog:

```text
## [Unreleased] - 2026-06-24
### Security
- Remove committed database credentials and enforce production secret validation.
- Enforce organization/branch scope for finance, reports, announcements and user assignments.
- Detect refresh-token reuse and revoke token families.
- Upgrade vulnerable backend runtime dependencies.
### Fixed
- Prevent concurrent payments from over-applying debt balances.
- Validate upload content and escape receipt print output.
```

Örnek commit'ler:

- `fix(security): remove committed secrets and fail closed in production`
- `fix(authz): enforce tenant scope across active object lookups`
- `fix(auth): rotate refresh tokens atomically and revoke reset sessions`
- `fix(finance): lock debt rows during payment mutations`
- `build(deps): upgrade vulnerable FastAPI auth and multipart stack`
- `test(security): add production config and upload regression coverage`
- `docs(operations): align setup and rollback guidance with repository state`

## Önerilen Komutlar

### Backend

```bash
cd backend
python -m pip install -r requirements-dev.txt  # runtime + dev bağımlılıkları
ruff check app tests                           # lint/import/bugbear
black --check app tests                       # format kontrolü
mypy app --ignore-missing-imports              # type borcunu ölçer; şu an gate değil
pytest tests/unit -v                           # DB'siz unit testler
pytest tests/integration -v                    # migrate edilmiş izole PostgreSQL gerekir
pip-audit -r requirements.txt                  # runtime CVE taraması
alembic upgrade head                           # migration
```

### Frontend

```bash
cd frontend
npm ci                                         # package-lock'a birebir kurulum
npm run lint                                   # ESLint
npm test                                       # Vitest
npm audit --omit=dev --audit-level=high        # production dependency audit
npm run build                                  # TypeScript + Vite; dist'i yeniden üretir
```

### Repo / Container / Security

```bash
docker compose config                          # env interpolation ve compose doğrulama
docker compose build --pull                    # temiz image build
trivy fs --scanners vuln,secret,misconfig .    # filesystem/dependency/misconfig
trivy image scs360-backend:<immutable-tag>   # image taraması
gitleaks detect --source . --no-banner         # secret scan
```

Trivy/Gitleaks sürümü repository'de belirtilmemiştir; CI action sürümünü resmi release ve SHA ile pinleyin.

## Mermaid Diyagramları

```mermaid
flowchart LR
  Browser["React / Vite SPA"] --> Edge["Nginx reverse proxy + security headers"]
  Edge --> API["FastAPI app/main.py"]
  API --> Guards["JWT + PermissionChecker + TenantContext"]
  Guards --> Routers["Active combined routers"]
  Routers --> Repo["BaseRepository tenant filters"]
  Routers --> Auth["Application AuthService"]
  Repo --> ORM["Infrastructure ORM models"]
  Auth --> ORM
  ORM --> PG[(PostgreSQL)]
  Routers --> Storage["Local upload volume"]
  Routers --> Outbox["Notification jobs"]
  Worker["Outbox worker"] --> Outbox
  Legacy["Legacy services/repositories/entities"] -. "muhtemel ölü kod" .-> API
```

```mermaid
flowchart TD
  A["1. DB secret rotation ve erişim inceleme"] --> B["2. Staging env + fail-closed startup"]
  B --> C["3. Dependency/image build + audit"]
  C --> D["4. Tenant/auth/finance regression"]
  D --> E["5. Backend + worker rollout"]
  E --> F["6. Frontend/Nginx rollout"]
  F --> G["7. Smoke + telemetry gözlemi"]
  G --> H["8. HttpOnly cookie ve explicit transaction fazı"]
  H --> I["9. Legacy katman kaldırma doğrulaması"]
```

## Uygulama Sırası

1. Dış altyapıda sızmış DB kimliğini iptal et/döndür; yeni secret'ı repository dışında dağıt.
2. Mevcut yamayı staging'de `APP_ENV=production` ile başlat; zayıf secret testinin fail ettiğini doğrula.
3. Migration/backup kontrolü, `pip-audit`, `npm audit`, unit ve contract testlerini çalıştır.
4. İki tenant/iki branch negatif IDOR testlerini ve eşzamanlı ödeme testini tamamla.
5. Backend ve worker'ı immutable tag ile deploy et; sonra frontend/Nginx'i yayınla.
6. 401/403/429/5xx, refresh reuse, DB pool ve notification telemetry'yi en az bir release izle.
7. HttpOnly cookie dual-mode geçişini uygula.
8. Explicit transaction geçişini endpoint bazında tamamla.
9. Aktif import/telemetry doğrulamasından sonra legacy router/service/repository/entity katmanını kaldır.
10. `frontend/dist/**` gerekiyorsa yalnız doğrulanmış `npm run build` çıktısıyla yeniden üret; elle patch yazma.

## Frontend Tamamlama Notu

24 Haziran 2026 tarihli ikinci geçişte görsel stil dosyaları ve mevcut tasarım sınıfları değiştirilmeden frontend davranışları güçlendirildi:

- Doğrudan URL erişimlerine modül ve yazma yetkisi korumaları eklendi; hatalı `students:write`, `users:write` ve `roles:write` kontrolleri kanonik izin adlarıyla düzeltildi.
- “Beni hatırla” gerçek davranış kazandı: varsayılan oturum `sessionStorage`, açık tercih ise `localStorage` kullanıyor; çıkış iki alanı da temizliyor ve eski Zustand kaydı okunabiliyor.
- Üretime gömülü demo kullanıcı/şifre kaldırıldı; demo yalnız açık geliştirme değişkenleriyle etkinleştirilebilir.
- API refresh eşzamanlılığı korunurken FormData sınırı, timeout, güvenli geri dönüş URL'si ve indirme hata bildirimleri düzeltildi.
- Yoklama notlarının kaybolması, UTC kaynaklı gün/ay sapması, state dizilerini yerinde sıralama ve ayarlar–entegrasyon API sözleşmesi uyuşmazlığı giderildi.
- Pasif “Dışa aktar” düğmeleri CSV üretimine bağlandı; CSV formül enjeksiyonuna karşı hücre koruması eklendi.
- Modal odak tuzağı/odak iadesi, toast timer temizliği, tablo aksiyon adları, profil menüsü klavye davranışı ve form etiket ilişkileri iyileştirildi.
- `src/styles/**`, görseller, ikonlar ve tasarım asset'leri değiştirilmedi.

Doğrulama sonucu: 12 Vitest testi geçti; ESLint, TypeScript build ve Vite production build başarılı; yerel tarayıcı duman testinde giriş ve şifre kurtarma akışı çalıştı, konsolda hata/uyarı görülmedi.

<!-- SCS360_SOURCE_END: 11 -->

---

<a id="belge-12"></a>

## 12. docs/CREATIVE_TIM_INTEGRATION.md

Kaynak: [docs/CREATIVE_TIM_INTEGRATION.md](docs/CREATIVE_TIM_INTEGRATION.md)  
SHA-256: `77ea481363e4a0f45319f37db8a9f1bfaf9376e6fc6d80a73900cf9f556922e0`

<!-- SCS360_SOURCE_BEGIN: 12 -->
# Creative Tim Material Dashboard React Integration Plan

## Overview

This document outlines the integration strategy for the Creative Tim Material Dashboard React template into the School Management System frontend.

## Template Source

**Repository:** https://github.com/creativetimofficial/material-dashboard-react.git  
**Version:** Latest stable version  
**License:** Check repository license terms

---

## Integration Strategy

### Phase 1: Template Acquisition and Setup

1. **Clone the Template**
   ```bash
   git clone https://github.com/creativetimofficial/material-dashboard-react.git frontend/template
   ```

2. **Copy to Project Structure**
   - Copy essential files from template to `frontend/src/`
   - Keep the template as reference in `frontend/template/`
   - Do not modify the original template files

3. **Package.json Analysis**
   - Review template dependencies
   - Merge with project-specific dependencies
   - Remove unused template dependencies
   - Add required project dependencies

### Phase 2: Cleanup Demo Content

**Files to Remove:**
- Demo pages from `layouts/pages/`
- Example components from `components/`
- Demo routes from `routes/index.js`
- Demo data files
- Example charts and dashboards

**Files to Keep:**
- Layout structure (`layouts/`)
- Core components (`components/`)
- Theme configuration (`assets/theme/`)
- Context providers (`context/`)
- Utility functions (`assets/theme/functions/`)

### Phase 3: TypeScript Migration (If Template is JavaScript)

**Migration Approach:**
1. Add TypeScript configuration
2. Create type definitions for existing components
3. Migrate core components first
4. Migrate layout components
5. Migrate utility functions
6. Add strict mode gradually

**Type Definition Files:**
- `src/types/material-ui.d.ts` - Material UI type extensions
- `src/types/theme.d.ts` - Theme type definitions
- `src/types/components.d.ts` - Component prop types

**If Template is Already TypeScript:**
- Keep existing types
- Add project-specific type definitions
- Enable strict mode in tsconfig.json

### Phase 4: Project Structure Adaptation

**New Structure:**
```
frontend/src/
├── assets/                    # From template (theme, images, icons)
├── components/               # From template + common components
│   ├── MaterialDashboard/    # Template core components
│   └── common/               # Project common components
├── context/                  # From template + project contexts
├── features/                 # Project feature modules
│   ├── auth/
│   ├── dashboard/
│   ├── organizations/
│   ├── branches/
│   ├── users/
│   ├── students/
│   ├── classes/
│   ├── attendance/
│   ├── finance/
│   ├── receipts/
│   ├── announcements/
│   ├── notifications/
│   ├── reports/
│   └── settings/
├── hooks/                    # Custom React hooks
├── layouts/                  # From template (adapted)
├── routes/                   # Project routing
├── services/                 # API services
├── types/                    # TypeScript definitions
├── utils/                    # Utility functions
└── App.tsx                   # Main app component
```

### Phase 5: Component Reuse Strategy

**Template Components to Reuse:**

1. **Layout Components**
   - `MaterialDashboard/Layout` - Main layout wrapper
   - `MaterialDashboard/Sidebar` - Navigation sidebar
   - `MaterialDashboard/Navbar` - Top navigation bar
   - `MaterialDashboard/Box` - Layout box component

2. **UI Components**
   - `MaterialDashboard/Button` - Styled buttons
   - `MaterialDashboard/Input` - Form inputs
   - `MaterialDashboard/Select` - Dropdown selects
   - `MaterialDashboard/Checkbox` - Checkboxes
   - `MaterialDashboard/Radio` - Radio buttons
   - `MaterialDashboard/Switch` - Toggle switches
   - `MaterialDashboard/Typography` - Text components
   - `MaterialDashboard/Card` - Card containers
   - `MaterialDashboard/Table` - Data tables
   - `MaterialDashboard/Alert` - Alert messages
   - `MaterialDashboard/Modal` - Dialog modals
   - `MaterialDashboard/Divider` - Visual dividers
   - `MaterialDashboard/Avatar` - User avatars
   - `MaterialDashboard/Chip` - Status chips
   - `MaterialDashboard/Progress` - Progress indicators
   - `MaterialDashboard/Skeleton` - Loading skeletons

3. **Form Components**
   - `MaterialDashboard/FormLabel` - Form labels
   - `MaterialDashboard/FormControl` - Form control wrapper
   - `MaterialDashboard/FormGroup` - Form group wrapper

4. **Navigation Components**
   - `MaterialDashboard/Link` - Navigation links
   - `MaterialDashboard/Breadcrumbs` - Breadcrumb navigation

**Template Components to Adapt:**

1. **Sidebar**
   - Remove demo menu items
   - Add project-specific menu items
   - Implement role-based menu filtering
   - Add active route highlighting

2. **Navbar**
   - Remove demo user info
   - Add real user info from auth context
   - Add logout functionality
   - Add branch selector (if applicable)

3. **Dashboard Layout**
   - Integrate with React Router
   - Add route guards
   - Add error boundary
   - Add loading states

### Phase 6: Theme Customization

**Theme Configuration:**

1. **Color Palette**
   ```javascript
   // Keep template base colors
   // Add school management specific colors
   primary: {
     main: '#9C27B0', // Keep template purple
     light: '#BA68C8',
     dark: '#7B1FA2'
   },
   secondary: {
     main: '#4CAF50', // Green for success
     light: '#81C784',
     dark: '#388E3C'
   },
   error: {
     main: '#F44336',
     light: '#E57373',
     dark: '#D32F2F'
   },
   warning: {
     main: '#FF9800',
     light: '#FFB74D',
     dark: '#F57C00'
   },
   info: {
     main: '#2196F3',
     light: '#64B5F6',
     dark: '#1976D2'
   }
   ```

2. **Typography**
   - Keep template font family (Roboto)
   - Add custom font sizes for specific use cases
   - Configure heading styles

3. **Spacing**
   - Use template spacing system
   - Add custom spacing values if needed

4. **Breakpoints**
   - Keep template breakpoints
   - Add custom breakpoints if needed

5. **Shadows**
   - Keep template shadow definitions
   - Add custom shadows for specific components

### Phase 7: State Management Integration

**Zustand Store Structure:**

```typescript
// stores/auth.store.ts
interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  login: (credentials: LoginCredentials) => Promise<void>;
  logout: () => void;
  refreshToken: () => Promise<void>;
}

// stores/ui.store.ts
interface UIState {
  sidebarOpen: boolean;
  toggleSidebar: () => void;
  setLoading: (loading: boolean) => void;
  loading: boolean;
}

// stores/branch.store.ts
interface BranchState {
  currentBranch: Branch | null;
  branches: Branch[];
  setCurrentBranch: (branch: Branch) => void;
}
```

**Context Integration:**
- Keep template MaterialUI context
- Add AuthContext for authentication
- Add NotificationContext for toast notifications
- Add ThemeContext for theme customization

### Phase 8: Routing Integration

**React Router Setup:**

```typescript
// routes/AppRoutes.tsx
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { ProtectedRoute } from './ProtectedRoute';
import { RoleBasedRoute } from './RoleBasedRoute';
import DashboardLayout from 'layouts/DashboardLayout';

const AppRoutes = () => (
  <BrowserRouter>
    <Routes>
      {/* Public Routes */}
      <Route path="/login" element={<Login />} />
      <Route path="/forgot-password" element={<ForgotPassword />} />
      <Route path="/reset-password/:token" element={<ResetPassword />} />
      
      {/* Protected Routes */}
      <Route path="/" element={<ProtectedRoute><DashboardLayout /></ProtectedRoute>}>
        <Route index element={<Dashboard />} />
        <Route path="dashboard" element={<Dashboard />} />
        
        {/* Role-based Routes */}
        <Route path="organizations" element={<RoleBasedRoute requiredPermission="organizations.view"><OrganizationList /></RoleBasedRoute>} />
        {/* ... more routes */}
      </Route>
      
      {/* Error Routes */}
      <Route path="/403" element={<Forbidden />} />
      <Route path="/404" element={<NotFound />} />
      <Route path="*" element={<NotFound />} />
    </Routes>
  </BrowserRouter>
);
```

### Phase 9: API Service Integration

**Axios Configuration:**

```typescript
// services/api.ts
import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for auth token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Handle token refresh or logout
    }
    return Promise.reject(error);
  }
);

export default api;
```

### Phase 10: Form Validation Integration

**React Hook Form + Zod Setup:**

```typescript
// hooks/useFormValidation.ts
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';

export const useStudentForm = () => {
  const schema = z.object({
    first_name: z.string().min(2, 'First name must be at least 2 characters'),
    last_name: z.string().min(2, 'Last name must be at least 2 characters'),
    email: z.string().email('Invalid email address'),
    // ... more fields
  });

  return useForm({
    resolver: zodResolver(schema),
    defaultValues: {
      first_name: '',
      last_name: '',
      // ... more fields
    },
  });
};
```

### Phase 11: Toast Notification Integration

**Toast Configuration:**

```typescript
// components/common/Toast.tsx
import { toast } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';

export const showToast = {
  success: (message: string) => toast.success(message),
  error: (message: string) => toast.error(message),
  warning: (message: string) => toast.warning(message),
  info: (message: string) => toast.info(message),
};

// Use in components
import { showToast } from 'components/common/Toast';

showToast.success('Student created successfully');
```

### Phase 12: Responsive Design Adaptation

**Mobile Adaptations:**
- Sidebar becomes drawer on mobile
- Tables become horizontal scrollable or card-based
- Forms stack vertically
- Charts resize appropriately
- Touch-friendly button sizes

**Tablet Adaptations:**
- Sidebar collapsible
- Optimized table layouts
- Responsive grid layouts

**Desktop Optimizations:**
- Full sidebar
- Multi-column layouts
- Hover states
- Keyboard navigation

### Phase 13: Accessibility Enhancements

**Accessibility Features:**
- ARIA labels for all interactive elements
- Keyboard navigation support
- Screen reader compatibility
- Focus management
- Color contrast compliance (WCAG AA)
- Skip to main content link
- Alt text for images

### Phase 14: Performance Optimization

**Optimization Strategies:**
- Code splitting with React.lazy
- Route-based chunking
- Image optimization
- Lazy loading components
- Memoization with React.memo
- Virtual scrolling for large lists
- Debounced search inputs

### Phase 15: Testing Integration

**Testing Setup:**
```typescript
// Component testing with React Testing Library
import { render, screen } from '@testing-library/react';
import { renderWithProviders } from 'test/utils';

// Feature testing with Vitest
import { describe, it, expect } from 'vitest';
```

### Phase 16: Build Configuration

**Vite Configuration:**

```typescript
// vite.config.ts
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom', 'react-router-dom'],
          mui: ['@mui/material', '@mui/icons-material'],
        },
      },
    },
  },
});
```

---

## Integration Checklist

### Template Setup
- [ ] Clone Creative Tim Material Dashboard React
- [ ] Copy essential files to project
- [ ] Remove demo content
- [ ] Update package.json dependencies
- [ ] Configure TypeScript (if needed)

### Component Integration
- [ ] Adapt Sidebar with project menu
- [ ] Adapt Navbar with user info
- [ ] Integrate Dashboard Layout
- [ ] Reuse template UI components
- [ ] Create project-specific components

### Routing & State
- [ ] Set up React Router
- [ ] Implement route guards
- [ ] Set up Zustand stores
- [ ] Create Auth context
- [ ] Create Notification context

### API & Forms
- [ ] Configure Axios
- [ ] Set up interceptors
- [ ] Integrate React Hook Form
- [ ] Integrate Zod validation
- [ ] Create API service modules

### Styling & Theme
- [ ] Customize theme colors
- [ ] Customize typography
- [ ] Add custom components styling
- [ ] Ensure responsive design
- [ ] Test accessibility

### Build & Deploy
- [ ] Configure Vite
- [ ] Set up code splitting
- [ ] Configure production build
- [ ] Test build output
- [ ] Configure Docker build

---

## Migration Steps Summary

1. **Setup Phase** (1-2 days)
   - Clone and analyze template
   - Set up project structure
   - Configure build tools

2. **Cleanup Phase** (1 day)
   - Remove demo content
   - Clean up unused dependencies
   - Organize file structure

3. **Integration Phase** (3-5 days)
   - Adapt layout components
   - Integrate routing
   - Set up state management
   - Configure API services

4. **Feature Development Phase** (Ongoing)
   - Build feature pages using template components
   - Implement forms with validation
   - Add data tables with pagination
   - Integrate charts and visualizations

5. **Testing Phase** (2-3 days)
   - Test component integration
   - Test responsive design
   - Test accessibility
   - Performance testing

6. **Optimization Phase** (1-2 days)
   - Code splitting
   - Lazy loading
   - Bundle optimization
   - Image optimization

---

## Notes

- **Template License:** Ensure compliance with Creative Tim's license terms
- **Customization:** Maintain template's design language while adapting to project needs
- **Updates:** Document any template modifications for future updates
- **Performance:** Monitor bundle size and optimize as needed
- **Browser Support:** Test across required browsers (Chrome, Firefox, Safari, Edge)

<!-- SCS360_SOURCE_END: 12 -->

---

<a id="belge-13"></a>

## 13. docs/DEVELOPMENT_ORDER.md

Kaynak: [docs/DEVELOPMENT_ORDER.md](docs/DEVELOPMENT_ORDER.md)  
SHA-256: `be4ca97ce89953985d5ec390b007ba59bdbb05a9a8e795195a4abb648594e2c6`

<!-- SCS360_SOURCE_BEGIN: 13 -->
# Development Order

## Overview

This document outlines the recommended development order for building the School Management System. The order is designed to build a solid foundation first, then incrementally add features while maintaining system stability and testability.

---

## Phase 1: Foundation Setup (Week 1-2)

### 1.1 Project Structure Creation
**Duration:** 1 day
**Tasks:**
- Create root directory structure
- Create backend directory structure
- Create frontend directory structure
- Create docs directory
- Initialize Git repository
- Create .gitignore files
- Create README.md

**Deliverables:**
- Complete directory structure
- Git repository initialized
- README with project overview

### 1.2 Backend Core Setup
**Duration:** 2 days
**Tasks:**
- Create Python virtual environment
- Set up requirements.txt with dependencies
- Create core/config.py
- Create core/database.py with SQLAlchemy setup
- Create core/security.py with JWT and password hashing
- Create core/dependencies.py for FastAPI dependencies
- Create core/exceptions.py for custom exceptions
- Create core/middleware.py for custom middleware
- Create main.py with FastAPI app setup
- Configure CORS
- Set up structured logging

**Deliverables:**
- Working FastAPI application
- Database connection configured
- Security utilities implemented
- Logging configured

### 1.3 Database Schema Setup
**Duration:** 2 days
**Tasks:**
- Create database/schema.sql with all tables
- Create database/seed.sql with demo data
- Set up Alembic for migrations
- Create initial migration
- Test database schema locally
- Verify seed data insertion

**Deliverables:**
- Complete database schema
- Alembic configured
- Initial migration created
- Seed data tested

### 1.4 Docker Setup
**Duration:** 1 day
**Tasks:**
- Create backend/Dockerfile
- Create frontend/Dockerfile (placeholder)
- Create docker-compose.yml for development
- Create nginx/default.conf
- Test Docker containers locally
- Verify database connectivity

**Deliverables:**
- Working Docker setup
- All containers running
- Database accessible

---

## Phase 2: Authentication & Authorization (Week 3)

### 2.1 Authentication System
**Duration:** 3 days
**Tasks:**
- Create user model in domain/entities/
- Create user repository in infrastructure/repositories/
- Create authentication use cases in application/use_cases/
- Implement JWT token generation
- Implement refresh token with rotation
- Create auth schemas in application/schemas/
- Create auth router in routers/
- Implement login endpoint
- Implement refresh token endpoint
- Implement logout endpoint
- Implement password reset flow
- Add login attempt tracking
- Write unit tests for auth

**Deliverables:**
- Complete authentication system
- All auth endpoints working
- Unit tests passing

### 2.2 Authorization System
**Duration:** 2 days
**Tasks:**
- Create role and permission models
- Create role and permission repositories
- Implement RBAC middleware
- Create permission checker utility
- Implement role-based route protection
- Implement permission-based route protection
- Create permission dependency for FastAPI
- Add authorization tests

**Deliverables:**
- Complete authorization system
- Role-based access control working
- Permission-based access control working

### 2.3 Multi-tenancy Setup
**Duration:** 2 days
**Tasks:**
- Create organization and branch models
- Implement tenant resolver middleware
- Add organization context to requests
- Implement branch scope filtering
- Create tenant isolation tests
- Verify data isolation between organizations

**Deliverables:**
- Multi-tenancy implemented
- Organization isolation working
- Branch isolation working

---

## Phase 3: Frontend Foundation (Week 4)

### 3.1 Creative Tim Template Integration
**Duration:** 2 days
**Tasks:**
- Clone Creative Tim Material Dashboard React
- Copy essential files to project
- Remove demo content
- Clean up unused dependencies
- Update package.json
- Configure Vite
- Set up TypeScript (if needed)
- Test template build

**Deliverables:**
- Template integrated
- Build working
- Demo content removed

### 3.2 Frontend Core Setup
**Duration:** 2 days
**Tasks:**
- Set up Axios with interceptors
- Create API service base
- Implement error handler
- Create toast notification system
- Set up Zustand stores (auth, ui)
- Create AuthContext
- Create protected route component
- Create role-based route component
- Create 403 and 404 pages
- Create error boundary

**Deliverables:**
- Frontend core infrastructure
- API service configured
- Route guards implemented

### 3.3 Authentication UI
**Duration:** 1 day
**Tasks:**
- Create login page
- Create forgot password page
- Create reset password page
- Implement form validation with Zod
- Connect to backend auth API
- Test authentication flow
- Add loading states
- Add error handling

**Deliverables:**
- Complete authentication UI
- Login flow working
- Password reset working

---

## Phase 4: Organization & User Management (Week 5)

### 4.1 Organization Module (Backend)
**Duration:** 2 days
**Tasks:**
- Create organization entity and repository
- Create organization use cases
- Create organization schemas
- Create organization router
- Implement CRUD operations
- Add organization tests
- Create branch entity and repository
- Create branch use cases
- Create branch schemas
- Create branch router
- Implement CRUD operations
- Add branch tests

**Deliverables:**
- Organization CRUD working
- Branch CRUD working
- Tests passing

### 4.2 User Module (Backend)
**Duration:** 2 days
**Tasks:**
- Create user repository
- Create user use cases
- Create user schemas
- Create user router
- Implement user CRUD
- Implement role assignment
- Implement branch assignment
- Add user tests
- Create role management endpoints
- Create permission matrix endpoint

**Deliverables:**
- User CRUD working
- Role assignment working
- Tests passing

### 4.3 Organization & User UI (Frontend)
**Duration:** 1 day
**Tasks:**
- Create organization list page
- Create organization form page
- Create branch list page
- Create branch form page
- Create user list page
- Create user form page
- Create role permission matrix page
- Connect to backend APIs
- Add form validation

**Deliverables:**
- Organization management UI
- User management UI
- All forms working

---

## Phase 5: Student & Parent Management (Week 6)

### 5.1 Student Module (Backend)
**Duration:** 3 days
**Tasks:**
- Create student entity and repository
- Create parent entity and repository
- Create student-parent relationship
- Create student use cases
- Create student schemas
- Create student router
- Implement student CRUD
- Implement parent management
- Add student tests
- Implement student-photo upload
- Implement file upload abstraction

**Deliverables:**
- Student CRUD working
- Parent management working
- File upload working
- Tests passing

### 5.2 Student Module (Frontend)
**Duration:** 2 days
**Tasks:**
- Create student list page
- Create student form page
- Create student detail page
- Create parent management UI
- Create file upload component
- Implement photo upload
- Connect to backend APIs
- Add form validation

**Deliverables:**
- Student management UI
- Parent management UI
- File upload working

---

## Phase 6: Class Management (Week 7)

### 6.1 Class Module (Backend)
**Duration:** 2 days
**Tasks:**
- Create class entity and repository
- Create class use cases
- Create class schemas
- Create class router
- Implement class CRUD
- Implement student-class assignment
- Implement capacity validation
- Add occupancy calculation
- Add class tests

**Deliverables:**
- Class CRUD working
- Student assignment working
- Capacity validation working
- Tests passing

### 6.2 Class Module (Frontend)
**Duration:** 1 day
**Tasks:**
- Create class list page
- Create class form page
- Create class detail page
- Create student assignment UI
- Create occupancy display
- Connect to backend APIs
- Add form validation

**Deliverables:**
- Class management UI
- Student assignment UI
- Occupancy display working

---

## Phase 7: Attendance Management (Week 8)

### 7.1 Attendance Module (Backend)
**Duration:** 3 days
**Tasks:**
- Create attendance entity and repository
- Create attendance use cases
- Create attendance schemas
- Create attendance router
- Implement single attendance record
- Implement bulk attendance
- Implement duplicate prevention
- Implement class-based attendance view
- Implement student-based attendance view
- Add attendance tests
- Create monthly report endpoint

**Deliverables:**
- Attendance CRUD working
- Bulk attendance working
- Duplicate prevention working
- Tests passing

### 7.2 Attendance Module (Frontend)
**Duration:** 2 days
**Tasks:**
- Create attendance list page
- Create take attendance page (daily)
- Create bulk attendance page
- Create student attendance history page
- Create monthly report page
- Connect to backend APIs
- Add validation

**Deliverables:**
- Attendance management UI
- Bulk attendance UI
- Reports working

---

## Phase 8: Financial Management (Week 9-10)

### 8.1 Debt Module (Backend)
**Duration:** 3 days
**Tasks:**
- Create debt entity and repository
- Create debt use cases
- Implement debt status calculation
- Implement overdue detection
- Create debt schemas
- Create debt router
- Implement debt CRUD
- Implement debt status recalculation
- Add debt tests
- Ensure Decimal type for all financial calculations

**Deliverables:**
- Debt CRUD working
- Status calculation working
- Overdue detection working
- Tests passing

### 8.2 Payment Module (Backend)
**Duration:** 3 days
**Tasks:**
- Create payment entity and repository
- Create payment use cases
- Implement payment transaction safety
- Implement payment cancellation (reverse transaction)
- Create payment schemas
- Create payment router
- Implement payment creation
- Implement payment cancellation
- Add payment tests
- Ensure audit logging for all transactions

**Deliverables:**
- Payment creation working
- Payment cancellation working
- Transaction safety ensured
- Tests passing

### 8.3 Receipt Module (Backend)
**Duration:** 2 days
**Tasks:**
- Create receipt entity and repository
- Create receipt use cases
- Implement receipt number generation
- Implement PDF generation
- Create receipt schemas
- Create receipt router
- Implement receipt creation
- Implement PDF download
- Implement print view
- Add receipt tests

**Deliverables:**
- Receipt creation working
- PDF generation working
- Print view working
- Tests passing

### 8.4 Financial Module (Frontend)
**Duration:** 3 days
**Tasks:**
- Create debt list page
- Create debt form page
- Create payment list page
- Create take payment page
- Create receipt detail page
- Create receipt print view
- Connect to backend APIs
- Add financial validation
- Implement PDF download

**Deliverables:**
- Debt management UI
- Payment management UI
- Receipt UI working
- PDF download working

---

## Phase 9: Notification System (Week 11)

### 9.1 Notification Infrastructure (Backend)
**Duration:** 3 days
**Tasks:**
- Create notification base provider
- Create email provider (SMTP)
- Create SMS provider (Netgsm adapter)
- Create WhatsApp provider (Meta adapter)
- Create notification dispatcher
- Create template renderer
- Create notification_jobs table
- Implement outbox pattern
- Add notification tests

**Deliverables:**
- All providers implemented
- Dispatcher working
- Outbox pattern working
- Tests passing

### 9.2 Notification Worker
**Duration:** 2 days
**Tasks:**
- Create outbox worker
- Implement polling mechanism
- Implement retry logic with exponential backoff
- Implement error handling
- Add worker logging
- Test worker locally
- Add worker to Docker Compose

**Deliverables:**
- Worker running
- Retry logic working
- Error handling working

### 9.3 Notification Integration
**Duration:** 2 days
**Tasks:**
- Integrate notifications with payment flow
- Integrate notifications with announcement flow
- Create notification job creation utilities
- Add notification endpoints
- Create notification log UI
- Test notification flows end-to-end

**Deliverables:**
- Payment notifications working
- Announcement notifications working
- Notification log UI working

---

## Phase 10: Announcement System (Week 12)

### 10.1 Announcement Module (Backend)
**Duration:** 2 days
**Tasks:**
- Create announcement entity and repository
- Create announcement recipient entity
- Create announcement use cases
- Implement audience calculation
- Create announcement schemas
- Create announcement router
- Implement announcement CRUD
- Implement announcement sending
- Add announcement tests

**Deliverables:**
- Announcement CRUD working
- Announcement sending working
- Tests passing

### 10.2 Announcement Module (Frontend)
**Duration:** 2 days
**Tasks:**
- Create announcement list page
- Create announcement form page
- Create announcement detail page
- Implement rich text editor
- Implement audience selection
- Implement channel selection
- Connect to backend APIs
- Add form validation

**Deliverables:**
- Announcement management UI
- Rich text editor working
- Channel selection working

### 10.3 Message Templates
**Duration:** 1 day
**Tasks:**
- Create template CRUD endpoints
- Create template management UI
- Implement variable substitution
- Test template rendering
- Add template examples

**Deliverables:**
- Template management working
- Variable substitution working

---

## Phase 11: Reporting System (Week 13)

### 11.1 Report Endpoints (Backend)
**Duration:** 3 days
**Tasks:**
- Create report use cases
- Implement monthly payment report
- Implement debt report
- Implement overdue debt report
- Implement attendance report
- Implement class occupancy report
- Implement branch performance report
- Implement CSV export
- Implement Excel export
- Add report tests

**Deliverables:**
- All report endpoints working
- CSV export working
- Excel export working
- Tests passing

### 11.2 Report UI (Frontend)
**Duration:** 2 days
**Tasks:**
- Create monthly payment report page
- Create debt report page
- Create overdue debt report page
- Create attendance report page
- Create class occupancy report page
- Create branch performance report page
- Implement chart visualizations
- Implement export functionality
- Connect to backend APIs

**Deliverables:**
- All report pages working
- Charts displaying correctly
- Export working

---

## Phase 12: Dashboard (Week 14)

### 12.1 Dashboard API (Backend)
**Duration:** 2 days
**Tasks:**
- Create dashboard use cases
- Implement summary statistics
- Implement chart data endpoints
- Implement role-based data filtering
- Add dashboard tests
- Optimize queries for performance

**Deliverables:**
- Summary statistics working
- Chart data working
- Role-based filtering working
- Tests passing

### 12.2 Dashboard UI (Frontend)
**Duration:** 2 days
**Tasks:**
- Create dashboard page
- Implement summary cards
- Implement charts (monthly collection, debt vs payment, occupancy)
- Implement recent activities
- Connect to backend APIs
- Add loading states
- Optimize for performance

**Deliverables:**
- Dashboard page working
- Charts displaying correctly
- Real-time updates working

---

## Phase 13: Settings & Configuration (Week 15)

### 13.1 Settings Module (Backend)
**Duration:** 2 days
**Tasks:**
- Create app_settings entity and repository
- Create integration_settings entity and repository
- Create settings use cases
- Create settings schemas
- Create settings router
- Implement general settings CRUD
- Implement integration settings CRUD
- Add settings tests

**Deliverables:**
- Settings CRUD working
- Integration settings working
- Tests passing

### 13.2 Settings Module (Frontend)
**Duration:** 2 days
**Tasks:**
- Create general settings page
- Create integration settings page
- Create SMTP configuration form
- Create SMS configuration form
- Create WhatsApp configuration form
- Implement test connection buttons
- Connect to backend APIs
- Add form validation

**Deliverables:**
- Settings UI working
- Configuration forms working
- Test connection working

---

## Phase 14: Testing & Quality Assurance (Week 16)

### 14.1 Backend Testing
**Duration:** 3 days
**Tasks:**
- Write unit tests for all use cases
- Write integration tests for all endpoints
- Write tests for auth flow
- Write tests for permissions
- Write tests for branch isolation
- Write tests for financial calculations
- Write tests for notification system
- Achieve minimum 80% code coverage
- Run test suite

**Deliverables:**
- Comprehensive test suite
- 80%+ code coverage
- All tests passing

### 14.2 Frontend Testing
**Duration:** 2 days
**Tasks:**
- Write component tests
- Write form validation tests
- Write protected route tests
- Write API service tests
- Achieve minimum 80% code coverage
- Run test suite

**Deliverables:**
- Comprehensive test suite
- 80%+ code coverage
- All tests passing

### 14.3 End-to-End Testing
**Duration:** 2 days
**Tasks:**
- Set up Playwright or Cypress
- Write E2E tests for critical flows
- Test login flow
- Test student creation flow
- Test payment flow
- Test announcement flow
- Run E2E tests

**Deliverables:**
- E2E test suite
- Critical flows tested
- All tests passing

---

## Phase 15: CI/CD Setup (Week 17)

### 15.1 GitHub Actions Configuration
**Duration:** 2 days
**Tasks:**
- Create backend-ci.yml workflow
- Create frontend-ci.yml workflow
- Create docker-build.yml workflow
- Create deploy-staging.yml workflow
- Create deploy-production.yml workflow
- Configure GitHub secrets
- Test CI/CD pipelines
- Fix any pipeline issues

**Deliverables:**
- All CI/CD workflows working
- Tests running on push
- Docker images building
- Deployment workflows configured

### 15.2 Staging Deployment
**Duration:** 2 days
**Tasks:**
- Deploy to staging environment
- Run database migrations
- Load seed data
- Test all features on staging
- Verify integrations (email, SMS, WhatsApp)
- Performance testing
- Fix any staging issues

**Deliverables:**
- Staging environment deployed
- All features tested
- Integrations verified

---

## Phase 16: Production Deployment (Week 18)

### 16.1 Production Preparation
**Duration:** 2 days
**Tasks:**
- Review all configurations
- Update production environment variables
- Generate SSL certificates
- Configure production Nginx
- Set up monitoring
- Set up logging
- Create backup procedures
- Document rollback plan

**Deliverables:**
- Production configured
- SSL certificates installed
- Monitoring configured
- Backup procedures documented

### 16.2 Production Deployment
**Duration:** 1 day
**Tasks:**
- Create database backup
- Deploy to production
- Run database migrations
- Load production seed data
- Verify deployment
- Run health checks
- Monitor for issues

**Deliverables:**
- Production deployed
- Database migrated
- Health checks passing

### 16.3 Post-Deployment Verification
**Duration:** 2 days
**Tasks:**
- Test all critical flows
- Verify all integrations
- Monitor performance
- Check logs for errors
- Fix any production issues
- Document any known issues

**Deliverables:**
- All features verified
- Integrations working
- Performance acceptable
- Issues documented

---

## Phase 17: Documentation & Handover (Week 19)

### 17.1 Technical Documentation
**Duration:** 2 days
**Tasks:**
- Update README.md
- Document API endpoints
- Document database schema
- Document deployment procedures
- Document troubleshooting guide
- Document runbook
- Create architecture diagrams

**Deliverables:**
- Complete technical documentation
- API documentation
- Deployment guide
- Troubleshooting guide

### 17.2 User Documentation
**Duration:** 2 days
**Tasks:**
- Create user manual
- Create admin guide
- Create video tutorials
- Create FAQ
- Document best practices
- Create training materials

**Deliverables:**
- User manual
- Admin guide
- Training materials

### 17.3 Final Review
**Duration:** 1 day
**Tasks:**
- Review all code
- Review all documentation
- Security audit
- Performance review
- Create final report
- Handover to operations team

**Deliverables:**
- Code review complete
- Documentation complete
- Final report
- Handover complete

---

## Summary Timeline

| Phase | Duration | Weeks |
|-------|----------|-------|
| Foundation Setup | 1-2 | 1-2 |
| Authentication & Authorization | 1 | 3 |
| Frontend Foundation | 1 | 4 |
| Organization & User Management | 1 | 5 |
| Student & Parent Management | 1 | 6 |
| Class Management | 1 | 7 |
| Attendance Management | 1 | 8 |
| Financial Management | 2 | 9-10 |
| Notification System | 1 | 11 |
| Announcement System | 1 | 12 |
| Reporting System | 1 | 13 |
| Dashboard | 1 | 14 |
| Settings & Configuration | 1 | 15 |
| Testing & Quality Assurance | 1 | 16 |
| CI/CD Setup | 1 | 17 |
| Production Deployment | 1 | 18 |
| Documentation & Handover | 1 | 19 |

**Total Duration:** 19 weeks (approximately 4.5 months)

---

## Parallel Development Opportunities

To accelerate development, some phases can be worked on in parallel by different team members:

### Parallel Tracks

**Track A (Backend):**
- Phase 2: Authentication & Authorization
- Phase 4.1: Organization Module
- Phase 5.1: Student Module
- Phase 6.1: Class Module
- Phase 7.1: Attendance Module
- Phase 8.1-8.3: Financial Module
- Phase 9.1-9.2: Notification Infrastructure
- Phase 10.1: Announcement Module
- Phase 11.1: Report Endpoints
- Phase 12.1: Dashboard API
- Phase 13.1: Settings Module

**Track B (Frontend):**
- Phase 3: Frontend Foundation
- Phase 4.2: Organization & User UI
- Phase 5.2: Student Module UI
- Phase 6.2: Class Module UI
- Phase 7.2: Attendance Module UI
- Phase 8.4: Financial Module UI
- Phase 9.3: Notification Integration
- Phase 10.2: Announcement Module UI
- Phase 11.2: Report UI
- Phase 12.2: Dashboard UI
- Phase 13.2: Settings Module UI

**Track C (DevOps & Testing):**
- Phase 1.4: Docker Setup
- Phase 14: Testing & Quality Assurance
- Phase 15: CI/CD Setup
- Phase 16: Production Deployment

---

## Milestones

### Milestone 1: Foundation Complete (End of Week 2)
- Project structure created
- Backend core setup
- Database schema ready
- Docker working

### Milestone 2: Authentication Complete (End of Week 3)
- Login/logout working
- JWT tokens implemented
- RBAC implemented
- Multi-tenancy working

### Milestone 3: Core Modules Complete (End of Week 7)
- Organization management
- User management
- Student management
- Class management

### Milestone 4: Operational Features Complete (End of Week 8)
- Attendance tracking
- All CRUD operations working

### Milestone 5: Financial System Complete (End of Week 10)
- Debt management
- Payment processing
- Receipt generation
- Financial reports

### Milestone 6: Communication System Complete (End of Week 12)
- Notification infrastructure
- Announcement system
- All notification channels working

### Milestone 7: Reporting & Dashboard Complete (End of Week 14)
- All reports working
- Dashboard with charts
- Export functionality

### Milestone 8: Production Ready (End of Week 18)
- All features complete
- Testing complete
- CI/CD working
- Production deployed

### Milestone 9: Handover Complete (End of Week 19)
- Documentation complete
- Training materials ready
- System handed over

---

## Risk Mitigation

### Technical Risks
- **Risk:** Integration with external notification providers fails
  - **Mitigation:** Implement adapter pattern early, test each provider independently

- **Risk:** Financial calculation errors
  - **Mitigation:** Use Decimal types, extensive testing, code reviews

- **Risk:** Performance issues with large datasets
  - **Mitigation:** Implement pagination, indexing, query optimization early

### Schedule Risks
- **Risk:** Development takes longer than estimated
  - **Mitigation:** Build in buffer time, prioritize MVP features

- **Risk:** Team member availability
  - **Mitigation:** Cross-train team members, document everything

### Quality Risks
- **Risk:** Insufficient test coverage
  - **Mitigation:** Enforce minimum coverage, require tests for PRs

- **Risk:** Security vulnerabilities
  - **Mitigation:** Regular security audits, dependency scanning

---

## Success Criteria

The project will be considered successful when:

1. **Functional Requirements:**
   - All planned features implemented and working
   - All user stories completed
   - Acceptance criteria met

2. **Non-Functional Requirements:**
   - System performance meets requirements
   - Security requirements met
   - System is scalable
   - System is maintainable

3. **Quality Requirements:**
   - Test coverage ≥ 80%
   - No critical bugs
   - Code review approved
   - Documentation complete

4. **Deployment Requirements:**
   - Successfully deployed to production
   - CI/CD pipeline working
   - Monitoring configured
   - Backup procedures in place

5. **User Acceptance:**
   - User testing completed
   - Feedback incorporated
   - Training completed
   - Sign-off received

<!-- SCS360_SOURCE_END: 13 -->

---

<a id="belge-14"></a>

## 14. docs/DOCKER_DEPLOYMENT.md

Kaynak: [docs/DOCKER_DEPLOYMENT.md](docs/DOCKER_DEPLOYMENT.md)  
SHA-256: `76a39ccab64cdee5d0efdbc80224dec311350c39ab2a978e78b05647928a72f5`

<!-- SCS360_SOURCE_BEGIN: 14 -->
# Docker and Deployment Plan

> Historical design document. For the current ports, environment variables, migrations, bootstrap, HTTPS and provider acceptance steps, use [Üretim kurulumu ve mobil bağlantı](URETIM_KURULUMU_VE_MOBIL.md). The examples below are not the current release procedure.

## Overview

This document outlines the Docker containerization strategy and deployment procedures for the School Management System.

---

## Docker Architecture

### Container Components

```
┌─────────────────────────────────────────────────────────┐
│                    Nginx Reverse Proxy                   │
│              (Port 80/443, SSL Termination)              │
└──────────────────────┬──────────────────────────────────┘
                       │
        ┌──────────────┴──────────────┐
        │                             │
┌───────▼────────┐          ┌────────▼────────┐
│   Frontend     │          │    Backend      │
│   (React)      │          │   (FastAPI)     │
│   Port 3000    │          │   Port 8000     │
└────────────────┘          └────────┬────────┘
                                     │
                          ┌──────────▼──────────┐
                          │   PostgreSQL       │
                          │   Port 5432        │
                          └───────────────────┘
```

---

## Dockerfiles

### Backend Dockerfile

**File:** `backend/Dockerfile`

```dockerfile
# Multi-stage build for production optimization
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /root/.local /root/.local

# Copy application code
COPY . .

# Make sure scripts in .local are usable
ENV PATH=/root/.local/bin:$PATH

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### Frontend Dockerfile

**File:** `frontend/Dockerfile`

```dockerfile
# Multi-stage build for production optimization
FROM node:18-alpine as builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --only=production

# Copy source code
COPY . .

# Build application
RUN npm run build

# Production stage with Nginx
FROM nginx:alpine

# Copy built assets from builder
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy custom nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost:3000 || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
```

### Nginx Configuration

**File:** `nginx/default.conf`

```nginx
upstream backend {
    server backend:8000;
}

upstream frontend {
    server frontend:3000;
}

server {
    listen 80;
    server_name localhost;

    # Frontend static files
    location / {
        proxy_pass http://frontend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Backend API
    location /api {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Health checks
    location /health {
        proxy_pass http://backend/health;
        access_log off;
    }

    # File uploads (increase size limit)
    location /api/uploads {
        proxy_pass http://backend;
        client_max_body_size 10M;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/x-javascript application/xml+rss application/json;
}
```

### Frontend Nginx Configuration

**File:** `frontend/nginx.conf`

```nginx
server {
    listen 3000;
    server_name localhost;
    root /usr/share/nginx/html;
    index index.html;

    # Enable gzip
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/x-javascript application/xml+rss application/json;

    # Handle client-side routing
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Cache static assets
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
}
```

---

## Docker Compose Files

### Development Docker Compose

**File:** `docker-compose.yml`

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    container_name: school-management-db
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: school_management
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./database/schema.sql:/docker-entrypoint-initdb.d/01-schema.sql
      - ./database/seed.sql:/docker-entrypoint-initdb.d/02-seed.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: school-management-backend
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://postgres:postgres@postgres:5432/school_management
      JWT_SECRET_KEY: dev_secret_key_change_in_production
      JWT_ALGORITHM: HS256
      ACCESS_TOKEN_EXPIRE_MINUTES: 30
      REFRESH_TOKEN_EXPIRE_DAYS: 7
      APP_ENV: development
      DEBUG: true
    volumes:
      - ./backend:/app
      - backend_uploads:/app/uploads
    depends_on:
      postgres:
        condition: service_healthy
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: school-management-frontend
    ports:
      - "3000:3000"
    environment:
      VITE_API_BASE_URL: http://localhost:8000/api
    volumes:
      - ./frontend:/app
      - /app/node_modules
    command: npm run dev

  nginx:
    image: nginx:alpine
    container_name: school-management-nginx
    ports:
      - "80:80"
    volumes:
      - ./nginx/default.conf:/etc/nginx/conf.d/default.conf
    depends_on:
      - backend
      - frontend

volumes:
  postgres_data:
  backend_uploads:
```

### Staging Docker Compose

**File:** `docker-compose.staging.yml`

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    container_name: school-management-db-staging
    environment:
      POSTGRES_USER: ${STAGING_DB_USER}
      POSTGRES_PASSWORD: ${STAGING_DB_PASSWORD}
      POSTGRES_DB: school_management_staging
    volumes:
      - postgres_staging_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${STAGING_DB_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  backend:
    image: ${DOCKER_USERNAME}/school-management-backend:develop
    container_name: school-management-backend-staging
    environment:
      DATABASE_URL: postgresql://${STAGING_DB_USER}:${STAGING_DB_PASSWORD}@postgres:5432/school_management_staging
      JWT_SECRET_KEY: ${STAGING_JWT_SECRET}
      JWT_ALGORITHM: HS256
      ACCESS_TOKEN_EXPIRE_MINUTES: 30
      REFRESH_TOKEN_EXPIRE_DAYS: 7
      APP_ENV: staging
      DEBUG: false
      CORS_ORIGINS: https://staging.schoolmanagement.com
    volumes:
      - backend_uploads_staging:/app/uploads
    depends_on:
      postgres:
        condition: service_healthy
    restart: unless-stopped

  frontend:
    image: ${DOCKER_USERNAME}/school-management-frontend:develop
    container_name: school-management-frontend-staging
    environment:
      VITE_API_BASE_URL: https://staging.schoolmanagement.com/api
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    container_name: school-management-nginx-staging
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/default.conf:/etc/nginx/conf.d/default.conf
      - ./nginx/ssl-staging:/etc/nginx/ssl
    depends_on:
      - backend
      - frontend
    restart: unless-stopped

  worker:
    image: ${DOCKER_USERNAME}/school-management-backend:develop
    container_name: school-management-worker-staging
    environment:
      DATABASE_URL: postgresql://${STAGING_DB_USER}:${STAGING_DB_PASSWORD}@postgres:5432/school_management_staging
      APP_ENV: staging
    command: python -m app.infrastructure.notifications.outbox_worker
    depends_on:
      - postgres
    restart: unless-stopped

volumes:
  postgres_staging_data:
  backend_uploads_staging:
```

### Production Docker Compose

**File:** `docker-compose.prod.yml`

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    container_name: school-management-db-prod
    environment:
      POSTGRES_USER: ${PROD_DB_USER}
      POSTGRES_PASSWORD: ${PROD_DB_PASSWORD}
      POSTGRES_DB: school_management
    volumes:
      - postgres_prod_data:/var/lib/postgresql/data
      - ./backups:/backups
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${PROD_DB_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G

  backend:
    image: ${DOCKER_USERNAME}/school-management-backend:main
    container_name: school-management-backend-prod
    environment:
      DATABASE_URL: postgresql://${PROD_DB_USER}:${PROD_DB_PASSWORD}@postgres:5432/school_management
      JWT_SECRET_KEY: ${PROD_JWT_SECRET}
      JWT_ALGORITHM: HS256
      ACCESS_TOKEN_EXPIRE_MINUTES: 30
      REFRESH_TOKEN_EXPIRE_DAYS: 7
      APP_ENV: production
      DEBUG: false
      CORS_ORIGINS: https://app.schoolmanagement.com
      LOG_LEVEL: INFO
    volumes:
      - backend_uploads_prod:/app/uploads
    depends_on:
      postgres:
        condition: service_healthy
    restart: unless-stopped
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '1'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M

  frontend:
    image: ${DOCKER_USERNAME}/school-management-frontend:main
    container_name: school-management-frontend-prod
    environment:
      VITE_API_BASE_URL: https://app.schoolmanagement.com/api
    restart: unless-stopped
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
        reservations:
          cpus: '0.25'
          memory: 256M

  nginx:
    image: nginx:alpine
    container_name: school-management-nginx-prod
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/default.conf:/etc/nginx/conf.d/default.conf
      - ./nginx/ssl-prod:/etc/nginx/ssl
    depends_on:
      - backend
      - frontend
    restart: unless-stopped
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
        reservations:
          cpus: '0.25'
          memory: 256M

  worker:
    image: ${DOCKER_USERNAME}/school-management-backend:main
    container_name: school-management-worker-prod
    environment:
      DATABASE_URL: postgresql://${PROD_DB_USER}:${PROD_DB_PASSWORD}@postgres:5432/school_management
      APP_ENV: production
      LOG_LEVEL: INFO
    command: python -m app.infrastructure.notifications.outbox_worker
    depends_on:
      - postgres
    restart: unless-stopped
    deploy:
      replicas: 2

  redis:
    image: redis:7-alpine
    container_name: school-management-redis-prod
    volumes:
      - redis_prod_data:/data
    restart: unless-stopped
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M

volumes:
  postgres_prod_data:
  backend_uploads_prod:
  redis_prod_data:
```

---

## Deployment Procedures

### Local Development Setup

1. **Clone Repository**
   ```bash
   git clone https://github.com/your-org/school-management.git
   cd school-management
   ```

2. **Configure Environment**
   ```bash
   cp backend/.env.example backend/.env
   cp frontend/.env.example frontend/.env
   ```

3. **Start Services**
   ```bash
   docker-compose up -d
   ```

4. **Run Migrations**
   ```bash
   docker-compose exec backend alembic upgrade head
   ```

5. **Seed Data**
   ```bash
   docker-compose exec backend python -m app.seed.seed_data
   ```

6. **Access Application**
   - Frontend: http://localhost
   - Backend API: http://localhost/api
   - API Docs: http://localhost/api/docs

### Staging Deployment

1. **Build and Push Images**
   ```bash
   docker build -t your-dockerhub/school-management-backend:develop ./backend
   docker build -t your-dockerhub/school-management-frontend:develop ./frontend
   docker push your-dockerhub/school-management-backend:develop
   docker push your-dockerhub/school-management-frontend:develop
   ```

2. **Deploy to Staging Server**
   ```bash
   ssh user@staging-server
   cd /opt/school-management
   docker-compose -f docker-compose.staging.yml pull
   docker-compose -f docker-compose.staging.yml up -d
   ```

3. **Run Migrations**
   ```bash
   docker-compose -f docker-compose.staging.yml exec -T backend alembic upgrade head
   ```

4. **Health Check**
   ```bash
   curl https://staging.schoolmanagement.com/health
   ```

### Production Deployment

1. **Pre-deployment Checklist**
   - [ ] All tests pass
   - [ ] Code reviewed and approved
   - [ ] Database migrations tested
   - [ ] Backup created
   - [ ] Rollback plan ready

2. **Build and Tag Images**
   ```bash
   docker build -t your-dockerhub/school-management-backend:latest ./backend
   docker build -t your-dockerhub/school-management-frontend:latest ./frontend
   docker tag your-dockerhub/school-management-backend:latest your-dockerhub/school-management-backend:$(date +%Y%m%d)
   docker tag your-dockerhub/school-management-frontend:latest your-dockerhub/school-management-frontend:$(date +%Y%m%d)
   docker push your-dockerhub/school-management-backend:latest
   docker push your-dockerhub/school-management-frontend:latest
   docker push your-dockerhub/school-management-backend:$(date +%Y%m%d)
   docker push your-dockerhub/school-management-frontend:$(date +%Y%m%d)
   ```

3. **Create Backup**
   ```bash
   ssh user@production-server
   cd /opt/school-management
   ./scripts/backup.sh
   ```

4. **Deploy with Zero Downtime**
   ```bash
   docker-compose -f docker-compose.prod.yml pull
   docker-compose -f docker-compose.prod.yml up -d --no-deps --build backend frontend
   docker-compose -f docker-compose.prod.yml up -d
   ```

5. **Run Migrations**
   ```bash
   docker-compose -f docker-compose.prod.yml exec -T backend alembic upgrade head
   ```

6. **Health Check**
   ```bash
   curl https://app.schoolmanagement.com/health
   curl https://app.schoolmanagement.com/ready
   ```

7. **Monitor Logs**
   ```bash
   docker-compose -f docker-compose.prod.yml logs -f
   ```

---

## SSL/TLS Configuration

### Let's Encrypt Setup

1. **Install Certbot**
   ```bash
   sudo apt-get install certbot python3-certbot-nginx
   ```

2. **Generate SSL Certificate**
   ```bash
   sudo certbot --nginx -d app.schoolmanagement.com -d staging.schoolmanagement.com
   ```

3. **Auto-renewal**
   ```bash
   sudo certbot renew --dry-run
   ```

### SSL Configuration in Nginx

```nginx
server {
    listen 443 ssl http2;
    server_name app.schoolmanagement.com;

    ssl_certificate /etc/nginx/ssl/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # ... rest of configuration
}

server {
    listen 80;
    server_name app.schoolmanagement.com;
    return 301 https://$server_name$request_uri;
}
```

---

## Monitoring and Logging

### Container Monitoring

```bash
# View container stats
docker stats

# View logs
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f postgres

# Inspect container
docker inspect school-management-backend-prod
```

### Log Aggregation

**Setup ELK Stack or use cloud service:**
- Elasticsearch for log storage
- Logstash for log processing
- Kibana for log visualization

### Health Monitoring

**Prometheus + Grafana:**
- Expose metrics endpoint
- Configure Prometheus scraping
- Create Grafana dashboards

---

## Backup and Recovery

### Database Backup Script

```bash
#!/bin/bash
# scripts/backup.sh

BACKUP_DIR="/opt/backups/school-management"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

# Database backup
docker-compose exec -T postgres pg_dump -U postgres school_management > $BACKUP_DIR/db_$TIMESTAMP.sql

# File backup
tar -czf $BACKUP_DIR/files_$TIMESTAMP.tar.gz uploads/

# Cleanup old backups (keep last 30 days)
find $BACKUP_DIR -name "db_*.sql" -mtime +30 -delete
find $BACKUP_DIR -name "files_*.tar.gz" -mtime +30 -delete

echo "Backup completed: $TIMESTAMP"
```

### Restore Script

```bash
#!/bin/bash
# scripts/restore.sh

BACKUP_FILE=$1

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: ./restore.sh <backup_file>"
    exit 1
fi

# Restore database
docker-compose exec -T postgres psql -U postgres -d school_management < $BACKUP_FILE

echo "Restore completed"
```

---

## Troubleshooting

### Common Issues

**Container won't start:**
```bash
# Check logs
docker-compose logs backend

# Check resource usage
docker stats

# Restart container
docker-compose restart backend
```

**Database connection issues:**
```bash
# Check if postgres is running
docker-compose ps postgres

# Test connection
docker-compose exec backend python -c "from app.core.database import engine; print(engine.connect())"
```

**Migration issues:**
```bash
# Check migration status
docker-compose exec backend alembic current

# Rollback migration
docker-compose exec backend alembic downgrade -1

# Force migration
docker-compose exec backend alembic stamp head
```

**Nginx issues:**
```bash
# Test nginx configuration
docker-compose exec nginx nginx -t

# Reload nginx
docker-compose exec nginx nginx -s reload
```

---

## Security Best Practices

1. **Use non-root users in containers**
2. **Scan images for vulnerabilities**
3. **Keep images updated**
4. **Use secrets management for sensitive data**
5. **Enable SSL/TLS**
6. **Implement rate limiting**
7. **Regular security audits**
8. **Network segmentation**
9. **Regular backups**
10. **Monitor container activity**

---

## Performance Optimization

### Backend Optimization

- Use Gunicorn with multiple workers
- Enable database connection pooling
- Implement caching with Redis
- Use async operations where possible
- Optimize database queries

### Frontend Optimization

- Enable gzip compression
- Implement CDN for static assets
- Use lazy loading for images
- Minify JavaScript and CSS
- Implement service worker for caching

### Database Optimization

- Regular vacuum and analyze
- Optimize indexes
- Use connection pooling
- Monitor slow queries
- Implement read replicas for scaling

<!-- SCS360_SOURCE_END: 14 -->

---

<a id="belge-15"></a>

## 15. docs/FRONTEND_PAGES.md

Kaynak: [docs/FRONTEND_PAGES.md](docs/FRONTEND_PAGES.md)  
SHA-256: `f74ca731fed564401ffa679d80493906f7098c7a078732033333c53e99a45e49`

<!-- SCS360_SOURCE_BEGIN: 15 -->
# School Management System - Frontend Pages

## Page Structure

All pages follow the Creative Tim Material Dashboard React template structure with:
- Sidebar navigation
- Top navbar with user info
- Main content area with cards, tables, and forms
- Responsive design (mobile, tablet, desktop)

---

## Authentication Pages

### Login Page
**Route:** `/login`  
**File:** `frontend/src/features/auth/pages/Login.tsx`  
**Components:**
- Email input with validation
- Password input with validation
- Remember me checkbox
- Login button
- Forgot password link
- Error display

**Features:**
- Form validation with Zod
- JWT token storage
- Redirect to dashboard on success
- Error handling with toast notifications

### Forgot Password Page
**Route:** `/forgot-password`  
**File:** `frontend/src/features/auth/pages/ForgotPassword.tsx`  
**Components:**
- Email input
- Submit button
- Back to login link

**Features:**
- Email validation
- API call to request reset
- Success message display

### Reset Password Page
**Route:** `/reset-password/:token`  
**File:** `frontend/src/features/auth/pages/ResetPassword.tsx`  
**Components:**
- New password input
- Confirm password input
- Submit button

**Features:**
- Password strength validation
- Password match validation
- Token-based reset

### 403 Forbidden Page
**Route:** `/403`  
**File:** `frontend/src/features/auth/pages/Forbidden.tsx`  
**Components:**
- Forbidden message
- Back to home button
- Contact admin link

### 404 Not Found Page
**Route:** `/404`  
**File:** `frontend/src/features/auth/pages/NotFound.tsx`  
**Components:**
- Not found message
- Back to home button

---

## Dashboard Pages

### Dashboard Home
**Route:** `/dashboard`  
**File:** `frontend/src/features/dashboard/pages/Dashboard.tsx`  
**Components:**
- Summary cards (Total Students, Active Students, Total Branches, etc.)
- Monthly collection chart
- Debt vs payment comparison chart
- Class occupancy chart
- Attendance trend chart
- Recent activities list

**Features:**
- Role-based data display
- Real-time statistics
- Interactive charts
- Responsive grid layout

---

## Organization Pages

### Organization List
**Route:** `/organizations`  
**File:** `frontend/src/features/organizations/pages/OrganizationList.tsx`  
**Components:**
- Data table with pagination
- Search input
- Filter by status
- Add organization button
- Action buttons (Edit, Delete, View)

**Features:**
- List all organizations (Super Admin only)
- Search and filter
- Pagination
- Delete confirmation modal

### Organization Create/Edit
**Route:** `/organizations/new`  
**Route:** `/organizations/:id/edit`  
**File:** `frontend/src/features/organizations/pages/OrganizationForm.tsx`  
**Components:**
- Name input
- Tax number input
- Tax office input
- Address textarea
- Phone input
- Email input
- Logo upload
- Save/Cancel buttons

**Features:**
- Form validation
- Logo preview
- Create/Update mode

---

## Branch Pages

### Branch List
**Route:** `/branches`  
**File:** `frontend/src/features/branches/pages/BranchList.tsx`  
**Components:**
- Data table with pagination
- Search input
- Filter by organization
- Filter by status
- Add branch button
- Action buttons

**Features:**
- List branches based on user permissions
- Organization filter
- Capacity display
- Status badges

### Branch Create/Edit
**Route:** `/branches/new`  
**Route:** `/branches/:id/edit`  
**File:** `frontend/src/features/branches/pages/BranchForm.tsx`  
**Components:**
- Organization select
- Name input
- Code input
- Address textarea
- Phone input
- Email input
- Capacity input
- Save/Cancel buttons

**Features:**
- Organization selection (Super Admin only)
- Code uniqueness validation
- Capacity validation

### Branch Detail
**Route:** `/branches/:id`  
**File:** `frontend/src/features/branches/pages/BranchDetail.tsx`  
**Components:**
- Branch information card
- Statistics cards
- Classes list
- Students count
- Staff list

**Features:**
- Detailed branch view
- Related data display
- Quick actions

---

## User Pages

### User List
**Route:** `/users`  
**File:** `frontend/src/features/users/pages/UserList.tsx`  
**Components:**
- Data table with pagination
- Search input
- Filter by role
- Filter by branch
- Filter by status
- Add user button
- Action buttons

**Features:**
- List users based on organization/branch scope
- Role badges
- Status badges
- Branch assignment display

### User Create/Edit
**Route:** `/users/new`  
**Route:** `/users/:id/edit`  
**File:** `frontend/src/features/users/pages/UserForm.tsx`  
**Components:**
- Email input
- Password input (create only)
- First name input
- Last name input
- Phone input
- Role multi-select
- Branch multi-select
- Status toggle
- Save/Cancel buttons

**Features:**
- Email uniqueness validation
- Password strength validation
- Role assignment
- Branch assignment
- Status management

### User Detail
**Route:** `/users/:id`  
**File:** `frontend/src/features/users/pages/UserDetail.tsx`  
**Components:**
- User information card
- Roles list
- Branches list
- Activity log
- Edit/Delete buttons

**Features:**
- Detailed user view
- Role management
- Branch management
- Activity history

### Role List
**Route:** `/roles`  
**File:** `frontend/src/features/users/pages/RoleList.tsx`  
**Components:**
- Data table
- Role name
- Description
- Permission count
- Edit button

**Features:**
- List all roles
- Permission count display
- System role badges

### Role Permission Matrix
**Route:** `/roles/:id/permissions`  
**File:** `frontend/src/features/users/pages/RolePermissions.tsx`  
**Components:**
- Permission matrix table
- Module-based grouping
- Checkboxes for permissions
- Save button

**Features:**
- Visual permission matrix
- Module grouping
- Bulk permission assignment
- Save changes

---

## Student Pages

### Student List
**Route:** `/students`  
**File:** `frontend/src/features/students/pages/StudentList.tsx`  
**Components:**
- Data table with pagination
- Search input
- Filter by branch
- Filter by class
- Filter by status
- Add student button
- Action buttons

**Features:**
- Photo display
- Name search
- Status badges
- Class assignment display
- Export button

### Student Create/Edit
**Route:** `/students/new`  
**Route:** `/students/:id/edit`  
**File:** `frontend/src/features/students/pages/StudentForm.tsx`  
**Components:**
- Branch select
- Class select
- First name input
- Last name input
- Date of birth picker
- Gender radio
- Photo upload
- Enrollment date picker
- Address textarea
- Notes textarea
- Parents section (dynamic)
- Save/Cancel buttons

**Features:**
- Photo upload with preview
- Parent management (add/remove)
- Class assignment
- Form validation

### Student Detail
**Route:** `/students/:id`  
**File:** `frontend/src/features/students/pages/StudentDetail.tsx`  
**Components:**
- Student profile card
- Photo display
- Personal information
- Parents list
- Class information
- Tabs: Files, Payments, Attendance, Notes
- Edit/Delete buttons

**Features:**
- Comprehensive student view
- Tabbed interface
- Quick actions
- Related data display

### Student Files
**Route:** `/students/:id/files`  
**File:** `frontend/src/features/students/pages/StudentFiles.tsx`  
**Components:**
- File list table
- File category filter
- Upload button
- Download button
- Delete button
- File preview modal

**Features:**
- File upload
- File preview
- Category filtering
- Download/delete actions

### Student Parents
**Route:** `/students/:id/parents`  
**File:** `frontend/src/features/students/pages/StudentParents.tsx`  
**Components:**
- Parents list
- Add parent button
- Parent form modal
- Contact information display
- Notification preferences

**Features:**
- Parent management
- Contact info display
- Notification preferences
- Primary parent selection

---

## Class Pages

### Class List
**Route:** `/classes`  
**File:** `frontend/src/features/classes/pages/ClassList.tsx`  
**Components:**
- Data table with pagination
- Search input
- Filter by branch
- Filter by teacher
- Filter by academic year
- Add class button
- Action buttons

**Features:**
- Class code display
- Teacher assignment
- Capacity display
- Occupancy rate
- Status badges

### Class Create/Edit
**Route:** `/classes/new`  
**Route:** `/classes/:id/edit`  
**File:** `frontend/src/features/classes/pages/ClassForm.tsx`  
**Components:**
- Branch select
- Name input
- Code input
- Capacity input
- Teacher select
- Academic year input
- Save/Cancel buttons

**Features:**
- Code uniqueness validation
- Teacher assignment
- Capacity validation
- Academic year selection

### Class Detail
**Route:** `/classes/:id`  
**File:** `frontend/src/features/classes/pages/ClassDetail.tsx`  
**Components:**
- Class information card
- Teacher information
- Statistics cards
- Students list
- Occupancy chart
- Assign students button
- Take attendance button

**Features:**
- Detailed class view
- Student list
- Occupancy visualization
- Quick actions

### Class Occupancy
**Route:** `/classes/:id/occupancy`  
**File:** `frontend/src/features/classes/pages/ClassOccupancy.tsx`  
**Components:**
- Occupancy chart
- Student list
- Available slots
- Capacity information

**Features:**
- Visual occupancy display
- Student count
- Available slots
- Capacity warning

### Assign Students to Class
**Route:** `/classes/:id/assign-students`  
**File:** `frontend/src/features/classes/pages/AssignStudents.tsx`  
**Components:**
- Available students list
- Assigned students list
- Search input
- Transfer buttons (add/remove)
- Save button

**Features:**
- Dual list selection
- Search functionality
- Capacity validation
- Bulk assignment

---

## Attendance Pages

### Attendance List
**Route:** `/attendance`  
**File:** `frontend/src/features/attendance/pages/AttendanceList.tsx`  
**Components:**
- Date picker
- Class select
- Student select
- Status filter
- Data table
- Export button

**Features:**
- Date filtering
- Class-based view
- Student-based view
- Status filtering
- Export functionality

### Take Attendance (Daily)
**Route:** `/attendance/take`  
**File:** `frontend/src/features/attendance/pages/TakeAttendance.tsx`  
**Components:**
- Date picker
- Class select
- Student list with radio buttons
- Status options (Present, Absent, Excused, Late, Half Day)
- Notes field
- Save button

**Features:**
- Class-based attendance
- Quick status selection
- Notes per student
- Duplicate prevention
- Bulk save

### Bulk Attendance
**Route:** `/attendance/bulk`  
**File:** `frontend/src/features/attendance/pages/BulkAttendance.tsx`  
**Components:**
- Date picker
- Class select
- Student table with status dropdowns
- Notes column
- Save button

**Features:**
- Table-based entry
- Status dropdowns
- Notes per student
- Bulk save
- Validation

### Student Attendance History
**Route:** `/attendance/student/:id`  
**File:** `frontend/src/features/attendance/pages/StudentAttendance.tsx`  
**Components:**
- Student info card
- Date range picker
- Attendance calendar
- Statistics cards
- Attendance list

**Features:**
- Calendar view
- Statistics summary
- Date range filtering
- History list

### Monthly Attendance Report
**Route:** `/attendance/reports/monthly`  
**File:** `frontend/src/features/attendance/pages/MonthlyReport.tsx`  
**Components:**
- Month/year picker
- Class select
- Report table
- Summary cards
- Export buttons (PDF, Excel)

**Features:**
- Monthly summary
- Class-based report
- Statistics
- Export options

---

## Finance Pages

### Debt List
**Route:** `/finance/debts`  
**File:** `frontend/src/features/finance/pages/DebtList.tsx`  
**Components:**
- Data table with pagination
- Search input
- Filter by student
- Filter by branch
- Filter by status
- Filter by type
- Date range picker
- Add debt button
- Action buttons

**Features:**
- Amount display
- Status badges
- Type badges
- Due date display
- Overdue highlighting

### Debt Create/Edit
**Route:** `/finance/debts/new`  
**Route:** `/finance/debts/:id/edit`  
**File:** `frontend/src/features/finance/pages/DebtForm.tsx`  
**Components:**
- Student select
- Debt type select
- Description input
- Amount input
- Due date picker
- Academic year input
- Save/Cancel buttons

**Features:**
- Student search
- Type selection
- Amount validation
- Due date validation

### Payment List
**Route:** `/finance/payments`  
**File:** `frontend/src/features/finance/pages/PaymentList.tsx`  
**Components:**
- Data table with pagination
- Search input
- Filter by student
- Filter by branch
- Filter by method
- Date range picker
- Take payment button
- Action buttons

**Features:**
- Payment amount display
- Method badges
- Date display
- Receipt link
- Cancel button

### Take Payment
**Route:** `/finance/payments/new`  
**File:** `frontend/src/features/finance/pages/TakePayment.tsx`  
**Components:**
- Student select
- Debt select
- Amount input
- Payment method select
- Payment date picker
- Notes textarea
- Save/Cancel buttons

**Features:**
- Student debt display
- Remaining amount calculation
- Payment method selection
- Auto-receipt generation

### Student Payment History
**Route:** `/finance/payments/student/:id`  
**File:** `frontend/src/features/finance/pages/StudentPayments.tsx`  
**Components:**
- Student info card
- Debt summary
- Payment list
- Receipt links
- Export button

**Features:**
- Debt vs payment summary
- Payment history
- Receipt access
- Export functionality

---

## Receipt Pages

### Receipt Detail
**Route:** `/finance/receipts/:id`  
**File:** `frontend/src/features/receipts/pages/ReceiptDetail.tsx`  
**Components:**
- Receipt card
- Organization info
- Branch info
- Student info
- Payment details
- Remaining debt display
- Download PDF button
- Print button
- Send email button

**Features:**
- Professional receipt layout
- All payment details
- PDF download
- Print functionality
- Email sending

### Receipt Print View
**Route:** `/finance/receipts/:id/print`  
**File:** `frontend/src/features/receipts/pages/ReceiptPrint.tsx`  
**Components:**
- Print-optimized layout
- Organization header
- Receipt details
- Payment breakdown
- Footer
- Print button

**Features:**
- A4 print layout
- Professional design
- Auto-print option
- Close button

---

## Announcement Pages

### Announcement List
**Route:** `/announcements`  
**File:** `frontend/src/features/announcements/pages/AnnouncementList.tsx`  
**Components:**
- Data table with pagination
- Search input
- Filter by audience
- Filter by status
- Date range picker
- Create announcement button
- Action buttons

**Features:**
- Title display
- Audience badges
- Channel indicators
- Scheduled date
- Sent status
- View details

### Announcement Create/Edit
**Route:** `/announcements/new`  
**Route:** `/announcements/:id/edit`  
**File:** `frontend/src/features/announcements/pages/AnnouncementForm.tsx`  
**Components:**
- Title input
- Content rich text editor
- Audience select (All Parents, Branch Parents, Class Parents, Single Student)
- Branch select (conditional)
- Class select (conditional)
- Student select (conditional)
- Channel checkboxes (Email, SMS, WhatsApp)
- Schedule datetime picker
- Send now/Schedule buttons
- Preview button

**Features:**
- Rich text editing
- Conditional fields based on audience
- Channel selection
- Scheduling
- Preview functionality

### Announcement Detail
**Route:** `/announcements/:id`  
**File:** `frontend/src/features/announcements/pages/AnnouncementDetail.tsx`  
**Components:**
- Announcement card
- Content display
- Target audience info
- Channel info
- Sending status
- Recipients list
- Send results
- Retry failed button

**Features:**
- Full announcement view
- Sending status
- Recipient list
- Send results per channel
- Retry failed sends

---

## Notification Pages

### Notification Log
**Route:** `/notifications`  
**File:** `frontend/src/features/notifications/pages/NotificationLog.tsx`  
**Components:**
- Data table with pagination
- Search input
- Filter by channel
- Filter by status
- Filter by date range
- Retry failed button
- View details button

**Features:**
- Channel badges
- Status badges
- Recipient info
- Error display
- Retry functionality

### Notification Templates
**Route:** `/notifications/templates`  
**File:** `frontend/src/features/notifications/pages/NotificationTemplates.tsx`  
**Components:**
- Template list table
- Channel filter
- Create template button
- Edit button
- Delete button

**Features:**
- Template name
- Channel badge
- Subject preview
- Body preview
- Active status

### Template Create/Edit
**Route:** `/notifications/templates/new`  
**Route:** `/notifications/templates/:id/edit`  
**File:** `frontend/src/features/notifications/pages/TemplateForm.tsx`  
**Components:**
- Name input
- Channel select
- Subject input (Email only)
- Body textarea with variable hints
- Active toggle
- Save/Cancel buttons

**Features:**
- Variable placeholder hints
- Channel-specific fields
- Preview functionality
- Validation

---

## Report Pages

### Monthly Payment Report
**Route:** `/reports/monthly-payments`  
**File:** `frontend/src/features/reports/pages/MonthlyPayments.tsx`  
**Components:**
- Month/year picker
- Branch select
- Summary cards
- Chart
- Data table
- Export buttons (CSV, Excel, PDF)

**Features:**
- Monthly summary
- Branch comparison
- Chart visualization
- Export options

### Debt Report
**Route:** `/reports/debts`  
**File:** `frontend/src/features/reports/pages/DebtReport.tsx`  
**Components:**
- Date range picker
- Branch select
- Status filter
- Type filter
- Summary cards
- Data table
- Export buttons

**Features:**
- Debt summary
- Status breakdown
- Type breakdown
- Export options

### Overdue Debt Report
**Route:** `/reports/overdue-debts`  
**File:** `frontend/src/features/reports/pages/OverdueDebts.tsx`  
**Components:**
- Days overdue filter
- Branch select
- Summary cards
- Data table
- Export buttons
- Send reminder button

**Features:**
- Overdue summary
- Days overdue grouping
- Reminder sending
- Export options

### Attendance Report
**Route:** `/reports/attendance`  
**File:** `frontend/src/features/reports/pages/AttendanceReport.tsx`  
**Components:**
- Date range picker
- Class select
- Student select
- Summary cards
- Chart
- Data table
- Export buttons

**Features:**
- Attendance summary
- Status breakdown
- Trend analysis
- Export options

### Class Occupancy Report
**Route:** `/reports/class-occupancy`  
**File:** `frontend/src/features/reports/pages/ClassOccupancyReport.tsx`  
**Components:**
- Branch select
- Academic year select
- Summary cards
- Chart
- Data table
- Export buttons

**Features:**
- Occupancy summary
- Branch comparison
- Visual chart
- Export options

### Branch Performance Report
**Route:** `/reports/branch-performance`  
**File:** `frontend/src/features/reports/pages/BranchPerformance.tsx`  
**Components:**
- Date range picker
- Summary cards
- Charts (Revenue, Students, Attendance)
- Data table
- Export buttons

**Features:**
- Multi-metric comparison
- Revenue tracking
- Student growth
- Attendance rates
- Export options

---

## Settings Pages

### General Settings
**Route:** `/settings/general`  
**File:** `frontend/src/features/settings/pages/GeneralSettings.tsx`  
**Components:**
- School name input
- Tax number input
- Tax office input
- Address textarea
- Phone input
- Email input
- Logo upload
- Default currency select
- Academic year input
- Save button

**Features:**
- Organization settings
- Logo upload
- Currency selection
- Academic year management

### Integration Settings
**Route:** `/settings/integrations`  
**File:** `frontend/src/features/settings/pages/IntegrationSettings.tsx`  
**Components:**
- Tab navigation (SMTP, SMS, WhatsApp)
- SMTP settings form
- SMS settings form
- WhatsApp settings form
- Test connection button
- Save button

**Features:**
- SMTP configuration
- SMS provider configuration
- WhatsApp provider configuration
- Connection testing
- Secure storage

### File Upload Settings
**Route:** `/settings/uploads`  
**File:** `frontend/src/features/settings/pages/UploadSettings.tsx`  
**Components:**
- Max upload size input
- Allowed file types input
- Storage path input
- Save button

**Features:**
- Size limit configuration
- File type restrictions
- Storage path management

### Notification Settings
**Route:** `/settings/notifications`  
**File:** `frontend/src/features/settings/pages/NotificationSettings.tsx`  
**Components:**
- Default sender email
- Default sender name
- SMS sender ID
- Retry count input
- Retry interval input
- Save button

**Features:**
- Default sender configuration
- Retry policy
- Notification preferences

---

## Common Components

### Layout Components
- `DashboardLayout` - Main layout with sidebar and navbar
- `AuthLayout` - Authentication page layout
- `Sidebar` - Navigation sidebar with role-based menu
- `Navbar` - Top navigation with user info

### Common UI Components
- `DataTable` - Reusable data table with pagination
- `SearchInput` - Search input component
- `FilterPanel` - Filter panel with multiple filters
- `ConfirmModal` - Confirmation modal for destructive actions
- `LoadingSpinner` - Loading indicator
- `EmptyState` - Empty state display
- `ErrorState` - Error state display
- `Toast` - Toast notification component
- `Card` - Material UI card wrapper
- `Button` - Styled button component
- `FormInput` - Form input with validation
- `FormSelect` - Form select with validation
- `DatePicker` - Date picker component
- `FileUpload` - File upload component
- `Badge` - Status badge component
- `StatusChip` - Status chip with colors

---

## Route Guards

### ProtectedRoute
**File:** `frontend/src/routes/ProtectedRoute.tsx`  
**Purpose:** Protect routes requiring authentication  
**Behavior:** Redirect to login if not authenticated

### RoleBasedRoute
**File:** `frontend/src/routes/RoleBasedRoute.tsx`  
**Purpose:** Protect routes based on user roles  
**Behavior:** Redirect to 403 if user lacks required role

### PermissionBasedRoute
**File:** `frontend/src/routes/PermissionBasedRoute.tsx`  
**Purpose:** Protect routes based on user permissions  
**Behavior:** Redirect to 403 if user lacks required permission

---

## Error Handling

### ErrorBoundary
**File:** `frontend/src/components/ErrorBoundary.tsx`  
**Purpose:** Catch React component errors  
**Behavior:** Display error page with retry option

### Global Error Handler
**File:** `frontend/src/utils/errorHandler.ts`  
**Purpose:** Handle API errors globally  
**Behavior:** Display toast notifications, redirect on auth errors

<!-- SCS360_SOURCE_END: 15 -->

---

<a id="belge-16"></a>

## 16. docs/NOTIFICATION_ARCHITECTURE.md

Kaynak: [docs/NOTIFICATION_ARCHITECTURE.md](docs/NOTIFICATION_ARCHITECTURE.md)  
SHA-256: `e7cab99f8e91bc7f373302b9ae32bb7a3b8e9fd4220f36ed0b54dcd4c5b02893`

<!-- SCS360_SOURCE_BEGIN: 16 -->
# Notification Architecture

## Overview

The notification system is designed to be provider-independent, reliable, and scalable using the Outbox Pattern. It supports multiple channels (Email, SMS, WhatsApp) with automatic retry mechanisms and comprehensive logging.

---

## Architecture Principles

1. **Provider Independence:** System is not coupled to specific notification providers
2. **Reliability:** Outbox pattern ensures notifications are never lost
3. **Scalability:** Background worker processes notifications asynchronously
4. **Observability:** Comprehensive logging and status tracking
5. **Flexibility:** Easy to add new notification channels and providers

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Application Layer                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Payment      │  │ Announcement │  │ Debt Reminder│          │
│  │ Created      │  │ Sent         │  │ Scheduled    │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                 │                 │                    │
│         └─────────────────┴─────────────────┘                    │
│                           │                                       │
│                           ▼                                       │
│                  ┌────────────────┐                               │
│                  │ Notification  │                               │
│                  │ Dispatcher    │                               │
│                  └────────┬───────┘                               │
└───────────────────────────┼───────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Database Layer                              │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              notification_jobs Table                       │   │
│  │  - id, channel, recipient_type, recipient_id             │   │
│  │  - subject, body, status, scheduled_for                   │   │
│  │  - sent_at, failed_at, error_message, retry_count         │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Background Worker                             │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              Outbox Worker Process                        │   │
│  │  - Polls for PENDING jobs                                │   │
│  │  - Processes by scheduled_for timestamp                   │   │
│  │  - Routes to appropriate provider                         │   │
│  │  - Updates job status                                     │   │
│  │  - Handles retries                                        │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                            │
            ┌───────────────┼───────────────┐
            │               │               │
            ▼               ▼               ▼
┌──────────────────┐ ┌──────────────┐ ┌──────────────┐
│   Email Provider │ │ SMS Provider│ │WhatsApp      │
│   (SMTP)         │ │ (Netgsm/    │ │Provider      │
│                  │ │ Twilio)     │ │(Meta API)    │
└──────────────────┘ └──────────────┘ └──────────────┘
```

---

## Component Design

### 1. Base Notification Provider

**File:** `backend/app/infrastructure/notifications/base.py`

```python
from abc import ABC, abstractmethod
from typing import Dict, Any

class NotificationProvider(ABC):
    """Abstract base class for notification providers"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
    
    @abstractmethod
    async def send(
        self,
        recipient: str,
        subject: str,
        body: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Send notification
        
        Args:
            recipient: Recipient address/number
            subject: Message subject (for email)
            body: Message body
            **kwargs: Provider-specific parameters
        
        Returns:
            Dict containing provider response
        """
        pass
    
    @abstractmethod
    def validate_config(self) -> bool:
        """Validate provider configuration"""
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """Get provider name for logging"""
        pass
```

### 2. Email Provider

**File:** `backend/app/infrastructure/notifications/email_provider.py`

```python
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any
from .base import NotificationProvider

class EmailProvider(NotificationProvider):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.smtp_host = config.get("smtp_host")
        self.smtp_port = config.get("smtp_port", 587)
        self.smtp_user = config.get("smtp_user")
        self.smtp_password = config.get("smtp_password")
        self.from_email = config.get("from_email")
        self.from_name = config.get("from_name")
    
    async def send(
        self,
        recipient: str,
        subject: str,
        body: str,
        **kwargs
    ) -> Dict[str, Any]:
        try:
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = f"{self.from_name} <{self.from_email}>"
            message["To"] = recipient
            
            # Add body
            text_part = MIMEText(body, "plain")
            message.attach(text_part)
            
            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(message)
            
            return {
                "success": True,
                "provider_response": "Email sent successfully",
                "message_id": None
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "provider_response": None
            }
    
    def validate_config(self) -> bool:
        return all([
            self.smtp_host,
            self.smtp_port,
            self.smtp_user,
            self.smtp_password,
            self.from_email
        ])
    
    def get_provider_name(self) -> str:
        return "Email (SMTP)"
```

### 3. SMS Provider

**File:** `backend/app/infrastructure/notifications/sms_provider.py`

```python
import httpx
from typing import Dict, Any
from .base import NotificationProvider

class SMSProvider(NotificationProvider):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_url = config.get("api_url")
        self.username = config.get("username")
        self.password = config.get("password")
        self.header = config.get("header", "SCHOOL")
    
    async def send(
        self,
        recipient: str,
        subject: str,
        body: str,
        **kwargs
    ) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.api_url,
                    data={
                        "usercode": self.username,
                        "password": self.password,
                        "gsmno": recipient,
                        "message": body,
                        "msgheader": self.header
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    return {
                        "success": True,
                        "provider_response": response.text,
                        "message_id": response.json().get("message_id")
                    }
                else:
                    return {
                        "success": False,
                        "error": f"HTTP {response.status_code}",
                        "provider_response": response.text
                    }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "provider_response": None
            }
    
    def validate_config(self) -> bool:
        return all([self.api_url, self.username, self.password])
    
    def get_provider_name(self) -> str:
        return "SMS"
```

### 4. WhatsApp Provider

**File:** `backend/app/infrastructure/notifications/whatsapp_provider.py`

```python
import httpx
from typing import Dict, Any
from .base import NotificationProvider

class WhatsAppProvider(NotificationProvider):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_url = config.get("api_url")
        self.access_token = config.get("access_token")
        self.phone_number_id = config.get("phone_number_id")
    
    async def send(
        self,
        recipient: str,
        subject: str,
        body: str,
        **kwargs
    ) -> Dict[str, Any]:
        try:
            # Format phone number
            phone_number = recipient.replace("+", "")
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_url}/{self.phone_number_id}/messages",
                    headers={
                        "Authorization": f"Bearer {self.access_token}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "messaging_product": "whatsapp",
                        "to": phone_number,
                        "type": "text",
                        "text": {"body": body}
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    return {
                        "success": True,
                        "provider_response": response.json(),
                        "message_id": response.json().get("messages", [{}])[0].get("id")
                    }
                else:
                    return {
                        "success": False,
                        "error": f"HTTP {response.status_code}",
                        "provider_response": response.text
                    }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "provider_response": None
            }
    
    def validate_config(self) -> bool:
        return all([self.api_url, self.access_token, self.phone_number_id])
    
    def get_provider_name(self) -> str:
        return "WhatsApp (Meta)"
```

### 5. Notification Dispatcher

**File:** `backend/app/infrastructure/notifications/dispatcher.py`

```python
from typing import Dict, Any
from enum import Enum
from .email_provider import EmailProvider
from .sms_provider import SMSProvider
from .whatsapp_provider import WhatsAppProvider

class NotificationChannel(Enum):
    EMAIL = "EMAIL"
    SMS = "SMS"
    WHATSAPP = "WHATSAPP"

class NotificationDispatcher:
    def __init__(self):
        self.providers: Dict[NotificationChannel, NotificationProvider] = {}
        self._initialize_providers()
    
    def _initialize_providers(self):
        """Initialize notification providers from configuration"""
        # Email provider
        email_config = self._get_provider_config("smtp")
        if email_config:
            self.providers[NotificationChannel.EMAIL] = EmailProvider(email_config)
        
        # SMS provider
        sms_config = self._get_provider_config("sms")
        if sms_config:
            self.providers[NotificationChannel.SMS] = SMSProvider(sms_config)
        
        # WhatsApp provider
        whatsapp_config = self._get_provider_config("whatsapp")
        if whatsapp_config:
            self.providers[NotificationChannel.WHATSAPP] = WhatsAppProvider(whatsapp_config)
    
    def _get_provider_config(self, provider_type: str) -> Dict[str, Any]:
        """Get provider configuration from database or environment"""
        # Implementation: Fetch from integration_settings table
        pass
    
    async def dispatch_notification(
        self,
        channel: NotificationChannel,
        recipient: str,
        subject: str,
        body: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Dispatch notification to appropriate provider
        
        Args:
            channel: Notification channel
            recipient: Recipient address/number
            subject: Message subject
            body: Message body
            **kwargs: Provider-specific parameters
        
        Returns:
            Dict containing send result
        """
        provider = self.providers.get(channel)
        
        if not provider:
            return {
                "success": False,
                "error": f"Provider not configured for channel: {channel.value}"
            }
        
        if not provider.validate_config():
            return {
                "success": False,
                "error": f"Provider configuration invalid for: {provider.get_provider_name()}"
            }
        
        return await provider.send(recipient, subject, body, **kwargs)
```

### 6. Outbox Worker

**File:** `backend/app/infrastructure/notifications/outbox_worker.py`

```python
import asyncio
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.infrastructure.notifications.dispatcher import NotificationDispatcher, NotificationChannel
from app.models.notification import NotificationJob

class OutboxWorker:
    def __init__(self, poll_interval: int = 60):
        self.dispatcher = NotificationDispatcher()
        self.poll_interval = poll_interval
        self.running = False
    
    async def start(self):
        """Start the outbox worker"""
        self.running = True
        print("Outbox worker started")
        
        while self.running:
            try:
                await self.process_pending_jobs()
                await asyncio.sleep(self.poll_interval)
            except Exception as e:
                print(f"Error in outbox worker: {e}")
                await asyncio.sleep(self.poll_interval)
    
    async def stop(self):
        """Stop the outbox worker"""
        self.running = False
        print("Outbox worker stopped")
    
    async def process_pending_jobs(self):
        """Process pending notification jobs"""
        db: Session = next(get_db())
        
        try:
            # Get pending jobs that are due
            now = datetime.utcnow()
            pending_jobs = db.query(NotificationJob).filter(
                NotificationJob.status == "PENDING",
                NotificationJob.scheduled_for <= now,
                NotificationJob.retry_count < NotificationJob.max_retries
            ).limit(100).all()
            
            for job in pending_jobs:
                await self.process_job(job, db)
            
            db.commit()
        finally:
            db.close()
    
    async def process_job(self, job: NotificationJob, db: Session):
        """Process a single notification job"""
        try:
            # Dispatch notification
            channel = NotificationChannel(job.channel)
            result = await self.dispatcher.dispatch_notification(
                channel=channel,
                recipient=job.recipient_id,
                subject=job.subject,
                body=job.body
            )
            
            if result["success"]:
                # Update job status to SENT
                job.status = "SENT"
                job.sent_at = datetime.utcnow()
                job.provider_response = str(result.get("provider_response"))
            else:
                # Update job status to FAILED
                job.status = "FAILED"
                job.failed_at = datetime.utcnow()
                job.error_message = result.get("error")
                job.provider_response = str(result.get("provider_response"))
                job.retry_count += 1
                
                # If max retries not reached, reset to PENDING for retry
                if job.retry_count < job.max_retries:
                    job.status = "PENDING"
                    # Exponential backoff: 2^retry_count minutes
                    job.scheduled_for = datetime.utcnow() + timedelta(minutes=2 ** job.retry_count)
        
        except Exception as e:
            # Handle unexpected errors
            job.status = "FAILED"
            job.failed_at = datetime.utcnow()
            job.error_message = str(e)
            job.retry_count += 1
            
            if job.retry_count < job.max_retries:
                job.status = "PENDING"
                job.scheduled_for = datetime.utcnow() + timedelta(minutes=2 ** job.retry_count)

# Worker entry point
async def main():
    worker = OutboxWorker(poll_interval=30)
    try:
        await worker.start()
    except KeyboardInterrupt:
        await worker.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

### 7. Template Renderer

**File:** `backend/app/infrastructure/notifications/template_renderer.py`

```python
from typing import Dict, Any
from string import Template

class TemplateRenderer:
    def __init__(self):
        self.templates = {}
        self._load_templates()
    
    def _load_templates(self):
        """Load templates from database"""
        # Implementation: Fetch from message_templates table
        pass
    
    def render(
        self,
        template_name: str,
        channel: str,
        variables: Dict[str, Any]
    ) -> tuple:
        """
        Render template with variables
        
        Args:
            template_name: Name of the template
            channel: Notification channel (EMAIL, SMS, WHATSAPP)
            variables: Dictionary of variables to substitute
        
        Returns:
            Tuple of (subject, body)
        """
        template_key = f"{template_name}_{channel}"
        template = self.templates.get(template_key)
        
        if not template:
            raise ValueError(f"Template not found: {template_key}")
        
        # Render subject
        subject = Template(template["subject"]).safe_substitute(**variables)
        
        # Render body
        body = Template(template["body"]).safe_substitute(**variables)
        
        return subject, body
    
    def get_template(self, template_name: str, channel: str) -> Dict[str, str]:
        """Get template without rendering"""
        template_key = f"{template_name}_{channel}"
        return self.templates.get(template_key)
```

---

## Outbox Pattern Implementation

### Database Schema

**notification_jobs Table:**
```sql
CREATE TABLE notification_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    channel notification_channel NOT NULL,
    recipient_type VARCHAR(50) NOT NULL,
    recipient_id UUID NOT NULL,
    subject VARCHAR(255),
    body TEXT NOT NULL,
    status notification_status DEFAULT 'PENDING',
    scheduled_for TIMESTAMP WITH TIME ZONE,
    sent_at TIMESTAMP WITH TIME ZONE,
    failed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    provider_response TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

### Transactional Outbox

**Example: Payment Notification**

```python
from sqlalchemy.orm import Session
from app.models.payment import Payment
from app.models.notification import NotificationJob
from app.infrastructure.notifications.dispatcher import NotificationChannel

def create_payment_with_notification(
    payment_data: PaymentCreate,
    db: Session
) -> Payment:
    """Create payment and notification in single transaction"""
    
    # Create payment
    payment = Payment(**payment_data.dict())
    db.add(payment)
    db.flush()  # Get payment ID without committing
    
    # Create notification job (outbox)
    notification_job = NotificationJob(
        organization_id=payment.organization_id,
        channel=NotificationChannel.EMAIL.value,
        recipient_type="parent",
        recipient_id=payment.student.parent_id,
        subject="Payment Received",
        body=f"Payment of {payment.amount} received for {payment.student.name}",
        status="PENDING",
        scheduled_for=datetime.utcnow()
    )
    db.add(notification_job)
    
    # Commit transaction (both payment and notification)
    db.commit()
    
    return payment
```

---

## Notification Scenarios

### 1. Payment Received

**Trigger:** Payment created successfully

**Channels:**
- Email: Payment receipt to parent
- SMS: Optional payment confirmation
- WhatsApp: Optional payment notification

**Template Variables:**
```python
{
    "student_name": "Ahmet Yılmaz",
    "payment_amount": "5,000.00 TL",
    "payment_date": "2024-01-15",
    "receipt_number": "RCP-20240115-000001",
    "remaining_debt": "2,000.00 TL"
}
```

### 2. Announcement Sent

**Trigger:** Announcement created and sent

**Channels:**
- Email: Full announcement with formatting
- SMS: Short summary with link
- WhatsApp: Message with link to full announcement

**Template Variables:**
```python
{
    "announcement_title": "Kış Tatili Duyurusu",
    "announcement_content": "...",
    "school_name": "Demo Eğitim Kurumu",
    "announcement_date": "2024-01-15"
}
```

### 3. Debt Reminder

**Trigger:** Scheduled job checks for overdue debts

**Channels:**
- Email: Detailed debt information
- SMS: Short reminder
- WhatsApp: Reminder with payment link

**Template Variables:**
```python
{
    "parent_name": "Ali Yılmaz",
    "student_name": "Ahmet Yılmaz",
    "debt_amount": "2,000.00 TL",
    "due_date": "2024-01-20",
    "days_overdue": "5"
}
```

### 4. Password Reset

**Trigger:** User requests password reset

**Channels:**
- Email: Password reset link only

**Template Variables:**
```python
{
    "user_name": "Ahmet Yılmaz",
    "reset_link": "https://app.schoolmanagement.com/reset-password/token123",
    "expiry_hours": "1"
}
```

---

## Retry Strategy

### Exponential Backoff

**Algorithm:**
```
Retry delay = 2^retry_count minutes

Retry 1: 2^1 = 2 minutes
Retry 2: 2^2 = 4 minutes
Retry 3: 2^3 = 8 minutes
```

**Configuration:**
- Max retries: 3 (configurable)
- Initial delay: 2 minutes
- Max delay: 1 hour

### Failure Handling

**Permanent Failure:**
- Max retries exceeded
- Provider returns permanent error (e.g., invalid recipient)
- Job marked as FAILED permanently

**Temporary Failure:**
- Network timeout
- Provider rate limit
- Temporary provider outage
- Job rescheduled with exponential backoff

---

## Monitoring and Observability

### Metrics to Track

**Per Channel:**
- Total jobs created
- Total jobs sent successfully
- Total jobs failed
- Average delivery time
- Retry rate

**Per Provider:**
- Provider response time
- Provider error rate
- Provider availability

### Logging

**Log Events:**
- Job created
- Job dispatched
- Job sent successfully
- Job failed
- Retry scheduled
- Provider error

**Log Format:**
```python
{
    "timestamp": "2024-01-15T10:30:00Z",
    "event": "notification_sent",
    "job_id": "uuid",
    "channel": "EMAIL",
    "recipient": "parent@example.com",
    "provider": "Email (SMTP)",
    "duration_ms": 1234,
    "success": true
}
```

### Alerts

**Alert Conditions:**
- Failure rate > 10% for 5 minutes
- Queue size > 1000 jobs
- Provider unavailable for > 5 minutes
- Average delivery time > 30 seconds

---

## Security Considerations

### Data Protection

- Never log sensitive data (passwords, full credit card numbers)
- Encrypt notification content at rest
- Use TLS for all provider communications
- Validate recipient addresses before sending

### Rate Limiting

- Per-recipient rate limiting (prevent spam)
- Per-channel rate limiting (provider limits)
- Global rate limiting (system protection)

### Access Control

- Only authorized users can send notifications
- Audit log of all notification sends
- Role-based notification permissions

---

## Configuration

### Environment Variables

```bash
# Email (SMTP)
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=notifications@example.com
SMTP_PASSWORD=secure_password
SMTP_FROM_EMAIL=noreply@example.com
SMTP_FROM_NAME=School Management

# SMS (Netgsm)
SMS_API_URL=https://api.netgsm.com
SMS_USERNAME=username
SMS_PASSWORD=password
SMS_HEADER=SCHOOL

# WhatsApp (Meta)
WHATSAPP_API_URL=https://graph.facebook.com
WHATSAPP_ACCESS_TOKEN=access_token
WHATSAPP_PHONE_NUMBER_ID=phone_number_id

# Worker Settings
NOTIFICATION_WORKER_POLL_INTERVAL=30
NOTIFICATION_MAX_RETRIES=3
```

### Database Configuration

Provider settings stored in `integration_settings` table:
```json
{
  "integration_type": "smtp",
  "provider_name": "default",
  "settings": {
    "smtp_host": "smtp.example.com",
    "smtp_port": 587,
    "smtp_user": "notifications@example.com",
    "smtp_password": "encrypted_password",
    "from_email": "noreply@example.com",
    "from_name": "School Management"
  },
  "is_active": true
}
```

---

## Testing

### Unit Tests

```python
import pytest
from app.infrastructure.notifications.email_provider import EmailProvider

def test_email_provider_send():
    config = {
        "smtp_host": "localhost",
        "smtp_port": 1025,  # Test SMTP server
        "smtp_user": "test",
        "smtp_password": "test",
        "from_email": "test@example.com",
        "from_name": "Test"
    }
    provider = EmailProvider(config)
    
    result = await provider.send(
        recipient="recipient@example.com",
        subject="Test Subject",
        body="Test Body"
    )
    
    assert result["success"] is True
```

### Integration Tests

```python
@pytest.mark.asyncio
async def test_notification_flow():
    # Create notification job
    job = create_notification_job(...)
    
    # Process job
    await worker.process_job(job, db)
    
    # Verify job status
    assert job.status == "SENT"
    assert job.sent_at is not None
```

---

## Future Enhancements

### Planned Features

1. **Webhook Support:** Allow external systems to send notifications
2. **Template Editor:** UI for creating and editing templates
3. **Notification Preferences:** User-level notification preferences
4. **Bulk Sending:** Optimized bulk notification sending
5. **Analytics Dashboard:** Visualization of notification metrics
6. **Multi-language Support:** Templates in multiple languages
7. **Attachment Support:** Send attachments with emails
8. **Scheduled Notifications:** Advanced scheduling options

<!-- SCS360_SOURCE_END: 16 -->

---

<a id="belge-17"></a>

## 17. docs/SATIS_ONCESI_KABUL_2026-11-02.md

Kaynak: [docs/SATIS_ONCESI_KABUL_2026-11-02.md](docs/SATIS_ONCESI_KABUL_2026-11-02.md)  
SHA-256: `449220a124149ad908cc12c2c98915c90e9e2663366156510c4daa8dfc516ed0`

<!-- SCS360_SOURCE_BEGIN: 17 -->
# Satış öncesi kabul durumu — 2 Kasım 2026

> Sonraki test ve yerel çalıştırma turu: [3 Kasım 2026 — 79 backend, 78 frontend, 7 tarayıcı senaryosu](TEST_VE_CALISTIRMA_2026-11-03.md). Aşağıdaki sonuçlar bu belgenin önceki kabul anını kaydeder.

**Durum: bu turdaki kod düzeltmeleri ve aşağıdaki yerel kabul testleri tamamlandı; canlı satış/üretim kabulü bekliyor.** Hedef sunucu, gerçek sağlayıcı hesapları ve fiziksel mobil cihaz kabulü olmadan “tüm API ve butonlar koşulsuz sorunsuz” onayı verilmemiştir. Bu rapor önceki aynı tarihli kabul raporunun yerini alır.

## Doğrulanan sonuçlar

| Kontrol | Sonuç | Kanıt / kapsam |
|---|---|---|
| Backend | **79 test geçti** | SCS360 sürümünde SQLite ve PostgreSQL üzerinde çift çalıştırılan entegrasyon senaryoları dahil; tüm 79 testin her iki veritabanında ayrı ayrı çalıştığı anlamına gelmez. [Test kaydı](../output/scs360-backend-tests.log) |
| Frontend | **73 test geçti** | Menü/izin, bağlantı sözleşmeleri ve eski oturumların SCS360 anahtarına taşınması dahil. [Test kaydı](../output/scs360-frontend-tests.log) |
| Üretim derlemesi | **Başarılı** | TypeScript + Vite. Ana paket yaklaşık 906 kB; paket boyutu uyarısı sürüyor. [Derleme kaydı](../output/scs360-frontend-build.log) |
| Gerçek tarayıcı | **5 senaryo geçti** | SCS360 + Edge + PostgreSQL: yönetici menüleri, 390×844 veli ekranı/chatbot yönlendirmesi, ödev oluşturma/yeniden yükleme/detay, iki ayrı oturumda veli–öğretmen mesajlaşması ve dosyalı ödev yükleme/indirme/notlandırma. [Kayıt](../output/scs360-browser-acceptance.log), [HTML raporu](../frontend/playwright-report/index.html), [mobil sohbet görüntüsü](../output/chat-acceptance-mobile.png) |
| Rol bazlı GET taraması | **1.815 istek** | 11 mevcut rol × 165 adres: **1.149 adet 200, 666 adet 403; 500/404/401 yok**. Kaynak SQLite veritabanının geçici kopyasında. [Ham sonuçlar](api-smoke-results.json) |
| Temiz PostgreSQL 16 | **Başarılı** | Boş veritabanında tüm migration'lar ve ilk kurum/şube/yönetici kurulumu; başlık **027**. [Migration kaydı](../output/clean-postgres-install.log) |
| PostgreSQL yedekten dönüş | **Başarılı** | Ayrı veritabanına pg_dump/pg_restore; kullanıcı, öğrenci, veli, ödev, mesaj, tahsilat sayımları ve 027 başlığı eşleşti. Kabul verisinde tahsilat sayısı sıfırdır. [Karşılaştırma](postgres-restore-acceptance.json) |
| Python üretim bağımlılıkları | **Bilinen açık yok** | Bu tarihteki pip-audit sonucu. [Rapor](python-dependency-audit.json) |
| Frontend üretim bağımlılıkları | **Bilinen açık yok** | npm audit --omit=dev. [Rapor](frontend-production-dependency-audit.json) |
| Geliştirme bağımlılıkları | **12 orta seviye bulgu açık** | ESLint/minimatch zinciri; yüksek/kritik bulgu yok. Uyumsuz sürüm zorlaması yapılmadı. [Tam rapor](frontend-all-dependency-audit.json) |
| Tanımsız değişken taraması | **Temiz** | Ruff F821/F823; bütün proje için tam stil/lint temizliği anlamına gelmez. |

GET taraması dinamik kayıt adreslerini, zorunlu parametreli istekleri, export/indirme ve harici sağlayıcı adreslerini kapsamaz. Yazma işlemlerinin bir bölümü ayrı entegrasyon ve tarayıcı testindedir. 403 yanıtları erişimin reddedildiğini gösterir; her özel rolün işletmenin nihai politikasına uygunluğunu tek başına kanıtlamaz. Geçersiz oturumda 401, yetkisiz işlemde 403, bulunamayan kayıtta 404 korunmuştur.

## Önceki kabul maddelerinde yapılanlar

| Önceki madde | Uygulanan değişiklik | Kalan kabul |
|---|---|---|
| Veli portalında örnek veriler | Notlar, program, ödev, materyal, iletişim, duyuru, kulüp/aktivite, haftalık rapor ve öğretmen listeleri gerçek, ilişkili kayıtlardan okunuyor. Kayıt yoksa boş sonuç gösteriliyor. | Kurumun gerçek veri setiyle iş kabulü |
| Bellek içi operasyonlar | Ödev/teslim, günlük rapor, outbox, veli bildirimi, görev, personel izni, sınıf programı, kantin cüzdanı, cihaz token'ı ve okundu bilgisi kalıcı kaynaklara bağlandı. Kitap ve randevu kalıcılığı korundu. | Kapsam dışı kalan dinamik formlar ve dosya akışları için ek kabul |
| Rol ve kurum izolasyonu | Ortak kimlik/yetki bağlamı, ORM kurum/şube/öğrenci sınırları, yazma kontrolleri, yetki kataloğu ve negatif testler eklendi. Veli–çocuk, öğretmen–sınıf ve doğrudan öğretmen–öğrenci ataması kullanılıyor. | Özel rollerin işletme tarafından eşleştirilmesi; tüm endpoint'ler için bağımsız güvenlik incelemesi |
| Tarayıcı kabulü | Beş gerçek Edge senaryosu ve mobil ekran genişliği doğrulandı; sohbet, chatbot ve dosyalı ödev teslimi/notlandırma dahil. | Her form/buton, erişilebilirlik ve fiziksel Android/iOS kabulü |
| Üretim altyapısı ve sağlayıcılar | Temiz PostgreSQL, ilk yönetici kurulumu ve geri yükleme geçti. Docker dosyaları, üretim ortam örnekleri, migration başlangıcı ve hazır olma kontrolü hazırlandı. Ödeme/bildirim sağlayıcı protokolleri düzeltildi. | Docker hedef ortamı, HTTPS, gerçek LLM, ödeme ve teslimat kabulü |

## Başlıca davranış düzeltmeleri

- Chatbot belirsiz LLM sınıflandırmasında güçlü kural eşleşmesine dönebiliyor. Zaman aşımı/hata geri dönüşü test edildi. Genel sohbet yanlışlıkla bir işlem sayfasına yönlenmiyor; “notlarım” ardından “Detayları aç” doğru veli not sayfasına gidiyor. Tarayıcı testinde test sağlayıcısı kullanıldı; gerçek LLM gecikmesi/doğruluğu ayrıca ölçülmeli.
- Öğretmen sohbetinin olmayan model alanları ve hatayı başarılı boş yanıtla gizlemesi kaldırıldı. Öğretmen/yönetici ve veli aynı öğrenciye ait kalıcı görüşmeyi kullanıyor. Bir öğrenciye bağlı birden fazla veli kullanıcı hesabı seçilebiliyor; kardeşlerin görüşmeleri ayrılıyor. Çift /api adresi, mobil pencere taşması ve chatbot düğmesinin gönder düğmesini kapatması düzeltildi.
- Ödev oluşturma ve değerlendirme yetkileri ayrıldı; sınıf ataması kontrol ediliyor. Taslak ödev veliden gizleniyor; notlandırılmış teslim yeniden yazılamıyor. Dosya içeriği ayrı özel depolamaya kaydediliyor, yetkili indirme ve öğretmen notlandırma ekranları eklendi. SQLite/PostgreSQL HTTP testinde dosya baytları, oturumlar arasında kalıcılık, yabancı öğrenci reddi, tür/boyut sınırları ve notlandırma sonrası değiştirme engeli doğrulandı.
- Randevu çakışması kalıcı kayıtlarda kontrol ediliyor. Saat dilimsiz web girdisi İstanbul yerel saati olarak alınıyor; uygun saat hesaplamasında ve liste tarih/saat alanlarında saat dilimi hatası giderildi. [Son ek doğrulama](../output/appointment-timezone-final.log) SQLite ve PostgreSQL'de geçti.
- Outbox yalnız sağlayıcının olumlu yanıtından sonra gönderildi oluyor. Eksik/kapalı sağlayıcı sahte başarı üretmiyor. Worker kaydı atomik kiralıyor, alıcı sonucunu saklıyor, yeniden denemede başarılı alıcıları koruyor. Harici gönderim ile yerel kayıt arasındaki süreç çökmesi için mutlak “tam bir kez teslim” garantisi verilmez.
- iyzico örnek anahtar/alıcı/URL üretimi kaldırıldı. Yetkili borç için gerçek checkout isteği hazırlanıyor; callback sağlayıcıdan sorgulanıp imza, token, sepet, para birimi ve tutarla doğrulanıyor. Tekrarlanan callback ikinci tahsilat yaratmıyor. Bu senaryonun testinde sahte ağ sağlayıcısı kullanıldı; gerçek sandbox ödemesi yapılmadı.
- Finans, kantin, gider ve dashboard tutarları gerçek kayıtlardan okunuyor. Cüzdanda hayalî bakiye üretilmiyor; bakiye/günlük limit aşımı ve nakit işlemi ayrılıyor. Yapay not/akran yüzdeleri gibi kanıtsız AI değerleri kaldırıldı veya veri yok olarak gösteriliyor.
- Öğrenci/veli/sınıf/kurum/şube/kitap/kantin/borç içe aktarmaları gerçek kayıt oluşturuyor; hatalı satır ayrı raporlanıyor. Rapor dışa aktarımlarında gerçek satırlar ve formül enjeksiyonu koruması kullanılıyor.
- JWT kütüphanesi PyJWT'ye geçirildi; izin verilen algoritma ve zorunlu süre/kimlik/tür iddiaları doğrulanıyor. Şifre sıfırlama gerçek bildirim kuyruğuna yazılıyor; token içeren içerik outbox ayrıntısında maskeleniyor.
- Aynı yöntem/adresteki router çakışmaları, statik/dinamik adres sırası ve OpenAPI kimlikleri düzeltildi. Mobil hata yanıtlarında durum kodu ve request_id korunuyor; genel sunucu hatası SQL ayrıntısını istemciye açmıyor.

## Veri ve kurulum durumu

Yerel SQLite veritabanı 027 başlığında. Önceki 021–022 işlemleri öncesindeki yedek: backend/school_management.before-release-20261102.db. Sonraki kalıcılık migration'larından önceki yedek: backend/school_management.before-parent-outbox-20261102.db. Eski UUID biçimleri uyumluluk sorgularıyla okunuyor; mevcut veri topluca silinmedi veya birleştirilmedi.

Eski veride geçersiz/tekrarlı kimlikler ve kurum–öğrenci numarası çakışmaları bulundu. Temiz PostgreSQL kabulü bu SQLite verisinin tamamının taşındığını göstermez. Satış verisine geçişte gerçek kayıtların ayrıca temizlenip mutabakatının yapılması gerekir.

Test PostgreSQL kümesi yalnız 127.0.0.1:55436 üzerinde ayrı bir dizinde çalıştırıldı; mevcut PostgreSQL Windows servislerine müdahale edilmedi. Kabul kullanıcıları yalnız bu test veritabanındadır. Kullanıcı dosyaları ve önceden var olan çalışma ağacı değişiklikleri korunmuştur.

## Canlı satış kabulü için kalanlar

1. Gerçek sunucu/alan adı, HTTPS ve Docker imajları hedef ortamda doğrulanmalı. Bu bilgisayarda Docker motoru yok; imaj çalıştırma kabulü yapılmadı. Hedef kullanıcı/eşzamanlılık yük testi ve izleme/geri dönüş provası tamamlanmadı.
2. SMTP, Netgsm, WhatsApp, iyzico ve gerçek LLM erişimi yapılandırılıp yetkili test alıcısı/sandbox üzerinden uçtan uca doğrulanmalı. Hesap bilgileri bulunmadığı için gerçek ileti veya ödeme yapılmadı. Android/iOS push teslimatı ve kurum başına ayrı sağlayıcı hesabı kabulü de yapılmadı.
3. İşletmenin özel rol politikasıyla tüm dinamik formlar, işlem butonları, dosya ve dışa aktarma akışları kabul edilmeli. Tarayıcı senaryoları tüm butonların test edildiği anlamına gelmez. Ödev dosyaları için yeni özel depolama hacmi hedef ortamda bağlanıp yedekten geri dönüş provası yapılmalı; PostgreSQL dump testi tek başına dosya içeriğini kapsamaz.
4. Fiziksel Android/iOS cihazında oturum yenileme, API hataları, ödeme dönüşü, dosyalar ve bildirim kabulü yapılmalı. Mobil uygulama kodu veya mağaza dağıtımı bu çalışma kapsamında geliştirilmedi.
5. Geliştirme bağımlılıklarındaki 12 orta seviye bulgu ve büyük frontend paketinin iyileştirmesi izlenmeli; eski SQLite verisinin üretim geçişi ayrıca mutabık kalınmalı.

[Yerel tam ön kontrol](release-preflight-local.json) beklenen şekilde ready=false: çalışma ortamı geliştirme/SQLite ve sağlayıcılar eksik. [Ayrı üretim ayarlı PostgreSQL ön kontrolü](release-preflight-acceptance.json) application_only kapsamında ready=true; bu dosyada da sağlayıcılar kapalı ve gerçek teslimat kabulü bekliyor. Ön kontrol sonucu ticari/canlı kabul yerine geçmez.

## Yeniden doğrulama

Backend dizininde sanal ortam Python'u ile:

```powershell
python -m pytest -q
python -m ruff check app --select F821,F823
python scripts/audit_api_smoke.py
python scripts/export_openapi.py
python scripts/release_preflight.py --require-integrations
```

PostgreSQL entegrasyon vakalarının da çalışması için TEST_POSTGRES_URL ayrı, yalnız kabul amaçlı bir scs360_acceptance veritabanına ayarlanmalıdır. Bu değişken olmadan PostgreSQL vakaları atlanır.

Frontend dizininde:

```powershell
npm test
npm run build
npm run test:e2e
npm audit --omit=dev
```

Tarayıcı test sunucusu varsayılan olarak geçici SQLite kullanır. PostgreSQL kabulü için ACCEPTANCE_DATABASE_URL yalnız ayrı scs360_acceptance veritabanına ayarlanır. Üretim veritabanı bu değişkenlere verilmemelidir.

Güncel kurulum, sağlayıcı ve mobil API adımları: [Üretim kurulumu ve mobil bağlantı](URETIM_KURULUMU_VE_MOBIL.md). Güncel istemci sözleşmesi: [openapi.json](openapi.json).

<!-- SCS360_SOURCE_END: 17 -->

---

<a id="belge-18"></a>

## 18. docs/SCS360_MARKA.md

Kaynak: [docs/SCS360_MARKA.md](docs/SCS360_MARKA.md)  
SHA-256: `885b435b5209cd38d1da93bbe2f4cad5e7eb8acea3cbc2a77cdfc2bcbdcfb8f4`

<!-- SCS360_SOURCE_BEGIN: 18 -->
# SCS360 logo kullanımı

Sembol, eğitimi temsil eden açık kitabı ve okulun tüm operasyonlarını çevreleyen 360 derece bağlantı yörüngesini birleştirir. Yörüngedeki nokta, sistemdeki bağlantıyı ve devamlılığı temsil eder.

## Dosyalar

- `frontend/public/scs360-mark.svg`: uygulama içindeki ana sembol; 64×64 vektör çizim.
- `frontend/public/scs360-logo.svg`: açık zemin için yatay logo.
- `frontend/public/scs360-logo-dark.svg`: koyu zemin için yatay logo.
- `frontend/public/scs360-icon-32.png`: küçük tarayıcı simgesi.
- `frontend/public/scs360-apple-touch-icon.png`: mobil ana ekran simgesi.
- `output/branding`: SVG kopyaları, şeffaf PNG ve önizleme.
- `backend/app/infrastructure/pdf/assets/scs360-mark.png`: aynı SVG'den üretilen PDF baskı görseli.

Uygulama başlıkları ortak `Brand`/`BrandMark`, basılı belgeler `ReceiptBrand` bileşenini kullanır. Sembol giriş, menü, chatbot, tarayıcı sekmesi, mobil simge, rapor ve makbuzlarda kullanılır. Kurumun yasal adı ve belge bilgileri ayrıca korunur.

## Renkler

| Kullanım | Renk |
|---|---|
| Petrol yeşili ana zemin | `#163B3B` |
| Yörünge / bağlantı noktası | `#F1BD70` |
| Kitap sol sayfa | `#FBF7E9` |
| Kitap sağ sayfa | `#84CBB4` |
| Açık zemin yazı vurgusu | `#176B5B` |

Vektörün oranlarını koruyun. Sembolü esnetmeyin; dar alanlarda yatay logo yerine sembolü kullanın. SVG güncellenirse PNG karşılıklarını ve PDF görselini aynı kaynaktan yeniden üretin.

<!-- SCS360_SOURCE_END: 18 -->

---

<a id="belge-19"></a>

## 19. docs/SECURITY_PLAN.md

Kaynak: [docs/SECURITY_PLAN.md](docs/SECURITY_PLAN.md)  
SHA-256: `0e2ea3caa24df931fa0d5d1beeefbbe52ed88c9c8914d191bda04fe9b92edc54`

<!-- SCS360_SOURCE_BEGIN: 19 -->
# Security Plan

## Overview

This document outlines the comprehensive security strategy for the School Management System, covering authentication, authorization, data protection, and operational security.

---

## Authentication Security

### JWT Token Management

**Access Token:**
- Algorithm: HS256
- Expiration: 30 minutes
- Storage: HttpOnly cookie or localStorage (with XSS protection)
- Payload: User ID, organization ID, permissions, expiration

**Refresh Token:**
- Algorithm: HS256
- Expiration: 7 days
- Storage: HttpOnly cookie
- Rotation: On every refresh
- Revocation: Database-backed with expiration tracking

**Token Security:**
```python
# Token generation
def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

def create_refresh_token(user_id: str) -> str:
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    token_data = {
        "sub": user_id,
        "exp": expire,
        "type": "refresh",
        "jti": str(uuid4())  # Unique token ID
    }
    token = jwt.encode(token_data, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    
    # Store in database for revocation
    store_refresh_token(user_id, token, expire)
    return token
```

### Password Security

**Password Requirements:**
- Minimum length: 8 characters
- Must include: uppercase, lowercase, number, special character
- No common passwords (check against breached passwords list)
- No personal information (name, email, etc.)

**Password Hashing:**
```python
import bcrypt

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )
```

**Password Reset Flow:**
1. User requests reset with email
2. Generate secure token (UUID + timestamp)
3. Send email with reset link (valid 1 hour)
4. User sets new password
5. Invalidate all existing refresh tokens
6. Log password reset event

### Login Attempt Tracking

**Implementation:**
```python
# Track failed login attempts
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION = 30  # minutes

def track_login_attempt(email: str, success: bool):
    if success:
        # Reset counter on successful login
        reset_login_counter(email)
    else:
        # Increment counter
        attempts = increment_login_counter(email)
        if attempts >= MAX_LOGIN_ATTEMPTS:
            lock_user_account(email, LOCKOUT_DURATION)
            send_lockout_notification(email)
```

---

## Authorization Security

### Role-Based Access Control (RBAC)

**Role Hierarchy:**
1. Super Admin - Full system access
2. Kurum Admini - Organization-level access
3. Şube Yetkilisi - Branch-level access
4. Öğretmen - Class-level access
5. Muhasebe - Finance module access
6. Personel - Limited access

**Permission Matrix:**
- Granular permissions for each action
- Permission inheritance from roles
- Permission checking at every protected endpoint

**Implementation:**
```python
from functools import wraps
from fastapi import HTTPException, Depends

def require_permission(permission: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, current_user: User = Depends(get_current_user), **kwargs):
            if not has_permission(current_user, permission):
                raise HTTPException(status_code=403, detail="Insufficient permissions")
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def has_permission(user: User, permission: str) -> bool:
    user_permissions = get_user_permissions(user.id)
    return permission in user_permissions
```

### Organization and Branch Isolation

**Multi-tenancy Strategy:**
- Every request includes organization context
- Database queries filtered by organization_id
- Branch-level data filtered by branch_id
- Cross-organization access prevention

**Implementation:**
```python
# Tenant resolver middleware
async def get_current_organization(
    request: Request,
    current_user: User = Depends(get_current_user)
) -> Organization:
    organization_id = request.headers.get("X-Organization-ID")
    if not organization_id:
        organization_id = current_user.organization_id
    
    organization = get_organization(organization_id)
    if not organization or organization.id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Invalid organization")
    
    return organization

# Branch scope filter
def apply_branch_filter(query: Query, user: User) -> Query:
    if user.role not in ["Super Admin", "Kurum Admini"]:
        user_branches = get_user_branches(user.id)
        query = query.filter(Branch.id.in_(user_branches))
    return query
```

---

## Data Protection

### Sensitive Data Handling

**Data Classification:**
- **Public:** Organization name, general info
- **Internal:** User names, roles, class info
- **Confidential:** Student personal data, financial data
- **Restricted:** Passwords, API keys, secrets

**Encryption at Rest:**
- Database: PostgreSQL with TLS
- File storage: Encrypted volumes
- Backups: Encrypted with GPG

**Encryption in Transit:**
- TLS 1.2/1.3 for all connections
- Certificate pinning for API calls
- HTTPS only in production

### Financial Data Security

**Transaction Safety:**
```python
from decimal import Decimal
from sqlalchemy import text

@transaction.atomic
def process_payment(payment_data: PaymentCreate):
    # Validate amount
    if payment_data.amount <= 0:
        raise ValueError("Amount must be positive")
    
    # Check debt exists and belongs to user's organization
    debt = get_debt(payment_data.debt_id)
    validate_debt_ownership(debt, current_user)
    
    # Check payment doesn't exceed remaining debt
    if payment_data.amount > debt.remaining_amount:
        raise ValueError("Payment exceeds remaining debt")
    
    # Create payment
    payment = create_payment(payment_data)
    
    # Create receipt (immutable)
    receipt = create_receipt(payment)
    
    # Update debt
    update_debt_paid_amount(debt.id, payment.amount)
    
    # Audit log
    log_financial_transaction(payment, receipt)
    
    return payment
```

**Audit Trail:**
- All financial transactions logged
- Before/after values recorded
- User and timestamp tracked
- Immutable audit logs

### Personal Data Protection (GDPR Compliance)

**Data Minimization:**
- Collect only necessary data
- Regular data review and cleanup
- Data retention policies

**Right to be Forgotten:**
- Soft delete with anonymization
- Complete deletion after retention period
- Export data on request

**Data Portability:**
- Export functionality for user data
- Standard formats (JSON, CSV)
- Secure transfer mechanisms

---

## API Security

### Input Validation

**Pydantic Schemas:**
```python
from pydantic import BaseModel, Field, validator

class StudentCreate(BaseModel):
    first_name: str = Field(..., min_length=2, max_length=100)
    last_name: str = Field(..., min_length=2, max_length=100)
    email: Optional[EmailStr]
    phone: Optional[str] = Field(None, regex=r'^\+?[0-9]{10,15}$')
    
    @validator('first_name', 'last_name')
    def name_must_not_contain_numbers(cls, v):
        if any(char.isdigit() for char in v):
            raise ValueError('Name must not contain numbers')
        return v
```

### SQL Injection Prevention

**ORM Usage:**
- Always use SQLAlchemy ORM
- Never use raw SQL with user input
- Parameterized queries for raw SQL when necessary

**Example:**
```python
# Safe
students = session.query(Student).filter(
    Student.organization_id == org_id,
    Student.branch_id == branch_id
).all()

# Unsafe - NEVER DO THIS
query = f"SELECT * FROM students WHERE organization_id = '{org_id}'"
session.execute(query)
```

### XSS Prevention

**Frontend:**
- React auto-escapes JSX
- DOMPurify for HTML content
- Content Security Policy (CSP) headers

**Backend:**
- Sanitize user input
- Escape output in templates
- Use safe rendering methods

### CORS Configuration

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://app.schoolmanagement.com",
        "https://staging.schoolmanagement.com"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)
```

### Rate Limiting

**Implementation:**
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/api/auth/login")
@limiter.limit("10/minute")
async def login(request: Request, credentials: LoginSchema):
    # Login logic
    pass

@app.get("/api/students")
@limiter.limit("100/minute")
async def get_students(request: Request):
    # Get students logic
    pass
```

---

## File Upload Security

### File Validation

**Validation Rules:**
```python
ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png', 'docx'}
ALLOWED_MIME_TYPES = {
    'application/pdf',
    'image/jpeg',
    'image/png',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

def validate_file(file: UploadFile):
    # Check extension
    file_ext = file.filename.split('.')[-1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise ValueError("Invalid file type")
    
    # Check MIME type
    file_content = file.file.read(1024)
    file.file.seek(0)
    mime_type = magic.from_buffer(file_content, mime=True)
    if mime_type not in ALLOWED_MIME_TYPES:
        raise ValueError("Invalid MIME type")
    
    # Check file size
    file.file.seek(0, os.SEEK_END)
    file_size = file.file.tell()
    file.file.seek(0)
    if file_size > MAX_FILE_SIZE:
        raise ValueError("File too large")
```

### Secure File Storage

**Storage Strategy:**
- Random filenames (UUID)
- Separate storage directory
- No direct file access (serve through application)
- Virus scanning on upload

**Implementation:**
```python
import uuid
import os

def save_uploaded_file(file: UploadFile, upload_dir: str) -> str:
    # Generate random filename
    file_ext = file.filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{file_ext}"
    
    # Create secure path
    file_path = os.path.join(upload_dir, filename)
    
    # Save file
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Scan for viruses
    if not scan_file_for_viruses(file_path):
        os.remove(file_path)
        raise ValueError("File contains virus")
    
    return filename
```

---

## Logging and Monitoring

### Structured Logging

**Implementation:**
```python
import structlog

logger = structlog.get_logger()

def log_security_event(event_type: str, user_id: str, details: dict):
    logger.info(
        "security_event",
        event_type=event_type,
        user_id=user_id,
        timestamp=datetime.utcnow().isoformat(),
        details=details
    )
```

**Log Levels:**
- DEBUG: Development information
- INFO: Normal operations
- WARNING: Security concerns
- ERROR: Errors and failures
- CRITICAL: Security incidents

### Security Event Logging

**Events to Log:**
- Login attempts (success/failure)
- Permission denials
- Data access (sensitive data)
- Configuration changes
- Financial transactions
- File uploads/downloads
- Password changes
- Token refresh/revocation

### Monitoring and Alerting

**Metrics to Monitor:**
- Failed login attempts
- Permission denials
- Unusual data access patterns
- API error rates
- Response time anomalies
- Failed transactions

**Alert Triggers:**
- > 10 failed logins from same IP in 5 minutes
- > 50 permission denials in 1 hour
- Unusual data export activity
- Financial transaction failures
- Database connection failures

---

## Secrets Management

### Environment Variables

**Sensitive Data in .env:**
```bash
# Never commit .env to version control
JWT_SECRET_KEY=your-secret-key-here
DATABASE_URL=postgresql://user:password@host:port/db
SMTP_PASSWORD=smtp-password
SMS_API_KEY=sms-api-key
WHATSAPP_ACCESS_TOKEN=whatsapp-token
```

### Secrets Storage

**Production Options:**
- HashiCorp Vault
- AWS Secrets Manager
- Azure Key Vault
- Docker Secrets (for containers)

**Implementation:**
```python
import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY")
    DATABASE_URL: str = os.getenv("DATABASE_URL")
    
    def __init__(self):
        if not self.JWT_SECRET_KEY:
            raise ValueError("JWT_SECRET_KEY not set")
```

---

## Network Security

### Firewall Rules

**Allowed Ports:**
- 80/443: HTTP/HTTPS (Nginx)
- 22: SSH (restricted IPs only)
- 5432: PostgreSQL (internal only)

**Blocked Ports:**
- All other ports

### SSL/TLS Configuration

**Nginx SSL Config:**
```nginx
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
ssl_prefer_server_ciphers on;
ssl_session_cache shared:SSL:10m;
ssl_session_timeout 10m;
```

### DDoS Protection

**Mitigation Strategies:**
- Rate limiting
- IP blocking
- Cloudflare or similar service
- Request size limits

---

## Dependency Security

### Vulnerability Scanning

**Tools:**
- Safety (Python)
- Snyk
- Dependabot
- Trivy (Docker images)

**Process:**
- Weekly automated scans
- Immediate scan on new dependencies
- Manual review before production deployment

### Dependency Updates

**Strategy:**
- Regular dependency updates
- Security patches immediately
- Major version updates with testing
- Changelog review

---

## Backup and Recovery Security

### Secure Backups

**Backup Encryption:**
```bash
# Encrypt backup with GPG
gpg --symmetric --cipher-algo AES256 backup.sql

# Decrypt backup
gpg --decrypt backup.sql.gpg > backup.sql
```

**Backup Storage:**
- Encrypted at rest
- Offsite storage
- Access logging
- Regular restoration testing

### Disaster Recovery

**Recovery Plan:**
1. Assess damage and scope
2. Restore from latest clean backup
3. Verify data integrity
4. Bring systems online
5. Monitor for anomalies
6. Document incident

---

## Security Testing

### Penetration Testing

**Testing Areas:**
- Authentication bypass
- Authorization flaws
- SQL injection
- XSS vulnerabilities
- CSRF protection
- File upload vulnerabilities
- API security
- Network security

**Schedule:**
- Quarterly penetration tests
- After major changes
- Before production deployment

### Code Review

**Security Review Checklist:**
- Input validation
- Output encoding
- Authentication/authorization
- Error handling
- Logging (no sensitive data)
- Dependency vulnerabilities
- Configuration security

---

## Incident Response

### Incident Response Plan

**1. Detection:**
- Monitor security alerts
- Analyze logs
- Identify scope

**2. Containment:**
- Isolate affected systems
- Block malicious IPs
- Disable compromised accounts

**3. Eradication:**
- Remove malware
- Patch vulnerabilities
- Update configurations

**4. Recovery:**
- Restore from clean backups
- Verify system integrity
- Monitor for recurrence

**5. Lessons Learned:**
- Document incident
- Update procedures
- Train team

### Security Team Contacts

- **Security Lead:** security@schoolmanagement.com
- **CTO:** cto@schoolmanagement.com
- **Incident Response:** incidents@schoolmanagement.com

---

## Compliance

### GDPR Compliance

**Requirements:**
- Data protection by design
- Data subject rights
- Breach notification (72 hours)
- Data protection officer
- Privacy policy
- Cookie consent

### SOC 2 Compliance

**Trust Service Criteria:**
- Security
- Availability
- Processing integrity
- Confidentiality
- Privacy

---

## Security Checklist

### Pre-Deployment Checklist
- [ ] All secrets are in environment variables
- [ ] SSL/TLS certificates valid
- [ ] Database backups tested
- [ ] Security scans passed
- [ ] Dependencies updated
- [ ] Firewall rules configured
- [ ] Monitoring enabled
- [ ] Logging configured
- [ ] Rate limiting enabled
- [ ] CORS configured correctly

### Ongoing Security Tasks
- [ ] Weekly dependency scans
- [ ] Monthly security reviews
- [ ] Quarterly penetration tests
- [ ] Regular backup testing
- [ ] Security training for team
- [ ] Update incident response plan
- [ ] Review access logs
- [ ] Update security documentation

<!-- SCS360_SOURCE_END: 19 -->

---

<a id="belge-20"></a>

## 20. docs/TEKNIK_DURUM_2026-11-02.md

Kaynak: [docs/TEKNIK_DURUM_2026-11-02.md](docs/TEKNIK_DURUM_2026-11-02.md)  
SHA-256: `dfa7500e6421e5b141c65a5cc462d9f61851f5e36d49e85f6df5c5e81b1d0a31`

<!-- SCS360_SOURCE_BEGIN: 20 -->
# Teknik durum — 2 Kasım 2026

> Bu belge önceki doğrulama turunun tarihsel kaydıdır. Güncel sonuçlar ve açık kabul maddeleri [satış öncesi kabul raporundadır](SATIS_ONCESI_KABUL_2026-11-02.md).

## Doğrulanan sonuçlar

- Backend: `python -m pytest -q --disable-warnings` — 29 test geçti.
- Frontend: `npm test -- --run` — 4 dosyada 21 test geçti.
- Frontend: `npm run build` — TypeScript kontrolü ve Vite derlemesi başarılı.
- `ruff check app --select F821,F823` — tanımsız/değer atanmamış değişken hatası yok.
- `pip check` — kurulu Python bağımlılıklarında çatışma yok.
- `alembic heads` — tek başlık: 020. Bu kontrol migration'ların boş PostgreSQL üzerinde uygulanabildiğini doğrulamaz.

## Bu incelemede giderilen hatalar

- Ortak yanıt fonksiyonuna `success=False` gönderen çok sayıdaki endpoint'in TypeError üretmesi giderildi. Mevcut JSON sözleşmesi korundu.
- Sınıf, dashboard, sınav, materyal, ders programı, güvenlik, öğrenci ve operasyon endpoint'lerinde eksik importlar tamamlandı.
- Borç listesinde sorgu sonucunun yanlış değişkenden okunması düzeltildi.
- Ödev oluşturmada geçersiz `UUID.uuid4()` çağrısı düzeltildi.
- Chatbot takip mesajı yalnızca kısa, bağlama bağlı komutlarda önceki konuyu kullanıyor. Yeni konu içeren “Borçları göster” mesajının notlar konusunu devralması önlendi; borç eşleştirmesi genişletildi.
- Güven puanının sabit değerine bağlı kırılgan testler, geçerli aralık ve niyet davranışını denetleyecek şekilde güncellendi. Konu değişimi ve hata yanıtı için regresyon testleri eklendi.
- Ollama varsayılan OpenAI uyumlu adresine `/v1` eklendi.
- Eksik backend ve frontend Dockerfile dosyaları oluşturuldu. Sağlık kontrolü curl yerine Python standart kitaplığını kullanıyor.
- Docker Compose backend/worker bağlantısı konteyner içi PostgreSQL adresine bağlandı; kök ortamda DATABASE_URL ile değiştirilebilir.
- Nginx `/ready` yönlendirmesi gerçek `/api/ready` endpoint'ine düzeltildi.

## Üretim öncesi tamamlanması gereken işler

1. `backend/app/routers/parent_portal.py`: not, ders programı, ödev, materyal, iletişim, duyuru, etkinlik ve haftalık rapor bölümlerinde örnek veri blokları var. Veritabanına bağlı sorgulara ve öğrenci/kurum erişim testlerine dönüştürülmeli.
2. `backend/app/routers/homework.py` ve `outbox.py`: bellek içi kayıtlar yeniden başlatmada kaybolur. Kalıcı veri modeli, migration ve kurum/şube kapsamı gerekir. Ayrı ödev endpoint'leri farklı veri kaynakları kullanıyor.
3. Birden fazla router aynı HTTP yöntemini ve yolu kaydediyor. Özellikle `ai_analytics.py` ve ödeme/borç/öğrenci kayıtları incelenmeli. Çalışan ilk endpoint davranışı doğrulanmadan kopyaları silmek veri akışını değiştirebilir.
4. Ödeme iadesi/iptali, bildirim sağlayıcıları ve bazı PDF üretimleri için TODO alanları var. Gerçek sağlayıcı kimlik bilgileriyle sandbox kabul testleri yapılmalı; gerçek finansal işlem yapılmadı.
5. Docker çalıştırılabilir komutu bu ortamda bulunmadığından imajlar oluşturulup compose ayağa kaldırılarak doğrulanamadı. Yeni Dockerfile dosyaları uçtan uca Docker doğrulaması bekliyor. PostgreSQL şema başlangıcı ve migration zinciri temiz bir test veritabanında denenmeli.
6. Frontend ana JavaScript parçası için boyut uyarısı var; sayfa bazlı lazy loading uygulanabilir.
7. Testler tüm iş akışlarını kapsamıyor. Gerçek tarayıcıda rol bazlı öğrenci/veli/öğretmen, tahsilat, rapor ve chatbot gezinme kabul testleri henüz bu incelemede yapılmadı.
8. Çalışma ağacında inceleme öncesinden çok sayıda kaynak ve veritabanı değişikliği bulunuyor. Bunlar korunmuştur; sürüm kontrolüne alınmadan önce kullanıcı değişiklikleriyle birlikte gözden geçirilmelidir.

Bu rapor üretime hazır olunduğuna dair onay değildir. Testlerin geçmesi, örnek veri kullanan modüllerin tamamlandığı anlamına gelmez.

<!-- SCS360_SOURCE_END: 20 -->

---

<a id="belge-21"></a>

## 21. docs/TEST_VE_CALISTIRMA_2026-11-03.md

Kaynak: [docs/TEST_VE_CALISTIRMA_2026-11-03.md](docs/TEST_VE_CALISTIRMA_2026-11-03.md)  
SHA-256: `b156b239ace5e48fde278a10eca855030c547db5cad07a9d149a29a18a02cd0e`

<!-- SCS360_SOURCE_BEGIN: 21 -->
# SCS360 test ve yerel çalıştırma — 3 Kasım 2026

Yerel uygulama başlatıldı. Arayüz: http://127.0.0.1:5173 — API belgeleri: http://127.0.0.1:8000/api/docs. Servisler yalnız bu bilgisayardan erişilecek şekilde çalışıyor; bu işlem canlı sunucuya dağıtım değildir.

## Doğrulama sonuçları

| Kontrol | Sonuç | Kanıt |
|---|---|---|
| Backend | 106 test geçti; ilgili entegrasyon vakaları SQLite ve ayrı PostgreSQL kabul veritabanında çalıştı | [Kayıt](../output/continued-backend-20261103.log) |
| Frontend | 83 test geçti; chatbot, materyal işlemleri ve iptal edilmiş makbuz baskısı dahil | [Kayıt](../output/continued-frontend-20261103.log) |
| Edge tarayıcı | 9 senaryo geçti: önceki 7 akışa ek olarak gerçek materyal yükleme/veli indirmesi ve mazeret talebi/yönetici onayı | [Kayıt](../output/continued-browser-20261103.log) |
| ESLint | 0 hata, 0 uyarı | [JSON rapor](../output/continued-lint-20261103.json) |
| Üretim derlemesi | TypeScript ve Vite başarılı. Sayfalar ayrıldı; ana JavaScript paketi yaklaşık 911 kB'den 387 kB'ye indi, büyük paket uyarısı yok | [Kayıt](../output/continued-build-20261103.log) |
| Rol bazlı GET taraması | 11 rol, 165 adres, 1.815 istek: 1.141 adet 200 ve 674 adet 403; beklenmeyen 500/404/401 yok | [Kayıt](../output/continued-api-audit-20261103.log), [sonuçlar](api-smoke-results.json) |
| Çalışan yerel uygulama | Mevcut hesapla giriş, yönetim paneli, API proxy, personel öğrenci seçimi, chatbot hazır sorusu ve normal yanıt geçti; test oturumu kapatıldı | [Sonuç](../output/running-local-verification-20261103.json) |
| Bağımlılıklar / şema | pip check ve Ruff F821/F823 temiz; tüm npm ve üretim npm denetimleri 0 açık; yerel veritabanı 028 başlığında, yedek alınarak mevcut satır sayıları korunmuş | [Şema kaydı](../output/local-migration028-20261103.log), [npm raporu](frontend-all-dependency-audit.json) |

GET taraması dinamik kimlik isteyen adreslerin tamamını, tüm yazma işlemlerini veya bütün butonları kapsamaz. Yetkisiz erişimde 403 güvenlik gereğidir; 200 ile gizlenmedi. Otomatik kabul verileri ayrı test veritabanındadır. Yerel uygulama mevcut SQLite verisini kullanır; kullanıcı hesapları ve parolaları sıfırlanmadı.

## Düzeltilenler

- Materyal yükleme, indirme, kaldırma, teslim ve notlandırma gerçek kayıtlara bağlandı. Dosya boyutu/uzantısı/içeriği ve saklama yolu denetleniyor; veli yalnız izinli materyallere kimlik doğrulamayla erişiyor. Öğrenci dosyalarında geçersiz kategori 500 yerine doğrulama yanıtı veriyor.
- Mazeret talepleri kalıcı kaydediliyor; veli geçmişi ve yönetici onay/ret ekranları eklendi. Günlük pano istatistikleri gerçek kayıtlardan, seçilen şubeye göre hesaplanıyor. Bekleyen toplamı ilk 10 satırla sınırlanmıyor.
- Okul günü için `BUSINESS_TIMEZONE=Europe/Istanbul` eklendi. Pano ve materyal tarih kontrolleri sunucunun UTC/işletim sistemi saat dilimine bağlı değil.
- Toplu ileti API'sinde sahte alıcılar ve SENT kayıtları kaldırıldı; gerçek, tekrar etmeyen ve bildirim izni bulunan alıcılar kalıcı kuyruğa ekleniyor. Eşzamanlı gönderim isteği ikinci iş oluşturmuyor. Başarı/başarısızlık sağlayıcı sonucundan okunuyor. Platform SMS sağlayıcı kataloğu süper yöneticiye sınırlandı.
- Eski finans yolları ortak tahsilat/iptal defterine bağlandı. Taksitlerde kuruş toplamı ve takvim ayları korunuyor; tahsilatın tutarı sonradan değiştirilerek borç dengesi bozulamıyor. Silme işlemi muhasebe iptali yapıyor. Gerçek PDF dönüyor, iptal edilen makbuz her iki kopyada işaretleniyor; hatırlatmalar gönderilmiş gibi gösterilmiyor.
- Yazı tipleri Türkçe karakterlerle yerel sunuluyor; Google Fonts ağ isteği kaldırıldı. Yazı tipi lisansları dağıtıma dahil edildi.
- Donanım API'sinde kimlik doğrulamasız erişim kapatıldı. Cihaz, güvenlik ve kantin işlemleri ilgili rol yetkileriyle korunuyor; kart ödeme/yükleme/bakiye ortak cüzdana bağlı. Cihaz kurum/şube kaydı ve heartbeat durumu düzeltildi; WiFi okuma geçmişi kalıcı. Tam koşuya ek 4 donanım entegrasyon testi SQLite ve PostgreSQL'de geçti: [kayıt](../output/hardware-security-backend-20261103.log).
- Chatbot hazır soru düğmesi, güncellenmesini beklediği eski giriş alanı yerine seçilen soruyu doğrudan gönderiyor. Türkçe karakterler korunuyor.
- Personel öğrenci seçimi hem liste hem sayfalı API yanıtını okuyabiliyor. Öğrenci okuma yetkisi olmayan rol için yetkisiz öğrenci isteği oluşturulmuyor.
- Öğrenci seçimi gerektiren chatbot yanıtında asıl soru saklanıyor; seçimden sonra doğru öğrenci kimliğiyle tekrar gönderiliyor.
- Mesaj kimlikleri zaman damgası yerine çakışmayan sayaçla oluşturuluyor. Öğretmene bağlan yanıtı standart API zarfından okunuyor; katılımcı adı doğru gösteriliyor.
- Süper yönetici ve muhasebe/kantin gibi rol adlarının sohbet başlığı eşleştirmeleri düzeltildi.
- ESLint kapsamından oluşturulmuş Playwright raporları ve test sonuçları çıkarıldı; kaynak ve test dosyaları kontrolde kalıyor.
- Windows için başlatma/durdurma betikleri eklendi. Başlatma, proxy ve hazır olma kontrollerini yapıyor; ikinci çalıştırma aynı süreçleri kullanıyor. Durdurma, süreç kimliği/başlangıç zamanı/çalıştırılabilir dosyayı doğrulayıp yalnız betiğin başlattığı servisleri kapatıyor. Durdur–başlat ve tekrar başlatma kontrolleri geçti.

## Kullanım

Proje kökünden:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start-local.ps1
```

Durdurmak için:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/stop-local.ps1
```

Yerel servis logları ve süreç bilgileri `.codex-build/local` içindedir. Backend kodu veya ortam ayarı değiştiğinde durdurup yeniden başlatın. Başlatma betiği demo kayıtları oluşturmaz ve mevcut portlarda çalışan başka uygulamaları kapatmaz.

Gerçek ödeme, SMS/e-posta/WhatsApp teslimatı, hedef sunucu/HTTPS, yük testi ve fiziksel mobil cihaz kabulü bu test turuyla tamamlanmış sayılmaz. Canlı kurulum ayrıntıları ve kalan kabul sınırları için [üretim kılavuzunu](URETIM_KURULUMU_VE_MOBIL.md) ve [satış öncesi kabul raporunu](SATIS_ONCESI_KABUL_2026-11-02.md) kullanın.

<!-- SCS360_SOURCE_END: 21 -->

---

<a id="belge-22"></a>

## 22. docs/URETIM_KURULUMU_VE_MOBIL.md

Kaynak: [docs/URETIM_KURULUMU_VE_MOBIL.md](docs/URETIM_KURULUMU_VE_MOBIL.md)  
SHA-256: `79177b9c6e79ec857dbffe730b09e6d652900e950116d9807f887964ce5b08e9`

<!-- SCS360_SOURCE_BEGIN: 22 -->
# Üretim kurulumu ve mobil bağlantı

Bu kılavuz 2 Kasım 2026 tarihindeki kaynak kod içindir. Doğrulanmış testler ve açık kabul maddeleri için [satış öncesi kabul raporunu](SATIS_ONCESI_KABUL_2026-11-02.md) okuyun. Bu bilgisayarda Docker motoru bulunmadığından aşağıdaki konteyner kurulumu hedef sunucuda ayrıca çalıştırılmalıdır.

## Yapılandırma

Ürün markası SCS360'tır. Yeni kurulum örneklerinde PostgreSQL kullanıcı adı ve konteyner adları da bu adı kullanır. Mevcut bir kurulumun veritabanı kullanıcı adı, hesap e-postaları veya hacim adları yalnız marka değişti diye otomatik değiştirilmez; var olan veri hacmiyle aynı bağlantı bilgilerini koruyun. Frontend önceki sürümün geçerli tarayıcı oturumunu yeni depolama anahtarına taşır.

1. Kök `.env.compose.example` dosyasını kök `.env` dosyasına, `backend/.env.production.example` dosyasını `backend/.env` dosyasına kopyalayın. Mevcut dosyaları üzerine yazmadan önce yedekleyin. Gerçek sırları sürüm kontrolüne eklemeyin.
2. `POSTGRES_PASSWORD` için benzersiz, URL içinde güvenli bir değer; `JWT_SECRET_KEY` için en az 32 karakterlik rastgele bir değer kullanın. `APP_ENV=production`, `SEED_DEMO_DATA=false` kalmalıdır. Doğrudan kurulumda `DATABASE_URL` gerçek PostgreSQL adresini içermelidir; Compose bu adresi kendi ortamından atar.
3. `CORS_ORIGINS`, `PASSWORD_RESET_URL` ve `IYZICO_CALLBACK_URL` gerçek HTTPS alan adını kullanmalıdır. Nginx yapılandırmasındaki `server_name` değerini bu alan adıyla eşleştirin. Mevcut Compose yalnız port 80 açar; HTTPS sonlandırması ve sertifika yenilemesi hedef sunucunun ters vekilinde/yük dengeleyicisinde kurulmalıdır. TLS kurulmadan mobil veya ticari trafik açılmamalıdır.
4. Chatbot için erişilebilir Ollama adresi/modeli veya desteklenen diğer LLM sağlayıcısını yapılandırın. Örnek dosyadaki `http://ollama:11434/v1` adresi bir Ollama servisi gerektirir; mevcut Compose bu servisi oluşturmaz. Üretimde `mock` sağlayıcısı kabul edilmez. LLM zaman aşımında sınırlı süre ve kural tabanlı yanıt devreye girer; bu, modelin doğruluğuna veya her isteğin işleme dönüşmesine dair garanti değildir.
5. SMTP, Netgsm, Meta WhatsApp ve iyzico alanlarını ilgili hesaplardan doldurun. WhatsApp URL'sindeki sürüm yer tutucusunu sağlayıcının desteklediği sürümle değiştirin. Önce iyzico sandbox hesabını kullanın. Sağlayıcılar hazır olmadan `NOTIFICATION_DELIVERY_ENABLED=false` kalmalıdır; kapalı/eksik sağlayıcı gönderimi başarılı gösterilmez.

Sağlayıcı sırları sunucu ortam değişkenlerinden okunur. Yönetim ekranındaki bağlantı bilgilerini kaydetmek tek başına teslimat kabulü değildir. Kurum başına ayrı sağlayıcı hesabı ve Twilio gibi alternatifler bu sürümün canlı kabul kapsamına alınmamıştır.

## İlk çalıştırma

Kök dizinde:

```powershell
docker compose build
docker compose up -d db backend
docker compose exec backend python scripts/release_preflight.py
```

Backend başlangıcı Alembic migration'larını uygular. `/health` süreç canlılığını, `/api/ready` veritabanı ve migration sürümünü kontrol eder. `/api/ready` başarısızsa trafiği açmayın. PostgreSQL ve frontend konteyneri doğrudan dışarıya yayınlanmaz; dış trafik Nginx üzerinden geçer.

İlk kurum, şube ve yönetici yalnız boş kurulumda oluşturulur. Şu değerleri tek seferlik bootstrap sürecinin ortamına güvenli biçimde aktarın:

- `BOOTSTRAP_ORGANIZATION_NAME`
- `BOOTSTRAP_BRANCH_NAME`
- `BOOTSTRAP_ADMIN_EMAIL`
- `BOOTSTRAP_ADMIN_PASSWORD` — en az 16 karakter

Ardından:

```powershell
docker compose exec -e BOOTSTRAP_ORGANIZATION_NAME -e BOOTSTRAP_BRANCH_NAME -e BOOTSTRAP_ADMIN_EMAIL -e BOOTSTRAP_ADMIN_PASSWORD backend python scripts/bootstrap_production.py
docker compose up -d worker frontend nginx
docker compose exec backend python scripts/release_preflight.py --require-integrations
```

Komut ortam değerlerini ana sistemden alır. Bootstrap mevcut hesapları değiştirmez; dolu kurulumda durur. Yeni izin kataloğu ve sistem rollerinin izinleri `027` migration'ıyla kurulur. Özel roller otomatik olarak genişletilmez; yönetim ekranından işletmenin yetki politikasıyla eşleştirilmelidir.

`release_preflight.py` yalnız yapılandırma ve şema ön kontrolüdür. Çıktıdaki `ready=true`, sağlayıcıdan gerçek teslimat/ödeme alındığını veya bütün ekranların kabul edildiğini göstermez. `--require-integrations` tüm sağlayıcı yapılandırmalarını da zorunlu tutar.

## Hedef ortam kabulü

- Her kullanılan rol için giriş, yetkili liste/detay/oluşturma/güncelleme/silme akışı; başka kurum/şube/öğrenciye erişimin reddedilmesi.
- Gerçek LLM ile yanıt süresi, sağlayıcı erişilemezken chatbot yanıtı ve detay sayfasına geçiş.
- iyzico sandbox ödeme, doğrulanmış callback, borç/tahsilat/makbuz tutarlarının eşleşmesi ve aynı callback tekrarında tek tahsilat. Sonrasında hesabın canlı ortam ayarlarıyla kontrollü kabul.
- Yetkilendirilmiş test alıcılarında SMTP/Netgsm/WhatsApp teslimatı, outbox durumu, hata/yeniden deneme ve webhook sırrı. Bu çalışma sırasında gerçek alıcılara ileti gönderilmedi.
- HTTPS üzerinden şifre sıfırlama, dosya erişimi, oturum yenileme, servis yeniden başlatma ve hedef eşzamanlı kullanıcı sayısında yük testi.
- Aşağıdaki yedekten geri dönüş provası ve gerçek Android/iOS cihazında kabul.

## Yedekleme ve geri dönüş

Migration veya veri taşıma öncesinde PostgreSQL için `pg_dump -Fc` ile ayrı bir yedek oluşturun. Yedeğin yanında uygulama sürümünü ve Alembic başlığını kaydedin; yüklenen dosyaları barındıran `upload_data` ve ödev teslimlerini barındıran `private_upload_data` hacimlerini de yedekleyin. Yedekleri aynı sunucunun tek diskinde tutmayın. Veritabanı dump'ı dosya içeriğini içermez; hacim yedekleri aynı kabul provasında geri yüklenmelidir.

Geri dönüşü önce ayrı bir boş veritabanında `pg_restore --no-owner` ile deneyin. Kullanıcı/öğrenci/finans/ödev sayımları, kritik ilişkiler ve `/api/ready` kontrolünden sonra uygulama akışını test edin. Kabul edilmeden üretim veritabanını geri yükleme hedefi seçmeyin. Şema downgrade'i yerine veritabanı yedeğiyle uyumlu uygulama sürümüne dönün.

Bu çalışma sırasında yerel PostgreSQL 16 üzerinde ayrı kabul veritabanından alınan dump başka bir veritabanına geri yüklendi; kullanıcı/ödev sayımları ve `027` başlığı eşleşti. Bu, hedef sunucunun depolama, zamanlanmış yedek ve kurtarma süresi kabulünün yerine geçmez.

Eski SQLite verisini taşımak ayrı bir veri geçişidir. UUID biçimlerini topluca birleştiren eski yardımcı scriptleri üretim verisine doğrudan çalıştırmayın. Yerel veride çakışan kimlik/öğrenci numarası örnekleri bulundu; uyumluluk okumaları eklenerek mevcut kayıtlar korundu. Temiz PostgreSQL kurulumu, eski SQLite verisinin tümüyle taşındığını göstermez.

## Mobil API sözleşmesi

- Kök: `https://GERCEK_ALAN_ADI/api`; güncel şema: [openapi.json](openapi.json).
- Giriş: `POST /auth/login`, JSON `email`, `password`. Yanıtın `data` alanındaki `access_token`, `refresh_token` ve `token_type` kullanılır.
- Profil ve izinler: `GET /auth/me`. Menü/işlem görünürlüğü bu izinlerden türetilir; sunucu da erişimi kontrol eder.
- Yetkili istek: `Authorization: Bearer <access_token>`.
- Yenileme: `POST /auth/refresh`, JSON `refresh_token`. Dönen iki token birlikte değiştirilir. Eski refresh token yeniden kullanılamaz. Eşzamanlı 401 yanıtlarında istemci tek yenileme isteği paylaşmalı; yenileme başarısızsa giriş ekranına dönmelidir. Token'lar işletim sisteminin güvenli deposunda tutulmalıdır.
- Başarılı yanıt genel olarak `success`, `message`, `data`; hata yanıtı `success=false`, `message`, `errors`, `request_id` içerir. Liste sayfalaması kaynak şemasına göre okunur. 401 oturumu, 403 yetkiyi, 404 erişilebilir kaynağın bulunamadığını, 409 iş kuralı çakışmasını, 422 giriş doğrulamasını ifade eder. Bu durumlar istemcide 200 gibi işlenmemelidir.
- Veli işlemlerinde öğrenci kimliği ilgili çocuğun gerçek kaydından seçilir. Öğretmen sohbetinde `parent_id`, veli profilinin değil veli **kullanıcı hesabının** kimliğidir. Bir öğrenciye bağlı velilerin görüşmeleri ayrıdır.
- Ödev teslimi: metin için `POST /homework/{id}/submit` JSON `student_id`, `submission_text`; dosya için `POST /homework/{id}/submit-file` multipart `student_id`, isteğe bağlı `submission_text`, `file`. Dosya türü ve boyutu sunucu ayarlarıyla sınırlıdır. Öğretmen/veli listesinde dönen `attachment_url`, API köküne göre ve Bearer başlığıyla indirilir. Dosyalar `PRIVATE_UPLOAD_DIR` altında, herkese açık statik yüklemelerden ayrı tutulur. Notlandırılmış teslim değiştirilemez; not ve geri bildirim teslim listesinden okunur.
- iyzico hosted checkout adresi yalnız backend'den alınır; sağlayıcı anahtarları mobil uygulamaya gömülmez. Ödeme sonucu istemci dönüş ekranından tahsilat yaratılarak işlenmez; sunucunun doğruladığı callback esas alınır.
- FCM token kaydı kalıcıdır; bu çalışma Android/iOS push teslimatı, APNs/FCM sağlayıcı kurulumu veya uygulama mağazası kabulü yapmamıştır.

Şemayı yeniden üretmek için backend dizininden `python scripts/export_openapi.py` çalıştırın. Yerel doğrulama komutları kabul raporunda yer alır.

<!-- SCS360_SOURCE_END: 22 -->

---

<a id="belge-23"></a>

## 23. frontend/README.md

Kaynak: [frontend/README.md](frontend/README.md)  
SHA-256: `b315391643853c152e3d304b02bc83db796363ca7a7567401122889cf9eae3d4`

<!-- SCS360_SOURCE_BEGIN: 23 -->
# SCS360 Frontend

Material Dashboard veya hazır admin tema kullanmadan geliştirilmiş React + TypeScript yönetim panelidir. FastAPI backend'inin `/api` sözleşmesine bağlıdır.

## Yerel geliştirme

```bash
cp .env.example .env
npm install
npm run dev
```

Varsayılan arayüz `http://localhost:5173`, backend ise `http://localhost:5006/api` adresindedir.

## Komutlar

- `npm run dev`: geliştirme sunucusu
- `npm run build`: TypeScript kontrolü ve production build
- `npm run lint`: kod kalitesi kontrolü
- `npm run test`: Vitest testleri

## Demo hesabı

- E-posta: `admin@demo.com`
- Şifre: `Admin123*`

Roller ve izinler backend'den alınır; kullanıcıya kapalı modüller menüde gösterilmez.

<!-- SCS360_SOURCE_END: 23 -->

---

<a id="belge-24"></a>

## 24. hardware/README.md

Kaynak: [hardware/README.md](hardware/README.md)  
SHA-256: `88c6d6da57be2c17b81ce59b683a722c8886d341dffa001276d752f0ff6f68ff`

<!-- SCS360_SOURCE_BEGIN: 24 -->
# RFID Hardware Integration

Bu proje, SCS360 sistemi için RFID kart okuyucu ve turnike donanımlarının entegrasyonunu içerir.

## Donanım Bileşenleri

### Gerekli Donanım
- **Wemos D1 Mini** (ESP8266 tabanlı)
- **MFRC522 RFID Okuyucu Modülü**
- **Jumper Kablolar**
- **Breadboard (opsiyonel)**
- **5V Güç Kaynağı**
- **LED'ler (Yeşil, Kırmızı)**
- **Buzzer**
- **Röle (Turnike ve Kapı Kilidi için)**
- **LCD Ekran (Opsiyonel - Kantin ve Yoklama Kiosku için)**

## Cihaz Türleri

Projede 5 farklı cihaz türü bulunmaktadır:

### 1. Turnike Cihazı (`turnstile-device/`)
- **Özellikler**: Kart okuma, erişim kontrolü, turnike röle kontrolü
- **Kullanım**: Okul girişlerinde, turnike geçişlerinde
- **Pin Konfigürasyonu**:
  - SS_PIN: D2
  - RST_PIN: D1
  - BUZZER_PIN: D3
  - TURNSTILE_RELAY_PIN: D4
  - LED_GREEN_PIN: D5
  - LED_RED_PIN: D6

### 2. Kantin Terminali (`canteen-terminal/`)
- **Özellikler**: Kart okuma, bakiye sorgulama, ödeme işleme
- **Kullanım**: Kantin ödemelerinde
- **Pin Konfigürasyonu**:
  - SS_PIN: D2
  - RST_PIN: D1
  - BUZZER_PIN: D3
  - LED_GREEN_PIN: D5
  - LED_RED_PIN: D6

### 3. Kart Okuyucu (`card-reader/`)
- **Özellikler**: Kart okuma, kart bilgisi görüntüleme, basit loglama
- **Kullanım**: Genel kart okuma amaçları
- **Pin Konfigürasyonu**:
  - SS_PIN: D2
  - RST_PIN: D1
  - BUZZER_PIN: D3
  - LED_GREEN_PIN: D5
  - LED_RED_PIN: D6

### 4. Kapı Kilidi (`door-lock/`)
- **Özellikler**: Kart okuma, erişim kontrolü, kapı kilidi röle kontrolü
- **Kullanım**: Oda veya kapı erişim kontrolü
- **Pin Konfigürasyonu**:
  - SS_PIN: D2
  - RST_PIN: D1
  - BUZZER_PIN: D3
  - DOOR_LOCK_RELAY_PIN: D4
  - LED_GREEN_PIN: D5
  - LED_RED_PIN: D6

### 5. Yoklama Kiosku (`attendance-kiosk/`)
- **Özellikler**: Kart okuma, yoklama işaretleme, LCD ekran desteği
- **Kullanım**: Öğrenci ve personel yoklaması
- **Pin Konfigürasyonu**:
  - SS_PIN: D2
  - RST_PIN: D1
  - BUZZER_PIN: D3
  - LED_GREEN_PIN: D5
  - LED_RED_PIN: D6
  - LCD I2C (Opsiyonel): SDA=D4, SCL=D7

## Kurulum Adımları

### 1. Arduino IDE Kurulumu

1. Arduino IDE'yi indirin ve kurun: https://www.arduino.cc/en/software
2. Arduino IDE'de:
   - File > Preferences
   - "Additional Boards Manager URLs" kısmına ekleyin:
     ```
     http://arduino.esp8266.com/stable/package_esp8266com_index.json
     ```
3. Tools > Board > Boards Manager
4. "esp8266" arayın ve "esp8266 by ESP8266 Community" paketini kurun

### 2. Kütüphanelerin Kurulumu

Arduino IDE'de şu kütüphaneleri kurun:

1. **ESP8266WiFi** (ESP8266 ile birlikte gelir)
2. **ESP8266HTTPClient** (ESP8266 ile birlikte gelir)
3. **ArduinoJson** (versiyon 6.x)
   - Sketch > Include Library > Manage Libraries
   - "ArduinoJson" arayın ve kurun
4. **MFRC522**
   - Sketch > Include Library > Manage Libraries
   - "MFRC522" arayın ve kurun

### 3. Donanım Bağlantıları

#### MFRC522 RFID Okuyucu Bağlantıları

| MFRC522 Pin | Wemos D1 Pin |
|-------------|--------------|
| SDA (SS)    | D2           |
| SCK         | D5           |
| MOSI        | D7           |
| MISO        | D6           |
| RST         | D1           |
| 3.3V        | 3.3V         |
| GND         | GND          |

#### LED ve Buzzer Bağlantıları

| Bileşen | Wemos D1 Pin |
|---------|--------------|
| Yeşil LED | D5 |
| Kırmızı LED | D6 |
| Buzzer | D3 |

**Not**: LED'ler için 220Ω direnç kullanın.

#### Röle Bağlantıları (Turnike ve Kapı Kilidi)

| Röle | Wemos D1 Pin |
|------|--------------|
| IN   | D4           |
| VCC  | 5V           |
| GND  | GND          |

### 4. Yazılım Konfigürasyonu

Her cihazın `.ino` dosyasında şu konfigürasyonları yapın:

```cpp
// WiFi Ayarları
const char* WIFI_SSID = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

// API Ayarları
const char* API_BASE_URL = "http://YOUR_SERVER_IP:8000";
const char* API_KEY = "YOUR_API_KEY";

// Cihaz Ayarları
const char* DEVICE_ID = "DEVICE_TYPE_001";  // Her cihaz için benzersiz
const char* DEVICE_TYPE = "DEVICE_TYPE";    // TURNSTILE, CANTEEN_TERMINAL, vb.
const char* BRANCH_ID = "YOUR_BRANCH_ID";  // Şube UUID'si
```

### 5. Kodun Yüklenmesi

1. İlgili cihaz klasörüne gidin (örn: `turnstile-device/`)
2. `.ino` dosyasını Arduino IDE ile açın
3. Tools > Board > "LOLIN(WEMOS) D1 R2 & mini" seçin
4. Tools > Port > Wemos D1'nin bağlı olduğu portu seçin
5. Upload butonuna tıklayın

## API Entegrasyonu

Backend API endpoint'leri `backend/app/routers/hardware.py` dosyasında tanımlanmıştır.

### Endpoint'ler

#### Cihaz Kaydı
```
POST /api/hardware/devices/register
```

#### Cihaz Heartbeat
```
POST /api/hardware/devices/{device_id}/heartbeat
```

#### Erişim Kontrolü
```
POST /api/hardware/access/check
```

#### Erişim Loglama
```
POST /api/hardware/access/log
```

#### Kart Bakiyesi Sorgulama
```
POST /api/hardware/card/balance
```

#### Kart Ödeme İşleme
```
POST /api/hardware/payment/process
```

#### Kart Bakiye Yükleme
```
POST /api/hardware/card/topup
```

## Frontend Entegrasyonu

Kart bakiye yükleme arayüzü `frontend/src/features/operations/CardBalancePage.tsx` dosyasında bulunur.

### Kullanım

1. Sisteme giriş yapın
2. `/canteen/card-balance` sayfasına gidin
3. Kart numarasını girin veya kart okutun
4. Kart bilgileri görüntülenir
5. Bakiye yükleme işlemi yapın

## Sorun Giderme

### WiFi Bağlantı Sorunu
- WiFi SSID ve şifresini kontrol edin
- Wemos D1'nin güç kaynağının yeterli olduğundan emin olun (en az 1A)
- Router sinyal gücünü kontrol edin

### RFID Okuyucu Çalışmıyor
- Bağlantıları kontrol edin
- 3.3V güç kaynağının yeterli olduğundan emin olun
- MFRC522 kütüphanesinin doğru kurulduğunu kontrol edin

### API Bağlantı Sorunu
- API_BASE_URL'nin doğru olduğundan emin olun
- Sunucunun çalıştığını ve erişilebilir olduğunu kontrol edin
- Güvenlik duvarı ayarlarını kontrol edin

### Röle Çalışmıyor
- Röle modülünün doğru bağlandığını kontrol edin
- Röle için yeterli güç kaynağı kullanın (5V)
- Röle pin konfigürasyonunu kontrol edin

## Güvenlik Notları

1. **API Key**: Her cihaz için benzersiz API anahtarı kullanın
2. **WiFi**: Güçlü WiFi şifresi kullanın
3. **HTTPS**: Mümkünse HTTPS kullanın (SSL sertifikası gerektirir)
4. **Fiziksel Güvenlik**: Cihazları güvenli yerlere monte edin
5. **Güç Kaynağı**: Güvenilir güç kaynakları kullanın

## Bakım

### Düzenli Görevler
- Cihaz heartbeat loglarını kontrol edin
- WiFi bağlantılarını izleyin
- Donanımın fiziksel durumunu kontrol edin
- Güç kaynaklarını test edin

### Güncellemeler
- Arduino kodlarını düzenli olarak güncelleyin
- Kütüphaneleri güncel tutun
- API değişikliklerini takip edin

## Destek

Sorunlar için:
- Proje dokümantasyonunu inceleyin
- GitHub issues kısmını kontrol edin
- Geliştirici ekibiyle iletişime geçin

## Lisans

Bu proje SCS360 projesinin bir parçasıdır.

<!-- SCS360_SOURCE_END: 24 -->

---

<a id="belge-25"></a>

## 25. PROJE_DOKUMANTASYONU.md

Kaynak: [PROJE_DOKUMANTASYONU.md](PROJE_DOKUMANTASYONU.md)  
SHA-256: `a374b16afee5bce37fe501803c0d7c453761fc4dfa1684794c45237f122c7ac4`

<!-- SCS360_SOURCE_BEGIN: 25 -->
# SCS360 Proje Dokümantasyonu

Bu doküman SCS360 projesinin tüm API'lerini, veritabanı tablolarını ve frontend ekranlarını içeren kapsamlı bir referanstır.

## Proje Genel Bakış

SCS360, anaokulu, kreş, etüt ve kurs merkezleri için yönetim sistemi olan kapsamlı bir eğitim yönetim platformudur.

## Backend API Endpoints

### Temel Bileşenler
- **API Base URL**: `/api`
- **Authentication**: JWT token based
- **Multi-tenancy**: Organization ve Branch bazlı izolasyon
- **Permission System**: Rol bazlı yetkilendirme

### API Modülleri

#### 1. Authentication (`/api/auth`)
- `POST /api/auth/login` - Kullanıcı girişi
- `POST /api/auth/refresh` - Token yenileme
- `POST /api/auth/logout` - Çıkış
- `GET /api/auth/me` - Mevcut kullanıcı bilgileri
- `POST /api/auth/forgot-password` - Şifre sıfırlama isteği
- `POST /api/auth/reset-password` - Şifre sıfırlama

#### 2. Organizations (`/api/organizations`)
- `GET /api/organizations` - Kurum listesi
- `POST /api/organizations` - Kurum oluşturma
- `GET /api/organizations/{org_id}` - Kurum detayı
- `PUT /api/organizations/{org_id}` - Kurum güncelleme
- `DELETE /api/organizations/{org_id}` - Kurum silme (pasife alma)

#### 3. Branches (`/api/branches`)
- `GET /api/branches` - Şube listesi
- `POST /api/branches` - Şube oluşturma
- `GET /api/branches/{branch_id}` - Şube detayı
- `PUT /api/branches/{branch_id}` - Şube güncelleme
- `DELETE /api/branches/{branch_id}` - Şube silme (pasife alma)

#### 4. Users (`/api/users`)
- `GET /api/users` - Kullanıcı listesi
- `POST /api/users` - Kullanıcı oluşturma
- `GET /api/users/{user_id}` - Kullanıcı detayı
- `PUT /api/users/{user_id}` - Kullanıcı güncelleme
- `DELETE /api/users/{user_id}` - Kullanıcı silme

#### 5. Students (`/api/students`)
- `POST /api/students` - Öğrenci oluşturma
- `GET /api/students` - Öğrenci listesi (filtreleme ile)
- `GET /api/students/{student_id}` - Öğrenci detayı
- `PUT /api/students/{student_id}` - Öğrenci güncelleme
- `DELETE /api/students/{student_id}` - Öğrenci silme
- `POST /api/students/import-excel` - Excel'den öğrenci içe aktarma
- `GET /api/students/export-excel` - Öğrencileri Excel'e dışa aktarma

#### 6. Classes (`/api/classes`)
- `POST /api/classes` - Sınıf oluşturma
- `GET /api/classes` - Sınıf listesi
- `GET /api/classes/{class_id}` - Sınıf detayı
- `PUT /api/classes/{class_id}` - Sınıf güncelleme
- `DELETE /api/classes/{class_id}` - Sınıf silme
- `POST /api/classes/{class_id}/transfer-students` - Öğrenci transferi

#### 7. Attendance (`/api/attendance`)
- `POST /api/attendance` - Yoklama oluşturma
- `GET /api/attendance` - Yoklama listesi (sınıf, öğrenci, tarih filtreleri ile)
- `GET /api/attendance/{attendance_id}` - Yoklama detayı
- `PUT /api/attendance/{attendance_id}` - Yoklama güncelleme
- `DELETE /api/attendance/{attendance_id}` - Yoklama silme
- `POST /api/attendance/bulk` - Toplu yoklama oluşturma (öğretmenler için)
- `POST /api/attendance/mark-all-present` - Tümünü "Geldi" işaretle

**İzinler:** `attendance.read`, `attendance.write`, `attendance.take`

#### 8. Debts (`/api/debts`)
- `GET /api/debts` - Borç listesi
- `GET /api/debts/{debt_id}` - Borç detayı
- `POST /api/debts` - Borç oluşturma
- `PUT /api/debts/{debt_id}` - Borç güncelleme
- `DELETE /api/debts/{debt_id}` - Borç silme

#### 9. Payments (`/api/payments`)

##### Basic Operations
- `POST /api/payments` - Ödeme oluşturma
- `GET /api/payments` - Ödeme listesi
- `GET /api/payments/{payment_id}` - Ödeme detayı
- `PUT /api/payments/{payment_id}` - Ödeme güncelleme
- `DELETE /api/payments/{payment_id}` - Ödeme silme

##### iyzico Integration
- `POST /api/payments/iyzico/initialize` - iyzico ödeme başlatma
- `POST /api/payments/iyzico/callback` - iyzico callback

##### Finance Operations
- `POST /api/payments/finances/invoices/generate-plan` - Taksit planı oluşturma
- `POST /api/payments/finances/payments/collect` - Ödeme toplama
- `GET /api/payments/finances/payments/{payment_id}/receipt-pdf` - Makbuz PDF
- `POST /api/payments/finances/reminders/send` - Ödeme hatırlatması gönderme

**İzinler:** `payments.read`, `payments.write`, `payments.create`, `payments.update`, `payments.delete`, `finance.invoices_manage`, `finance.collect_payment`

#### 10. Communications (`/api/communications`)

##### SMS Providers
- `GET /api/communications/sms-providers` - SMS sağlayıcı listesi
- `POST /api/communications/sms-providers` - SMS sağlayıcı oluşturma

##### Broadcast Jobs
- `GET /api/communications/broadcast-jobs` - Broadcast işleri listesi
- `POST /api/communications/broadcast-jobs` - Broadcast işi oluşturma
- `PUT /api/communications/broadcast-jobs/{job_id}` - Broadcast işi güncelleme
- `POST /api/communications/broadcast-jobs/{job_id}/send` - Broadcast gönderme
- `DELETE /api/communications/broadcast-jobs/{job_id}` - Broadcast iptal

##### Delivery Reports
- `GET /api/communications/delivery-reports` - Teslimat raporları
- `GET /api/communications/broadcast-jobs/{job_id}/delivery-summary` - Teslimat özeti

##### Message Templates
- `GET /api/communications/message-templates` - Mesaj şablonları
- `POST /api/communications/message-templates` - Şablon oluşturma

**İzinler:** `communications.read`, `communications.write`

#### 11. Parent Portal (`/api/parent`)
- `GET /api/parent/my-children` - Veli çocukları listesi
- `GET /api/parent/child/{id}/today-status` - Çocuğun günlük durumu
- `GET /api/parent/child/{id}/timeline` - Çocuk zaman çizelgesi
- `GET /api/parent/child/{id}/attendance` - Çocuk devamsızlık takvimi (aylık)
- `GET /api/parent/child/{id}/grades` - Çocuk notları
- `GET /api/parent/child/{id}/schedule` - Çocuk ders programı
- `GET /api/parent/child/{id}/homework` - Çocuk ödevleri
- `GET /api/parent/child/{id}/financial-invoices` - Çocuk finansal faturaları
- `GET /api/parent/child/{id}/medicine-requests` - Çocuk ilaç talepleri
- `POST /api/parent/child/{id}/excuse-request` - İzin talebi
- `POST /api/parent/child/{id}/medicine-requests` - İlaç talebi
- `POST /api/parent/payments/checkout-session` - Ödeme oturumu oluşturma

**İzinler:** `parent.view_children`, `parent.view_daily_report`, `parent.view_attendance`, `parent.view_finances`, `parent.send_excuse`, `parent.medicine_request`, `parent.make_payment`

#### 12. Diğer API Modülleri
- **Health**: `/api/health` - Sistem sağlık kontrolü
- **Dashboard**: `/api/dashboard` - Dashboard verileri
- **Announcements**: `/api/announcements` - Duyurular
- **Appointments**: `/api/appointments` - Randevular
- **Bus**: `/api/bus` - Servis yönetimi
- **Canteen**: `/api/canteen` - Kantin işlemleri
- **Clubs**: `/api/clubs` - Kulüpler
- **Consents**: `/api/consents` - İzinler
- **Daily Reports**: `/api/daily-reports` - Günlük raporlar
- **Debts**: `/api/debts` - Borçlar
- **Devices**: `/api/devices` - Cihazlar
- **Exams**: `/api/exams` - Sınavlar
- **Expenses**: `/api/expenses` - Giderler
- **Files**: `/api/files` - Dosya yönetimi
- **Guidance**: `/api/guidance` - Rehberlik
- **Hardware**: `/api/hardware` - Donanım
- **HQ**: `/api/hq` - Merkez yönetimi
- **Homework**: `/api/homework` - Ödevler
- **Data Import**: `/api/data-import` - Veri içe aktarma
- **Infirmary**: `/api/infirmary` - Sağlık oda
- **Inventory**: `/api/inventory` - Envanter
- **Library**: `/api/library` - Kütüphane
- **Materials**: `/api/materials` - Materyaller
- **Messages**: `/api/messages` - Mesajlar
- **Operations**: `/api/operations` - Operasyonlar
- **Outbox**: `/api/outbox` - Giden kutusu
- **Parent Notices**: `/api/parent-notices` - Veli talepleri
- **Parents**: `/api/parents` - Veliler
- **Payroll**: `/api/payroll` - Maaş
- **Pickup**: `/api/pickup` - Teslim alma
- **RFID Cards**: `/api/rfid-cards` - RFID kartlar
- **Card Numbers**: `/api/card-numbers` - Kart numaraları
- **Security**: `/api/security` - Güvenlik
- **Settings**: `/api/settings` - Ayarlar
- **Staff Operations**: `/api/staff-operations` - Personel operasyonları
- **Surveys**: `/api/surveys` - Anketler
- **Teacher**: `/api/teacher` - Öğretmen işlemleri
- **Timetable**: `/api/timetable` - Ders programı
- **Tutoring**: `/api/tutoring` - Etüt
- **User Roles**: `/api/user-roles` - Kullanıcı rolleri
- **AI Analytics**: `/api/ai-analytics` - AI analitikleri

## Veritabanı Tabloları

### Temel Tablolar

#### 1. organizations
Kurum/okul bilgilerini tutar
- `id` (UUID) - Primary Key
- `name` - Kurum adı
- `legal_name` - Resmi ad
- `tax_number` - Vergi numarası
- `tax_office` - Vergi dairesi
- `phone` - Telefon
- `email` - E-posta
- `address` - Adres
- `city` - Şehir
- `country` - Ülke
- `logo_url` - Logo URL
- `website` - Web sitesi
- `is_active` - Aktif mi
- `created_by` - Oluşturan
- `updated_by` - Güncelleyen
- `created_at` - Oluşturma tarihi
- `updated_at` - Güncelleme tarihi
- `deleted_at` - Silme tarihi (soft delete)

#### 2. branches
Şube bilgilerini tutar
- `id` (UUID) - Primary Key
- `organization_id` - Kurum ID (FK)
- `name` - Şube adı
- `code` - Şube kodu
- `phone` - Telefon
- `email` - E-posta
- `address` - Adres
- `city` - Şehir
- `capacity` - Kapasite
- `is_active` - Aktif mi
- `created_by` - Oluşturan
- `updated_by` - Güncelleyen
- `created_at` - Oluşturma tarihi
- `updated_at` - Güncelleme tarihi
- `deleted_at` - Silme tarihi (soft delete)

#### 3. users
Kullanıcı hesaplarını tutar
- `id` (UUID) - Primary Key
- `organization_id` - Kurum ID (FK)
- `email` - E-posta (unique)
- `password_hash` - Şifre hash
- `first_name` - Ad
- `last_name` - Soyad
- `phone` - Telefon
- `position` - Pozisyon
- `department` - Departman
- `status` - Durum (ACTIVE, PASSIVE, BLOCKED)
- `is_super_admin` - Süper admin mi
- `last_login_at` - Son giriş
- `created_by` - Oluşturan
- `updated_by` - Güncelleyen
- `created_at` - Oluşturma tarihi
- `updated_at` - Güncelleme tarihi
- `deleted_at` - Silme tarihi (soft delete)

#### 4. roles
Rol tanımlarını tutar
- `id` (UUID) - Primary Key
- `name` - Rol adı
- `slug` - Rol slug
- `description` - Açıklama
- `is_system` - Sistem rolü mü
- `organization_id` - Kurum ID (FK)
- `created_at` - Oluşturma tarihi
- `updated_at` - Güncelleme tarihi
- `deleted_at` - Silme tarihi (soft delete)

#### 5. permissions
İzin tanımlarını tutar
- `id` (UUID) - Primary Key
- `code` - İzin kodu (unique)
- `name` - İzin adı
- `module` - Modül
- `description` - Açıklama
- `created_at` - Oluşturma tarihi

#### 6. role_permissions
Rol-izin ilişkilerini tutar
- `role_id` - Rol ID (FK, PK)
- `permission_id` - İzin ID (FK, PK)
- `created_at` - Oluşturma tarihi

#### 7. user_roles
Kullanıcı-rol ilişkilerini tutar
- `user_id` - Kullanıcı ID (FK, PK)
- `role_id` - Rol ID (FK, PK)
- `assigned_at` - Atama tarihi
- `assigned_by` - Atayan

#### 8. user_branches
Kullanıcı-şube ilişkilerini tutar
- `user_id` - Kullanıcı ID (FK, PK)
- `branch_id` - Şube ID (FK, PK)
- `assigned_at` - Atama tarihi
- `assigned_by` - Atayan

### Güvenlik Tabloları

#### 9. refresh_tokens
Refresh token'ları tutar
- `id` (UUID) - Primary Key
- `user_id` - Kullanıcı ID (FK)
- `token_hash` - Token hash
- `family_id` - Token ailesi ID
- `expires_at` - Son kullanma tarihi
- `revoked_at` - İptal tarihi
- `replaced_by` - Yerine geçen token
- `created_at` - Oluşturma tarihi
- `ip_address` - IP adresi
- `user_agent` - User agent

#### 10. password_reset_tokens
Şifre sıfırlama token'larını tutar
- `id` (UUID) - Primary Key
- `user_id` - Kullanıcı ID (FK)
- `token_hash` - Token hash
- `expires_at` - Son kullanma tarihi
- `used_at` - Kullanım tarihi
- `created_at` - Oluşturma tarihi

#### 11. login_attempts
Giriş denemelerini tutar
- `id` (UUID) - Primary Key
- `email` - E-posta
- `ip_address` - IP adresi
- `user_agent` - User agent
- `success` - Başarılı mı
- `failure_reason` - Başarısızlık sebebi
- `attempted_at` - Deneme tarihi

### Eğitim Tabloları

#### 12. classes
Sınıf bilgilerini tutar
- `id` (UUID) - Primary Key
- `organization_id` - Kurum ID (FK)
- `branch_id` - Şube ID (FK)
- `name` - Sınıf adı
- `code` - Sınıf kodu
- `description` - Açıklama
- `capacity` - Kapasite
- `academic_year` - Akademik yıl
- `teacher_id` - Öğretmen ID (FK)
- `is_active` - Aktif mi
- `created_by` - Oluşturan
- `updated_by` - Güncelleyen
- `created_at` - Oluşturma tarihi
- `updated_at` - Güncelleme tarihi
- `deleted_at` - Silme tarihi (soft delete)

#### 13. class_teachers
Sınıf-öğretmen ilişkilerini tutar
- `class_id` - Sınıf ID (FK, PK)
- `user_id` - Kullanıcı ID (FK, PK)
- `is_primary` - Birincil mi
- `assigned_at` - Atama tarihi
- `assigned_by` - Atayan

#### 14. students
Öğrenci bilgilerini tutar
- `id` (UUID) - Primary Key
- `organization_id` - Kurum ID (FK)
- `branch_id` - Şube ID (FK)
- `class_id` - Sınıf ID (FK)
- `student_number` - Öğrenci numarası
- `first_name` - Ad
- `last_name` - Soyad
- `gender` - Cinsiyet (MALE, FEMALE, OTHER)
- `birth_date` - Doğum tarihi
- `enrollment_date` - Kayıt tarihi
- `status` - Durum (ACTIVE, PASSIVE, GRADUATED, LEFT)
- `photo_url` - Fotoğraf URL
- `health_notes` - Sağlık notları
- `notes` - Notlar
- `created_by` - Oluşturan
- `updated_by` - Güncelleyen
- `created_at` - Oluşturma tarihi
- `updated_at` - Güncelleme tarihi
- `deleted_at` - Silme tarihi (soft delete)

#### 15. parents
Veli bilgilerini tutar
- `id` (UUID) - Primary Key
- `organization_id` - Kurum ID (FK)
- `user_id` - Kullanıcı ID (FK)
- `first_name` - Ad
- `last_name` - Soyad
- `relation_type` - İlişki türü (MOTHER, FATHER, GUARDIAN, OTHER)
- `phone` - Telefon
- `sms_phone` - SMS telefonu
- `whatsapp_phone` - WhatsApp telefonu
- `email` - E-posta
- `address` - Adres
- `receive_notifications` - Bildirim al mı
- `created_by` - Oluşturan
- `updated_by` - Güncelleyen
- `created_at` - Oluşturma tarihi
- `updated_at` - Güncelleme tarihi
- `deleted_at` - Silme tarihi (soft delete)

#### 16. student_parents
Öğrenci-veli ilişkilerini tutar
- `student_id` - Öğrenci ID (FK, PK)
- `parent_id` - Veli ID (FK, PK)
- `is_primary` - Birincil mi
- `is_emergency` - Acil durum mi
- `created_at` - Oluşturma tarihi

#### 17. student_files
Öğrenci dosyalarını tutar
- `id` (UUID) - Primary Key
- `organization_id` - Kurum ID (FK)
- `branch_id` - Şube ID (FK)
- `student_id` - Öğrenci ID (FK)
- `category` - Kategori (IDENTITY, HEALTH_REPORT, REGISTRATION_CONTRACT, PAYMENT_CONTRACT, PHOTO, OTHER)
- `file_name` - Dosya adı
- `original_name` - Orijinal ad
- `mime_type` - MIME tipi
- `file_size` - Dosya boyutu
- `storage_path` - Depolama yolu
- `uploaded_by` - Yükleyen
- `created_at` - Oluşturma tarihi
- `updated_at` - Güncelleme tarihi
- `deleted_at` - Silme tarihi (soft delete)

#### 18. attendance_records
Yoklama kayıtlarını tutar
- `id` (UUID) - Primary Key
- `organization_id` - Kurum ID (FK)
- `branch_id` - Şube ID (FK)
- `class_id` - Sınıf ID (FK)
- `student_id` - Öğrenci ID (FK)
- `attendance_date` - Yoklama tarihi
- `status` - Durum (PRESENT, ABSENT, EXCUSED, LATE, HALF_DAY)
- `check_in_time` - Giriş saati
- `notes` - Notlar
- `recorded_by` - Kaydeden
- `created_at` - Oluşturma tarihi
- `updated_at` - Güncelleme tarihi
- `deleted_at` - Silme tarihi (soft delete)

#### 19. grades
Notları tutar
- `id` (UUID) - Primary Key
- `organization_id` - Kurum ID (FK)
- `branch_id` - Şube ID (FK)
- `class_id` - Sınıf ID (FK)
- `student_id` - Öğrenci ID (FK)
- `teacher_id` - Öğretmen ID (FK)
- `subject` - Ders (MATHEMATICS, SCIENCE, TURKISH, SOCIAL_STUDIES, ENGLISH, PHYSICAL_EDUCATION, ART, MUSIC, COMPUTER, RELIGION, OTHER)
- `grade_type` - Not türü (EXAM, QUIZ, HOMEWORK, PROJECT, PARTICIPATION, MIDTERM, FINAL)
- `score` - Puan
- `max_score` - Maksimum puan
- `exam_date` - Sınav tarihi
- `term` - Dönem
- `notes` - Notlar
- `created_by` - Oluşturan
- `updated_by` - Güncelleyen
- `created_at` - Oluşturma tarihi
- `updated_at` - Güncelleme tarihi

#### 20. daily_development_reports
Günlük gelişim raporlarını tutar
- `id` (UUID) - Primary Key
- `student_id` - Öğrenci ID (FK)
- `class_id` - Sınıf ID (FK)
- `date` - Tarih
- `meal_status` - Yemek durumu (ALL, HALF, NONE)
- `sleep_status` - Uyku durumu (SLEPT_WELL, SHORT, NO_SLEEP)
- `mood` - Ruh hali (HAPPY, CALM, UNSETTLED, TIRED)
- `activities` - Aktiviteler (JSON)
- `teacher_notes` - Öğretmen notları
- `recorded_by` - Kaydeden
- `created_at` - Oluşturma tarihi
- `updated_at` - Güncelleme tarihi

### Finans Tabloları

#### 21. debts
Borçları tutar
- `id` (UUID) - Primary Key
- `organization_id` - Kurum ID (FK)
- `branch_id` - Şube ID (FK)
- `student_id` - Öğrenci ID (FK)
- `debt_type` - Borç türü (EDUCATION, FOOD, SERVICE, STATIONERY, ACTIVITY, OTHER)
- `description` - Açıklama
- `amount` - Tutar
- `paid_amount` - Ödenen tutar
- `status` - Durum (UNPAID, PARTIALLY_PAID, PAID, OVERDUE, CANCELLED)
- `due_date` - Son ödeme tarihi
- `created_by` - Oluşturan
- `updated_by` - Güncelleyen
- `created_at` - Oluşturma tarihi
- `updated_at` - Güncelleme tarihi
- `deleted_at` - Silme tarihi (soft delete)

#### 22. payments
Ödemeleri tutar
- `id` (UUID) - Primary Key
- `organization_id` - Kurum ID (FK)
- `branch_id` - Şube ID (FK)
- `student_id` - Öğrenci ID (FK)
- `debt_id` - Borç ID (FK)
- `amount` - Tutar
- `payment_method` - Ödeme yöntemi (CASH, CREDIT_CARD, BANK_TRANSFER, EFT, OTHER)
- `payment_date` - Ödeme tarihi
- `status` - Durum
- `notes` - Notlar
- `received_by` - Alan
- `cancelled_at` - İptal tarihi
- `cancelled_by` - İptal eden
- `cancel_reason` - İptal sebebi
- `created_at` - Oluşturma tarihi
- `updated_at` - Güncelleme tarihi

#### 23. receipts
Makbuzları tutar
- `id` (UUID) - Primary Key
- `organization_id` - Kurum ID (FK)
- `branch_id` - Şube ID (FK)
- `student_id` - Öğrenci ID (FK)
- `payment_id` - Ödeme ID (FK, unique)
- `receipt_number` - Makbuz numarası (unique)
- `status` - Durum (ACTIVE, CANCELLED)
- `issued_at` - Düzenleme tarihi
- `issued_by` - Düzenleyen
- `pdf_path` - PDF yolu
- `remaining_debt` - Kalan borç
- `created_at` - Oluşturma tarihi
- `updated_at` - Güncelleme tarihi

#### 24. expenses
Giderleri tutar
- `id` (UUID) - Primary Key
- `organization_id` - Kurum ID (FK)
- `branch_id` - Şube ID (FK)
- `description` - Açıklama
- `category` - Kategori
- `amount` - Tutar
- `expense_date` - Gider tarihi
- `status` - Durum
- `notes` - Notlar
- `created_by` - Oluşturan
- `updated_by` - Güncelleyen
- `created_at` - Oluşturma tarihi
- `updated_at` - Güncelleme tarihi
- `deleted_at` - Silme tarihi (soft delete)

### İletişim Tabloları

#### 25. announcements
Duyuruları tutar
- `id` (UUID) - Primary Key
- `organization_id` - Kurum ID (FK)
- `branch_id` - Şube ID (FK)
- `class_id` - Sınıf ID (FK)
- `student_id` - Öğrenci ID (FK)
- `title` - Başlık
- `content` - İçerik
- `audience` - Hedef kitle (ALL_PARENTS, BRANCH_PARENTS, CLASS_PARENTS, SINGLE_STUDENT)
- `channels` - Kanallar (JSON)
- `status` - Durum (DRAFT, SCHEDULED, SENT, CANCELLED)
- `scheduled_at` - Planlanan tarih
- `sent_at` - Gönderim tarihi
- `created_by` - Oluşturan
- `created_at` - Oluşturma tarihi
- `updated_at` - Güncelleme tarihi
- `deleted_at` - Silme tarihi (soft delete)

#### 26. announcement_recipients
Duyuru alıcılarını tutar
- `id` (UUID) - Primary Key
- `announcement_id` - Duyuru ID (FK)
- `parent_id` - Veli ID (FK)
- `student_id` - Öğrenci ID (FK)
- `channel` - Kanal (EMAIL, SMS, WHATSAPP)
- `status` - Durum (PENDING, SENT, FAILED, CANCELLED)
- `sent_at` - Gönderim tarihi
- `error_message` - Hata mesajı
- `created_at` - Oluşturma tarihi

#### 27. message_templates
Mesaj şablonlarını tutar
- `id` (UUID) - Primary Key
- `organization_id` - Kurum ID (FK)
- `code` - Şablon kodu
- `name` - Şablon adı
- `channel` - Kanal (EMAIL, SMS, WHATSAPP)
- `subject` - Konu
- `body_template` - İçerik şablonu
- `is_active` - Aktif mi
- `created_at` - Oluşturma tarihi
- `updated_at` - Güncelleme tarihi
- `deleted_at` - Silme tarihi (soft delete)

#### 28. notification_jobs
Bildirim işlerini tutar
- `id` (UUID) - Primary Key
- `organization_id` - Kurum ID (FK)
- `branch_id` - Şube ID (FK)
- `channel` - Kanal (EMAIL, SMS, WHATSAPP)
- `template_code` - Şablon kodu
- `subject` - Konu
- `body` - İçerik
- `status` - Durum (PENDING, SENT, FAILED, CANCELLED)
- `retry_count` - Yeniden deneme sayısı
- `max_retries` - Maksimum deneme
- `scheduled_at` - Planlanan tarih
- `processed_at` - İşleme tarihi
- `reference_type` - Referans türü
- `reference_id` - Referans ID
- `created_by` - Oluşturan
- `created_at` - Oluşturma tarihi
- `updated_at` - Güncelleme tarihi

#### 29. notification_recipients
Bildirim alıcılarını tutar
- `id` (UUID) - Primary Key
- `notification_job_id` - Bildirim işi ID (FK)
- `parent_id` - Veli ID (FK)
- `user_id` - Kullanıcı ID (FK)
- `recipient_name` - Alıcı adı
- `recipient_address` - Alıcı adresi
- `status` - Durum (PENDING, SENT, FAILED, CANCELLED)
- `provider_response` - Sağlayıcı yanıtı (JSON)
- `error_message` - Hata mesajı
- `sent_at` - Gönderim tarihi
- `created_at` - Oluşturma tarihi
- `updated_at` - Güncelleme tarihi

#### 30. chat_messages
Sohbet mesajlarını tutar
- `id` (UUID) - Primary Key
- `sender_id` - Gönderen ID (FK)
- `receiver_id` - Alıcı ID (FK)
- `class_id` - Sınıf ID (FK)
- `content` - İçerik
- `attachment_url` - Ek URL
- `is_read` - Okundu mu
- `sent_at` - Gönderim tarihi
- `created_at` - Oluşturma tarihi
- `updated_at` - Güncelleme tarihi

### Sistem Tabloları

#### 31. integration_settings
Entegrasyon ayarlarını tutar
- `id` (UUID) - Primary Key
- `organization_id` - Kurum ID (FK)
- `provider` - Sağlayıcı (SMTP, NETGSM, TWILIO, META_WHATSAPP, OTHER)
- `config` - Konfigürasyon (JSON)
- `is_active` - Aktif mi
- `updated_by` - Güncelleyen
- `created_at` - Oluşturma tarihi
- `updated_at` - Güncelleme tarihi

#### 32. app_settings
Uygulama ayarlarını tutar
- `id` (UUID) - Primary Key
- `organization_id` - Kurum ID (FK)
- `setting_key` - Ayar anahtarı
- `setting_value` - Ayar değeri (JSON)
- `description` - Açıklama
- `updated_by` - Güncelleyen
- `created_at` - Oluşturma tarihi
- `updated_at` - Güncelleme tarihi

#### 33. audit_logs
Denetim loglarını tutar
- `id` (UUID) - Primary Key
- `organization_id` - Kurum ID (FK)
- `branch_id` - Şube ID (FK)
- `user_id` - Kullanıcı ID (FK)
- `action` - Aksiyon (CREATE, UPDATE, DELETE, LOGIN, LOGOUT, PAYMENT, CANCEL_PAYMENT, SEND_NOTIFICATION, OTHER)
- `entity_type` - Varlık türü
- `entity_id` - Varlık ID
- `old_values` - Eski değerler (JSON)
- `new_values` - Yeni değerler (JSON)
- `ip_address` - IP adresi
- `user_agent` - User agent
- `created_at` - Oluşturma tarihi

### Donanım Tabloları

#### 34. card_numbers
Kart numaralarını tutar
- `id` (String) - Primary Key
- `organization_id` - Kurum ID
- `branch_id` - Şube ID
- `card_number` - Kart numarası
- `status` - Durum (AVAILABLE, ASSIGNED, DAMAGED, LOST)
- `notes` - Notlar
- `purchased_date` - Satın alma tarihi
- `supplier` - Tedarikçi
- `created_at` - Oluşturma tarihi
- `updated_at` - Güncelleme tarihi

#### 35. devices
Cihazları tutar
- `id` (String) - Primary Key
- `organization_id` - Kurum ID
- `branch_id` - Şube ID
- `name` - Cihaz adı
- `device_type` - Cihaz türü (TURNSTILE, CARD_READER, DOOR_LOCK, ATTENDANCE_KIOSK, CANTEEN_TERMINAL)
- `serial_number` - Seri numarası
- `ip_address` - IP adresi
- `location` - Konum
- `status` - Durum (ACTIVE, INACTIVE, MAINTENANCE, BROKEN)
- `last_heartbeat` - Son kalp atışı
- `notes` - Notlar
- `created_at` - Oluşturma tarihi
- `updated_at` - Güncelleme tarihi

#### 36. rfid_cards
RFID kartlarını tutar
- `id` (String) - Primary Key
- `organization_id` - Kurum ID
- `branch_id` - Şube ID
- `card_number` - Kart numarası
- `card_type` - Kart türü (STUDENT, STAFF)
- `holder_id` - Sahip ID
- `holder_name` - Sahip adı
- `status` - Durum (ACTIVE, INACTIVE, BLOCKED)
- `issue_date` - Veriliş tarihi
- `expiry_date` - Son kullanma tarihi
- `created_at` - Oluşturma tarihi
- `updated_at` - Güncelleme tarihi

### Ders Programı Tabloları

#### 37. timetable_slots
Ders programı zamanlarını tutar
- `id` (UUID) - Primary Key
- `day` - Gün
- `start_time` - Başlangıç saati
- `end_time` - Bitiş saati
- `is_break` - Ara mı
- `created_at` - Oluşturma tarihi
- `updated_at` - Güncelleme tarihi

#### 38. classroom_assignments
Sınıf atamalarını tutar
- `id` (UUID) - Primary Key
- `class_id` - Sınıf ID (FK)
- `teacher_id` - Öğretmen ID (FK)
- `subject_id` - Ders ID
- `room_number` - Oda numarası
- `capacity` - Kapasite
- `created_at` - Oluşturma tarihi
- `updated_at` - Güncelleme tarihi

#### 39. timetables
Ders programlarını tutar
- `id` (UUID) - Primary Key
- `class_id` - Sınıf ID (FK)
- `slot_id` - Zaman ID (FK)
- `classroom_assignment_id` - Sınıf atama ID (FK)
- `academic_year` - Akademik yıl
- `semester` - Dönem
- `is_active` - Aktif mi
- `created_at` - Oluşturma tarihi
- `updated_at` - Güncelleme tarihi

## Frontend Ekranları ve API İlişkileri

### Yönetim Bölümü

#### 1. Dashboard (`/dashboard`)
**Kullanılan API'ler:**
- `GET /api/dashboard/summary` - Özet istatistikler (öğrenci sayısı, tahsilat, devamsızlık)
- `GET /api/dashboard/charts` - Aylık tahsilat grafiği
- `GET /api/dashboard/overview` - Genel bakış verileri
- `GET /api/ai/insights-report` - AI öngörüler ve öncelikli aksiyonlar
- `GET /api/admin/students` - Öğrenci listesi (chat için)
- `GET /api/users` - Kullanıcı listesi (chat için)

**İzinler:** `dashboard.view`

#### 2. Organizations (`/organizations`)
**Kullanılan API'ler:**
- `GET /api/organizations` - Kurum listesi
- `POST /api/organizations` - Kurum oluşturma
- `GET /api/organizations/{id}` - Kurum detayı
- `PUT /api/organizations/{id}` - Kurum güncelleme
- `DELETE /api/organizations/{id}` - Kurum silme

**İzinler:** `org.read`, `org.write`

#### 3. Branches (`/branches`)
**Kullanılan API'ler:**
- `GET /api/branches` - Şube listesi
- `POST /api/branches` - Şube oluşturma
- `GET /api/branches/{id}` - Şube detayı
- `PUT /api/branches/{id}` - Şube güncelleme
- `DELETE /api/branches/{id}` - Şube silme

**İzinler:** `branch.read`, `branch.write`

#### 4. Users (`/users`)
**Kullanılan API'ler:**
- `GET /api/users` - Kullanıcı listesi
- `POST /api/users` - Kullanıcı oluşturma
- `GET /api/users/{id}` - Kullanıcı detayı
- `PUT /api/users/{id}` - Kullanıcı güncelleme
- `DELETE /api/users/{id}` - Kullanıcı silme

**İzinler:** `users.read`, `users.write`

#### 5. Roles (`/roles`)
**Kullanılan API'ler:**
- `GET /api/roles` - Rol listesi
- `POST /api/roles` - Rol oluşturma
- `GET /api/roles/{id}` - Rol detayı
- `PUT /api/roles/{id}` - Rol güncelleme
- `DELETE /api/roles/{id}` - Rol silme
- `GET /api/roles/{id}/permissions` - Rol yetkileri

**İzinler:** `users.read`, `users.write`

#### 6. Staff (`/staff`)
**Kullanılan API'ler:**
- `GET /api/staff` - Personel listesi
- `POST /api/staff` - Personel oluşturma
- `GET /api/staff/{id}` - Personel detayı
- `PUT /api/staff/{id}` - Personel güncelleme

**İzinler:** `users.read`, `users.write`

#### 7. Teacher Portal (`/teacher`)
**Kullanılan API'ler:**
- `GET /api/dashboard/summary` - Öğretmen özeti
- `GET /api/dashboard/overview` - Genel bakış
- `GET /api/students` - Öğrenci listesi
- `GET /api/users` - Kullanıcı listesi

**İzinler:** `dashboard.view`

### Eğitim Bölümü

#### 8. Students (`/students`)
**Kullanılan API'ler:**
- `GET /api/students` - Öğrenci listesi (arama, sayfalama ile)
- `POST /api/students` - Öğrenci oluşturma
- `GET /api/students/{id}` - Öğrenci detayı
- `PUT /api/students/{id}` - Öğrenci güncelleme
- `DELETE /api/students/{id}` - Öğrenci silme
- `POST /api/students/import-excel` - Excel'den içe aktarma
- `GET /api/students/export-excel` - Excel'e dışa aktarma
- `GET /api/ai/students-overview` - AI öğrenci analizi

**İzinler:** `students.read`, `students.write`, `students.import`, `students.export`

#### 9. Student Detail (`/students/{id}`)
**Kullanılan API'ler:**
- `GET /api/students/{id}` - Öğrenci detayı
- `GET /api/students/{id}/files` - Öğrenci dosyaları
- `GET /api/students/{id}/parents` - Öğrenci velileri
- `GET /api/attendance?student_id={id}` - Öğrenci yoklaması

**İzinler:** `students.read`

#### 10. Parents (`/parents`)
**Kullanılan API'ler:**
- `GET /api/parents` - Veli listesi
- `POST /api/parents` - Veli oluşturma
- `GET /api/parents/{id}` - Veli detayı
- `PUT /api/parents/{id}` - Veli güncelleme

**İzinler:** `parents.read`, `parents.write`

#### 11. Classes (`/classes`)
**Kullanılan API'ler:**
- `GET /api/classes` - Sınıf listesi
- `POST /api/classes` - Sınıf oluşturma
- `GET /api/classes/{id}` - Sınıf detayı
- `PUT /api/classes/{id}` - Sınıf güncelleme
- `DELETE /api/classes/{id}` - Sınıf silme
- `POST /api/classes/{id}/transfer-students` - Öğrenci transferi

**İzinler:** `classes.read`, `classes.write`

#### 12. Class Detail (`/classes/{id}`)
**Kullanılan API'ler:**
- `GET /api/classes/{id}` - Sınıf detayı
- `GET /api/students?class_id={id}` - Sınıf öğrencileri
- `GET /api/attendance?class_id={id}` - Sınıf yoklaması

**İzinler:** `classes.read`, `students.read`

#### 13. Class Occupancy (`/classes/occupancy`)
**Kullanılan API'ler:**
- `GET /api/classes` - Sınıf listesi
- `GET /api/students` - Öğrenci sayıları

**İzinler:** `classes.read`

#### 14. Assign Students (`/classes/{id}/assign`)
**Kullanılan API'ler:**
- `GET /api/students` - Öğrenci listesi
- `POST /api/classes/{id}/transfer-students` - Öğrenci atama

**İzinler:** `classes.write`

#### 15. Attendance (`/attendance`)
**Kullanılan API'ler:**
- `GET /api/classes` - Sınıf listesi
- `GET /api/students?class_id={id}` - Sınıf öğrencileri
- `POST /api/attendance/bulk` - Toplu yoklama oluşturma
- `POST /api/attendance/mark-all-present` - Tümünü "Geldi" işaretle
- `GET /api/ai/attendance-analysis` - AI devamsızlık analizi

**İzinler:** `attendance.read`, `attendance.write`, `attendance.take`

#### 16. Bulk Attendance (`/attendance/bulk`)
**Kullanılan API'ler:**
- `GET /api/classes` - Sınıf listesi
- `GET /api/students?class_id={id}` - Sınıf öğrencileri
- `POST /api/attendance/bulk` - Toplu yoklama

**İzinler:** `attendance.take`

#### 17. Student Attendance (`/attendance/student/{id}`)
**Kullanılan API'ler:**
- `GET /api/attendance?student_id={id}` - Öğrenci yoklaması
- `GET /api/students/{id}` - Öğrenci detayı

**İzinler:** `attendance.read`

#### 18. Monthly Attendance Report (`/attendance/monthly`)
**Kullanılan API'ler:**
- `GET /api/attendance` - Yoklama verileri
- `GET /api/dashboard/attendance-summary` - Yoklama özeti

**İzinler:** `attendance.read`

#### 19. Homework (`/homework`)
**Kullanılan API'ler:**
- `GET /api/homework` - Ödev listesi
- `POST /api/homework` - Ödev oluşturma
- `GET /api/homework/{id}` - Ödev detayı
- `PUT /api/homework/{id}` - Ödev güncelleme

**İzinler:** `students.read`, `students.write`

#### 20. Library (`/library`)
**Kullanılan API'ler:**
- `GET /api/library` - Kütüphane listesi
- `POST /api/library` - Kütüphane kaydı
- `GET /api/library/{id}` - Kütüphane detayı

**İzinler:** `students.read`, `students.write`

#### 21. Daily Reports (`/daily-reports`)
**Kullanılan API'ler:**
- `GET /api/daily-reports` - Günlük raporlar
- `POST /api/daily-reports` - Rapor oluşturma
- `GET /api/daily-reports/{id}` - Rapor detayı

**İzinler:** `students.read`, `students.write`

#### 22. Exams (`/exams`)
**Kullanılan API'ler:**
- `GET /api/exams` - Sınav listesi
- `POST /api/exams` - Sınav oluşturma
- `GET /api/exams/{id}` - Sınav detayı

**İzinler:** `students.read`, `students.write`

#### 23. Materials (`/materials`)
**Kullanılan API'ler:**
- `GET /api/materials` - Materyal listesi
- `POST /api/materials` - Materyal oluşturma
- `GET /api/materials/{id}` - Materyal detayı

**İzinler:** `students.read`, `students.write`

#### 24. Timetable (`/timetable`)
**Kullanılan API'ler:**
- `GET /api/timetable` - Ders programı
- `GET /api/timetable/{class_id}` - Sınıf programı

**İzinler:** `students.read`

### Veli Portalı

#### 25. Parent Dashboard (`/parent/dashboard`)
**Kullanılan API'ler:**
- `GET /api/parent/my-children` - Çocuklarım
- `GET /api/parent/child/{id}/today-status` - Günlük durum
- `GET /api/dashboard/summary` - Özet veriler

**İzinler:** `parent.view_children`, `parent.view_daily_report`

#### 26. My Children (`/parent/children`)
**Kullanılan API'ler:**
- `GET /api/parent/my-children` - Çocuklarım listesi
- `GET /api/parent/child/{id}/today-status` - Günlük durum

**İzinler:** `parent.view_children`

#### 27. Academic Status (`/parent/academic`)
**Kullanılan API'ler:**
- `GET /api/parent/child/{id}/grades` - Notlar
- `GET /api/parent/child/{id}/homework` - Ödevler

**İzinler:** `parent.view_children`

#### 28. Schedule (`/parent/schedule`)
**Kullanılan API'ler:**
- `GET /api/parent/child/{id}/schedule` - Ders programı

**İzinler:** `parent.view_children`

#### 29. Parent Homework (`/parent/homework`)
**Kullanılan API'ler:**
- `GET /api/parent/child/{id}/homework` - Ödevler

**İzinler:** `parent.view_children`

#### 30. Parent Materials (`/parent/materials`)
**Kullanılan API'ler:**
- `GET /api/materials` - Materyaller

**İzinler:** `parent.view_children`

#### 31. Parent Attendance (`/parent/attendance`)
**Kullanılan API'ler:**
- `GET /api/attendance?student_id={id}` - Devamsızlık
- `GET /api/parent/child/{id}/attendance` - Çocuk devamsızlığı

**İzinler:** `parent.view_attendance`

#### 32. Parent Finances (`/parent/finances`)
**Kullanılan API'ler:**
- `GET /api/debts?student_id={id}` - Borçlar
- `GET /api/payments?student_id={id}` - Ödemeler
- `GET /api/receipts?student_id={id}` - Makbuzlar

**İzinler:** `parent.view_finances`

#### 33. Health (`/parent/health`)
**Kullanılan API'ler:**
- `GET /api/parent/child/{id}/health` - Sağlık bilgileri
- `POST /api/parent/child/{id}/excuse-request` - İzin talebi
- `POST /api/parent/child/{id}/medicine-request` - İlaç talebi

**İzinler:** `parent.view_children`

#### 34. Communication (`/parent/communication`)
**Kullanılan API'ler:**
- `GET /api/messages` - Mesajlar
- `GET /api/announcements` - Duyurular

**İzinler:** `parent.view_children`

#### 35. Chat (`/parent/chat`)
**Kullanılan API'ler:**
- `GET /api/messages` - Mesaj geçmişi
- `POST /api/messages` - Mesaj gönderme
- `GET /api/parent/my-children` - Çocuklarım

**İzinler:** `parent.view_children`

#### 36. Parent Announcements (`/parent/announcements`)
**Kullanılan API'ler:**
- `GET /api/announcements` - Duyurular
- `GET /api/announcements/{id}` - Duyuru detayı

**İzinler:** `parent.view_children`

#### 37. Activities (`/parent/activities`)
**Kullanılan API'ler:**
- `GET /api/clubs` - Kulüpler
- `GET /api/parent/child/{id}/activities` - Aktiviteler

**İzinler:** `parent.view_children`

#### 38. Parent Reports (`/parent/reports`)
**Kullanılan API'ler:**
- `GET /api/parent/child/{id}/reports` - Raporlar
- `GET /api/daily-reports?student_id={id}` - Günlük raporlar

**İzinler:** `parent.view_children`

### İletişim Bölümü

#### 39. Parent Notices (`/parent-notices`)
**Kullanılan API'ler:**
- `GET /api/parent-notices` - Veli talepleri
- `POST /api/parent-notices` - Talep oluşturma
- `PUT /api/parent-notices/{id}` - Talep güncelleme

**İzinler:** `students.read`, `students.write`

#### 40. Appointments (`/appointments`)
**Kullanılan API'ler:**
- `GET /api/appointments` - Randevular
- `POST /api/appointments` - Randevu oluşturma
- `PUT /api/appointments/{id}` - Randevu güncelleme

**İzinler:** `students.read`, `students.write`

#### 41. Announcements (`/announcements`)
**Kullanılan API'ler:**
- `GET /api/announcements` - Duyuru listesi
- `POST /api/announcements` - Duyuru oluşturma
- `GET /api/announcements/{id}` - Duyuru detayı
- `PUT /api/announcements/{id}` - Duyuru güncelleme
- `DELETE /api/announcements/{id}` - Duyuru silme
- `POST /api/announcements/{id}/send` - Duyuru gönderme

**İzinler:** `announcements.read`, `announcements.write`

#### 42. Announcement Detail (`/announcements/{id}`)
**Kullanılan API'ler:**
- `GET /api/announcements/{id}` - Duyuru detayı
- `GET /api/communications/broadcast-jobs/{id}/delivery-summary` - Teslimat özeti

**İzinler:** `announcements.read`

#### 43. Notifications (`/notifications`)
**Kullanılan API'ler:**
- `GET /api/communications/broadcast-jobs` - Broadcast işleri
- `GET /api/communications/delivery-reports` - Teslimat raporları

**İzinler:** `notification.read`

#### 44. Outbox (`/outbox`)
**Kullanılan API'ler:**
- `GET /api/communications/broadcast-jobs` - Broadcast işleri
- `GET /api/communications/broadcast-jobs/{id}` - İş detayı
- `PUT /api/communications/broadcast-jobs/{id}` - İş güncelleme
- `POST /api/communications/broadcast-jobs/{id}/send` - Gönderme
- `DELETE /api/communications/broadcast-jobs/{id}` - İptal

**İzinler:** `notification.read`, `notification.write`

#### 45. Outbox Detail (`/outbox/{id}`)
**Kullanılan API'ler:**
- `GET /api/communications/broadcast-jobs/{id}` - İş detayı
- `GET /api/communications/broadcast-jobs/{id}/delivery-summary` - Teslimat özeti
- `GET /api/communications/delivery-reports?broadcast_job_id={id}` - Teslimat raporları

**İzinler:** `notification.read`

#### 46. Templates (`/notifications/templates`)
**Kullanılan API'ler:**
- `GET /api/communications/message-templates` - Şablon listesi
- `POST /api/communications/message-templates` - Şablon oluşturma

**İzinler:** `notification.read`, `notification.write`

#### 47. Template Form (`/notifications/templates/{id}`)
**Kullanılan API'ler:**
- `GET /api/communications/message-templates/{id}` - Şablon detayı
- `PUT /api/communications/message-templates/{id}` - Şablon güncelleme
- `DELETE /api/communications/message-templates/{id}` - Şablon silme

**İzinler:** `notification.write`

### Operasyon Bölümü

#### 48. Transport (`/transport`)
**Kullanılan API'ler:**
- `GET /api/bus` - Servis listesi
- `POST /api/bus` - Servis oluşturma
- `GET /api/bus/{id}` - Servis detayı

**İzinler:** `students.read`, `students.write`

#### 49. Canteen (`/canteen`)
**Kullanılan API'ler:**
- `GET /api/canteen` - Kantin ürünleri
- `POST /api/canteen` - Ürün oluşturma
- `PUT /api/canteen/{id}` - Ürün güncelleme

**İzinler:** `canteen.read`, `canteen.write`

#### 50. Canteen Sales (`/canteen/sales`)
**Kullanılan API'ler:**
- `GET /api/canteen/sales` - Satış kayıtları
- `POST /api/canteen/sales` - Satış oluşturma

**İzinler:** `canteen.write`

#### 51. Card Balance (`/canteen/card-balance`)
**Kullanılan API'ler:**
- `GET /api/rfid-cards` - Kart bilgileri
- `POST /api/canteen/balance` - Bakiye yükleme

**İzinler:** `canteen.read`, `canteen.write`

#### 52. Canteen Receipt (`/canteen/receipt`)
**Kullanılan API'ler:**
- `GET /api/canteen/receipts` - Makbuzlar
- `GET /api/canteen/receipts/{id}` - Makbuz detayı

**İzinler:** `canteen.read`

### Finans Bölümü

#### 53. Debts (`/finance/debts`)
**Kullanılan API'ler:**
- `GET /api/debts` - Borç listesi (sayfalama, filtreleme ile)
- `GET /api/debts/{id}` - Borç detayı
- `POST /api/debts` - Borç oluşturma
- `PUT /api/debts/{id}` - Borç güncelleme
- `DELETE /api/debts/{id}` - Borç silme

**İzinler:** `finance.read`, `finance.write`, `debts.read`, `debts.write`

#### 54. Payments (`/finance/payments`)
**Kullanılan API'ler:**
- `GET /api/payments` - Ödeme listesi
- `POST /api/payments` - Ödeme oluşturma
- `GET /api/payments/{id}` - Ödeme detayı
- `PUT /api/payments/{id}` - Ödeme güncelleme
- `DELETE /api/payments/{id}` - Ödeme silme
- `POST /api/payments/{id}/cancel` - Ödeme iptali
- `GET /api/ai/payment-forecast` - AI ödeme tahmini

**İzinler:** `finance.read`, `finance.write`, `payments.read`, `payments.write`

#### 55. Payment Form (`/finance/payments/new`)
**Kullanılan API'ler:**
- `GET /api/debts` - Borç listesi
- `POST /api/payments` - Ödeme oluşturma

**İzinler:** `finance.write`, `payments.create`

#### 56. Student Payments (`/finance/students/{id}`)
**Kullanılan API'ler:**
- `GET /api/debts?student_id={id}` - Öğrenci borçları
- `GET /api/payments?student_id={id}` - Öğrenci ödemeleri
- `GET /api/receipts?student_id={id}` - Öğrenci makbuzları

**İzinler:** `finance.read`

#### 57. Expenses (`/finance/expenses`)
**Kullanılan API'ler:**
- `GET /api/expenses` - Gider listesi
- `POST /api/expenses` - Gider oluşturma
- `GET /api/expenses/{id}` - Gider detayı
- `PUT /api/expenses/{id}` - Gider güncelleme
- `DELETE /api/expenses/{id}` - Gider silme

**İzinler:** `finance.read`, `finance.write`

#### 58. Receipts (`/finance/receipts`)
**Kullanılan API'ler:**
- `GET /api/receipts` - Makbuz listesi
- `GET /api/receipts/{id}` - Makbuz detayı
- `GET /api/ai/payment-forecast` - AI finansal öngörü

**İzinler:** `finance.read`, `receipt.read`

#### 59. Receipt Print (`/finance/receipts/{id}`)
**Kullanılan API'ler:**
- `GET /api/receipts/{id}` - Makbuz detayı
- `GET /api/receipts/{id}/pdf` - PDF indir
- `GET /api/payments/finances/payments/{payment_id}/receipt-pdf` - Makbuz PDF

**İzinler:** `finance.read`

#### 60. Payment (`/payment`)
**Kullanılan API'ler:**
- `POST /api/payments/iyzico/initialize` - iyzico ödeme başlatma
- `POST /api/payments/iyzico/callback` - iyzico callback

**İzinler:** `payments.create`

### Analiz Bölümü

#### 61. Reports (`/reports`)
**Kullanılan API'ler:**
- `GET /api/dashboard/financial-summary` - Finansal özet
- `GET /api/dashboard/attendance-summary` - Yoklama özeti
- `GET /api/dashboard/reports` - Raporlar

**İzinler:** `report.read`

#### 62. AI Analytics (`/ai/analytics`)
**Kullanılan API'ler:**
- `GET /api/ai/insights-report` - AI öngörüler
- `GET /api/ai/students-overview` - Öğrenci analizi
- `GET /api/ai/attendance-analysis` - Devamsızlık analizi
- `GET /api/ai/payment-forecast` - Ödeme tahmini

**İzinler:** `ai.view`

### Sistem Bölümü

#### 63. RFID Cards (`/rfid-cards`)
**Kullanılan API'ler:**
- `GET /api/rfid-cards` - Kart listesi
- `POST /api/rfid-cards` - Kart oluşturma
- `PUT /api/rfid-cards/{id}` - Kart güncelleme
- `DELETE /api/rfid-cards/{id}` - Kart silme

**İzinler:** `settings.read`, `settings.write`

#### 64. Devices (`/devices`)
**Kullanılan API'ler:**
- `GET /api/devices` - Cihaz listesi
- `POST /api/devices` - Cihaz oluşturma
- `GET /api/devices/{id}` - Cihaz detayı
- `PUT /api/devices/{id}` - Cihaz güncelleme

**İzinler:** `settings.read`, `settings.write`

#### 65. Settings (`/settings`)
**Kullanılan API'ler:**
- `GET /api/settings` - Ayarlar
- `PUT /api/settings` - Ayar güncelleme

**İzinler:** `settings.read`, `settings.write`

#### 66. Security (`/security`)
**Kullanılan API'ler:**
- `GET /api/security` - Güvenlik ayarları
- `PUT /api/security` - Güvenlik güncelleme

**İzinler:** `settings.read`, `settings.write`

### Diğer Ekranlar

#### 67. Consents (`/consents`)
**Kullanılan API'ler:**
- `GET /api/consents` - İzin listesi
- `POST /api/consents` - İzin oluşturma

**İzinler:** `students.read`, `students.write`

#### 68. Guidance (`/guidance`)
**Kullanılan API'ler:**
- `GET /api/guidance` - Rehberlik kayıtları
- `POST /api/guidance` - Kayıt oluşturma

**İzinler:** `students.read`, `students.write`

#### 69. Health (`/health`)
**Kullanılan API'ler:**
- `GET /api/health` - Sağlık kayıtları
- `POST /api/health` - Kayıt oluşturma

**İzinler:** `students.read`, `students.write`

#### 70. Infirmary (`/infirmary`)
**Kullanılan API'ler:**
- `GET /api/infirmary` - Sağlık oda kayıtları
- `POST /api/infirmary` - Kayıt oluşturma

**İzinler:** `students.read`, `students.write`

#### 71. Inventory (`/inventory`)
**Kullanılan API'ler:**
- `GET /api/inventory` - Envanter listesi
- `POST /api/inventory` - Envanter oluşturma

**İzinler:** `settings.read`, `settings.write`

#### 72. Clubs (`/clubs`)
**Kullanılan API'ler:**
- `GET /api/clubs` - Kulüp listesi
- `POST /api/clubs` - Kulüp oluşturma

**İzinler:** `students.read`, `students.write`

#### 73. Surveys (`/surveys`)
**Kullanılan API'ler:**
- `GET /api/surveys` - Anket listesi
- `POST /api/surveys` - Anket oluşturma

**İzinler:** `students.read`, `students.write`

#### 74. Tutoring (`/tutoring`)
**Kullanılan API'ler:**
- `GET /api/tutoring` - Etüt kayıtları
- `POST /api/tutoring` - Kayıt oluşturma

**İzinler:** `students.read`, `students.write`

#### 75. Payroll (`/payroll`)
**Kullanılan API'ler:**
- `GET /api/payroll` - Maaş listesi
- `POST /api/payroll` - Maaş oluşturma

**İzinler:** `finance.read`, `finance.write`

#### 76. User Create (`/users/create`)
**Kullanılan API'ler:**
- `POST /api/users` - Kullanıcı oluşturma
- `GET /api/roles` - Roller

**İzinler:** `users.write`

#### 77. User Detail (`/users/{id}`)
**Kullanılan API'ler:**
- `GET /api/users/{id}` - Kullanıcı detayı
- `PUT /api/users/{id}` - Kullanıcı güncelleme
- `DELETE /api/users/{id}` - Kullanıcı silme

**İzinler:** `users.read`, `users.write`

#### 78. Staff Detail (`/staff/{id}`)
**Kullanılan API'ler:**
- `GET /api/staff/{id}` - Personel detayı
- `PUT /api/staff/{id}` - Personel güncelleme

**İzinler:** `users.read`, `users.write`

#### 79. Organization Detail (`/organizations/{id}`)
**Kullanılan API'ler:**
- `GET /api/organizations/{id}` - Kurum detayı
- `PUT /api/organizations/{id}` - Kurum güncelleme

**İzinler:** `org.read`, `org.write`

#### 80. Library Detail (`/library/{id}`)
**Kullanılan API'ler:**
- `GET /api/library/{id}` - Kütüphane detayı
- `PUT /api/library/{id}` - Kayıt güncelleme

**İzinler:** `students.read`, `students.write`

#### 81. Role Permissions (`/roles/{id}/permissions`)
**Kullanılan API'ler:**
- `GET /api/roles/{id}/permissions` - Rol yetkileri
- `POST /api/roles/{id}/permissions` - Yetki atama
- `DELETE /api/roles/{id}/permissions/{permission_id}` - Yetki kaldırma

**İzinler:** `users.write`

## Teknoloji Stack

### Backend
- **Framework**: FastAPI (Python)
- **Database**: PostgreSQL / SQLite
- **ORM**: SQLAlchemy
- **Authentication**: JWT
- **Payment Integration**: iyzico
- **Architecture**: Layered Architecture (Domain, Application, Infrastructure)

### Frontend
- **Framework**: React with TypeScript
- **UI Library**: Custom components
- **State Management**: React Context
- **HTTP Client**: Axios
- **Routing**: React Router

## İzin Sistemi

Sistem rol bazlı yetkilendirme (RBAC) kullanır. Temel izin modülleri:

- `dashboard.view` - Dashboard görüntüleme
- `org.read` / `org.write` - Kurum okuma/yazma
- `branch.read` / `branch.write` - Şube okuma/yazma
- `users.read` / `users.write` - Kullanıcı okuma/yazma
- `students.read` / `students.write` - Öğrenci okuma/yazma
- `students.import` / `students.export` - Öğrenci içe/dışa aktarma
- `parents.read` / `parents.write` - Veli okuma/yazma
- `classes.read` / `classes.write` - Sınıf okuma/yazma
- `attendance.read` / `attendance.write` / `attendance.take` - Yoklama işlemleri
- `finance.read` / `finance.write` - Finans işlemleri
- `debts.read` / `debts.write` - Borç işlemleri
- `payments.read` / `payments.write` / `payments.create` / `payments.update` / `payments.delete` - Ödeme işlemleri
- `announcements.read` / `announcements.write` - Duyuru işlemleri
- `notification.read` / `notification.write` - Bildirim işlemleri
- `canteen.read` / `canteen.write` - Kantin işlemleri
- `settings.read` / `settings.write` - Ayar işlemleri
- `parent.view_children` - Veli çocuk görüntüleme
- `parent.view_attendance` - Veli yoklama görüntüleme
- `parent.view_finances` - Veli finans görüntüleme

## Özel Özellikler

### Multi-Tenancy
- Organization bazlı veri izolasyonu
- Branch bazlı erişim kontrolü
- Tenant context üzerinden veri filtreleme

### Güvenlik
- JWT token authentication
- Refresh token mekanizması
- Rate limiting
- Password reset flow
- Login attempt tracking
- Audit logging

### İletişim
- Multi-channel notifications (SMS, Email, WhatsApp)
- Message templates
- Broadcast jobs
- Delivery reports
- Parent-teacher chat

### Finans
- Debt management
- Payment processing
- iyzico integration
- Receipt generation (PDF)
- Installment plans
- Expense tracking

### Operasyon
- RFID card management
- Device management
- Attendance kiosk integration
- Canteen operations
- Transport management

Bu doküman SCS360 projesinin tüm bileşenlerini kapsayan kapsamlı bir referans olarak kullanılabilir.
<!-- SCS360_SOURCE_END: 25 -->

---

<a id="belge-26"></a>

## 26. PROJE_DOKÜMANTASYONU.md

Kaynak: [PROJE_DOKÜMANTASYONU.md](PROJE_DOKÜMANTASYONU.md)  
SHA-256: `6ae97587c249b6ff80ae7b0f9585622977e59864dda4b6be7ec8766db09489cd`

<!-- SCS360_SOURCE_BEGIN: 26 -->
# SCS360 Proje Dokümantasyonu

Bu doküman SCS360 projesinin tüm API'lerini, veritabanı tablolarını ve frontend ekranlarını içeren kapsamlı bir referanstır.

## Proje Genel Bakış

SCS360, anaokulu, kreş, etüt ve kurs merkezleri için yönetim sistemi olan kapsamlı bir eğitim yönetim platformudur.

## Backend API Endpoints

### Temel Bileşenler
- **API Base URL**: `/api` 
- **Authentication**: JWT token based
- **Multi-tenancy**: Organization ve Branch bazlı izolasyon
- **Permission System**: Rol bazlı yetkilendirme

### API Modülleri

#### 1. Authentication (`/api/auth`)
- `POST /api/auth/login` - Kullanıcı girişi
- `POST /api/auth/refresh` - Token yenileme
- `POST /api/auth/logout` - Çıkış
- `GET /api/auth/me` - Mevcut kullanıcı bilgileri
- `POST /api/auth/forgot-password` - Şifre sıfırlama isteği
- `POST /api/auth/reset-password` - Şifre sıfırlama

#### 2. Organizations (`/api/organizations`)
- `GET /api/organizations` - Kurum listesi
- `POST /api/organizations` - Kurum oluşturma
- `GET /api/organizations/{org_id}` - Kurum detayı
- `PUT /api/organizations/{org_id}` - Kurum güncelleme
- `DELETE /api/organizations/{org_id}` - Kurum silme (pasife alma)

#### 3. Branches (`/api/branches`)
- `GET /api/branches` - Şube listesi
- `POST /api/branches` - Şube oluşturma
- `GET /api/branches/{branch_id}` - Şube detayı
- `PUT /api/branches/{branch_id}` - Şube güncelleme
- `DELETE /api/branches/{branch_id}` - Şube silme (pasife alma)

#### 4. Users (`/api/users`)
- `GET /api/users` - Kullanıcı listesi
- `POST /api/users` - Kullanıcı oluşturma
- `GET /api/users/{user_id}` - Kullanıcı detayı
- `PUT /api/users/{user_id}` - Kullanıcı güncelleme
- `DELETE /api/users/{user_id}` - Kullanıcı silme

#### 5. Students (`/api/students`)
- `POST /api/students` - Öğrenci oluşturma
- `GET /api/students` - Öğrenci listesi (filtreleme ile)
- `GET /api/students/{student_id}` - Öğrenci detayı
- `PUT /api/students/{student_id}` - Öğrenci güncelleme
- `DELETE /api/students/{student_id}` - Öğrenci silme
- `POST /api/students/import-excel` - Excel'den öğrenci içe aktarma
- `GET /api/students/export-excel` - Öğrencileri Excel'e dışa aktarma

#### 6. Classes (`/api/classes`)
- `POST /api/classes` - Sınıf oluşturma
- `GET /api/classes` - Sınıf listesi
- `GET /api/classes/{class_id}` - Sınıf detayı
- `PUT /api/classes/{class_id}` - Sınıf güncelleme
- `DELETE /api/classes/{class_id}` - Sınıf silme
- `POST /api/classes/{class_id}/transfer-students` - Öğrenci transferi

#### 7. Attendance (`/api/attendance`)
- `POST /api/attendance` - Yoklama oluşturma
- `GET /api/attendance` - Yoklama listesi (sınıf, öğrenci, tarih filtreleri ile)
- `GET /api/attendance/{attendance_id}` - Yoklama detayı
- `PUT /api/attendance/{attendance_id}` - Yoklama güncelleme
- `DELETE /api/attendance/{attendance_id}` - Yoklama silme
- `POST /api/attendance/bulk` - Toplu yoklama oluşturma (öğretmenler için)
- `POST /api/attendance/mark-all-present` - Tümünü "Geldi" işaretle

**İzinler:** `attendance.read`, `attendance.write`, `attendance.take` 

#### 8. Debts (`/api/debts`)
- `GET /api/debts` - Borç listesi
- `GET /api/debts/{debt_id}` - Borç detayı
- `POST /api/debts` - Borç oluşturma
- `PUT /api/debts/{debt_id}` - Borç güncelleme
- `DELETE /api/debts/{debt_id}` - Borç silme

#### 9. Payments (`/api/payments`)

##### Basic Operations
- `POST /api/payments` - Ödeme oluşturma
- `GET /api/payments` - Ödeme listesi
- `GET /api/payments/{payment_id}` - Ödeme detayı
- `PUT /api/payments/{payment_id}` - Ödeme güncelleme
- `DELETE /api/payments/{payment_id}` - Ödeme silme

##### iyzico Integration
- `POST /api/payments/iyzico/initialize` - iyzico ödeme başlatma
- `POST /api/payments/iyzico/callback` - iyzico callback

##### Finance Operations
- `POST /api/payments/finances/invoices/generate-plan` - Taksit planı oluşturma
- `POST /api/payments/finances/payments/collect` - Ödeme toplama
- `GET /api/payments/finances/payments/{payment_id}/receipt-pdf` - Makbuz PDF
- `POST /api/payments/finances/reminders/send` - Ödeme hatırlatması gönderme

**İzinler:** `payments.read`, `payments.write`, `payments.create`, `payments.update`, `payments.delete`, `finance.invoices_manage`, `finance.collect_payment` 

#### 10. Communications (`/api/communications`)

##### SMS Providers
- `GET /api/communications/sms-providers` - SMS sağlayıcı listesi
- `POST /api/communications/sms-providers` - SMS sağlayıcı oluşturma

##### Broadcast Jobs
- `GET /api/communications/broadcast-jobs` - Broadcast işleri listesi
- `POST /api/communications/broadcast-jobs` - Broadcast işi oluşturma
- `PUT /api/communications/broadcast-jobs/{job_id}` - Broadcast işi güncelleme
- `POST /api/communications/broadcast-jobs/{job_id}/send` - Broadcast gönderme
- `DELETE /api/communications/broadcast-jobs/{job_id}` - Broadcast iptal

##### Delivery Reports
- `GET /api/communications/delivery-reports` - Teslimat raporları
- `GET /api/communications/broadcast-jobs/{job_id}/delivery-summary` - Teslimat özeti

##### Message Templates
- `GET /api/communications/message-templates` - Mesaj şablonları
- `POST /api/communications/message-templates` - Şablon oluşturma

**İzinler:** `communications.read`, `communications.write` 

#### 11. Parent Portal (`/api/parent`)
- `GET /api/parent/my-children` - Veli çocukları listesi
- `GET /api/parent/child/{id}/today-status` - Çocuğun günlük durumu
- `GET /api/parent/child/{id}/timeline` - Çocuk zaman çizelgesi
- `GET /api/parent/child/{id}/attendance` - Çocuk devamsızlık takvimi (aylık)
- `GET /api/parent/child/{id}/grades` - Çocuk notları
- `GET /api/parent/child/{id}/schedule` - Çocuk ders programı
- `GET /api/parent/child/{id}/homework` - Çocuk ödevleri
- `GET /api/parent/child/{id}/financial-invoices` - Çocuk finansal faturaları
- `GET /api/parent/child/{id}/medicine-requests` - Çocuk ilaç talepleri
- `POST /api/parent/child/{id}/excuse-request` - İzin talebi
- `POST /api/parent/child/{id}/medicine-requests` - İlaç talebi
- `POST /api/parent/payments/checkout-session` - Ödeme oturumu oluşturma

**İzinler:** `parent.view_children`, `parent.view_daily_report`, `parent.view_attendance`, `parent.view_finances`, `parent.send_excuse`, `parent.medicine_request`, `parent.make_payment` 

#### 12. Diğer API Modülleri
- **Health**: `/api/health` - Sistem sağlık kontrolü
- **Dashboard**: `/api/dashboard` - Dashboard verileri
- **Announcements**: `/api/announcements` - Duyurular
- **Appointments**: `/api/appointments` - Randevular
- **Bus**: `/api/bus` - Servis yönetimi
- **Canteen**: `/api/canteen` - Kantin işlemleri
  - `GET /api/canteen/products` - Ürün listesi
  - `POST /api/canteen/products` - Ürün oluşturma
  - `PUT /api/canteen/products/{product_id}` - Ürün güncelleme
  - `DELETE /api/canteen/products/{product_id}` - Ürün silme
  - `GET /api/canteen/dietary-restrictions` - Diyet kısıtlamaları
  - `POST /api/canteen/dietary-restrictions` - Diyet kısıtlaması oluşturma
  - `DELETE /api/canteen/dietary-restrictions/{restriction_id}` - Diyet kısıtlaması silme
  - `POST /api/canteen/pos/checkout` - POS ödeme işlemi
  - `GET /api/canteen/student/{student_id}/wallet` - Öğrenci cüzdan bilgisi
  - `POST /api/canteen/student/{student_id}/wallet/top-up` - Cüzdan bakiye yükleme
  - `GET /api/canteen/orders` - Sipariş listesi
- **Clubs**: `/api/clubs` - Kulüpler
- **Consents**: `/api/consents` - İzinler
- **Daily Reports**: `/api/daily-reports` - Günlük raporlar
- **Debts**: `/api/debts` - Borçlar
- **Devices**: `/api/devices` - Cihazlar
- **Exams**: `/api/exams` - Sınavlar
- **Expenses**: `/api/expenses` - Giderler
- **Files**: `/api/files` - Dosya yönetimi
- **Guidance**: `/api/guidance` - Rehberlik
- **Hardware**: `/api/hardware` - Donanım
- **HQ**: `/api/hq` - Merkez yönetimi
- **Homework**: `/api/homework` - Ödevler
- **Data Import**: `/api/data-import` - Veri içe aktarma
- **Infirmary**: `/api/infirmary` - Sağlık oda
- **Inventory**: `/api/inventory` - Envanter
- **Library**: `/api/library` - Kütüphane
- **Materials**: `/api/materials` - Materyaller
- **Messages**: `/api/messages` - Mesajlar
- **Operations**: `/api/operations` - Operasyonlar
- **Outbox**: `/api/outbox` - Giden kutusu
- **Parent Notices**: `/api/parent-notices` - Veli talepleri
- **Parents**: `/api/parents` - Veliler
- **Payroll**: `/api/payroll` - Maaş
- **Pickup**: `/api/pickup` - Teslim alma
- **RFID Cards**: `/api/rfid-cards` - RFID kartlar
- **Card Numbers**: `/api/card-numbers` - Kart numaraları
- **Security**: `/api/security` - Güvenlik
- **Settings**: `/api/settings` - Ayarlar
- **Staff Operations**: `/api/staff-operations` - Personel operasyonları
- **Surveys**: `/api/surveys` - Anketler
- **Teacher**: `/api/teacher` - Öğretmen işlemleri
- **Timetable**: `/api/timetable` - Ders programı
- **Tutoring**: `/api/tutoring` - Etüt
- **User Roles**: `/api/user-roles` - Kullanıcı rolleri
- **AI Analytics**: `/api/ai-analytics` - AI analitikleri

## Veritabanı Tabloları

### Temel Tablolar

#### 1. organizations
Kurum/okul bilgilerini tutar
- `id` (UUID) - Primary Key
- `name` - Kurum adı
- `legal_name` - Resmi ad
- `tax_number` - Vergi numarası
- `tax_office` - Vergi dairesi
- `phone` - Telefon
- `email` - E-posta
- `address` - Adres
- `city` - Şehir
- `country` - Ülke
- `logo_url` - Logo URL
- `website` - Web sitesi
- `is_active` - Aktif mi
- `created_by` - Oluşturan
- `updated_by` - Güncelleyen
- `created_at` - Oluşturma tarihi
- `updated_at` - Güncelleme tarihi
- `deleted_at` - Silme tarihi (soft delete)

#### 2. branches
Şube bilgilerini tutar
- `id` (UUID) - Primary Key
- `organization_id` - Kurum ID (FK)
- `name` - Şube adı
- `code` - Şube kodu
- `phone` - Telefon
- `email` - E-posta
- `address` - Adres
- `city` - Şehir
- `capacity` - Kapasite
- `is_active` - Aktif mi
- `created_by` - Oluşturan
- `updated_by` - Güncelleyen
- `created_at` - Oluşturma tarihi
- `updated_at` - Güncelleme tarihi
- `deleted_at` - Silme tarihi (soft delete)

#### 3. users
Kullanıcı hesaplarını tutar
- `id` (UUID) - Primary Key
- `organization_id` - Kurum ID (FK)
- `email` - E-posta (unique)
- `password_hash` - Şifre hash
- `first_name` - Ad
- `last_name` - Soyad
- `phone` - Telefon
- `position` - Pozisyon
- `department` - Departman
- `status` - Durum (ACTIVE, PASSIVE, BLOCKED)
- `is_super_admin` - Süper admin mi
- `last_login_at` - Son giriş
- `created_by` - Oluşturan
- `updated_by` - Güncelleyen
- `created_at` - Oluşturma tarihi
- `updated_at` - Güncelleme tarihi
- `deleted_at` - Silme tarihi (soft delete)

#### 4. roles
Rol tanımlarını tutar
- `id` (UUID) - Primary Key
- `name` - Rol adı
- `slug` - Rol slug
- `description` - Açıklama
- `is_system` - Sistem rolü mü
- `organization_id` - Kurum ID (FK)
- `created_at` - Oluşturma tarihi
- `updated_at` - Güncelleme tarihi
- `deleted_at` - Silme tarihi (soft delete)

#### 5. permissions
İzin tanımlarını tutar
- `id` (UUID) - Primary Key
- `code` - İzin kodu (unique)
- `name` - İzin adı
- `module` - Modül
- `description` - Açıklama
- `created_at` - Oluşturma tarihi

#### 6. role_permissions
Rol-izin ilişkilerini tutar
- `role_id` - Rol ID (FK, PK)
- `permission_id` - İzin ID (FK, PK)
- `created_at` - Oluşturma tarihi

#### 7. user_roles
Kullanıcı-rol ilişkilerini tutar
- `user_id` - Kullanıcı ID (FK, PK)
- `role_id` - Rol ID (FK, PK)
- `assigned_at` - Atama tarihi
- `assigned_by` - Atayan

#### 8. user_branches
Kullanıcı-şube ilişkilerini tutar
- `user_id` - Kullanıcı ID (FK, PK)
- `branch_id` - Şube ID (FK, PK)
- `assigned_at` - Atama tarihi
- `assigned_by` - Atayan

### Güvenlik Tabloları

#### 9. refresh_tokens
Refresh token'ları tutar
- `id` (UUID) - Primary Key
- `user_id` - Kullanıcı ID (FK)
- `token_hash` - Token hash
- `family_id` - Token ailesi ID
- `expires_at` - Son kullanma tarihi
- `revoked_at` - İptal tarihi
- `replaced_by` - Yerine geçen token
- `created_at` - Oluşturma tarihi
- `ip_address` - IP adresi
- `user_agent` - User agent

#### 10. password_reset_tokens
Şifre sıfırlama token'larını tutar
- `id` (UUID) - Primary Key
- `user_id` - Kullanıcı ID (FK)
- `token_hash` - Token hash
- `expires_at` - Son kullanma tarihi
- `used_at` - Kullanım tarihi
- `created_at` - Oluşturma tarihi

#### 11. login_attempts
Giriş denemelerini tutar
- `id` (UUID) - Primary Key
- `email` - E-posta
- `ip_address` - IP adresi
- `user_agent` - User agent
- `success` - Başarılı mı
- `failure_reason` - Başarısızlık sebebi
- `attempted_at` - Deneme tarihi

### Eğitim Tabloları

#### 12. classes
Sınıf bilgilerini tutar
- `id` (UUID) - Primary Key
- `organization_id` - Kurum ID (FK)
- `branch_id` - Şube ID (FK)
- `name` - Sınıf adı
- `code` - Sınıf kodu
- `description` - Açıklama
- `capacity` - Kapasite
- `academic_year` - Akademik yıl
- `teacher_id` - Öğretmen ID (FK)
- `is_active` - Aktif mi
- `created_by` - Oluşturan
- `updated_by` - Güncelleyen
- `created_at` - Oluşturma tarihi
- `updated_at` - Güncelleme tarihi
- `deleted_at` - Silme tarihi (soft delete)

#### 13. class_teachers
Sınıf-öğretmen ilişkilerini tutar
- `class_id` - Sınıf ID (FK, PK)
- `user_id` - Kullanıcı ID (FK, PK)
- `is_primary` - Birincil mi
- `assigned_at` - Atama tarihi
- `assigned_by` - Atayan

#### 14. students
Öğrenci bilgilerini tutar
- `id` (UUID) - Primary Key
- `organization_id` - Kurum ID (FK)
- `branch_id` - Şube ID (FK)
- `class_id` - Sınıf ID (FK)
- `student_number` - Öğrenci numarası
- `first_name` - Ad
- `last_name` - Soyad
- `gender` - Cinsiyet (MALE, FEMALE, OTHER)
- `birth_date` - Doğum tarihi
- `enrollment_date` - Kayıt tarihi
- `status` - Durum (ACTIVE, PASSIVE, GRADUATED, LEFT)
- `photo_url` - Fotoğraf URL
- `health_notes` - Sağlık notları
- `notes` - Notlar
- `created_by` - Oluşturan
- `updated_by` - Güncelleyen
- `created_at` - Oluşturma tarihi
- `updated_at` - Güncelleme tarihi
- `deleted_at` - Silme tarihi (soft delete)

#### 15. parents
Veli bilgilerini tutar
- `id` (UUID) - Primary Key
- `organization_id` - Kurum ID (FK)
- `user_id` - Kullanıcı ID (FK)
- `first_name` - Ad
- `last_name` - Soyad
- `relation_type` - İlişki türü (MOTHER, FATHER, GUARDIAN, OTHER)
- `phone` - Telefon
- `sms_phone` - SMS telefonu
- `whatsapp_phone` - WhatsApp telefonu
- `email` - E-posta
- `address` - Adres
- `receive_notifications` - Bildirim al mı
- `created_by` - Oluşturan
- `updated_by` - Güncelleyen
- `created_at` - Oluşturma tarihi
- `updated_at` - Güncelleme tarihi
- `deleted_at` - Silme tarihi (soft delete)

#### 16. student_parents
Öğrenci-veli ilişkilerini tutar
- `student_id` - Öğrenci ID (FK, PK)
- `parent_id` - Veli ID (FK, PK)
- `is_primary` - Birincil mi
- `is_emergency` - Acil durum mi
- `created_at` - Oluşturma tarihi

#### 17. student_files
Öğrenci dosyalarını tutar
- `id` (UUID) - Primary Key
- `organization_id` - Kurum ID (FK)
- `branch_id` - Şube ID (FK)
- `student_id` - Öğrenci ID (FK)
- `category` - Kategori (IDENTITY, HEALTH_REPORT, REGISTRATION_CONTRACT, PAYMENT_CONTRACT, PHOTO, OTHER)
- `file_name` - Dosya adı
- `original_name` - Orijinal ad
- `mime_type` - MIME tipi
- `file_size` - Dosya boyutu
- `storage_path` - Depolama yolu
- `uploaded_by` - Yükleyen
- `created_at` - Oluşturma tarihi
- `updated_at` - Güncelleme tarihi
- `deleted_at` - Silme tarihi (soft delete)

#### 18. attendance_records
Yoklama kayıtlarını tutar
- `id` (UUID) - Primary Key
- `organization_id` - Kurum ID (FK)
- `branch_id` - Şube ID (FK)
- `class_id` - Sınıf ID (FK)
- `student_id` - Öğrenci ID (FK)
- `attendance_date` - Yoklama tarihi
- `status` - Durum (PRESENT, ABSENT, EXCUSED, LATE, HALF_DAY)
- `check_in_time` - Giriş saati
- `notes` - Notlar
- `recorded_by` - Kaydeden
- `created_at` - Oluşturma tarihi
- `updated_at` - Güncelleme tarihi
- `deleted_at` - Silme tarihi (soft delete)

#### 19. grades
Notları tutar
- `id` (UUID) - Primary Key
- `organization_id` - Kurum ID (FK)
- `branch_id` - Şube ID (FK)
- `class_id` - Sınıf ID (FK)
- `student_id` - Öğrenci ID (FK)
- `teacher_id` - Öğretmen ID (FK)
- `subject` - Ders (MATHEMATICS, SCIENCE, TURKISH, SOCIAL_STUDIES, ENGLISH, PHYSICAL_EDUCATION, ART, MUSIC, COMPUTER, RELIGION, OTHER)
- `grade_type` - Not türü (EXAM, QUIZ, HOMEWORK, PROJECT, PARTICIPATION, MIDTERM, FINAL)
- `score` - Puan
- `max_score` - Maksimum puan
- `exam_date` - Sınav tarihi
- `term` - Dönem
- `notes` - Notlar
- `created_by` - Oluşturan
- `updated_by` - Güncelleyen
- `created_at` - Oluşturma tarihi
- `updated_at` - Güncelleme tarihi

#### 20. daily_development_reports
Günlük gelişim raporlarını tutar
- `id` (UUID) - Primary Key
- `student_id` - Öğrenci ID (FK)
- `class_id` - Sınıf ID (FK)
- `date` - Tarih
- `meal_status` - Yemek durumu (ALL, HALF, NONE)
- `sleep_status` - Uyku durumu (SLEPT_WELL, SHORT, NO_SLEEP)
- `mood` - Ruh hali (HAPPY, CALM, UNSETTLED, TIRED)
- `activities` - Aktiviteler (JSON)
- `teacher_notes` - Öğretmen notları
- `recorded_by` - Kaydeden
- `created_at` - Oluşturma tarihi
- `updated_at` - Güncelleme tarihi

### Finans Tabloları

#### 21. debts
Borçları tutar
- `id` (UUID) - Primary Key
- `organization_id` - Kurum ID (FK)
- `branch_id` - Şube ID (FK)
- `student_id` - Öğrenci ID (FK)
- `debt_type` - Borç türü (EDUCATION, FOOD, SERVICE, STATIONERY, ACTIVITY, OTHER)
- `description` - Açıklama
- `amount` - Tutar
- `paid_amount` - Ödenen tutar
- `status` - Durum (UNPAID, PARTIALLY_PAID, PAID, OVERDUE, CANCELLED)
- `due_date` - Son ödeme tarihi
- `created_by` - Oluşturan
- `updated_by` - Güncelleyen
- `created_at` - Oluşturma tarihi
- `updated_at` - Güncelleme tarihi
- `deleted_at` - Silme tarihi (soft delete)

#### 22. payments
Ödemeleri tutar
- `id` (UUID) - Primary Key
- `organization_id` - Kurum ID (FK)
- `branch_id` - Şube ID (FK)
- `student_id` - Öğrenci ID (FK)
- `debt_id` - Borç ID (FK)
- `amount` - Tutar
- `payment_method` - Ödeme yöntemi (CASH, CREDIT_CARD, BANK_TRANSFER, EFT, OTHER)
- `payment_date` - Ödeme tarihi
- `status` - Durum
- `notes` - Notlar
- `received_by` - Alan
- `cancelled_at` - İptal tarihi
- `cancelled_by` - İptal eden
- `cancel_reason` - İptal sebebi
- `created_at` - Oluşturma tarihi
- `updated_at` - Güncelleme tarihi

#### 23. receipts
Makbuzları tutar
- `id` (UUID) - Primary Key
- `organization_id` - Kurum ID (FK)
- `branch_id` - Şube ID (FK)
- `student_id` - Öğrenci ID (FK)
- `payment_id` - Ödeme ID (FK, unique)
- `receipt_number` - Makbuz numarası (unique)
- `status` - Durum (ACTIVE, CANCELLED)
- `issued_at` - Düzenleme tarihi
- `issued_by` - Düzenleyen
- `pdf_path` - PDF yolu
- `remaining_debt` - Kalan borç
- `created_at` - Oluşturma tarihi
- `updated_at` - Güncelleme tarihi

#### 24. expenses
Giderleri tutar
- `id` (UUID) - Primary Key
- `organization_id` - Kurum ID (FK)
- `branch_id` - Şube ID (FK)
- `description` - Açıklama
- `category` - Kategori
- `amount` - Tutar
- `expense_date` - Gider tarihi
- `status` - Durum
- `notes` - Notlar
- `created_by` - Oluşturan
- `updated_by` - Güncelleyen
- `created_at` - Oluşturma tarihi
- `updated_at` - Güncelleme tarihi
- `deleted_at` - Silme tarihi (soft delete)

### İletişim Tabloları

#### 25. announcements
Duyuruları tutar
- `id` (UUID) - Primary Key
- `organization_id` - Kurum ID (FK)
- `branch_id` - Şube ID (FK)
- `class_id` - Sınıf ID (FK)
- `student_id` - Öğrenci ID (FK)
- `title` - Başlık
- `content` - İçerik
- `audience` - Hedef kitle (ALL_PARENTS, BRANCH_PARENTS, CLASS_PARENTS, SINGLE_STUDENT)
- `channels` - Kanallar (JSON)
- `status` - Durum (DRAFT, SCHEDULED, SENT, CANCELLED)
- `scheduled_at` - Planlanan tarih
- `sent_at` - Gönderim tarihi
- `created_by` - Oluşturan
- `created_at` - Oluşturma tarihi
- `updated_at` - Güncelleme tarihi
- `deleted_at` - Silme tarihi (soft delete)

#### 26. announcement_recipients
Duyuru alıcılarını tutar
- `id` (UUID) - Primary Key
- `announcement_id` - Duyuru ID (FK)
- `parent_id` - Veli ID (FK)
- `student_id` - Öğrenci ID (FK)
- `channel` - Kanal (EMAIL, SMS, WHATSAPP)
- `status` - Durum (PENDING, SENT, FAILED, CANCELLED)
- `sent_at` - Gönderim tarihi
- `error_message` - Hata mesajı
- `created_at` - Oluşturma tarihi

#### 27. message_templates
Mesaj şablonlarını tutar
- `id` (UUID) - Primary Key
- `organization_id` - Kurum ID (FK)
- `code` - Şablon kodu
- `name` - Şablon adı
- `channel` - Kanal (EMAIL, SMS, WHATSAPP)
- `subject` - Konu
- `body_template` - İçerik şablonu
- `is_active` - Aktif mi
- `created_at` - Oluşturma tarihi
- `updated_at` - Güncelleme tarihi
- `deleted_at` - Silme tarihi (soft delete)

#### 28. notification_jobs
Bildirim işlerini tutar
- `id` (UUID) - Primary Key
- `organization_id` - Kurum ID (FK)
- `branch_id` - Şube ID (FK)
- `channel` - Kanal (EMAIL, SMS, WHATSAPP)
- `template_code` - Şablon kodu
- `subject` - Konu
- `body` - İçerik
- `status` - Durum (PENDING, SENT, FAILED, CANCELLED)
- `retry_count` - Yeniden deneme sayısı
- `max_retries` - Maksimum deneme
- `scheduled_at` - Planlanan tarih
- `processed_at` - İşleme tarihi
- `reference_type` - Referans türü
- `reference_id` - Referans ID
- `created_by` - Oluşturan
- `created_at` - Oluşturma tarihi
- `updated_at` - Güncelleme tarihi

#### 29. notification_recipients
Bildirim alıcılarını tutar
- `id` (UUID) - Primary Key
- `notification_job_id` - Bildirim işi ID (FK)
- `parent_id` - Veli ID (FK)
- `user_id` - Kullanıcı ID (FK)
- `recipient_name` - Alıcı adı
- `recipient_address` - Alıcı adresi
- `status` - Durum (PENDING, SENT, FAILED, CANCELLED)
- `provider_response` - Sağlayıcı yanıtı (JSON)
- `error_message` - Hata mesajı
- `sent_at` - Gönderim tarihi
- `created_at` - Oluşturma tarihi
- `updated_at` - Güncelleme tarihi

#### 30. chat_messages
Sohbet mesajlarını tutar
- `id` (UUID) - Primary Key
- `sender_id` - Gönderen ID (FK)
- `receiver_id` - Alıcı ID (FK)
- `class_id` - Sınıf ID (FK)
- `content` - İçerik
- `attachment_url` - Ek URL
- `is_read` - Okundu mu
- `sent_at` - Gönderim tarihi
- `created_at` - Oluşturma tarihi
- `updated_at` - Güncelleme tarihi

### Sistem Tabloları

#### 31. integration_settings
Entegrasyon ayarlarını tutar
- `id` (UUID) - Primary Key
- `organization_id` - Kurum ID (FK)
- `provider` - Sağlayıcı (SMTP, NETGSM, TWILIO, META_WHATSAPP, OTHER)
- `config` - Konfigürasyon (JSON)
- `is_active` - Aktif mi
- `updated_by` - Güncelleyen
- `created_at` - Oluşturma tarihi
- `updated_at` - Güncelleme tarihi

#### 32. app_settings
Uygulama ayarlarını tutar
- `id` (UUID) - Primary Key
- `organization_id` - Kurum ID (FK)
- `setting_key` - Ayar anahtarı
- `setting_value` - Ayar değeri (JSON)
- `description` - Açıklama
- `updated_by` - Güncelleyen
- `created_at` - Oluşturma tarihi
- `updated_at` - Güncelleme tarihi

#### 33. audit_logs
Denetim loglarını tutar
- `id` (UUID) - Primary Key
- `organization_id` - Kurum ID (FK)
- `branch_id` - Şube ID (FK)
- `user_id` - Kullanıcı ID (FK)
- `action` - Aksiyon (CREATE, UPDATE, DELETE, LOGIN, LOGOUT, PAYMENT, CANCEL_PAYMENT, SEND_NOTIFICATION, OTHER)
- `entity_type` - Varlık türü
- `entity_id` - Varlık ID
- `old_values` - Eski değerler (JSON)
- `new_values` - Yeni değerler (JSON)
- `ip_address` - IP adresi
- `user_agent` - User agent
- `created_at` - Oluşturma tarihi

### Donanım Tabloları

#### 34. card_numbers
Kart numaralarını tutar
- `id` (String) - Primary Key
- `organization_id` - Kurum ID
- `branch_id` - Şube ID
- `card_number` - Kart numarası
- `status` - Durum (AVAILABLE, ASSIGNED, DAMAGED, LOST)
- `notes` - Notlar
- `purchased_date` - Satın alma tarihi
- `supplier` - Tedarikçi
- `created_at` - Oluşturma tarihi
- `updated_at` - Güncelleme tarihi

#### 35. devices
Cihazları tutar
- `id` (String) - Primary Key
- `organization_id` - Kurum ID
- `branch_id` - Şube ID
- `name` - Cihaz adı
- `device_type` - Cihaz türü (TURNSTILE, CARD_READER, DOOR_LOCK, ATTENDANCE_KIOSK, CANTEEN_TERMINAL)
- `serial_number` - Seri numarası
- `ip_address` - IP adresi
- `location` - Konum
- `status` - Durum (ACTIVE, INACTIVE, MAINTENANCE, BROKEN)
- `last_heartbeat` - Son kalp atışı
- `notes` - Notlar
- `created_at` - Oluşturma tarihi
- `updated_at` - Güncelleme tarihi

#### 36. rfid_cards
RFID kartlarını tutar
- `id` (String) - Primary Key
- `organization_id` - Kurum ID
- `branch_id` - Şube ID
- `card_number` - Kart numarası
- `card_type` - Kart türü (STUDENT, STAFF)
- `holder_id` - Sahip ID
- `holder_name` - Sahip adı
- `status` - Durum (ACTIVE, INACTIVE, BLOCKED)
- `issue_date` - Veriliş tarihi
- `expiry_date` - Son kullanma tarihi
- `created_at` - Oluşturma tarihi
- `updated_at` - Güncelleme tarihi

### Ders Programı Tabloları

#### 37. timetable_slots
Ders programı zamanlarını tutar
- `id` (UUID) - Primary Key
- `day` - Gün
- `start_time` - Başlangıç saati
- `end_time` - Bitiş saati
- `is_break` - Ara mı
- `created_at` - Oluşturma tarihi
- `updated_at` - Güncelleme tarihi

#### 38. classroom_assignments
Sınıf atamalarını tutar
- `id` (UUID) - Primary Key
- `class_id` - Sınıf ID (FK)
- `teacher_id` - Öğretmen ID (FK)
- `subject_id` - Ders ID
- `room_number` - Oda numarası
- `capacity` - Kapasite
- `created_at` - Oluşturma tarihi
- `updated_at` - Güncelleme tarihi

#### 39. timetables
Ders programlarını tutar
- `id` (UUID) - Primary Key
- `class_id` - Sınıf ID (FK)
- `slot_id` - Zaman ID (FK)
- `classroom_assignment_id` - Sınıf atama ID (FK)
- `academic_year` - Akademik yıl
- `semester` - Dönem
- `is_active` - Aktif mi
- `created_at` - Oluşturma tarihi
- `updated_at` - Güncelleme tarihi

## Frontend Ekranları ve API İlişkileri

### Yönetim Bölümü

#### 1. Dashboard (`/dashboard`)
**Kullanılan API'ler:**
- `GET /api/dashboard/summary` - Özet istatistikler (öğrenci sayısı, tahsilat, devamsızlık)
- `GET /api/dashboard/charts` - Aylık tahsilat grafiği
- `GET /api/dashboard/overview` - Genel bakış verileri
- `GET /api/ai/insights-report` - AI öngörüler ve öncelikli aksiyonlar
- `GET /api/admin/students` - Öğrenci listesi (chat için)
- `GET /api/users` - Kullanıcı listesi (chat için)

**İzinler:** `dashboard.view` 

#### 2. Organizations (`/organizations`)
**Kullanılan API'ler:**
- `GET /api/organizations` - Kurum listesi
- `POST /api/organizations` - Kurum oluşturma
- `GET /api/organizations/{id}` - Kurum detayı
- `PUT /api/organizations/{id}` - Kurum güncelleme
- `DELETE /api/organizations/{id}` - Kurum silme

**İzinler:** `org.read`, `org.write` 

#### 3. Branches (`/branches`)
**Kullanılan API'ler:**
- `GET /api/branches` - Şube listesi
- `POST /api/branches` - Şube oluşturma
- `GET /api/branches/{id}` - Şube detayı
- `PUT /api/branches/{id}` - Şube güncelleme
- `DELETE /api/branches/{id}` - Şube silme

**İzinler:** `branch.read`, `branch.write` 

#### 4. Users (`/users`)
**Kullanılan API'ler:**
- `GET /api/users` - Kullanıcı listesi
- `POST /api/users` - Kullanıcı oluşturma
- `GET /api/users/{id}` - Kullanıcı detayı
- `PUT /api/users/{id}` - Kullanıcı güncelleme
- `DELETE /api/users/{id}` - Kullanıcı silme

**İzinler:** `users.read`, `users.write` 

#### 5. Roles (`/roles`)
**Kullanılan API'ler:**
- `GET /api/roles` - Rol listesi
- `POST /api/roles` - Rol oluşturma
- `GET /api/roles/{id}` - Rol detayı
- `PUT /api/roles/{id}` - Rol güncelleme
- `DELETE /api/roles/{id}` - Rol silme
- `GET /api/roles/{id}/permissions` - Rol yetkileri

**İzinler:** `users.read`, `users.write` 

#### 6. Staff (`/staff`)
**Kullanılan API'ler:**
- `GET /api/staff` - Personel listesi
- `POST /api/staff` - Personel oluşturma
- `GET /api/staff/{id}` - Personel detayı
- `PUT /api/staff/{id}` - Personel güncelleme

**İzinler:** `users.read`, `users.write` 

#### 7. Teacher Portal (`/teacher`)
**Kullanılan API'ler:**
- `GET /api/dashboard/summary` - Öğretmen özeti
- `GET /api/dashboard/overview` - Genel bakış
- `GET /api/students` - Öğrenci listesi
- `GET /api/users` - Kullanıcı listesi

**İzinler:** `dashboard.view` 

### Eğitim Bölümü

#### 8. Students (`/students`)
**Kullanılan API'ler:**
- `GET /api/students` - Öğrenci listesi (arama, sayfalama ile)
- `POST /api/students` - Öğrenci oluşturma
- `GET /api/students/{id}` - Öğrenci detayı
- `PUT /api/students/{id}` - Öğrenci güncelleme
- `DELETE /api/students/{id}` - Öğrenci silme
- `POST /api/students/import-excel` - Excel'den içe aktarma
- `GET /api/students/export-excel` - Excel'e dışa aktarma
- `GET /api/ai/students-overview` - AI öğrenci analizi

**İzinler:** `students.read`, `students.write`, `students.import`, `students.export` 

#### 9. Student Detail (`/students/{id}`)
**Kullanılan API'ler:**
- `GET /api/students/{id}` - Öğrenci detayı
- `GET /api/students/{id}/files` - Öğrenci dosyaları
- `GET /api/students/{id}/parents` - Öğrenci velileri
- `GET /api/attendance?student_id={id}` - Öğrenci yoklaması

**İzinler:** `students.read` 

#### 10. Parents (`/parents`)
**Kullanılan API'ler:**
- `GET /api/parents` - Veli listesi
- `POST /api/parents` - Veli oluşturma
- `GET /api/parents/{id}` - Veli detayı
- `PUT /api/parents/{id}` - Veli güncelleme

**İzinler:** `parents.read`, `parents.write` 

#### 11. Classes (`/classes`)
**Kullanılan API'ler:**
- `GET /api/classes` - Sınıf listesi
- `POST /api/classes` - Sınıf oluşturma
- `GET /api/classes/{id}` - Sınıf detayı
- `PUT /api/classes/{id}` - Sınıf güncelleme
- `DELETE /api/classes/{id}` - Sınıf silme
- `POST /api/classes/{id}/transfer-students` - Öğrenci transferi

**İzinler:** `classes.read`, `classes.write` 

#### 12. Class Detail (`/classes/{id}`)
**Kullanılan API'ler:**
- `GET /api/classes/{id}` - Sınıf detayı
- `GET /api/students?class_id={id}` - Sınıf öğrencileri
- `GET /api/attendance?class_id={id}` - Sınıf yoklaması

**İzinler:** `classes.read`, `students.read` 

#### 13. Class Occupancy (`/classes/occupancy`)
**Kullanılan API'ler:**
- `GET /api/classes` - Sınıf listesi
- `GET /api/students` - Öğrenci sayıları

**İzinler:** `classes.read` 

#### 14. Assign Students (`/classes/{id}/assign`)
**Kullanılan API'ler:**
- `GET /api/students` - Öğrenci listesi
- `POST /api/classes/{id}/transfer-students` - Öğrenci atama

**İzinler:** `classes.write` 

#### 15. Attendance (`/attendance`)
**Kullanılan API'ler:**
- `GET /api/classes` - Sınıf listesi
- `GET /api/students?class_id={id}` - Sınıf öğrencileri
- `POST /api/attendance/bulk` - Toplu yoklama oluşturma
- `POST /api/attendance/mark-all-present` - Tümünü "Geldi" işaretle
- `GET /api/ai/attendance-analysis` - AI devamsızlık analizi

**İzinler:** `attendance.read`, `attendance.write`, `attendance.take` 

#### 16. Bulk Attendance (`/attendance/bulk`)
**Kullanılan API'ler:**
- `GET /api/classes` - Sınıf listesi
- `GET /api/students?class_id={id}` - Sınıf öğrencileri
- `POST /api/attendance/bulk` - Toplu yoklama

**İzinler:** `attendance.take` 

#### 17. Student Attendance (`/attendance/student/{id}`)
**Kullanılan API'ler:**
- `GET /api/attendance?student_id={id}` - Öğrenci yoklaması
- `GET /api/students/{id}` - Öğrenci detayı

**İzinler:** `attendance.read` 

#### 18. Monthly Attendance Report (`/attendance/monthly`)
**Kullanılan API'ler:**
- `GET /api/attendance` - Yoklama verileri
- `GET /api/dashboard/attendance-summary` - Yoklama özeti

**İzinler:** `attendance.read` 

#### 19. Homework (`/homework`)
**Kullanılan API'ler:**
- `GET /api/homework` - Ödev listesi
- `POST /api/homework` - Ödev oluşturma
- `GET /api/homework/{id}` - Ödev detayı
- `PUT /api/homework/{id}` - Ödev güncelleme

**İzinler:** `students.read`, `students.write` 

#### 20. Library (`/library`)
**Kullanılan API'ler:**
- `GET /api/library` - Kütüphane listesi
- `POST /api/library` - Kütüphane kaydı
- `GET /api/library/{id}` - Kütüphane detayı

**İzinler:** `students.read`, `students.write` 

#### 21. Daily Reports (`/daily-reports`)
**Kullanılan API'ler:**
- `GET /api/daily-reports` - Günlük raporlar
- `POST /api/daily-reports` - Rapor oluşturma
- `GET /api/daily-reports/{id}` - Rapor detayı

**İzinler:** `students.read`, `students.write` 

#### 22. Exams (`/exams`)
**Kullanılan API'ler:**
- `GET /api/exams` - Sınav listesi
- `POST /api/exams` - Sınav oluşturma
- `GET /api/exams/{id}` - Sınav detayı

**İzinler:** `students.read`, `students.write` 

#### 23. Materials (`/materials`)
**Kullanılan API'ler:**
- `GET /api/materials` - Materyal listesi
- `POST /api/materials` - Materyal oluşturma
- `GET /api/materials/{id}` - Materyal detayı

**İzinler:** `students.read`, `students.write` 

#### 24. Timetable (`/timetable`)
**Kullanılan API'ler:**
- `GET /api/timetable` - Ders programı
- `GET /api/timetable/{class_id}` - Sınıf programı

**İzinler:** `students.read` 

### Veli Portalı

#### 25. Parent Dashboard (`/parent/dashboard`)
**Kullanılan API'ler:**
- `GET /api/parent/my-children` - Çocuklarım
- `GET /api/parent/child/{id}/today-status` - Günlük durum
- `GET /api/dashboard/summary` - Özet veriler

**İzinler:** `parent.view_children`, `parent.view_daily_report` 

#### 26. My Children (`/parent/children`)
**Kullanılan API'ler:**
- `GET /api/parent/my-children` - Çocuklarım listesi
- `GET /api/parent/child/{id}/today-status` - Günlük durum

**İzinler:** `parent.view_children` 

#### 27. Academic Status (`/parent/academic`)
**Kullanılan API'ler:**
- `GET /api/parent/child/{id}/grades` - Notlar
- `GET /api/parent/child/{id}/homework` - Ödevler

**İzinler:** `parent.view_children` 

#### 28. Schedule (`/parent/schedule`)
**Kullanılan API'ler:**
- `GET /api/parent/child/{id}/schedule` - Ders programı

**İzinler:** `parent.view_children` 

#### 29. Parent Homework (`/parent/homework`)
**Kullanılan API'ler:**
- `GET /api/parent/child/{id}/homework` - Ödevler

**İzinler:** `parent.view_children` 

#### 30. Parent Materials (`/parent/materials`)
**Kullanılan API'ler:**
- `GET /api/materials` - Materyaller

**İzinler:** `parent.view_children` 

#### 31. Parent Attendance (`/parent/attendance`)
**Kullanılan API'ler:**
- `GET /api/attendance?student_id={id}` - Devamsızlık
- `GET /api/parent/child/{id}/attendance` - Çocuk devamsızlığı

**İzinler:** `parent.view_attendance` 

#### 32. Parent Finances (`/parent/finances`)
**Kullanılan API'ler:**
- `GET /api/debts?student_id={id}` - Borçlar
- `GET /api/payments?student_id={id}` - Ödemeler
- `GET /api/receipts?student_id={id}` - Makbuzlar

**İzinler:** `parent.view_finances` 

#### 33. Health (`/parent/health`)
**Kullanılan API'ler:**
- `GET /api/parent/child/{id}/health` - Sağlık bilgileri
- `POST /api/parent/child/{id}/excuse-request` - İzin talebi
- `POST /api/parent/child/{id}/medicine-request` - İlaç talebi

**İzinler:** `parent.view_children` 

#### 34. Communication (`/parent/communication`)
**Kullanılan API'ler:**
- `GET /api/messages` - Mesajlar
- `GET /api/announcements` - Duyurular

**İzinler:** `parent.view_children` 

#### 35. Chat (`/parent/chat`)
**Kullanılan API'ler:**
- `GET /api/messages` - Mesaj geçmişi
- `POST /api/messages` - Mesaj gönderme
- `GET /api/parent/my-children` - Çocuklarım

**İzinler:** `parent.view_children` 

#### 36. Parent Announcements (`/parent/announcements`)
**Kullanılan API'ler:**
- `GET /api/announcements` - Duyurular
- `GET /api/announcements/{id}` - Duyuru detayı

**İzinler:** `parent.view_children` 

#### 37. Activities (`/parent/activities`)
**Kullanılan API'ler:**
- `GET /api/clubs` - Kulüpler
- `GET /api/parent/child/{id}/activities` - Aktiviteler

**İzinler:** `parent.view_children` 

#### 38. Parent Reports (`/parent/reports`)
**Kullanılan API'ler:**
- `GET /api/parent/child/{id}/reports` - Raporlar
- `GET /api/daily-reports?student_id={id}` - Günlük raporlar

**İzinler:** `parent.view_children` 

### İletişim Bölümü

#### 39. Parent Notices (`/parent-notices`)
**Kullanılan API'ler:**
- `GET /api/parent-notices` - Veli talepleri
- `POST /api/parent-notices` - Talep oluşturma
- `PUT /api/parent-notices/{id}` - Talep güncelleme

**İzinler:** `students.read`, `students.write` 

#### 40. Appointments (`/appointments`)
**Kullanılan API'ler:**
- `GET /api/appointments` - Randevular
- `POST /api/appointments` - Randevu oluşturma
- `PUT /api/appointments/{id}` - Randevu güncelleme

**İzinler:** `students.read`, `students.write` 

#### 41. Announcements (`/announcements`)
**Kullanılan API'ler:**
- `GET /api/announcements` - Duyuru listesi
- `POST /api/announcements` - Duyuru oluşturma
- `GET /api/announcements/{id}` - Duyuru detayı
- `PUT /api/announcements/{id}` - Duyuru güncelleme
- `DELETE /api/announcements/{id}` - Duyuru silme
- `POST /api/announcements/{id}/send` - Duyuru gönderme

**İzinler:** `announcements.read`, `announcements.write` 

#### 42. Announcement Detail (`/announcements/{id}`)
**Kullanılan API'ler:**
- `GET /api/announcements/{id}` - Duyuru detayı
- `GET /api/communications/broadcast-jobs/{id}/delivery-summary` - Teslimat özeti

**İzinler:** `announcements.read` 

#### 43. Notifications (`/notifications`)
**Kullanılan API'ler:**
- `GET /api/communications/broadcast-jobs` - Broadcast işleri
- `GET /api/communications/delivery-reports` - Teslimat raporları

**İzinler:** `notification.read` 

#### 44. Outbox (`/outbox`)
**Kullanılan API'ler:**
- `GET /api/communications/broadcast-jobs` - Broadcast işleri
- `GET /api/communications/broadcast-jobs/{id}` - İş detayı
- `PUT /api/communications/broadcast-jobs/{id}` - İş güncelleme
- `POST /api/communications/broadcast-jobs/{id}/send` - Gönderme
- `DELETE /api/communications/broadcast-jobs/{id}` - İptal

**İzinler:** `notification.read`, `notification.write` 

#### 45. Outbox Detail (`/outbox/{id}`)
**Kullanılan API'ler:**
- `GET /api/communications/broadcast-jobs/{id}` - İş detayı
- `GET /api/communications/broadcast-jobs/{id}/delivery-summary` - Teslimat özeti
- `GET /api/communications/delivery-reports?broadcast_job_id={id}` - Teslimat raporları

**İzinler:** `notification.read` 

#### 46. Templates (`/notifications/templates`)
**Kullanılan API'ler:**
- `GET /api/communications/message-templates` - Şablon listesi
- `POST /api/communications/message-templates` - Şablon oluşturma

**İzinler:** `notification.read`, `notification.write` 

#### 47. Template Form (`/notifications/templates/{id}`)
**Kullanılan API'ler:**
- `GET /api/communications/message-templates/{id}` - Şablon detayı
- `PUT /api/communications/message-templates/{id}` - Şablon güncelleme
- `DELETE /api/communications/message-templates/{id}` - Şablon silme

**İzinler:** `notification.write` 

### Operasyon Bölümü

#### 48. Transport (`/transport`)
**Kullanılan API'ler:**
- `GET /api/bus` - Servis listesi
- `POST /api/bus` - Servis oluşturma
- `GET /api/bus/{id}` - Servis detayı

**İzinler:** `students.read`, `students.write` 

#### 49. Canteen (`/canteen`)
**Kullanılan API'ler:**
- `GET /api/canteen/products` - Ürün listesi
- `POST /api/canteen/products` - Ürün oluşturma
- `PUT /api/canteen/products/{product_id}` - Ürün güncelleme
- `DELETE /api/canteen/products/{product_id}` - Ürün silme
- `GET /api/canteen/dietary-restrictions` - Diyet kısıtlamaları
- `POST /api/canteen/dietary-restrictions` - Diyet kısıtlaması oluşturma

**İzinler:** `canteen.read`, `canteen.write` 

#### 50. Canteen Sales (`/canteen/sales`)
**Kullanılan API'ler:**
- `POST /api/canteen/pos/checkout` - POS ödeme işlemi
- `GET /api/canteen/orders` - Sipariş listesi

**İzinler:** `canteen.write` 

#### 51. Card Balance (`/canteen/card-balance`)
**Kullanılan API'ler:**
- `GET /api/canteen/student/{student_id}/wallet` - Öğrenci cüzdan bilgisi
- `POST /api/canteen/student/{student_id}/wallet/top-up` - Cüzdan bakiye yükleme
- `GET /api/rfid-cards` - Kart bilgileri

**İzinler:** `canteen.read`, `canteen.write` 

#### 52. Canteen Receipt (`/canteen/receipt`)
**Kullanılan API'ler:**
- `GET /api/canteen/orders` - Sipariş listesi
- `GET /api/canteen/orders/{order_id}` - Sipariş detayı

**İzinler:** `canteen.read` 

### Finans Bölümü

#### 53. Debts (`/finance/debts`)
**Kullanılan API'ler:**
- `GET /api/debts` - Borç listesi (sayfalama, filtreleme ile)
- `GET /api/debts/{id}` - Borç detayı
- `POST /api/debts` - Borç oluşturma
- `PUT /api/debts/{id}` - Borç güncelleme
- `DELETE /api/debts/{id}` - Borç silme

**İzinler:** `finance.read`, `finance.write`, `debts.read`, `debts.write` 

#### 54. Payments (`/finance/payments`)
**Kullanılan API'ler:**
- `GET /api/payments` - Ödeme listesi
- `POST /api/payments` - Ödeme oluşturma
- `GET /api/payments/{id}` - Ödeme detayı
- `PUT /api/payments/{id}` - Ödeme güncelleme
- `DELETE /api/payments/{id}` - Ödeme silme
- `POST /api/payments/{id}/cancel` - Ödeme iptali
- `GET /api/ai/payment-forecast` - AI ödeme tahmini

**İzinler:** `finance.read`, `finance.write`, `payments.read`, `payments.write` 

#### 55. Payment Form (`/finance/payments/new`)
**Kullanılan API'ler:**
- `GET /api/debts` - Borç listesi
- `POST /api/payments` - Ödeme oluşturma

**İzinler:** `finance.write`, `payments.create` 

#### 56. Student Payments (`/finance/students/{id}`)
**Kullanılan API'ler:**
- `GET /api/debts?student_id={id}` - Öğrenci borçları
- `GET /api/payments?student_id={id}` - Öğrenci ödemeleri
- `GET /api/receipts?student_id={id}` - Öğrenci makbuzları

**İzinler:** `finance.read` 

#### 57. Expenses (`/finance/expenses`)
**Kullanılan API'ler:**
- `GET /api/expenses` - Gider listesi
- `POST /api/expenses` - Gider oluşturma
- `GET /api/expenses/{id}` - Gider detayı
- `PUT /api/expenses/{id}` - Gider güncelleme
- `DELETE /api/expenses/{id}` - Gider silme

**İzinler:** `finance.read`, `finance.write` 

#### 58. Receipts (`/finance/receipts`)
**Kullanılan API'ler:**
- `GET /api/receipts` - Makbuz listesi
- `GET /api/receipts/{id}` - Makbuz detayı
- `GET /api/ai/payment-forecast` - AI finansal öngörü

**İzinler:** `finance.read`, `receipt.read` 

#### 59. Receipt Print (`/finance/receipts/{id}`)
**Kullanılan API'ler:**
- `GET /api/receipts/{id}` - Makbuz detayı
- `GET /api/receipts/{id}/pdf` - PDF indir
- `GET /api/payments/finances/payments/{payment_id}/receipt-pdf` - Makbuz PDF

**İzinler:** `finance.read` 

#### 60. Payment (`/payment`)
**Kullanılan API'ler:**
- `POST /api/payments/iyzico/initialize` - iyzico ödeme başlatma
- `POST /api/payments/iyzico/callback` - iyzico callback

**İzinler:** `payments.create` 

### Analiz Bölümü

#### 61. Reports (`/reports`)
**Kullanılan API'ler:**
- `GET /api/dashboard/financial-summary` - Finansal özet
- `GET /api/dashboard/attendance-summary` - Yoklama özeti
- `GET /api/dashboard/reports` - Raporlar

**İzinler:** `report.read` 

#### 62. AI Analytics (`/ai/analytics`)
**Kullanılan API'ler:**
- `GET /api/ai/insights-report` - AI öngörüler
- `GET /api/ai/students-overview` - Öğrenci analizi
- `GET /api/ai/attendance-analysis` - Devamsızlık analizi
- `GET /api/ai/payment-forecast` - Ödeme tahmini

**İzinler:** `ai.view` 

### Sistem Bölümü

#### 63. RFID Cards (`/rfid-cards`)
**Kullanılan API'ler:**
- `GET /api/rfid-cards` - Kart listesi
- `POST /api/rfid-cards` - Kart oluşturma
- `PUT /api/rfid-cards/{id}` - Kart güncelleme
- `DELETE /api/rfid-cards/{id}` - Kart silme

**İzinler:** `settings.read`, `settings.write` 

#### 64. Devices (`/devices`)
**Kullanılan API'ler:**
- `GET /api/devices` - Cihaz listesi
- `POST /api/devices` - Cihaz oluşturma
- `GET /api/devices/{id}` - Cihaz detayı
- `PUT /api/devices/{id}` - Cihaz güncelleme

**İzinler:** `settings.read`, `settings.write` 

#### 65. Settings (`/settings`)
**Kullanılan API'ler:**
- `GET /api/settings` - Ayarlar
- `PUT /api/settings` - Ayar güncelleme

**İzinler:** `settings.read`, `settings.write` 

#### 66. Security (`/security`)
**Kullanılan API'ler:**
- `GET /api/security` - Güvenlik ayarları
- `PUT /api/security` - Güvenlik güncelleme

**İzinler:** `settings.read`, `settings.write` 

### Diğer Ekranlar

#### 67. Consents (`/consents`)
**Kullanılan API'ler:**
- `GET /api/consents` - İzin listesi
- `POST /api/consents` - İzin oluşturma

**İzinler:** `students.read`, `students.write` 

#### 68. Guidance (`/guidance`)
**Kullanılan API'ler:**
- `GET /api/guidance` - Rehberlik kayıtları
- `POST /api/guidance` - Kayıt oluşturma

**İzinler:** `students.read`, `students.write` 

#### 69. Health (`/health`)
**Kullanılan API'ler:**
- `GET /api/health` - Sağlık kayıtları
- `POST /api/health` - Kayıt oluşturma

**İzinler:** `students.read`, `students.write` 

#### 70. Infirmary (`/infirmary`)
**Kullanılan API'ler:**
- `GET /api/infirmary` - Sağlık oda kayıtları
- `POST /api/infirmary` - Kayıt oluşturma

**İzinler:** `students.read`, `students.write` 

#### 71. Inventory (`/inventory`)
**Kullanılan API'ler:**
- `GET /api/inventory` - Envanter listesi
- `POST /api/inventory` - Envanter oluşturma

**İzinler:** `settings.read`, `settings.write` 

#### 72. Clubs (`/clubs`)
**Kullanılan API'ler:**
- `GET /api/clubs` - Kulüp listesi
- `POST /api/clubs` - Kulüp oluşturma

**İzinler:** `students.read`, `students.write` 

#### 73. Surveys (`/surveys`)
**Kullanılan API'ler:**
- `GET /api/surveys` - Anket listesi
- `POST /api/surveys` - Anket oluşturma

**İzinler:** `students.read`, `students.write` 

#### 74. Tutoring (`/tutoring`)
**Kullanılan API'ler:**
- `GET /api/tutoring` - Etüt kayıtları
- `POST /api/tutoring` - Kayıt oluşturma

**İzinler:** `students.read`, `students.write` 

#### 75. Payroll (`/payroll`)
**Kullanılan API'ler:**
- `GET /api/payroll` - Maaş listesi
- `POST /api/payroll` - Maaş oluşturma

**İzinler:** `finance.read`, `finance.write` 

#### 76. User Create (`/users/create`)
**Kullanılan API'ler:**
- `POST /api/users` - Kullanıcı oluşturma
- `GET /api/roles` - Roller

**İzinler:** `users.write` 

#### 77. User Detail (`/users/{id}`)
**Kullanılan API'ler:**
- `GET /api/users/{id}` - Kullanıcı detayı
- `PUT /api/users/{id}` - Kullanıcı güncelleme
- `DELETE /api/users/{id}` - Kullanıcı silme

**İzinler:** `users.read`, `users.write` 

#### 78. Staff Detail (`/staff/{id}`)
**Kullanılan API'ler:**
- `GET /api/staff/{id}` - Personel detayı
- `PUT /api/staff/{id}` - Personel güncelleme

**İzinler:** `users.read`, `users.write` 

#### 79. Organization Detail (`/organizations/{id}`)
**Kullanılan API'ler:**
- `GET /api/organizations/{id}` - Kurum detayı
- `PUT /api/organizations/{id}` - Kurum güncelleme

**İzinler:** `org.read`, `org.write` 

#### 80. Library Detail (`/library/{id}`)
**Kullanılan API'ler:**
- `GET /api/library/{id}` - Kütüphane detayı
- `PUT /api/library/{id}` - Kayıt güncelleme

**İzinler:** `students.read`, `students.write` 

#### 81. Role Permissions (`/roles/{id}/permissions`)
**Kullanılan API'ler:**
- `GET /api/roles/{id}/permissions` - Rol yetkileri
- `POST /api/roles/{id}/permissions` - Yetki atama
- `DELETE /api/roles/{id}/permissions/{permission_id}` - Yetki kaldırma

**İzinler:** `users.write` 

## Teknoloji Stack

### Backend
- **Framework**: FastAPI (Python)
- **Database**: PostgreSQL / SQLite
- **ORM**: SQLAlchemy
- **Authentication**: JWT
- **Payment Integration**: iyzico
- **Architecture**: Layered Architecture (Domain, Application, Infrastructure)

### Frontend
- **Framework**: React with TypeScript
- **UI Library**: Custom components
- **State Management**: React Context
- **HTTP Client**: Axios
- **Routing**: React Router

## İzin Sistemi

Sistem rol bazlı yetkilendirme (RBAC) kullanır. Temel izin modülleri:

- `dashboard.view` - Dashboard görüntüleme
- `org.read` / `org.write` - Kurum okuma/yazma
- `branch.read` / `branch.write` - Şube okuma/yazma
- `users.read` / `users.write` - Kullanıcı okuma/yazma
- `students.read` / `students.write` - Öğrenci okuma/yazma
- `students.import` / `students.export` - Öğrenci içe/dışa aktarma
- `parents.read` / `parents.write` - Veli okuma/yazma
- `classes.read` / `classes.write` - Sınıf okuma/yazma
- `attendance.read` / `attendance.write` / `attendance.take` - Yoklama işlemleri
- `finance.read` / `finance.write` - Finans işlemleri
- `debts.read` / `debts.write` - Borç işlemleri
- `payments.read` / `payments.write` / `payments.create` / `payments.update` / `payments.delete` - Ödeme işlemleri
- `announcements.read` / `announcements.write` - Duyuru işlemleri
- `notification.read` / `notification.write` - Bildirim işlemleri
- `canteen.read` / `canteen.write` - Kantin işlemleri
- `settings.read` / `settings.write` - Ayar işlemleri
- `parent.view_children` - Veli çocuk görüntüleme
- `parent.view_attendance` - Veli yoklama görüntüleme
- `parent.view_finances` - Veli finans görüntüleme

## Özel Özellikler

### Multi-Tenancy
- Organization bazlı veri izolasyonu
- Branch bazlı erişim kontrolü
- Tenant context üzerinden veri filtreleme

### Güvenlik
- JWT token authentication
- Refresh token mekanizması
- Rate limiting
- Password reset flow
- Login attempt tracking
- Audit logging

### İletişim
- Multi-channel notifications (SMS, Email, WhatsApp)
- Message templates
- Broadcast jobs
- Delivery reports
- Parent-teacher chat

### Finans
- Debt management
- Payment processing
- iyzico integration
- Receipt generation (PDF)
- Installment plans
- Expense tracking

### Operasyon
- RFID card management
- Device management
- Attendance kiosk integration
- Canteen operations
- Transport management

Bu doküman SCS360 projesinin tüm bileşenlerini kapsayan kapsamlı bir referans olarak kullanılabilir.

<!-- SCS360_SOURCE_END: 26 -->
