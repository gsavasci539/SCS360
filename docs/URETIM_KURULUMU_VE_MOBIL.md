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
- Tahsilat (4 Kasım güncellemesi): `finance.write` veya yalnız `finance.collect_payment` yetkilisi `GET /payments/debt-options?page=1&page_size=50&search=...` ile borç seçebilir. `selected_id` mevcut seçimi korur. Bu amaçla sınırlı liste genel borç okuma/iptal izni vermez.
- `POST /payments` gövdesi `debt_id`, iki ondalıklı pozitif `amount`, `payment_method`, isteğe bağlı `notes` ve istemcinin ürettiği UUID `request_id` içerir. Bir form/işlem için UUID'yi ağ isteğinden önce kalıcı tutun; zaman aşımında aynı içerik ve UUID ile yeniden deneyin. İlk yanıt kaybolsa bile aynı kullanıcıya tek tahsilat ve aynı makbuz döner. Farklı içerikle aynı UUID veya iptal edilmiş işlemin tekrarı `409` verir; belirsiz sonuca yeni UUID verip otomatik ikinci tahsilat göndermeyin. Eski istemciler için alan isteğe bağlıdır; yeni mobil istemci bu korumayı kullanmalıdır.
- Tahsilat yanıtı `payment_id`, `receipt_id`, `receipt_number`, `remaining_debt` içerir. Son alan işlem anındaki öğrencinin toplam kalan borcudur. Makbuz okuma izni olmayan tahsildara bu kendi işlem sonucu gösterilebilir; genel makbuz sayfasına zorunlu yönlendirme yapılmaz. `GET /payments?status=ALL` geçmişi; `ACTIVE` iptal edilmeyenleri; `CANCELLED` iptalleri getirir. Liste `search`, `page`, `page_size` kabul eder.
- `POST /payments/{payment_id}/cancel` yalnız `finance.write` ile, seçilen gerçek satırın kimliğine yapılır; aynı iptalin tekrarı bakiyeyi ikinci kez değiştirmez. Online ödeme bağlantılı satırdaki `requires_provider_refund` nakit iptalinin uygulanamayacağını belirtir. Sağlayıcı iadesi/mutabakatı ayrı akıştır; bu endpoint para iadesi göndermez.
- Ödev teslimi: metin için `POST /homework/{id}/submit` JSON `student_id`, `submission_text`; dosya için `POST /homework/{id}/submit-file` multipart `student_id`, isteğe bağlı `submission_text`, `file`. Dosya türü ve boyutu sunucu ayarlarıyla sınırlıdır. Öğretmen/veli listesinde dönen `attachment_url`, API köküne göre ve Bearer başlığıyla indirilir. Dosyalar `PRIVATE_UPLOAD_DIR` altında, herkese açık statik yüklemelerden ayrı tutulur. Notlandırılmış teslim değiştirilemez; not ve geri bildirim teslim listesinden okunur.
- iyzico hosted checkout adresi yalnız backend'den alınır; sağlayıcı anahtarları mobil uygulamaya gömülmez. Ödeme sonucu istemci dönüş ekranından tahsilat yaratılarak işlenmez; sunucunun doğruladığı callback esas alınır.
- FCM token kaydı kalıcıdır; bu çalışma Android/iOS push teslimatı, APNs/FCM sağlayıcı kurulumu veya uygulama mağazası kabulü yapmamıştır.

Şemayı yeniden üretmek için backend dizininden `python scripts/export_openapi.py` çalıştırın. Yerel doğrulama komutları kabul raporunda yer alır.
