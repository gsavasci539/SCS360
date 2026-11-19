# 19 Kasım 2026 · Web öğrenci sohbeti dosya doğrulaması

Web sohbeti, seçilen dosyanın SHA-256 özetini yazma isteğinden önce hesaplıyor. Aynı işlem kimliğinin sunucudan okunan sonucu, dosya adı ve bayt özeti eşleşince taslağı kapatıyor. Yanıt kaybolursa kontrol aynı işlem kimliğini ve önceden hesaplanan özeti kullanıyor. Görüşme değişirken devam eden özet hesaplaması gönderim başlatamıyor.

İndirme, oturumlu API'den gelen baytları kayıtlı özetle karşılaştırıyor. Tarayıcı yalnızca eşleşen dosya için kaydetmeyi başlatıyor. Dosya eki doğrulaması tarayıcının Web Crypto desteğini kullanır ve HTTPS veya localhost gerektirir.

Sekiz hedefli Vitest testi ve bir Edge uçtan uca testi geçti. Edge, geçici SQLite ve yerel FastAPI ile ek gönderme ve indirmeyi doğruladı. Bir test yanıtındaki baytlar değiştirilince arayüz hata gösterdi ve ikinci bir indirme başlatmadı. TypeScript ve hedefli ESLint geçti. Fiziksel cihaz ve iOS kabulü açık.

Sırada web ve Android öğrenci sohbeti geçmişini sıralı ve sayfalı yüklemek var. Mevcut katılımcı kapsamı ve dosya doğrulaması korunacak.
