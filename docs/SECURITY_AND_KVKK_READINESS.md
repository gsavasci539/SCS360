# Güvenlik ve KVKK canlıya geçiş kontrolü

Bu belge, uygulamadaki güvenlik kontrollerini işletim ve KVKK sorumluluklarından ayırır. Kodda güvenlik iyileştirmesi bulunması tek başına KVKK uyumu, sızma testi veya canlı ortamın güvenli olduğu anlamına gelmez. İnceleme tarihi: 26 Kasım 2026.

## Bu kaynak değişikliğinde uygulananlar

- `production` ve `staging`, tam HTTPS CORS origin listesi ve HTTPS parola sıfırlama adresi olmadan başlamaz. Ödeme akışı etkinse ilgili callback adresinin de HTTPS olması gerekir.
- Bilinmeyen `APP_ENV` değerleri reddedilir. `production` ve `staging` ortamlarında Swagger, ReDoc ve OpenAPI JSON uçları sunulmaz.
- API yanıtları merkezi `no-store`/`no-cache` başlıkları, MIME sniffing koruması, çerçeve engeli, referrer ve tarayıcı özellik politikaları alır.
- Nginx kaynak yapılandırmalarında `server_tokens off`, CSP, `X-Frame-Options: DENY`, Referrer-Policy ve Permissions-Policy bulunuyor. Frontend vhost’unda HSTS `max-age=31536000; includeSubDomains` olarak ayarlı ve `/assets/` alt konumunda güvenlik başlıkları ayrıca yineleniyor; dağıtım öncesi bütün tarayıcıya açık alt alan adlarının HTTPS durumu doğrulanmalı. CSP iki Nginx katmanında hizalı, `object-src 'none'` içeriyor; proxy yanıtlarında upstream `Server` ve `X-Powered-By` gizleniyor.
- Genel dosya uçları kurum/şube klasörüne bağlandı. Okuma `files.upload`, silme `files.delete` izni ve oturumun kurum/şube kapsamını gerektiriyor. Dosya yolu kanonik kök altında doğrulanıyor, dosyalar rastgele adla yazılıyor, yükleme boyutu/içeriği sınırlı ve indirme `attachment`/`no-store`. Eski kurumsuz/genel yollar güvenli sahiplik doğrulaması olmadığı için 404 verir; otomatik dosya taşıma yapılmadı.
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
