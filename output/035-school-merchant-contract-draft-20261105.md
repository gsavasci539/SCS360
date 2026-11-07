# 035 okul merchant entegrasyonu — sözleşme taslağı

Durum: **TASARIM; runtime/model/migration/API uygulanmadı, aşağıdaki kabul senaryoları çalıştırılmadı.**
5 Kasım 2026. Ana DB **034/107 tablo** olarak korunur. Root'un mevcut restart/kabul aşaması bitmeden 035 migration veya model eklenmez.
Önceki ayrıntılı inceleme: `docs/OKUL_ODEME_MERCHANT_PLANI.md`.

## Dosya sahipliği ve kesin yardımcı arayüzü

- Merchant ajanı: `models.py` içindeki yeni model/checkout ek alanlar; yeni035 migration; yeni merchant DTO/service/router ve özel testler.
- Root: `online_payment_service.py`, checkout/payment/parent rotaları, config anahtarları, main router kaydı, frontend ödeme/resume akışı ve ana DB'ye uygulama.
- UI ajanı: aşağıdaki güvenli merchant GET/PUT sözleşmesine göre kurum sahibi ayar formu.
- Servis modülü: `app/application/services/school_payment_merchant.py`.
- `async resolve_gateway(db, organization_id, checkout=None)` → `{gateway, merchant_account_id, merchant_scope, merchant_snapshot}`.
- `gateway`: mevcut `IyzicoGateway` ile uyumlu; `merchant_account_id`: UUID veya None; `merchant_scope`: sabit hesap kapsamı; `merchant_snapshot`: şifreli string veya eski kayıt için None.
- Yeni başlatmada current/enabled okul hesabı çözülür, sabit snapshot hazırlanır. Okul hesabı yoksa yalnız açıkça aynı kuruma bağlı eski `IYZICO_*` hesabına fallback yapılır.
- Okul hesabı kaydı varsa ve kapalıysa global hesaba fallback yapılmaz. Mevcut checkout çözümünde current ayarlar kullanılmaz; checkout snapshot'ı doğrulanıp açılır.
- Snapshot bulunmayan eski checkout yalnız eski, aynı okula bağlı merchant ile doğrulanır. Eski ödeme başlatmayı kapatmak callback doğrulamasını kapatmaz.
- `seal_school_secret(values: dict) -> str`, `open_school_secret(ciphertext: str) -> dict`: yalnız `SCHOOL_PAYMENT_ENCRYPTION_KEY` ve Fernet; eksik/bozuk anahtar veya ciphertext için güvenli503. SaaS/JWT anahtarını kullanmaz.
- Snapshot içeriği: sürüm, organization_id, merchant_account_id, merchant_scope, environment, api_key, secret_key, callback_url. Çözerken checkout'un kurum/scope/account kimlikleriyle karşılaştırılır.
- Yeni işlemlerde callback URL yalnız sunucudaki `SCHOOL_PAYMENT_CALLBACK_URL` değerinden gelir; owner rastgele sağlayıcı/callback adresi giremez.

## Güvenli GET / PUT

`GET /api/payments/merchant` standart success/data zarfında yöneticiye şu alanları döndürür:

```text
can_manage: boolean
configured: boolean
enabled: boolean
environment: SANDBOX | LIVE | null
account_id: UUID | null
revision: 64 karakter hex | null
has_api_key: boolean
has_secret_key: boolean
callback_configured: boolean
encryption_configured: boolean
production_compatible: boolean
available: boolean
updated_at: ISO zaman | null
```

Yönetici olmayan native `finance.read`, `finance.write` veya `parent.make_payment` kullanıcısına yalnız `{can_manage:false, available:boolean}` döner. Hesap UUID/revision/key varlığı/sırlar paylaşılmaz. Diğer kullanıcılara403.

`PUT /api/payments/merchant` gövdesi:

```text
request_id: zorunlu UUID
expected_revision: 64 karakter hex | null
enabled: boolean
environment: SANDBOX | LIVE
api_key?: SecretStr
secret_key?: SecretStr
replace_account: boolean = false
```

