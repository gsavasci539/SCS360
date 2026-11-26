# Güvenlik ve KVKK canlıya geçiş kontrolü

Bu belge, uygulamadaki güvenlik kontrollerini işletim ve KVKK sorumluluklarından ayırır. Kodda güvenlik iyileştirmesi bulunması tek başına KVKK uyumu, sızma testi veya canlı ortamın güvenli olduğu anlamına gelmez. İnceleme tarihi: 26 Kasım 2026.

## Bu kaynak değişikliğinde uygulananlar

- `production` ve `staging`, tam HTTPS CORS origin listesi ve HTTPS parola sıfırlama adresi olmadan başlamaz. Ödeme akışı etkinse ilgili callback adresinin de HTTPS olması gerekir.
- Bilinmeyen `APP_ENV` değerleri reddedilir. `production` ve `staging` ortamlarında Swagger, ReDoc ve OpenAPI JSON uçları sunulmaz.
- API yanıtları merkezi `no-store`/`no-cache` başlıkları, MIME sniffing koruması, çerçeve engeli, referrer ve tarayıcı özellik politikaları alır.
- Nginx kaynak yapılandırmalarında `server_tokens off`, CSP, `X-Frame-Options: DENY`, Referrer-Policy ve Permissions-Policy bulunuyor. Frontend vhost’unda HSTS `max-age=31536000; includeSubDomains` olarak ayarlı ve `/assets/` alt konumunda güvenlik başlıkları ayrıca yineleniyor; dağıtım öncesi bütün tarayıcıya açık alt alan adlarının HTTPS durumu doğrulanmalı. CSP iki Nginx katmanında hizalı, `object-src 'none'` içeriyor; proxy yanıtlarında upstream `Server` ve `X-Powered-By` gizleniyor.
- Genel dosya uçları kurum/şube klasörüne bağlandı. Okuma `files.upload`, silme `files.delete` izni ve oturumun kurum/şube kapsamını gerektiriyor. Dosya yolu kanonik kök altında doğrulanıyor, dosyalar rastgele adla yazılıyor, yükleme boyutu/içeriği sınırlı ve indirme `attachment`/`no-store`. Eski kurumsuz/genel yollar güvenli sahiplik doğrulaması olmadığı için 404 verir; otomatik dosya taşıma yapılmadı.
- Okul ödeme oturumunun `request_digest` alanı, TCKN/pasaport numarasını da kapsayan fatura gövdesinden düz SHA-256 yerine JWT anahtarından amaç ayrımlı HMAC-SHA-256 üretir. Böylece yalnız veritabanı özeti ele geçirilmesi çevrimdışı TCKN tahminini doğrulamak için yeterli olmaz. Yetkili kullanıcının aynı işlem gövdesiyle eski açık oturumu yeniden göndermesi hâlinde eski SHA özeti doğrulanıp yeni HMAC ile değiştirilir. Bu düzeltme mevcut eski veritabanı/yedek kopyalarındaki SHA özetlerini silmez; onların saklama ve imha süreci ayrıca işletilmelidir. HMAC anahtarının rotasyonu açık ödeme oturumlarıyla koordine edilmelidir. Kaynak commit `670e6e6c39cfab39e973a213d68030d21ad62b60` normal push ve `ls-remote` ile doğrulandı.
- Ödeme formu TCKN/pasaport değerini sağlayıcı isteğinde kullanır; kaynakta okul ödeme `sessionStorage` kaydı yalnızca sürüm, işlem/borç kimlikleri, tutar ve durum alanlarını whitelist eder. Form değeri React belleğinde geçicidir. Sağlayıcının bu alanı isteme gereği, veri sorumlusunun hukuki işleme şartı, sağlayıcı sözleşmesi/alt işleyen ve aktarım koşulları uygulama kodundan kanıtlanmış sayılmaz; satın alma akışında gereklilik ve daha az müdahaleci seçenekler ayrıca doğrulanmalıdır.
- Kurum `tax_number` alanı işletme vergi numarası olarak tutulsa da gerçek kişi işletmesinde TCKN içerebilir. Kurum API'sinde `org.read` yetkisi tek başına artık bu alanı açmaz; tam değer yalnız `org.write` veya platform yöneticisi yanıtına verilir. Bu alanın veritabanındaki saklama biçimi ve makbuz/PDF gibi finans çıktılarındaki hukuki gereklilik, erişim ve retention ayrıca incelenmelidir; bu API maskelemesi depolanan değeri şifrelemez veya eski kopyaları silmez. Kaynak commit `728c324f4a7af8b564459a257d5c653aa1baa059` normal push ve `ls-remote` ile doğrulandı.
- Öğrenci ödeme geçmişinin yazdırma ekranındaki sabit örnek vergi numarası, adres, telefon ve personel adı kaldırıldı; kurum/şube adı yalnız öğrenci API yanıtındaki değerlerden gelir, kurum vergi numarası API sağlamadıkça yazdırılmaz. Bu ödeme ekranını resmi e-belge/fatura üreticisi yapmaz ve sağlayıcı/finans kaydındaki gerçek verileri değiştirmez. Kaynak commit `e7992ff77d1893b1a4073dc862e2a23c325f802d` normal push ve `ls-remote` ile doğrulandı.
- Web login/refresh/logout ayrı cookie oturum uçlarını kullanıyor. Access ve refresh token JSON gövdesine dönmüyor, `localStorage`/`sessionStorage` içinde tutulmuyor; access/refresh cookie `HttpOnly`, production/staging’de `Secure`, `SameSite=Lax`. Web’de yazma istekleri CSRF çift gönderim doğrulaması ve izinli `Origin` kontrolü alıyor. Android’in bearer `/auth/login`, `/auth/refresh`, `/auth/logout` sözleşmesi değişmedi.

## Canlıya çıkış öncesi zorunlu teknik kontroller

- İnternete yalnız TLS sonlandıran güvenilir ingress/WAF açılmalı. Genel erişimde 443 dışında yönetim, SSH, Docker API, PostgreSQL 5432, uygulama 5006, statik servis ve varsa Redis portları kapalı olmalı. 80 yalnız HTTPS yönlendirmesi için kullanılmalı.
- `docker-compose.yml` bu kaynakta yalnız `80:80` portunu yayınlıyor ve Nginx TLS sertifikası sonlandırmıyor. Harici TLS ingress, güvenlik duvarı, WAF, HSTS ve origin erişim kısıtları bu depodan doğrulanmış değildir; bu nedenle bu Compose ayarı tek başına canlı internet yayını için güvenli sayılmaz.
- API ve veritabanı yalnız özel servis ağlarında kalmalı. Yönetim erişimi VPN/allowlist ve MFA arkasında olmalı. Proxy güven başlıklarını yalnız güvenilen ingress üzerinden kabul etmeli.
- Rate limit endpoint bazında ortak Redis/Valkey deposuna taşınıyor (WIP). Compose örneği parola korumalı, dış porta açılmayan ve backend/worker dışındaki servislerden ayrılmış iç Redis ağı kullanır. Production/staging bellek tabanlı veya parolasız sayaç deposunu reddeder. Çoklu API worker/instance aynı Redis adresini paylaşmalıdır. Bu URI/Compose yapılandırması henüz gerçek Redis ile çalıştırılmadı; Docker servisi, kesinti davranışı, kapasite, TLS ve çoklu instance kabulü açık. WAF/ingress oran sınırı ayrıca gereklidir.

