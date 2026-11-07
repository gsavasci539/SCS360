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

## Okulun tahsilat yetkileri

Kurum sahibi yalnız tahsilat yapacak personeline `finance.collect_payment` verebilir. Bu kullanıcı **Tahsilat al** ekranında arama ve sayfalama ile yetkili olduğu borcu seçer; genel borç listesini okuma, gider düzenleme veya tahsilat iptali yetkisi kazanmaz. Finans okuma yetkisi ayrıca verilirse tahsilat geçmişi de görünür. İptal yalnız `finance.write` yetkilisindedir ve düğmenin bulunduğu satırı hedefler.

Bağlantı kesilirse aynı tahsilat formundan tekrar denenir; form istek kimliğini korur. Başarıda makbuz okuma izni varsa makbuz açılır, yoksa makbuz numarası ve işlem anındaki toplam kalan borç formda gösterilir. Online tahsilatlar nakit iptaliyle silinmez; sağlayıcı iadesi ve mutabakatı gerekir. Mevcut finans kayıtları ve makbuz numaraları korunur.

## Kabul kaydı

Güncel testler, veritabanı yedeği ve yarım iş için [CALISMA_DURUMU.md](CALISMA_DURUMU.md); ayrıntılı kapsam için [SAAS_KABUL_PLANI.md](SAAS_KABUL_PLANI.md). Yerel testlerin geçmesi üretim/satış kabulünün tamamlandığı anlamına gelmez.
