# SCS360 test ve yerel çalıştırma — 3 Kasım 2026

Yerel uygulama başlatıldı. Arayüz: http://127.0.0.1:5173 — API belgeleri: http://127.0.0.1:8000/api/docs. Servisler yalnız bu bilgisayardan erişilecek şekilde çalışıyor; bu işlem canlı sunucuya dağıtım değildir.

## Doğrulama sonuçları

| Kontrol | Sonuç | Kanıt |
|---|---|---|
| Backend | 106 test geçti; ilgili entegrasyon vakaları SQLite ve ayrı PostgreSQL kabul veritabanında çalıştı | [Kayıt](../output/continued-backend-20261103.log) |
| Frontend | 83 test geçti; chatbot, materyal işlemleri ve iptal edilmiş makbuz baskısı dahil | [Kayıt](../output/continued-frontend-20261103.log) |
| Edge tarayıcı | 9 senaryo geçti: önceki 7 akışa ek olarak gerçek materyal yükleme/veli indirmesi ve mazeret talebi/yönetici onayı | [Kayıt](../output/continued-browser-20261103.log) |
| ESLint | 0 hata, 0 uyarı | [JSON rapor](../output/continued-lint-20261103.json) |
| Üretim derlemesi | TypeScript ve Vite başarılı. Sayfalar ayrıldı; ana JavaScript paketi yaklaşık 911 kB'den 387 kB'ye indi, büyük paket uyarısı yok | [Kayıt](../output/continued-build-20261103.log) |
| Rol bazlı GET taraması | 11 rol, 165 adres, 1.815 istek: 1.141 adet 200 ve 674 adet 403; beklenmeyen 500/404/401 yok | [Kayıt](../output/continued-api-audit-20261103.log), [sonuçlar](api-smoke-results.json) |
| Çalışan yerel uygulama | Mevcut hesapla giriş, yönetim paneli, API proxy, personel öğrenci seçimi, chatbot hazır sorusu ve normal yanıt geçti; test oturumu kapatıldı | [Sonuç](../output/running-local-verification-20261103.json) |
| Bağımlılıklar / şema | pip check ve Ruff F821/F823 temiz; tüm npm ve üretim npm denetimleri 0 açık; yerel veritabanı 028 başlığında, yedek alınarak mevcut satır sayıları korunmuş | [Şema kaydı](../output/local-migration028-20261103.log), [npm raporu](frontend-all-dependency-audit.json) |

GET taraması dinamik kimlik isteyen adreslerin tamamını, tüm yazma işlemlerini veya bütün butonları kapsamaz. Yetkisiz erişimde 403 güvenlik gereğidir; 200 ile gizlenmedi. Otomatik kabul verileri ayrı test veritabanındadır. Yerel uygulama mevcut SQLite verisini kullanır; kullanıcı hesapları ve parolaları sıfırlanmadı.

## Düzeltilenler

