# Güvenlik ve KVKK canlıya geçiş kontrolü

Bu belge, uygulamadaki güvenlik kontrollerini işletim ve KVKK sorumluluklarından ayırır. Kodda güvenlik iyileştirmesi bulunması tek başına KVKK uyumu, sızma testi veya canlı ortamın güvenli olduğu anlamına gelmez. İnceleme tarihi: 25 Kasım 2026.

## Bu kaynak değişikliğinde uygulananlar

- `production` ve `staging`, tam HTTPS CORS origin listesi ve HTTPS parola sıfırlama adresi olmadan başlamaz. Ödeme akışı etkinse ilgili callback adresinin de HTTPS olması gerekir.
- Bilinmeyen `APP_ENV` değerleri reddedilir. `production` ve `staging` ortamlarında Swagger, ReDoc ve OpenAPI JSON uçları sunulmaz.
- API yanıtları merkezi `no-store`/`no-cache` başlıkları, MIME sniffing koruması, çerçeve engeli, referrer ve tarayıcı özellik politikaları alır.
- Nginx kaynak yapılandırmalarında `server_tokens off`, CSP, `X-Frame-Options: DENY`, Referrer-Policy ve Permissions-Policy zaten bulunuyordu. Tarama notu üzerine HSTS `max-age=31536000` eklendi; `includeSubDomains` bütün alt alan adlarının HTTPS durumu doğrulanmadığı için eklenmedi. CSP iki Nginx katmanında aynı hale getirildi, `object-src 'none'` eklendi; proxy yanıtlarında upstream `Server` ve `X-Powered-By` gizleniyor.
- Genel dosya uçları kurum/şube klasörüne bağlandı. Okuma `files.upload`, silme `files.delete` izni ve oturumun kurum/şube kapsamını gerektiriyor. Dosya yolu kanonik kök altında doğrulanıyor, dosyalar rastgele adla yazılıyor, yükleme boyutu/içeriği sınırlı ve indirme `attachment`/`no-store`. Eski kurumsuz/genel yollar güvenli sahiplik doğrulaması olmadığı için 404 verir; otomatik dosya taşıma yapılmadı.
- Web login/refresh/logout ayrı cookie oturum uçlarını kullanıyor. Access ve refresh token JSON gövdesine dönmüyor, `localStorage`/`sessionStorage` içinde tutulmuyor; access/refresh cookie `HttpOnly`, production/staging’de `Secure`, `SameSite=Lax`. Web’de yazma istekleri CSRF çift gönderim doğrulaması ve izinli `Origin` kontrolü alıyor. Android’in bearer `/auth/login`, `/auth/refresh`, `/auth/logout` sözleşmesi değişmedi.

## Canlıya çıkış öncesi zorunlu teknik kontroller

- İnternete yalnız TLS sonlandıran güvenilir ingress/WAF açılmalı. Genel erişimde 443 dışında yönetim, SSH, Docker API, PostgreSQL 5432, uygulama 5006, statik servis ve varsa Redis portları kapalı olmalı. 80 yalnız HTTPS yönlendirmesi için kullanılmalı.
- `docker-compose.yml` bu kaynakta yalnız `80:80` portunu yayınlıyor ve Nginx TLS sertifikası sonlandırmıyor. Harici TLS ingress, güvenlik duvarı, WAF, HSTS ve origin erişim kısıtları bu depodan doğrulanmış değildir; bu nedenle bu Compose ayarı tek başına canlı internet yayını için güvenli sayılmaz.
- API ve veritabanı yalnız özel servis ağlarında kalmalı. Yönetim erişimi VPN/allowlist ve MFA arkasında olmalı. Proxy güven başlıklarını yalnız güvenilen ingress üzerinden kabul etmeli.
- Rate limit endpoint bazında ortak Redis/Valkey deposuna taşınıyor (WIP). Compose örneği parola korumalı, dış porta açılmayan ve backend/worker dışındaki servislerden ayrılmış iç Redis ağı kullanır. Production/staging bellek tabanlı veya parolasız sayaç deposunu reddeder. Çoklu API worker/instance aynı Redis adresini paylaşmalıdır. Bu URI/Compose yapılandırması henüz gerçek Redis ile çalıştırılmadı; Docker servisi, kesinti davranışı, kapasite, TLS ve çoklu instance kabulü açık. WAF/ingress oran sınırı ayrıca gereklidir.
- Web tokenlarının tarayıcı deposunda kalıcı tutulması azaltıldı; ancak XSS, açık oturum adına API işlemi yapabilir. CSP/XSS incelemesi, bağımsız tarayıcı testi ve gerçek HTTPS üzerinde SameSite/CORS/proxy doğrulaması hâlâ gerekli. Cookie oturumu HTTPS ve aynı site üzerinden frontend/API yayın varsayımına dayanır.
- Veritabanı, özel dosya deposu ve yedekler için aktarımda ve saklamada şifreleme, anahtar kasası, anahtar döndürme, erişim ayrımı, değiştirilemez denetim izi, yedek geri yükleme provası ve silme/yaşam döngüsü doğrulanmalı.
- Sürüm adayı üzerinde bağımlılık/SBOM taraması, statik ve dinamik güvenlik testi, tenant/rol/şube izolasyonu regresyonu ve bağımsız sızma testi tamamlanmalı. Bulgular kapatılmadan “sızmaya kapalı” veya “canlıya hazır” denmemeli.
- Android canlı sürümünde HTTPS zorunlu olmalı; debug HTTP, test endpointi, imza anahtarı ve üretim API adresi birbirinden ayrılıp mağaza öncesi incelenmeli.

