# 19 Kasım 2026 · Öğretmen portalı API ve web izinleri

Öğretmen portalının sınıf, günlük program ve bekleyen işler API’leri ayrı izinleri denetliyor. Her sorgu atanmış sınıfları seçili kurum ve yetkili şubelerle sınırlandırıyor. Bekleyen işler yoklama ve günlük rapor türlerini hesabın kaynak okuma izinlerine göre gösteriyor.

Web yalnızca izin verilen program, görev ve ilaç verilerini istiyor ve ilgili sekmeleri gösteriyor. Hesap veya çalışma alanı değiştiğinde önceki istek iptal ediliyor. Hata durumunda yeniden deneme sunuluyor.

Sekiz geçici SQLite API ve dört web testi geçti. TypeScript, hedefli ESLint ve Git diff kontrolü geçti. Yeni API testi varsayılan izin reddini, kısıtlı şubeyi ve izin verilmeyen görev türünü kapsadı. PostgreSQL ve fiziksel cihaz kabulü açık.

Android incelemesinde yerleşik Program sekmesinin günlük akışı örnek satırlardan oluşturduğu ve bu API’leri çağırmadığı bulundu. Sırada mevcut Kotlin ekranını gerçek verilere bağlamak var.
