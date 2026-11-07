# Okul ödemeleri: kurum bazlı merchant ve 035 kabul planı

**Durum: PLANLANDI; aşağıdaki 035 modeli ve akışları uygulanmadı.**
İnceleme tarihi: 4 Kasım 2026. Ana veritabanının mevcut şeması **034**, tablo sayısı **107**.
Bu belge öğrenci borcu tahsilatını kapsar; SaaS üyelik geliri ayrı merchant kullanır.

## Mevcut korumalar ve tamamlanan düzeltme

- [Öğrenci ödeme servisi](../backend/app/application/services/online_payment_service.py) varsayılan olarak kapalıdır; eski global merchant yalnız `IYZICO_ORGANIZATION_ID` ile bağlanan okulda açılır.
- [Ödeme rotaları](../backend/app/routers/payments.py) ve [veli rotaları](../backend/app/routers/parent_portal.py) gerçek kurum, öğrenci ve veli–çocuk erişimini kontrol eder.
- Callback; retrieve imzasını, token, conversation, basket, tutar, para birimi ve `fraudStatus=1` değerini denetler.
- Checkout claim ve koşullu borç güncellemesi tekrar callback'te ikinci tahsilatı/bakiye aşımını engeller; Payment ve Receipt tek işlemde oluşur.
- [Nakit tahsilat servisi](../backend/app/application/services/cash_payment_service.py) online checkout bağlantılı ödemeye nakit iptali uygulamaz.
- **Üretimde sandbox ile gerçek borç kapatma açığı düzeltildi:** `IyzicoGateway.configured()` üretimde yalnız canlı sağlayıcı adresini kabul eder. Geliştirme/test sandbox ve üretim canlı akışı korunur.
- [Ortam kabul testleri](../backend/tests/integration/test_student_checkout_environment.py) önce **3 başarısız / 6 başarılı**, düzeltmeden sonra mevcut kapsam ve callback testleriyle **14/14 başarılı**, 28.29 saniye verdi.
- Kanıt: [RED logu](../output/student-merchant-environment-before-20261104.log), [sonuç logu](../output/student-merchant-environment-final-20261104.log). HTTP sağlayıcısı sahtedir; gerçek ödeme/ağ çağrısı yapılmadı.

## Açık eksikler

- Başlatmada istemci istek kimliği ve başlangıç HMAC/conversation doğrulaması yok; sağlayıcı çağrısı açık DB işlemi içinde yapılır.
- Yalnız token özeti saklanır. Kaybolan bağlantı/başlatma yanıtı için kalıcı resume ve belirsiz sonuç kurtarma akışı yoktur.
- Callback güncel global anahtarları ve kurum bağını kullanır; eski oturumun merchant bilgileri değişmez biçimde saklanmaz.
- [PaymentCheckout](../backend/app/infrastructure/models/models.py) üzerindeki `provider_payment_id` bütün okullar için tekildir.
- Mevcut durum sorgusu yalnız DB'yi okur; [StudentCheckoutStatus](../frontend/src/features/payment/StudentCheckoutStatus.tsx) düğmesi sağlayıcıdan retrieve yapmaz.
- Para alınmış fakat borca uygulanamamış `REVIEW` için kalıcı kanıtlı `PAID_REVIEW`, yönetici uzlaştırması ve dış iade referansı akışı eksiktir.
- **Online makbuzdaki öğrenci toplam bakiyesi hâlâ açık:** servis yalnız ödenen borcun kalanını `remaining_debt` olarak yazar. Nakit servisiyle aynı toplam öğrenci bakiyesi hesabına bağlanmalıdır.

## Asgari veri modeli ve 035 migration