Rate-limit kaynak checkpoint'i normal push ve `ls-remote` ile SCS360 `codex/source-sync-20261111` SHA `436938cc9e2ea71ff36802885aa3bc3232738306` olarak doğrulandı. Canlıya dağıtım veya güvenlik kabulü değildir.

25 Kasım 2026 dependency taraması ilk backend-dev kontrolünde Black 26.3.1 için CVE-2026-114134 buldu; `requirements-dev.txt` Black 26.10.1'e yükseltildi. Sonraki backend-dev `pip-audit` ve frontend tam `npm audit --package-lock-only` bilinen zafiyet bulmadı. Bu sonuç Compose imajlarını, canlı image digestlerini veya gelecekteki advisory’leri kapsamaz.
- Black geliştirici bağımlılık güncellemesi SCS360 `codex/source-sync-20261111` SHA `81195e5722cc42cc38d5567dd2888ea0896cde9a` olarak push ve `ls-remote` ile doğrulandı. Bu kaynak checkpoint'i canlıya dağıtım veya uygulama güvenlik kabulü değildir.
- Frontend Nginx’te `/assets/` için ayrı cache başlığı diğer `add_header` yönergelerinin kalıtımını kesebildiğinden güvenlik başlıkları bu konuma da eklendi. Kaynakta `server_tokens off`, `Server` ve `X-Powered-By` upstream gizleme ve `includeSubDomains` HSTS var. Hedefli backend statik kontrolü 18/18 ve Ruff geçti; `nginx -t`, container ve canlı alan adı doğrulanmadı. `includeSubDomains` dağıtılmadan önce tüm tarayıcıya açık alt alan adlarının HTTPS envanteri doğrulanmalı. SCS360 `codex/source-sync-20261111` SHA `d4864250ea4de148c0bbe1b0090543f6d3624246` push ve `ls-remote` ile doğrulandı; bu canlıya hazır kabulü değildir.
- Devam kaydı güncellemesi SCS360 `codex/source-sync-20261111` SHA `48596b7bed2a67b4b3b0361c1ef15e9f848b8ce3` olarak push/`ls-remote` ile doğrulandı.
- Web access/refresh tokenları `localStorage`/`sessionStorage` içine yazılmıyor; access/refresh `HttpOnly`, production/staging `Secure`, `SameSite=Lax` cookie kullanılıyor ve mutasyonlarda CSRF tokenı+izinli Origin denetleniyor. XSS yine açık kullanıcının oturumu adına işlem yaptırabilir; cookie geçişi XSS’i çözmez. CSP/XSS incelemesi, bağımsız tarayıcı testi ve gerçek HTTPS üzerinde SameSite/CORS/proxy doğrulaması hâlâ gerekli. Cookie oturumu HTTPS ve aynı site üzerinden frontend/API yayın varsayımına dayanır.
- Veritabanı, özel dosya deposu ve yedekler için aktarımda ve saklamada şifreleme, anahtar kasası, anahtar döndürme, erişim ayrımı, değiştirilemez denetim izi, yedek geri yükleme provası ve silme/yaşam döngüsü doğrulanmalı.
- Sürüm adayı üzerinde bağımlılık/SBOM taraması, statik ve dinamik güvenlik testi, tenant/rol/şube izolasyonu regresyonu ve bağımsız sızma testi tamamlanmalı. Bulgular kapatılmadan “sızmaya kapalı” veya “canlıya hazır” denmemeli.
- Android canlı sürümünde HTTPS zorunlu olmalı; debug HTTP, test endpointi, imza anahtarı ve üretim API adresi birbirinden ayrılıp mağaza öncesi incelenmeli.

## KVKK için kurum ve işletme işlemleri

- Veri sorumlusu/veri işleyen rollerini, okul ile SaaS sağlayıcısı arasındaki talimat ve sözleşmeleri; veri kategorisi, ilgili kişi, amaç, hukuki sebep, alıcı, aktarım ve saklama süresi envanterini işletme bazında belirleyin.
- Öğrenci/çocuk verileri ile sağlık ve benzeri özel nitelikli veri akışlarını ayrı haritalandırın. Gereksiz alanı toplamayı, erişimi ve saklama süresini azaltın; görev temelli erişim ve düzenli yetki gözden geçirmesi yapın.
- Aydınlatma, ilgili kişi başvuruları, düzeltme/silme ve saklama-imha süreçleri, saklama politikası, veri işleyen sözleşmeleri, personel gizlilik/güvenlik eğitimi ve ihlal müdahale sorumlularını kurum adına tamamlayın.
- Yurt dışı bulut, e-posta, mesaj, analiz, yedek veya yapay zekâ sağlayıcısına aktarım olup olmadığını uçtan uca belirleyin. Aktarım varsa güncel KVKK Kanunu 9. madde mekanizması ve gerekli Kurul bildirimlerini hukuk/uyum sorumlusuyla doğrulayın.
- İhlal tatbikatı ve iletişim planı oluşturun. Kurulun kararlarına göre Kurula bildirim için en geç 72 saat kuralı ve etkilenen kişilere makul en kısa sürede bildirim süreci işletilebilir olmalı.

## 26 Kasım kaynak incelemesi — hassas debug çıktısı (WIP)

Borç listeleme öğrenci UUID’lerini; sınıf liste/detay ve repository kodu sınıf/öğretmen adlarını ve kimliklerini `print()` ile stdout’a yazıyordu. Bu çağrılar kaldırıldı; API yanıt sözleşmesi değiştirilmedi. Kod SHA `c8c3c33c9623e712a39d0355fec82382fc60351f` olarak normal push ve `ls-remote` ile doğrulandı. Hedefli test çalıştırılmadı; bu değişiklik canlı loglardan eski kayıtları silmez, bütün uygulamadaki logları kapsamaz ve güvenlik/KVKK veya canlıya hazır kabulü değildir. Kalan iş: backend genelinde hassas log taraması ve çalışan Nginx/ingress/container konfigürasyonu ile runtime doğrulama.

## Durum

25 Kasım 2026'da yapılan salt-okunur GET isteğinde `scs360.com.tr` yanıtı `nginx/1.18.0 (Ubuntu)` gösterdi; `X-Content-Type-Options` dışındaki incelenen başlıklar yoktu. `/iletisim` ve `/.well-known/security.txt` de gerçek iletişim/bildirim içeriği yerine SPA `index.html` döndürdü. Tarama bulguları canlı için doğrulandı. Repo Nginx kaynakları güçlendirildi; sonradan frontend statik `/assets/` konumu için üst vhost başlıkları yinelendi ve HSTS `includeSubDomains` olarak ayarlandı. Bu kaynak değişiklikleri üretime dağıtılmadı; aktif TLS terminatörü ve vhost yapılandırması repo ile eşleşmeyebilir. Alt alan adlarının HTTPS envanteri canlıya çıkmadan doğrulanmalı.