- Materyal yükleme, indirme, kaldırma, teslim ve notlandırma gerçek kayıtlara bağlandı. Dosya boyutu/uzantısı/içeriği ve saklama yolu denetleniyor; veli yalnız izinli materyallere kimlik doğrulamayla erişiyor. Öğrenci dosyalarında geçersiz kategori 500 yerine doğrulama yanıtı veriyor.
- Mazeret talepleri kalıcı kaydediliyor; veli geçmişi ve yönetici onay/ret ekranları eklendi. Günlük pano istatistikleri gerçek kayıtlardan, seçilen şubeye göre hesaplanıyor. Bekleyen toplamı ilk 10 satırla sınırlanmıyor.
- Okul günü için `BUSINESS_TIMEZONE=Europe/Istanbul` eklendi. Pano ve materyal tarih kontrolleri sunucunun UTC/işletim sistemi saat dilimine bağlı değil.
- Toplu ileti API'sinde sahte alıcılar ve SENT kayıtları kaldırıldı; gerçek, tekrar etmeyen ve bildirim izni bulunan alıcılar kalıcı kuyruğa ekleniyor. Eşzamanlı gönderim isteği ikinci iş oluşturmuyor. Başarı/başarısızlık sağlayıcı sonucundan okunuyor. Platform SMS sağlayıcı kataloğu süper yöneticiye sınırlandı.
- Eski finans yolları ortak tahsilat/iptal defterine bağlandı. Taksitlerde kuruş toplamı ve takvim ayları korunuyor; tahsilatın tutarı sonradan değiştirilerek borç dengesi bozulamıyor. Silme işlemi muhasebe iptali yapıyor. Gerçek PDF dönüyor, iptal edilen makbuz her iki kopyada işaretleniyor; hatırlatmalar gönderilmiş gibi gösterilmiyor.
- Yazı tipleri Türkçe karakterlerle yerel sunuluyor; Google Fonts ağ isteği kaldırıldı. Yazı tipi lisansları dağıtıma dahil edildi.
- Donanım API'sinde kimlik doğrulamasız erişim kapatıldı. Cihaz, güvenlik ve kantin işlemleri ilgili rol yetkileriyle korunuyor; kart ödeme/yükleme/bakiye ortak cüzdana bağlı. Cihaz kurum/şube kaydı ve heartbeat durumu düzeltildi; WiFi okuma geçmişi kalıcı. Tam koşuya ek 4 donanım entegrasyon testi SQLite ve PostgreSQL'de geçti: [kayıt](../output/hardware-security-backend-20261103.log).
- Chatbot hazır soru düğmesi, güncellenmesini beklediği eski giriş alanı yerine seçilen soruyu doğrudan gönderiyor. Türkçe karakterler korunuyor.
- Personel öğrenci seçimi hem liste hem sayfalı API yanıtını okuyabiliyor. Öğrenci okuma yetkisi olmayan rol için yetkisiz öğrenci isteği oluşturulmuyor.
- Öğrenci seçimi gerektiren chatbot yanıtında asıl soru saklanıyor; seçimden sonra doğru öğrenci kimliğiyle tekrar gönderiliyor.
- Mesaj kimlikleri zaman damgası yerine çakışmayan sayaçla oluşturuluyor. Öğretmene bağlan yanıtı standart API zarfından okunuyor; katılımcı adı doğru gösteriliyor.
- Süper yönetici ve muhasebe/kantin gibi rol adlarının sohbet başlığı eşleştirmeleri düzeltildi.
- ESLint kapsamından oluşturulmuş Playwright raporları ve test sonuçları çıkarıldı; kaynak ve test dosyaları kontrolde kalıyor.
- Windows için başlatma/durdurma betikleri eklendi. Başlatma, proxy ve hazır olma kontrollerini yapıyor; ikinci çalıştırma aynı süreçleri kullanıyor. Durdurma, süreç kimliği/başlangıç zamanı/çalıştırılabilir dosyayı doğrulayıp yalnız betiğin başlattığı servisleri kapatıyor. Durdur–başlat ve tekrar başlatma kontrolleri geçti.

## Kullanım

Proje kökünden:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start-local.ps1
```

Durdurmak için:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/stop-local.ps1
```

Yerel servis logları ve süreç bilgileri `.codex-build/local` içindedir. Backend kodu veya ortam ayarı değiştiğinde durdurup yeniden başlatın. Başlatma betiği demo kayıtları oluşturmaz ve mevcut portlarda çalışan başka uygulamaları kapatmaz.

Gerçek ödeme, SMS/e-posta/WhatsApp teslimatı, hedef sunucu/HTTPS, yük testi ve fiziksel mobil cihaz kabulü bu test turuyla tamamlanmış sayılmaz. Canlı kurulum ayrıntıları ve kalan kabul sınırları için [üretim kılavuzunu](URETIM_KURULUMU_VE_MOBIL.md) ve [satış öncesi kabul raporunu](SATIS_ONCESI_KABUL_2026-11-02.md) kullanın.
