# SCS360 SaaS kabul kapsamı

3 Kasım 2026 kullanıcı talebi. Tamamlanmadan satış/üretim kabulü verilmez.

- Platform yöneticisi mevcut `is_super_admin` hesabıdır. Kurum/paket/üyelik açma, kapatma ve süre yönetimi yalnız bu yetkiyle yapılır; okulun kendi rol veya yetki tanımlaması platform yöneticiliği kazandırmaz. Mevcut yönetici hesapları otomatik silinmez veya parolaları değiştirilmez.
- Okul sahibi kendi kurumunda personel, veli hesabı, öğrenci ve şube yönetir. Kurumlar arası veri ve hesap erişimi kapalı kalır.
- Paket adı, fiyatı, para birimi, dönemi ve şube/öğrenci/kullanıcı sınırları ana yönetici tarafından tanımlanır; fiyat uydurulmaz. Satın alınmış dönem kendi paket görüntüsünü saklar; katalog düzenlemesi eski satın almayı sessizce değiştirmez.
- Dönem bitince uyarı gösterilir. Bitiş anından itibaren 10 gün ek süre; 10. günün sonunda ödeme yoksa kurumun uygulama erişimi ödeme/üyelik ekranına gider. Mevcut token ve mobil API de bu durumu aşamaz. Ana yönetici bu engelden etkilenmez.
- Kapatılmış kurum ödeme ile kendiliğinden açılmaz; ana yönetici tekrar açmalıdır. Ödeme ve oturumdan çıkış yolları erişim engeli içinde çalışmalıdır. Personel/veli ödeme detaylarını göremez; kurum sahibine ulaşma durumu gösterilir.
- Şube/öğrenci/kullanıcı kotaları sunucuda ve eşzamanlı işlemlerde uygulanır. Sayım silinmemiş kayıtlar üzerinden yapılır; pasife alma kotayı gizlice aşma yolu değildir. Platform yöneticisi hesabı okul kullanıcı kotasında sayılmaz. Veli giriş hesabı kullanıcı kotasında sayılır.
- Mevcut kurumlarda paket yoksa veri ve erişim tahminle değiştirilmez; eski/paketsiz durum ana yöneticiye açıkça gösterilir. Yeni kurum oluşturma yolları paket/üyelik kurulumu olmadan sınırsız aktif hesap üretmemelidir.
- Paket düşürme, kota aşımı veya ödeme gecikmesi verileri silmez. Önceden girilmiş kayıtlar ve hesaplar korunur.
- Yalnız doğrulanmış sağlayıcı ödemesi veya ana yöneticinin kayıtlı yetkili işlemi üyeliği uzatır. İstemci tutarı/ödendi bayrağına güvenilmez. Tekrar/callback/yarış tek tahsilat ve tek uzatma üretir. Gerçek ödeme ve mesaj gönderimi yapılmaz; dış sağlayıcı kabulü ayrı kalır.

Kabul: geçici SQLite ve PostgreSQL; ana yönetici/okul sahibi/personel/veli; kurum dışı ret; paket sınırı ve eşzamanlı son yer; toplu içe aktarma; bitiş/ek sürenin son anı; eski token; kapatma/açma; ödeme tekrarları; mobil yönlendirme; mevcut veri/migration koruması. Sonra tüm testler, build ve canlı salt okuma kontrolü.

Yarım servis yönetim arayüzü ve önceki satış öncesi hata listesi kapsamda kalır. Saatlik devam otomasyonu bu SaaS kapsamıyla güncellendi; limit %100 veya ordinaryUsageAllowed=false olduğunda yeni geliştirme yapılmaz, sonraki kontrolde kaldığı kayıttan sürer.