Kaynak değişikliği SCS360 `codex/source-sync-20261111` dalına normal push ile gönderildi ve `ls-remote` SHA `7892eb31aad20e3847cc40f89fa877cf158aa402` ile doğrulandı. Bu yalnız kaynak checkpoint'idir.

`/.well-known/security.txt` için kuruluş adına izlenen, doğrulanmış bir güvenlik bildirim adresi/kanalı bulunamadı. Eski dokümandaki örnek e-posta kullanılmadı; gerçek iletişim kanalı tanımlanıp izleme sorumlusu atanıncaya kadar bu tarama bulgusu açık kalır.

Uygulama katmanındaki bu kontrol ve düzeltmeler sınırlı bir güvenlik checkpoint'idir. Canlı sunucu/edge firewall, TLS, yedek şifreleme/geri yükleme, WAF, dağıtık rate limit, bağımsız penetrasyon testi ve kurumların KVKK süreçleri bu kod değişikliğiyle doğrulanmış değildir. Bunlar tamamlanana kadar canlı güvenlik veya KVKK uyumu için kabul verilmez.

26 Kasım 2026 API hata yanıtı checkpoint'i: cookie oturumunda CSRF reddinin özel 403 yanıtına da `Permissions-Policy` eklendi. Hedefli testler 19/19, Ruff geçti. SCS360 `codex/source-sync-20261111` SHA `9db5bbd0107f6bea7d93a98b449175d61ecc065b` push ve `ls-remote` ile doğrulandı; Nginx runtime ve canlı edge doğrulaması değildir.

26 Kasım 2026 dokümantasyon tutarlılık düzeltmesi: Web cookie oturumunun storage durumunu ve HSTS `includeSubDomains` ön koşulunu son kaynakla hizaladım. SCS360 `codex/source-sync-20261111` SHA `88fb67803249d62aa5c55a750504306dc5c53127` normal push/`ls-remote` ile doğrulandı. Canlı site/edge doğrulaması değildir.

26 Kasım 2026 Public Nginx header tekilleştirmesi: edge config artık upstream API/frontend kopyalarını gizleyip security header setini tek noktadan yayıyor; hedefli test 20/20, Ruff geçti. SCS360 `codex/source-sync-20261111` SHA `63bd0120db199cf041b0125a07a9740a0cecf798` normal push/`ls-remote` ile doğrulandı. Container, TLS ingress veya canlı yanıt doğrulaması değildir.

26 Kasım 2026 rate-limit taşıma güvenliği: Production/staging remote Redis bağlantısı `rediss://` olmak zorunda; düz `redis://` yalnız private Compose `rate-limit-store` hostname’i için kabul edilir. Hedefli test 22/22, Ruff geçti. SCS360 `codex/source-sync-20261111` SHA `d249c2976ca645fa329ff3bbc8e92e05ac85d51f` normal push/`ls-remote` ile doğrulandı. Redis TLS ve container runtime test edilmedi.

26 Kasım 2026 host routing: public Nginx unknown `Host` değerlerini 444 ile reddediyor; hedefli test 23/23, Ruff geçti. SCS360 `codex/source-sync-20261111` SHA `1d5221973d86d4b8f9538c5b0020a70824e1d632` normal push/`ls-remote` ile doğrulandı. Nginx runtime ve canlı edge doğrulanmadı.

26 Kasım 2026 veli analizi WIP: `/api/ai/parent-analysis/{id}` stdout/traceback’inden veli adı, öğrenci sayısı, finans/yoklama metrikleri ve hata ayrıntıları kaldırıldı. Beklenmeyen hata sahte sıfır analiz yerine genel 503 döndürür; server loguna yalnız exception sınıfı yazılır. SHA `6e8c21ee` normal push/`ls-remote` ile doğrulanacak. Hedefli test çalıştırılmadı. Aynı router’daki diğer debug/exception yolları, mevcut logların yaşam döngüsü ve canlı/KVKK kabulü açık kalır.

26 Kasım 2026 AI analiz hata yolları WIP: parent-engagement, class-analysis, classes-overview, executive-summary, comparative-analysis, resource-utilization, staff-productivity, risk-management ve operational-metrics hataları artık boş/sıfır metriklerle başarı dönmüyor; genel 503 verir. Exception sınıfı dışında ayrıntı loglanmaz; kasıtlı `AppException` 4xx/iş hataları korunur. SCS360 `codex/source-sync-20261111` SHA `4d9fcfea50e35f4f1a0b66ebdb1dd16c1279e1fa` normal push ve `ls-remote` ile doğrulandı. Test/build çalıştırılmadı. Yalnız bu analiz router’ındaki listelenen catch blokları incelendi; başka router logları, canlıdaki eski logların temizliği, runtime ve KVKK operasyonları açık.

26 Kasım 2026 chatbot log mahremiyeti WIP: chatbot router/handler, konuşma geçmişi ve context servisleri ile OpenAI/Ollama adaptörlerinde hata mesajı, traceback ve kullanıcı kimliği loglaması kaldırıldı; hata türü ve sabit işlem etiketi kullanılıyor, API hata yanıtları genel kalıyor. SCS360 `codex/source-sync-20261111` SHA `f9107087bf303fac105df0f5c27c178bfbe01b99` normal push/`ls-remote` ile doğrulandı. Test/build çalıştırılmadı. Tüm backend logları, dış LLM sağlayıcısına gönderilen veri kapsamı, mevcut logların saklama/silme politikası ve canlı/KVKK kabulü ayrıca doğrulanmalı.

26 Kasım 2026 chatbot prompt logları WIP: intent tespiti sorgu metni, bilinmeyen dönem içeriği ve LLM'nin geçersiz JSON yanıt gövdesi logdan çıkarıldı; sabit olay adları kullanılıyor. SCS360 SHA `f4a635a9dbe494ff27591b26bfb00d56e673c260` normal push/`ls-remote` ile doğrulandı. Test/build yok. Bu kontrol chatbot akışıyla sınırlı; LLM aktarım envanteri/izin-hukuki mekanizma ve diğer uygulama logları açık.

Web analiz hata logu WIP: ayrıntı ekranındaki Axios hata nesnesi yazdırılmıyor; mevcut `reportClientError` production’da kapalı, DEV’de alanları whitelist ediyor. SCS360 SHA `fe88e0eb`. Hedefli frontend doğrulaması yapılmadı; kalan istemci logları, backend genel taraması ve canlı kabulü açık.

26 Kasım 2026 ödev analizi WIP: `/api/ai/ai-homework-analysis` hatasında exception/traceback loglaması ve kullanıcıya iç hata metni verme kaldırıldı; hata türüyle genel 503. SHA `6ab1a930`; test çalıştırılmadı. Diğer analiz uçları ve canlı log/infra doğrulaması açık.

