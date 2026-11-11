# Kaynak doğrulama durumu — 11 Kasım 2026

Bu dal geliştirme checkpoint'idir. Üretim veya tam web/native eşitliği kabulü değildir.

## Android / mobil

- Önceki responsive kaynak: native40/40PASS,0skip/0fail,8dakika.139Kotlin dosyasının SHA manifesti `native-responsive-checkpoint-20261111.json`. Sekiz pencere ve üç yazı ölçeği boyunca toplam48konfigürasyon adımı, gerçek Students/Platform ekranlarında20senaryo, büyük yazıda kritik Root düğmesine erişim ve dört görsel inceleme içerir.
- Sonraki kaynak: oturum/aktör/kurum/şube scope guard, gerçek login/me, AES-GCM token kasası ve sunucu hatasında sahte yerel başarıların kaldırılması henüz tam kabul edilmedi.145Kotlin dosyasının WIP manifesti `native-api-scope-wip-20261111.json`; önceki40PASS bu kaynağın kanıtı değildir.
- Derleme kaynak yetersizliği nedeniyle başarısız denemeler içeriyor. Güncel farklı bellekli derlemenin sonucu bekleniyor. Yeni testler ve güncel APK henüz kabul edilmedi.
- Expo birim testleri8/8PASS; Android/iOS Hermes ve web export geçti. Bu bir yerel iOS veya gerçek cihaz kabulü değildir.
- Gerçek A26 bağlı değil. Diğer native sayfalar ve API/payload/DTO sözleşmeleri tek tek doğrulanacak. Eski aktör/kurum bilgisi taşımayan telefon önbelleği korunur fakat gösterilmez; kapsamlı offline cache açık iştir.
- Gerçek sağlayıcı anahtarları/HTTPS ve mağaza ürünleri sağlanmadı. Sentetik HTTP testleri gerçek ödeme kabulü değildir.

## Backend / web

Son native aşamasından önce değişmeyen web/API kaynağı için:

- Backend904PASS/2DB'ye özgüSKIP; geçici SQLite/PostgreSQL kullanıldı. Skiplerin karşı DB'deki sürümleri çalıştı.
- Frontend62dosya/344PASS; TypeScript ve Vite build geçti.
- Web E2E32PASS/3SKIP; izole memory-provider ayarıyla eksik3vaka ayrıca geçti.35benzersiz vaka iki ayrı koşudadır.
- Gerçek yerel veritabanı yalnız okunarak17/17 kontrol geçti; veri hücreleri değişmedi. Gerçek veri veya veritabanı bu kaynak checkpoint'ine eklenmedi.

SaaS üyelik hesabı ve kurum tahsilat hesapları ayrıdır. İyzico/PayTR/Craftgate/Sipay adapterleri ve Craftgate'e bağlı banka POS yolu vardır; her bankanın doğrudan protokolü uygulanmış değildir. Üretim dağıtımı veya gerçek ödeme/mesaj yapılmadı.