1. Kuruma bağlı sabit merchant hesabı ekle: UUID, organization, provider, ortam, etkinlik, şifreli kimlik bilgileri/sürüm, oluşturan/güncelleyen ve tarihler.
2. Kimlik bilgilerini ayrı bir okul ödeme şifreleme anahtarıyla koru. JWT anahtarını veya SaaS merchant sırlarını kullanma; cevap/audit/loglarda sır döndürme.
3. API anahtarı rotasyonunda merchant hesabının UUID'si ve `merchant_scope` değişmesin. Gerçek sağlayıcı hesabı değiştiğinde yeni hesap kimliği oluşturulsun.
4. Yeni checkout; sabit `merchant_account_id`, `merchant_scope`, şifreli değişmez merchant snapshot'ı, `request_digest` ve şifreli token/URL/süre bilgisi taşısın.
5. Sağlayıcı işlem referansı, doğrulanmış tutar/para birimi, inceleme nedeni ve sonuç zamanı kalıcı olsun. Gerekli alanlar eski satırlar için nullable eklenmeli.
6. Provider ödeme referansı tekilliğini `(merchant_scope, provider_payment_id)` kapsamına taşı. Scope anahtar sürümü değildir; aynı hesabın rotasyonları arasında ödeme tekrar kullanılamaz.
7. Eski satırlara yeni scope için `legacy:<organization_id>` atanabilir. Eski UUID, token özeti, ödeme referansı, tutar, durum ve ilişkiler korunmalı; geçmişe tahmini credential snapshot yazılmamalı.
8. SQLite'daki eski adsız unique constraint için isimlendirilmiş batch migration gerekir; PostgreSQL ve SQLite üzerinde aynı veri koruma kabulü uygulanmalı.
9. Token özeti tekilliği değiştirilirse yeni callback'ler checkout kimliğiyle çözülmeli; belirsiz token eşleşmesi rastgele ilk kayda bağlanmamalı.
10. Anahtar değişimi eski checkout snapshot'ını değiştirmemeli. Sağlayıcı eski anahtarı iptal etmişse oturum incelemeye alınmalı; başka hesabın anahtarlarıyla sessizce denenmemeli.

## Başlatma, callback ve sonuç sözleşmesi

- İstemci UUID istek kimliğini ağ çağrısından önce saklar. Yeni checkout kimliği bu UUID olabilir; aynı actor/kurum/gövde aynı oturumu döndürür, farklı içerik aynı UUID ile genel 409 alır.
- Yetki kontrolü ve `Org → Debt → Checkout` kilit sırası altında rezervasyon/digest/snapshot kaydedilip commit edilir; sağlayıcı beklenirken okulun yazma kilidi tutulmaz.
- Aynı anda gelen tekrar, ikinci sağlayıcı başlatması yapmaz. Etkin belirsiz checkout varken yeni bir tahsilat başlatılması engellenir.
- Başlangıç HMAC, beklenen conversation, izinli HTTPS checkout adresi ve geçerli TTL doğrulanır; token/URL şifreli saklanır.
- Ağ hatası veya eksik yanıt tek başına kesin `FAILED` sayılmaz. Belirsiz sonuç korunur; süre dolması paranın alınmadığının kanıtı değildir.
- Mevcut `/api/payments/iyzico/callback` adresi korunur. Yeni başlatmalarda sunucu callback'e `checkout_id` ekler; böylece token henüz kaydedilmeden gelen sonuç da bulunabilir.
- Checkout kimliği tek başına ödeme kanıtı değildir. Snapshot merchant ile retrieve ve bütün eşleşmeler doğrulanmadan token benimsenmez veya borç azaltılmaz.
- Eski token-only callback eski bağlanmış merchant için desteklenir; yeni başlatmayı kapatmak mevcut gerçek ödemeyi doğrulamayı kapatmamalıdır.
- Doğrulanmış sonuç yeniden kilit alındıktan sonra taze borç/checkout durumuna uygulanır. Borcun kurumu checkout kurumuyla eşleşmelidir.
- Yeni durumlar mevcut istemci sözleşmesiyle açıkça eşlenir: `INITIALIZING`, `PENDING`, `FRAUD_REVIEW`, `PAID_REVIEW`, `COMPLETED`, kesin `FAILED` ve `REFUNDED`.
- Geçerli ödeme borca uygulanamıyorsa kanıt ve referans kaybolmadan `PAID_REVIEW` olur; ikinci kez ödeme önerilmez.
- Başarılı ledger yazımı tek Payment/Receipt/Audit/Queue üretir; makbuzda işlem anındaki toplam öğrenci borcu kullanılır.

## Rotalar, arayüz ve yetkiler