Veli memnuniyeti ve iletişim analizi WIP: iç exception/traceback ifşası kaldırıldı; sorgu hataları sahte/kısmi başarı üretmek yerine genel 503’e gider, hata türü dışında bilgi loglanmaz. SHA `494cd631`; hedefli test yok. Analiz router’ındaki kalan uçlar ve canlı log/infra kabulü açık.

Personel analiz hatası WIP: exception ayrıntısı artık kullanıcıya/loga yazılmaz. Gerçek DB verisi kullanmayan kütüphane ve kart analizleri placeholder üretmek yerine 503 verir; card number response’ta echo edilmez. SCS360 SHA `39b92001`; test yok. Gerçek analiz sözleşmeleri ve canlı doğrulama açık.

26 Kasım 2026 chatbot dış LLM veri minimizasyonu (WIP): önceki beş serbest metin mesajı provider prompt'undan çıkarıldı; yalnız bilinen intent etiketleri gönderilir. Mevcut sorgu, rol/tarih ve kişi sayıları hâlâ gönderilir. Dış hedefler `CHATBOT_EXTERNAL_DATA_TRANSFER_ALLOWED=true`, HTTPS/443 ve `CHATBOT_EXTERNAL_DATA_TRANSFER_HOSTS` içindeki tam host eşleşmesini gerektirir. SCS360 SHA `4b7faf049fd1cb083aa0a96fb2e393d3f361f3df`; test/build yok. KVKK dayanağı, sağlayıcı sözleşmesi/bölgesi, saklama, audit erişimi ve canlı egress ayrıca doğrulanmalı.
Kaynakta egress allowlist tam hostname eşleşmesidir; dış provider için opt-in + allowlist + HTTPS/443 gerekir. SCS360 SHA `1f69701d2d656a1374d7ba67b10bb1dd8843f639` push/`ls-remote` ile doğrulandı. Test/build veya canlı DNS/firewall egress doğrulaması yok.
26 Kasım 2026 chatbot request logu WIP: request query ile user/student/teacher/organization UUID'leri kaldırıldı; intent/kısa olay etiketi kalıyor. SCS360 `codex/source-sync-20261111` SHA `dd386dd1c4e12778ce7ddfb1ac467e9d899116b7`; hedefli test/build yok. Önceki canlı loglar ve tenant audit metinlerinin yetki/retention süresi doğrulanmadı.

26 Kasım 2026 chatbot audit/export WIP: ham audit okuma ve geri bildirim yazma `CHATBOT_AUDIT_TEXT_ACCESS_ALLOWED=true`, dataset dışa aktarımı ayrıca `CHATBOT_DATASET_EXPORT_ALLOWED=true` olmadan 503 ile kapalıdır; seçili kurum çalışma alanı zorunludur. Bu operasyonel kilit KVKK hukuki dayanağı, şeffaflık/izin, minimizasyon, saklama veya güvenli eğitim ortamını kanıtlamaz. Statik `git diff --check` geçti; test/build çalıştırılmadı.
Kaynak SCS360 SHA `245301330cc4dfc7d0d8f0783be543bc2a804c24` normal push/`ls-remote` ile doğrulandı. Sonraki inceleme: tenant audit yanıtında tam soru/yanıt verisinin gerekliliği, operatör erişim izi ve saklama/silme.
Ham audit okuma ve feedback güncelleme `CHATBOT_AUDIT_TEXT_ACCESS_ALLOWED=true` olmadan kapalı; dataset indirme ayrıca `CHATBOT_DATASET_EXPORT_ALLOWED=true` ister. SCS360 `codex/source-sync-20261111` SHA `d0d37a234eefbca57c7f989f1c7b1ac8d1a99ea8` push/`ls-remote` ile doğrulandı. Test/build çalıştırılmadı; erişim/audit/retention politika kanıtı hâlâ eksik.
Yeni chatbot audit satırlarının ham prompt/yanıt ve kimlik metadatasıyla kaydı `CHATBOT_AUDIT_STORAGE_ALLOWED=true` olmadan yapılmaz; storage kapalıyken audit metrikleri ve kullanıcı geçmişi de 503 verir. Önceden kaydedilmiş veriyi silmez ve log/DB saklama politikasını kurmaz. Test/build yok; yalnız statik diff kontrolü.
SCS360 `codex/source-sync-20261111` SHA `e309e80f87bd3e67d05a1d07cca7325f41d2c13c` push/`ls-remote` ile doğrulandı. Önceden depolanmış audit kayıtları, yedekler ve loglar için retention/silme ve erişim kanıtı hâlâ gereklidir.
Yeni audit metadata'sından öğrenci/öğretmen UUID alanları çıkarıldı. Mevcut DB satırları, yedekler veya loglar temizlenmedi.
Audit listesi API/UI gönderen adını, kullanıcı/kurum kimliğini, session ID'yi ve dahili metadata'yı dışarı vermez; ham soru ve yanıt için varsayılan kapalı audit-text ve tenant-scope kapıları sürer. SCS360 SHA `42312556bb7fc68d9bd9c0cfff6060cca35c051b` push/`ls-remote` doğrulandı. Test/build yok; geçmiş verinin saklama/silme kabulü açık.
Audit listesi API’si ve Web ekranı ad/UUID/session/dahili metadata göndermez; ham soru ve yanıt için varsayılan kapalı audit-text ve tenant-scope kapıları sürer. Statik diff kontrolü; test/build yok.
SCS360 kaynak SHA `867c48278b74ce2f0e68250890fc80bf728123bb` push/`ls-remote` ile doğrulandı. Sonraki adımda eski kayıt silme/retention süresi belirlenmeli; şu an gerçek politika yok.
Parola yenileme tokenı paint öncesi component state'e alınıp query/history'den çıkarılır; POST gövdesiyle gönderilir. Eski browser history, mail click tracking ve ilk HTTP access logları temizlenmez. SCS360 SHA `798d7f1521f8b4e150e70f4c9fbcf9948141335a` push/`ls-remote` doğrulandı; test/build yok.

### 26 Kasım 2026 — Dataset export yalnız incelenmiş kayıtları alır (WIP)

Backend export servisi tenant kimliğini zorunlu alır ve kendi sorgusunda yalnız `VERIFIED` + `is_fine_tuning_ready=true` satırlarını seçer; endpoint tenant yoksa 403 döndürür. İstemci kayıt durumuna göre bu sınırı gevşetemez. Üç kaynak dosyası için statik `git diff --check` geçmiştir; test/build çalıştırılmadı. SCS360 normal push/`ls-remote`: `670122f94b9c2b46576b2802e5c4adb50b20aecc`.

Bu, mevcut ayrı varsayılan-kapalı export ve audit-text ayarlarına ek kaynak filtresidir. Eğitim amacı/hukuki dayanak, bilgilendirme/izin, sağlayıcı sözleşmeleri ve aktarım, gerçek operatör audit izi, saklama/silme, log/veritabanı/yedek, canlı konfigürasyon ve bağımsız güvenlik incelemesi açık kalır. KVKK veya canlı güvenlik kabulü değildir.