- Boş/atlanmış anahtarlar mevcut hesabın anahtarlarını korur; ilk yapılandırma veya yeni hesap için iki anahtar da gereklidir.
- Native yetkili: kurumun gerçek `organization_subscriptions.owner_user_id` hesabı. Bu referans yoksa yalnız aynı kurumun gerçek `owner` rolü eski kurum fallback'idir; `org_admin` otomatik merchant yöneticisi değildir.
- Root yalnız `tenant.platform_admin` ve açıkça seçilmiş okul bağlamında yönetir; çalışma alanı dışındaki ham superadmin isteği403.
- Genel finance/settings yetkisi sır yazma hakkı vermez. PUT sağlayıcıya bağlanmaz veya ödeme göndermez.
- Aynı merchant hesabında anahtar rotasyonu UUID'yi korur. `replace_account=true` yeni sabit hesap UUID'si açar ve önceki kaydı current durumundan çıkarır. Ortam değişimi açık replacement gerektirir.
- request_id + actor + organization + gövde için keyed digest audit'te tutulur; aynı isteğin tekrarı aynı güvenli sonucu döndürür. Sır, düz fingerprint girişi veya SecretStr repr loglanmaz.
- expected_revision stale ise409. Başarılı değişiklik ve audit tek transaction'dır. Üretimde SANDBOX enable reddedilir; mevcut üretim-sandbox callback koruması korunur.
- Kapatma için sağlayıcı anahtarlarının/şifreleme yapılandırmasının çalışması gerekmez; kapatılmış hesabın eski snapshot'ları silinmez.

## Planlanan modeller ve migration

- `SchoolPaymentMerchant`: id, organization_id, is_current, enabled, environment, nullable credentials_ciphertext, created_by, updated_by, created_at, updated_at.
- Yalnız is_current=true satırlarda organization_id için partial unique index. Anahtar rotasyonu aynı hesabın güncellemesidir; gerçek sağlayıcı hesabı değişimi yeni satırdır.
- `PaymentCheckout`: merchant_account_id nullable FK, merchant_scope nullable String100, merchant_snapshot nullable Text, request_digest nullable String64, checkout_secret nullable Text, provider_transaction_id nullable String255, paid_amount nullable Numeric12,2, review_reason nullable String255, verified_at nullable zaman.
- Eski provider_payment_id global unique yerine `(merchant_scope, provider_payment_id)` unique. Scope **anahtar sürümü değildir**. token_hash ve payment_id tekilliği korunur.
- Eski satırlarda yalnız yeni merchant_scope alanı backfill edilir. Eski UUID/ilişki/tutar/tarih/token/reference/status değerleri veya eski sütun tipleri değiştirilmez.
- Legacy scope, UUID'nin canonical biçimiyle `legacy:<organization_id>` olmalı. SQLite32hex ve PostgreSQL36 karakter biçimleri aynı hesaba farklı scope üretmemeli; eski organization_id sütunu normalleştirilmez.
- Snapshot veya sırlar eski DB satırlarına tahmin edilerek yazılmaz. SQLite adsız eski unique constraint, reflection/naming convention ile güvenli batch migration gerektirir.
- Ana DB öncesi yeni backup → ayrı main klonunda034→035 → eski sütunlardan sıralı SHA ve tüm satır sayımı karşılaştırması → callback/ledger okuma → geçici SQLite ve PostgreSQL kabulü. Root doğrulayıp uygulamadıkça main035 yapılmaz.

## Çalıştırılmamış kabul senaryoları

1. İki kurumun kendi owner'ı ayrı hesap yapılandırır; diğer kurum/native finance/org_admin sır yazamaz; Root yalnız seçilmiş kurumda yönetir.
2. GET/PUT/audit/log çıktılarında gerçek/sahte credential değerleri bulunmaz; DB'de yalnız şifreli değer vardır; boş anahtar input'u mevcut sırrı silmez.
3. Aynı istek eşzamanlı tekrarında tek hesap/audit; actor/kurum/gövde değişirse409; stale revision mevcut anahtarı ezmez.
4. Rotasyon hesap UUID'sini korur; eski checkout snapshot eski sırrı çözmeye devam eder. Ortam/hakiki hesap değişimi explicit replacement ister ve yeni UUID üretir.
5. Disabled okul hesabı global legacy merchant'a düşmez. Hiç okul hesabı yokken legacy fallback yalnız açık kurum bağı ve açık başlatma bayrağıyla çalışır.
6. Cipher/callback eksikliği yeni başlatmayı engeller; kapatma işlemi yine yapılır. Üretim sandbox kapalı, üretim live ve geliştirme sandbox çalışır.
7. Aynı provider reference ayrı sabit merchant kapsamlarında kabul edilir; aynı hesapta rotasyon sonrası tekrar kullanılamaz.
8. Eski token-only callback, checkout ID/ödeme referansları ve eski alanların SHA manifesti klon migration sonrasında korunur.
9. Root entegrasyon kabulü: init imzası/nonce/resume, token metadata şifreleme, kaybolan yanıt/erken callback, PAID_REVIEW ve toplam öğrenci bakiyesi. Bu helper'ların yazılması akışların bağlı ve tamamlanmış olduğu anlamına gelmez.

Gerçek sağlayıcı hesabı/anahtarları kullanıcıda henüz yoktur. İç geliştirme sahte sağlayıcıyla ilerleyebilir; gerçek LIVE veya sandbox kabulü bu belgede yapılmış sayılmaz. Gerçek ödeme, mesaj veya üretim dağıtımı yapılmaz.
