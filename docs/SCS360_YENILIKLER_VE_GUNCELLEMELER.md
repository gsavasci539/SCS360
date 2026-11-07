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