Dataset export endpoint’i istek/IP başına 2 dakika sınırına alındı; mevcut ortak rate-limit deposu ayarını kullanır. Statik `git diff --check` dışında test/build/Redis runtime yapılmadı. Kaynak SHA `31b346722baebd049590ef02d714999c2e9c96ea`; 429 davranışı, çoklu worker sayacı ve Redis kesinti politikası canlı/runtime olarak açık.

### 26 Kasım 2026 — Parola sıfırlama tokenı fragment taşıma (WIP)

Yeni üretilen sıfırlama bağlantısı tokenı URL fragment’ine yerleştirir; browser fragment’i ilk HTTP isteğinde sunucuya göndermez. React tokenı ilk renderda belleğe alıp adres/geçmişten temizler; eski query formatı uyumluluk için okunur ve istemcide silinir. `git diff --check` geçti; test/build yok. SCS360 `codex/source-sync-20261111` SHA `0b9e091a0ed09a863f08899d315c4753ff4ab564` normal push/`ls-remote` ile doğrulandı.

Önceden üretilmiş query URL’leri, ingress/e-posta tracking logları veya eski tarayıcı geçmişi bu değişiklikle temizlenmez. E-posta sağlayıcısı davranışı, canlı ingress log formatı/saklama, reset akışının test kabulü ve tokenın erişim izi hâlâ açık. Bu WIP; canlı veya KVKK kabulü değildir.

### 26 Kasım 2026 — Chatbot dış hedeflerinde özel ağ reddi (WIP)

Harici LLM transfer politikası, allowlist + açık opt-in + HTTPS/443 şartları korunarak non-public IP literal’lerini, scoped IPv6 ve yaygın private/reserved DNS suffix’lerini (`.local`, `.internal`, `.test`, `.home`, `.lan`, `.invalid`, `.example`) reddeder. `git diff --check` geçti; test/build/DNS/runtime yok. SCS360 `codex/source-sync-20261111` SHA `08e14a7948d3bdcb7b0249b6ee8219a554925829` normal push/`ls-remote` ile doğrulandı.

Bu DNS rebinding/özel IP’ye çözümleme riskini tek başına kapatmaz. Egress firewall, resolver ve canlı ağ yolunun bağımsız doğrulaması; harici LLM veri işleme koşulları ve KVKK incelemesi açık kalır. WIP, canlı kabulü değildir.

Rate-limit export commitinde router seviyesinde `Request` ve `limiter` importları atlanmıştı; takip commitinde eklendi. `git diff --check` geçti, fakat Python import smoke, API testleri ve build çalıştırılmadı. SCS360 SHA `8611f0226c00f17858f2ace1daa5c6fd0ca82bdd` normal push/`ls-remote` ile doğrulandı. Endpoint WIP; izole import/API testinden geçmeden kabul edilmez.

### 26 Kasım 2026 — Chatbot audit metni erişim olayları (WIP)

Ham audit listesi okuma, geri bildirim güncelleme ve dataset dışa aktarımında ortak `audit_logs` tablosuna metin içermeyen olay kaydı eklenir. Kayıt aktörü, seçili kurumu, olay türünü, sayım/format bilgisini ve istemci IP’sini içerir; ham soru/yanıt veya düzeltme metni kopyalanmaz. GET liste 20/dk, geri bildirim PUT 10/dk rate-limit alır. `git diff --check` geçti; test/build çalıştırılmadı. SCS360 `codex/source-sync-20261111` SHA `8d908baa04f58da9378491ba309b4ba17490e4c9` normal push/`ls-remote` ile doğrulandı.

Bu olaylar aynı uygulama DB’sinde tutulur; değiştirilemez log, bağımsız SIEM veya retention politikası değildir. IP kişisel veridir. Erişim izinleri, saklama/silme süresi, yedeklerden silme ve fail-closed davranışı onaylı süreç ve geçici DB testleriyle doğrulanmadı; WIP, KVKK/canlı kabulü değildir.

### 26 Kasım 2026 — Parola reset token endpoint rate-limit (WIP)

`POST /auth/reset-password` artık ortak rate-limit deposu ile IP başına 5 istek/dakika sınırında. Auth router’da önceden var olan staged olmayan oturum WIP’si bu commit’e alınmadı. `git diff --check` geçti; test/build/Redis runtime yok. SCS360 SHA `ee930a857a335b530ef5ebe046bc752a59ba0427` normal push/`ls-remote` ile doğrulandı.

Rate-limit dağıtık runtime, proxy’nin istemci IP’sini güvenilir biçimde iletmesi, 429 başlıkları, token expiry/tek kullanımlılık, eski reset logları ve retention politikası doğrulanmadı. WIP; canlı veya KVKK kabulü değildir.

### 26 Kasım 2026 — Reset link proxy access-log azaltımı (WIP)

Public Nginx ve frontend Nginx exact `/reset-password` SPA rotasında access logu kapatır; public vhost `Referrer-Policy: no-referrer` ile URL sızıntı yüzeyini daraltır. Yeni tokenlar fragment’tedir; legacy query-tokenlar geçici uyumlulukta kalır. `git diff --check` geçti; `nginx -t`, container veya TLS edge testi yapılmadı. SCS360 SHA `78ffa647f4347fff43cb1f0bf509971be48a02fb` normal push/`ls-remote` ile doğrulandı.

Nginx error logları, e-posta link tracking/redirectleri, önceden yazılmış loglar ve üretim ingress davranışı bu değişiklikle doğrulanmış ya da temizlenmiş değildir. WIP; canlı ve KVKK kabulü değildir.

### 26 Kasım 2026 — Bildirim sağlayıcısı yanıt ve hata verisini daraltma (WIP)

Outbox katmanı sağlayıcının serbest `response` nesnesini doğrudan kalıcılaştırmaz; yalnız HTTP status, kısa kod, izin verilen teslim durumu ve biçim kontrollü opaque provider/message ID alanları tutulur. Başarısız gönderimde sağlayıcı hata gövdesi yerine sabit genel hata mesajı saklanır. Sağlayıcı ve worker hata yolları traceback, iş kimliği veya exception metni yazmaz; yalnız sabit olay etiketi ile exception sınıfı kalır. Bu, yeni log/yanıt üretimini daraltır; eski DB/yedek/log kayıtlarını silmez ve API yetkisini/retention politikasını değiştirmez.

Yalnız `git diff --check` yapıldı; test/build/provider/runtime doğrulaması yok. SCS360 `codex/source-sync-20261111` SHA `f8947cf9bb0061394d25d5cbb3858c8d8cd265e8` normal push ve `ls-remote` ile doğrulandı. İzole testte hata/yanıt sızıntısı ve retry/durum kurtarma, bildirim API alıcı kapsamı, retention/silme, üretim logları, sağlayıcı sözleşmesi ve KVKK süreçleri açık kalır. WIP; canlıya hazır, sızdırmaz veya KVKK uyumlu kabulü değildir.

