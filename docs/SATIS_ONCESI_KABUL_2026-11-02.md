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
