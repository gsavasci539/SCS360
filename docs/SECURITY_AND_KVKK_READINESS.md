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

Web analiz hata logu WIP: ayrıntı ekranındaki Axios hata nesnesi yazdırılmıyor; mevcut `reportClientError` production’da kapalı, DEV’de alanları whitelist ediyor. SCS360 SHA `fe88e0eb`. Hedefli frontend doğrulaması yapılmadı; kalan istemci logları, backend genel taraması ve canlı kabulü açık.

26 Kasım 2026 ödev analizi WIP: `/api/ai/ai-homework-analysis` hatasında exception/traceback loglaması ve kullanıcıya iç hata metni verme kaldırıldı; hata türüyle genel 503. SHA `6ab1a930`; test çalıştırılmadı. Diğer analiz uçları ve canlı log/infra doğrulaması açık.