### 26 Kasım 2026 — Teslim raporu alıcılarının şube kapsamı (WIP)

`GET /api/communications/delivery-reports` önce sadece kurumdaki yayınları seçiyordu; genel ORM tenant guard’ı `branch_id=NULL` kayıtlarına izin verdiğinden, şube atanmış personel kurum geneli yayınların telefon/ad listesini görebilirdi. Kaynak düzeltmesi şube listesi bulunan aktörlerde `NotificationJob.branch_id` değerini atanmış şubelerle ayrıca sınırlar; kurum geneli (`NULL`) yayınların alıcıları bu rapor sorgusundan çıkar. Kurum sahibi/platform yönetici akışı korunur.

Yalnız `git diff --check` yapıldı; izole tenant testleri, başka recipient endpoint incelemesi ve canlı konfigürasyon doğrulanmadı. SCS360 `codex/source-sync-20261111` SHA `ae2e4f54d49a21ea9a0b6dcca1c8dd4090c660f7` push/`ls-remote` ile doğrulandı. WIP; tenant scope, üretim güvenliği veya KVKK kabulü değildir.

### 26 Kasım 2026 — Outbox geçmişi şube kapsamı (WIP)

`outbox_service.scoped()` ortak repository filtresine ek olarak, şube listesi bulunan aktörlerde `NotificationJob.branch_id IN (atanmış şubeler)` koşulu uygular. Önceki generic filtre `branch_id=NULL` satırlarını kabul ediyordu; bu satırlar kurum geneli bildirim alıcılarını ve mesaj içeriğini içerebildiğinden branch-scoped outbox list/detail/retry/delete işlemlerinde dışarıda bırakılır. Kurum sahibi ve platform kapsamı değişmez.

Yalnız `git diff --check` yapıldı; geçici DB/rol/portal senaryoları, üretim ayarları ve eski log/DB retention-silme doğrulanmadı. SCS360 `codex/source-sync-20261111` SHA `b020cb2c8f18e4f9ebbf552adc6333aa955588fc` push/`ls-remote` ile doğrulandı. WIP; canlıya hazır veya KVKK uyumlu kabulü değildir.

### 26 Kasım 2026 — Bildirim liste/detay/yönetim şube kontrolü (WIP)

Dashboard bildirim uçlarında generic repository filtresi `branch_id=NULL` kayıtlarını okunabilir sayıyordu. `/api/notifications` listesi branch-scoped aktörlerde yalnız atanmış şubeleri seçer; detail, delete ve retry yolları da job branch’ini kontrol edip branchless/foreign işleri 404 ile gizler. Böylece bu uçların alıcı adresi okuma ve job değiştirme işlemleri kurum geneli bildirimlere uygulanmaz.

Yalnız `git diff --check` yapıldı; izole DB rol/şube testleri ve canlı runtime yok. SCS360 `codex/source-sync-20261111` SHA `201e5af4088fc27f90642981d55e904a35d0044c` push/`ls-remote` doğrulandı. Çoklu şube aktörünün kendi branchless işi için erişim modeli, geçici DB kabulü, diğer broadcast API’leri ve KVKK süreçleri açık; WIP.

### 26 Kasım 2026 — Broadcast listeleme ve değişiklikte branch scope (WIP)

`broadcast_service` liste/`get` yolları aktörün atanmış şubelerindeki hedef-şube veya hedef-sınıf kayıtlarını seçer. Null branch + null class olan kurum-geneli işler şube-scoped kullanıcıya görünmez; tenant filtresi get üzerinden update/send/cancel ve delivery report job lookup’larına da uygulanır. Kurum sahibi/platform kapsamı korunur.

Yalnız `git diff --check` yapıldı; geçici DB testleri, çok şubeli generic notification UX’i ve canlı runtime yok. SCS360 `codex/source-sync-20261111` SHA `8af46648f30ba7af404f8e8119d26ddf2ea180e8` normal push/`ls-remote` ile doğrulandı. WIP; canlı veya KVKK kabulü değildir.

### 26 Kasım 2026 — Bildirim provider ve hata verisinin API'den azaltılması (WIP)

Ortak notification helper, sağlayıcı JSON yanıtından yalnız sınırlandırılmış HTTP durum/kısa kod, onaylı teslim durumları ve karakter/uzunluk kontrolünden geçen opak kimlikleri tutar. Başarısız gönderimde sağlayıcı gövdesi yerine sabit genel hata mesajı kullanılır. Worker yazma yolu ile outbox, iletişim teslim raporu, duyuru sonuçları ve bildirim detayının okuma yanıtları aynı filtreyi kullanır; eski DB satırlarından ham gövde/hata metni API'den tekrar sunulmaz.

Bu işlem eski DB/yedek/log içeriğini silmez. Yalnız `git diff --check` yapıldı; test/build/DB/provider/runtime doğrulanmadı. SCS360 `codex/source-sync-20261111` SHA `16fd01b035551cc7be856b16a8c40cd5a442d2e0` normal push/`ls-remote` ile doğrulandı. Güvenli izin-listesi davranışı, retry ve tenant regresyonları, eski kayıtların retention/silmesi, sağlayıcı sözleşmeleri ve KVKK süreçleri açık; WIP.

### 26 Kasım 2026 — Manuel bildirim gönderim endpointi (WIP)

Legacy `POST /api/notifications/send` artık IP bazında `5/minute` rate-limit uygular. Şube ataması olan aktör `branch_id` olarak sadece atanmış şubeyi verebilir; başlık (255), ileti (10.000), alıcı adedi (1–100), adres (255) ve ad (200) sınırlandırılır; subject/address CR/LF içeriği reddedilir. SCS360 `codex/source-sync-20261111` SHA `3f6cf3da93273f22f9ff207af309966d282e6713` normal push/`ls-remote` ile doğrulandı. Sadece statik diff kontrolü; test/build/provider/runtime yok.

Önemli açık risk: endpoint, adreslerin aynı tenant/branch içindeki kayıtlı veli/personel iletişim adresleri olduğunu kontrol etmiyor; `notification.write` yetkilisi hâlâ dış adrese serbest bildirim oluşturabilir. Canlı öncesi alıcıları veritabanı kaydı ve onay tercihleriyle eşleştir ya da bu legacy ucu kapat. Rate-limit, hukuki dayanak/izin veya KVKK kabulü değildir.

### 26 Kasım 2026 — Manuel bildirim dış alıcı engeli (WIP)

Legacy manuel gönderim endpointi, dışarıdan girilen e-posta/telefon adreslerinin kurum/şube içindeki kayıtlı iletişimlerle eşleşmesini zorunlu kılar. Veli tarafında `receive_notifications` kontrol edilir; personel kayıtlı şube scope'unda aranır. Kayıtlı iletişim adı esas alınır, normalizasyondan sonra tekrar adresler kaldırılır; açık şubedeki personel listesi kurum geneline genişlemez. Kod SHA `56d4dba1ce50eff716e7a8f68e7c593259717e69` push/`ls-remote` ile doğrulandı.