- Merchant ayarları için kurum sahibi ve açık kurum çalışma alanındaki Root yetkisi sunucuda doğrulanmalı. Root'un varsayılan SaaS alanı okul ayarlarını açmamalı.
- Genel `finance.write` veya `settings.write`, sağlayıcı sırlarını yönetme yetkisine kendiliğinden dönüşmemeli. Özel roller otomatik genişletilmemeli.
- Ayar cevabı etkinlik/ortam/yapılandırma durumunu döndürür; anahtarların tamamı veya şifreli değerler geri okunamaz. Rotasyon ayrı, açık işlem olmalıdır.
- Staff `/api/payments/iyzico/checkouts/{id}` ve Parent `/api/parent/payments/checkouts/{id}` kapsamında `resume` ve gerçek `payment-status` işlemleri tasarlanmalı.
- Resume URL'si oluşturan kullanıcıya veya açıkça yetkili finans yöneticisine verilmeli; yalnız ortak çocuk ilişkisi başka velinin ödeme oturumunu açmamalı.
- [PaymentPage](../frontend/src/features/payment/PaymentPage.tsx), [ParentPortalPage](../frontend/src/features/parent/ParentPortalPage.tsx) ve StudentCheckoutStatus aynı kalıcı istek/sonuç sözleşmesini kullanmalı.
- Aynı kullanıcı/kurum/sekme için sayfa yenilemede belirsiz işlem sürdürülebilmeli; kurum veya hesap değişiminde taslaklar karışmamalı.
- Yönetici uzlaştırması gerekçe ve istek kimliğiyle idempotent olmalı. Tutar/para birimi/kalem uyuşmazlığı zorla borca uygulanmamalı.
- `REFUND_RECORDED` dışarıda doğrulanmış iade referansını, tutarını ve aktörü kaydeder; bankaya/sağlayıcıya para veya iade isteği göndermez. Tekrarı bakiyeyi ikinci kez değiştirmez.
- [SaaS gateway](../backend/app/application/services/saas_gateway.py) içindeki şifreleme/imza/URL örüntüleri kullanılabilir; belirsiz sonucu zamanla `FAILED` yapan SaaS iş akışı bütünüyle kopyalanmamalı.
- [release_preflight.py](../backend/scripts/release_preflight.py) etkin merchant, kurum bağı, şifreleme ve üretim/canlı koşullarını denetlemeli; yalnız üç global alanın doluluğu yeterli değildir.

## Zorunlu geçici DB ve sahte sağlayıcı kabulü

- İki okulun ayrı merchant'ı; başka kurum/şube/çocuk/actor erişiminin reddi; cevaplarda/auditlerde sır bulunmaması.
- Aynı provider referansının farklı merchantlarda kabulü, aynı merchantta ve anahtar rotasyonu sonrasında tekrarının reddi.
- Rotasyon/kapatma sonrasında eski callback; eski token-only callback ve mevcut ödeme referanslarının korunması.
- Eşzamanlı aynı UUID, farklı içerik/actor UUID çakışması; kaybolan başlatma yanıtı ve erken checkout kimlikli callback.
- Sahte başlangıç/retrieve imzası, yanlış conversation/basket/tutar/para birimi/kalem, geçersiz URL/TTL ve bozuk eski sayısal veriler.
- Üretimde sandbox engeli; üretim canlı ve geliştirme sandbox devamı; fraud inceleme → onayda bir kez tahsilat.
- Cash ile eşzamanlı ödeme, kapatılan/silinen/ödenmiş borç: tek ledger veya kanıtlı `PAID_REVIEW`; makbuzdaki toplam öğrenci bakiyesi.
- Resume/reload/gerçek durum kontrolü; yönetici uzlaştırması ve dış iade kaydının tekrarı; gerçekleşmeyen işlemin başarı gösterilmemesi.
- Mevcut [kapsam](../backend/tests/integration/test_student_checkout_scope.py), [veli amacı](../backend/tests/integration/test_parent_purpose_scope.py), callback ve SaaS testleri korunmalı; mobil akış ayrıca sınanmalı.

## Ana veriye uygulamadan önce

1. Ana uygulama/worker yazılarını kontrollü durdur; **035 öncesi yeni ve doğrulanmış yedek** al. Mevcut kullanıcı/hesap/parola/UUID/finans kayıtlarını değiştirme.
2. Önce ana verinin ayrı klonunda `034 → 035` uygula. Yeni kurulumun geçmesi eski verinin taşındığı anlamına gelmez.
3. Önce/sonra bütün eski tabloların satır sayılarını, ilişkilerini ve **yalnız eski sütunlardan oluşan sıralı SHA manifestini** karşılaştır. Yeni sütun/scope eklenmesi eski değerlerin değişmesini haklı çıkarmaz.
4. Klonda migration, eski callback/ödeme/makbuz okumaları, paket/rol ayrımı ve geri dönüş provası geçmeden ana DB'ye 035 uygulama.
5. Kabul sonuçlarını devam kaydına yaz; gerçek mesaj/ödeme/iade göndermeden ve üretime dağıtmadan iç geliştirme doğrulamasını tamamla.