## KVKK için kurum ve işletme işlemleri

- Veri sorumlusu/veri işleyen rollerini, okul ile SaaS sağlayıcısı arasındaki talimat ve sözleşmeleri; veri kategorisi, ilgili kişi, amaç, hukuki sebep, alıcı, aktarım ve saklama süresi envanterini işletme bazında belirleyin.
- Öğrenci/çocuk verileri ile sağlık ve benzeri özel nitelikli veri akışlarını ayrı haritalandırın. Gereksiz alanı toplamayı, erişimi ve saklama süresini azaltın; görev temelli erişim ve düzenli yetki gözden geçirmesi yapın.
- Aydınlatma, ilgili kişi başvuruları, düzeltme/silme ve saklama-imha süreçleri, saklama politikası, veri işleyen sözleşmeleri, personel gizlilik/güvenlik eğitimi ve ihlal müdahale sorumlularını kurum adına tamamlayın.
- Yurt dışı bulut, e-posta, mesaj, analiz, yedek veya yapay zekâ sağlayıcısına aktarım olup olmadığını uçtan uca belirleyin. Aktarım varsa güncel KVKK Kanunu 9. madde mekanizması ve gerekli Kurul bildirimlerini hukuk/uyum sorumlusuyla doğrulayın.
- İhlal tatbikatı ve iletişim planı oluşturun. Kurulun kararlarına göre Kurula bildirim için en geç 72 saat kuralı ve etkilenen kişilere makul en kısa sürede bildirim süreci işletilebilir olmalı.

## Durum

25 Kasım 2026'da yapılan salt-okunur GET isteğinde `scs360.com.tr` yanıtı `nginx/1.18.0 (Ubuntu)` gösterdi; `X-Content-Type-Options` dışındaki incelenen başlıklar yoktu. `/iletisim` ve `/.well-known/security.txt` de gerçek iletişim/bildirim içeriği yerine SPA `index.html` döndürdü. Tarama bulguları canlı için doğrulandı. Repo Nginx yapılandırmalarında CSP/çerçeve/referrer/permissions ve sürüm kapatma zaten vardı; HSTS eklendi, CSP/proxy üstbilgileri hizalandı ve bilinen `scs360.com.tr` hostu vhost listesine eklendi. Bu kaynak değişikliği üretime dağıtılmadı; aktif TLS terminatörü ve vhost yapılandırması repo ile eşleşmeyebilir.

Kaynak değişikliği SCS360 `codex/source-sync-20261111` dalına normal push ile gönderildi ve `ls-remote` SHA `7892eb31aad20e3847cc40f89fa877cf158aa402` ile doğrulandı. Bu yalnız kaynak checkpoint'idir.

`/.well-known/security.txt` için kuruluş adına izlenen, doğrulanmış bir güvenlik bildirim adresi/kanalı bulunamadı. Eski dokümandaki örnek e-posta kullanılmadı; gerçek iletişim kanalı tanımlanıp izleme sorumlusu atanıncaya kadar bu tarama bulgusu açık kalır.

Uygulama katmanındaki bu kontrol ve düzeltmeler sınırlı bir güvenlik checkpoint'idir. Canlı sunucu/edge firewall, TLS, yedek şifreleme/geri yükleme, WAF, dağıtık rate limit, bağımsız penetrasyon testi ve kurumların KVKK süreçleri bu kod değişikliğiyle doğrulanmış değildir. Bunlar tamamlanana kadar canlı güvenlik veya KVKK uyumu için kabul verilmez.