Yalnız statik `git diff --check`; test/build veya sağlayıcı gönderimi yapılmadı. Diğer iletişim/broadcast/ödeme uyumluluk uçları, kanal bazlı hukuki dayanak/rıza, veri retention ve silme, canlı HTTPS/proxy ayarı ve KVKK uyum değerlendirmesi kabul edilmedi. WIP; canlıya hazır veya KVKK uyumlu ilan edilemez. Sonraki somut iş diğer bildirim alıcı uçlarını denetlemek ve izole geçici DB regresyonlarıdır.

### 26 Kasım 2026 — Kuyruklanan manuel bildirim scope koruması (WIP)

`POST /api/notifications` recipient çözümlemesi tenant'a bağlandı. İstemciden kurum fallback'i kaldırıldı; explicit seçili kurum gerekli. Belirli şube, hem veli-öğrenci ilişki sorgusuna hem branch-aware staff scope'una uygulanır; çoklu şubeye atanmış aktör şubesiz kurum-geneli iş açamaz. Veli tercihi korunur, adresler tekilleştirilir ve iş boyutu 500 alıcı/10.000 karakter/5 istek-dk ile sınırlandırılır. Kaynak `2e82c25dd1f8db7f437aaddc50d5e4872897ac01` normal push/`ls-remote` ile doğrulandı.

Yalnız `git diff --check`; test, build, DB veya sağlayıcı runtime yapılmadı. Oluşan kuyruk işlerinde tenant/branch regressions ve planlanmış dispatch, ayrıca alternatif bildirim uçları ve kanal rızası incelemesi yapılmalı. Hukuki dayanak, aydınlatma, retention/silme, canlı altyapı ve KVKK uyumu kabul edilmedi; WIP, canlıya hazır ilan edilemez.

### 26 Kasım 2026 — Borç hatırlatma API'si abuse sınırı (WIP)

Gecikmiş borç hatırlatma POST'u IP başına 5/dk; body yalnız en çok 100 öğeli bir `debt_ids` listesi kabul eder. Duplicate UUID'ler tekilleştirilir, geçersiz ID 4xx validation hatasına çevrilir. Tenant/şube ve kayıtlı veli bildirimi kontrolleri değişmedi. SCS360 SHA `614323aee46b347a1725974f42c8634fc433837c` normal push/`ls-remote` doğrulandı.

Sadece `git diff --check`; test/build/send/provider runtime yok. İzole DB regresyonları, gerçek distributed rate-limit deposu, reverse-proxy IP güven zinciri, kanal rızası/hukuki dayanak, retention/silme ve canlı KVKK/siber güvenlik kabulü açık. WIP; canlıya hazır ilan edilemez.

### 26 Kasım 2026 — Notification branch picker/API kapsamı (WIP)

Web composer için yeni `GET /api/notifications/branch-options` yalnız aktif şube kimlik/adlarını seçili kurum ve kullanıcının atanmış şube kimlikleriyle sınırlar; permission `notification.write`. Frontend modal gerekli durumda branch seçimini zorunlu tutup seçimi `POST /api/notifications` payload'ına ekler; backend scope kontrolü ayrıca kalır. SCS360 SHA `8a0a6991aa5ac2862c32bb59763594c090a008b7` normal push/`ls-remote` doğrulandı. Yalnız `git diff --check`; React/API contract testleri ve canlı doğrulama yok. Sıradaki somut iş geçici DB ve frontend DTO regresyonları; KVKK/canlı kabul değildir.

### 26 Kasım 2026 — Bildirim branch payload null uyumu (WIP)

Frontend, opsiyonel branch seçiminin boş stringini API POST öncesi `null`'a çevirerek `UUID | null` backend DTO'suna uyar. SCS360 SHA `0dcfa5f23a42d6dd3c6d5f894abedbf6977dc799` normal push/`ls-remote` doğrulandı. Statik diff dışında test/build/API runtime yapılmadı; WIP.

### 26 Kasım 2026 — Makbuz ileti kuyruğu opt-in/rate-limit (WIP)

Makbuz paylaşım e-posta/SMS/WhatsApp API uçlarında mevcut generic bildirim tercihi kapalıysa veli recipient çözümlemesi reddeder; endpoint başına IP limit 10/dk. Kaynak `e69cccc95780cff11c15a599f2ba5c3da358ecf6` normal push/`ls-remote` ile doğrulandı.

Yalnız `git diff --check`; test, build, gerçek ileti veya provider çağrısı yok. `receive_notifications` tercihinin makbuz/finansal ileti için hukuki yeterliliği ayrıca veri sorumlusu tarafından değerlendirilmelidir; kanal bazlı izin/amaç, retention, provider sözleşmesi ve KVKK/canlı kabul açık. WIP.

### 26 Kasım 2026 — Finansal hatırlatma suistimal sınırı (WIP)

`POST /api/payments/finances/reminders/send` endpointi IP bazında 5/dk; body'deki borç kimlikleri 1–100 aralığına sınırlandı. `finance_compat_service` kayıtlı veli, seçili tenant/şube ve `receive_notifications` koşullarını korur. SCS360 SHA `0491db2dfbc472befc902d5e6bda530e45d7e3bb` normal push/`ls-remote` ile doğrulandı.

Sadece `git diff --check`; test/build/gerçek sağlayıcı gönderimi yok. Dağıtık rate limit, reverse-proxy IP güven zinciri, finansal bildirimler için kanal/amaç hukuki dayanağı, eski verilerin saklama/silme ve canlı KVKK/güvenlik kabulü açık. WIP.

### 26 Kasım 2026 — Broadcast send abuse azaltımı (WIP)

`POST /api/communications/broadcast-jobs` ve `.../{job_id}/send` endpointleri IP başına 5/dk ile sınırlandı; send service mevcut tenant/branch hedef, kayıtlı adres ve veli tercih kontrollerini sürdürür. Kod `ed27badba35691b58d8d4c2cf6f13ef80934f9af` normal push/`ls-remote` ile doğrulandı.

Yalnız `git diff --check`; test/build/gerçek provider yok. Paylaşılan limiter deposu, reverse proxy IP zinciri, yüksek alıcı sayısı davranışı, kanal rızası ve retention/silme kabulü açık. WIP, KVKK veya canlı hazırlık kararı değildir.

### 26 Kasım 2026 — Dış uç güvenlik yanıtı gözlemi (WIP)

Read-only HTTPS HEAD on `/` returned 200 with `Server: nginx/1.18.0 (Ubuntu)` and `X-Content-Type-Options: nosniff`; no HSTS, CSP, X-Frame-Options, Referrer-Policy, or Permissions-Policy appeared in this response. GET `/.well-known/security.txt` returned the SPA HTML rather than a security contact document. This is a single-path observation, not full TLS/runtime/KVKK acceptance. No credentials, messages, or state-changing requests were sent. Source branch SHA remained `b42384bfbf3d05bc7dd7669ef8ecc3906a711cc3`; no deploy occurred.

The publisher working tree still has uncommitted Nginx/rate-limit WIP that removes HSTS/upstream Server hiding and forces an in-memory limiter; it was not staged or pushed. Next: resolve that WIP and identify an approved security contact before preparing deployable headers/security.txt. WIP; live protection/KVKK not accepted.

### 26 Nov 2026 — Spreadsheet import/export error and tenant bounds (WIP)

The legacy student spreadsheet import now reads only up to the configured upload limit plus one byte, caps rows at 5,000, and binds active class/branch records to the selected organization and the actor's assigned branches when present. Each row uses a savepoint. Parse and processing errors no longer expose raw exception text or student numbers in failure responses. The shared import parser and chatbot dataset export also return generic errors. Source checkpoint `5ff948a3c02f01fd94cd8166132cc41fc62c4e4b` was pushed normally and verified with `ls-remote`.

Only `git diff --check` was run; no tests/build/database runtime. Temporary-DB tenant/branch/savepoint regressions, malicious workbook testing, special-category health data purpose/access/retention review, and live/KVKK acceptance remain open.

The `.xlsx` path also checks ZIP metadata before pandas parsing: no more than 1,024 members and no more than 64 MiB total uncompressed content. Oversized archives are rejected; malformed archives receive a generic client error. Source checkpoint `041dad12cb04e67514bdc8bc3f2cc925f79977a8` was pushed normally and verified with `ls-remote`. This is an application bound, not proof against every parser/resource-exhaustion case; malicious-file and concurrent-upload tests remain open.

### 26 Nov 2026 — Safe external meeting links (WIP)

Frontend only renders an appointment meeting link when it parses as an absolute HTTPS URL without embedded user information. The new-tab link sets `noopener noreferrer` and `no-referrer`; invalid or non-HTTPS values are not rendered as links. Source checkpoint `31afdcc12754efd94a945c691bd512ea7e926205` was pushed normally and verified with `ls-remote`. No tests/build/API runtime were run; WIP.

Static review also found the appointment create form is not aligned with the backend DTO and contains fixed example identity fields; the status action uses `PATCH` while the backend route is `PUT /{id}/status`. This was not changed in this checkpoint. Align the UI with tenant-scoped student/teacher/time-slot options before accepting the workflow; do not treat it as verified security or feature behavior.

Correction: the mounted route already used the DTO-aligned communications appointment page; the fixed example/payload mismatch was in an unmounted duplicate under operations. That duplicate now re-exports the mounted page, and its status action uses the backend's `PUT` method. Source checkpoint `6723edbf14bce088ba1ca800c6c8a7e4051bb6f7` was pushed normally. Existing status assertions were aligned but not run. Review remains open for non-parent create semantics (`parent_id` is derived from the acting user), role behavior, and isolated verification.
# TCKN/VKN at-rest koruması — 26 Kasım 2026 WIP

Kurum vergi kimlik numarası ORM'de açık metin kolon yerine Fernet ciphertext olarak saklanır; arama/tekrar kontrolü yalnız dedicated encryption key'den domain-separated HMAC ile yapılır. HMAC fingerprint takma kimliktir, anonimleştirme değildir ve gizli anahtarla korunmalıdır. `ORGANIZATION_TAX_NUMBER_ENCRYPTION_KEY` production/staging başlangıcında zorunludur ve JWT, kurum ödeme veya SaaS ödeme anahtarıyla aynı olamaz. Migration `041` anahtar gerektirdiği için online çalıştırılmalıdır; duplicate fingerprint varsa işlem durur. Migration downgrade'ı bilerek reddeder. Kod commit `3113ded0067087676b8ce3b4a1d8e2935e1ddcd6` `codex/source-sync-20261111` dalında; migration ve runtime kabulü açık.

Bu koruma eski dump/yedekleri, logları, PDF/receipt kayıtlarını veya ödeme sağlayıcısına hukuki dayanağa göre yapılan aktarımı geriye dönük temizlemez. Canlı geçiş için secret manager/erişim ve anahtar kurtarma-rotasyon prosedürü, şifreli yedek/geri dönüş planı, eski plaintext yedeklerin retention kararı, makbuz/finans çıktılarının kapsamı ve veri sorumlusu onayı gerekir. Test, build veya migration çalıştırılmadı; WIP ve KVKK/hukuki uygunluk kanıtı değildir.

## Checkout kimlik alanı maskesi — 26 Kasım 2026 WIP

Web okul ödeme formu TCKN/pasaport değerini varsayılan maskeler, göster/gizle düğmesini sunar ve `autocomplete="off"` kullanır. Değer işlem hazırlanana kadar form/React belleğindedir ve gerekli ödeme isteğiyle sunucuya/provider'a gider; bu maske şifreleme veya aktarımın hukuki dayanak/onay kanıtı değildir. Yalnız `git diff --check`, UI/API testi ve provider runtime yok. Kaynak SHA `da315d1e336bac6f4d05269ea842600b56379e1b` normal push/`ls-remote` ile doğrulandı. Canlı kabul açık.

## Kurum vergi numarasına erişim izi — 26 Kasım 2026 WIP

Organization list response'ları TCKN/VKN içermez. Tekil detayda yalnız platform yönetimi/aktif owner rolü tam değeri alır; gerçek okuma, değeri içermeyen `ORGANIZATION_TAX_IDENTIFIER_READ` audit olayı yazar. Genel `org.write` tek başına mevcut değeri göstermez; boş form alanı update payload'ından çıkarılarak değer silinmeden korunur. API, rol ve UI regresyonları çalıştırılmadı; audit retention/erişim ilkesi ve canlı kabul açık. Kod commit `af0671007f4106e7b11dee5a23522e07813febcd` normal push/`ls-remote` ile doğrulandı.

## SaaS üyelik checkout kimlik alanı — 26 Kasım 2026 WIP

SaaS abonelik ödeme formundaki kimlik/vergi numarası artık varsayılan maskelenir; kullanıcı erişilebilir düğmeyle geçici olarak gösterebilir. `autocomplete`, `autocapitalize` ve `spellCheck` kapalıdır. Bu sunum önlemidir; verinin React/DOM belleğinde bulunmasını, backend'e/ödeme sağlayıcısına aktarılmasını veya sağlayıcıdaki saklamayı engellemez. Kodda yeni bir kalıcı kopya oluşturulmadı. Yalnız `git diff --check`; UI/API/provider/build doğrulaması yok. Değişiklik commit/push SHA'sı çalışma kaydında tutulur. KVKK amacı/dayanak, TCKN'siz alternatif, sağlayıcı sözleşmesi/retention ve canlı kabul açık.

## Beklenmeyen backend hatalarında log minimizasyonu — 26 Kasım 2026 WIP

Global 500 hata yolunda traceback ve exception metni yerine yalnız hata sınıfı, path ve request ID loglanır. SQL/provider exception metinleri hassas alan veya sağlayıcı payload parçaları içerebileceğinden bu log minimizasyonu riski azaltır; log platformu erişimi/retention'ı, APM ve diğer logger'lar ayrıca incelenmelidir. Test çalıştırılmadı; WIP.
