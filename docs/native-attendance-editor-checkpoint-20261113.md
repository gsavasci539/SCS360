# Yoklama formu: mevcut kaydı yükleme ve düzenleme

13 Kasım 2026: Web yoklama formu sınıf+tarih için mevcut kayıtları gerçek `/api/attendance` GET yanıtından yükler; status/not/version korunur. Sunucuda kaydı olmayan öğrenci `UNRECORDED` kalır ve yazma isteğine katılmaz. Durum seçilmeden not veya kayıt gönderilemez. Yeni kayıt ve değişiklikler version kontrollü `/api/attendance/bulk` ile gönderilir; başarı sayısı API yanıtından gösterilir. Belirsiz ağ yanıtında aynı request id/gövdeyle tekrar, eski sürümde 409 ve okuma rolünde salt okunur davranış korunur.

Backend endpoint'i diğer modüllerdeki değişikliklerle dolu `core_modules.py` dosyasına yeni test kodu eklememek için ayrı router modülüne taşındı ve route registry içinde önce kaydediliyor. GET sınıfı tenant/şube kapsamıyla doğrular; sınıf/tarih ve sayfalama filtresi, sürüm özeti ve notu döndürür. PUT mevcut atomic editor service'i kullanır.

## Kanıt

- Backend: `backend/tests/integration/test_attendance_editor.py` — **6 passed, 6 skipped**; SQLite test DB kullanıldı. Atlananlar PostgreSQL’e özel fixture varyantlarıdır.
- Web UI: `frontend/src/test/attendance-editor.test.tsx` — **7 passed**. Eski kayıt yükleme/düzenleme, sınıf yükleme retry, class/date değişiminde eski yanıtı reddetme, başlangıç GET hatasında kaydı kilitleme, timeoutta özdeş tekrar, salt-okuma ve kayıtsız öğrencinin varsayılan olarak “Geldi” olmaması doğrulandı.
- Frontend `tsc -b && vite build` başarılı. Rollup yalnızca üçüncü taraf Zod yorum anotasyonlarını kaldırdığına ilişkin uyarı verdi.
- Yeni Python kaynaklarında Ruff F821/F823 temiz. Hiçbir production DB, fiziksel cihaz, ödeme sağlayıcısı veya mesaj servisi kullanılmadı.

Bu hedefli checkpoint bütün web/native modüllerinin, tam test paketinin veya cihaz kabulünün tamamlandığı anlamına gelmez. Native günlük yoklama istemcisi önceki checkpoint’te kabul edilmiş ve bu turda değişmemiştir. Sonraki iç iş: kalan native/API mutasyonlarını modül bazında eşitlemek ve tam paket testlerini son kaynak değişikliğinde çalıştırmak. Fiziksel A26 ve gerçek sağlayıcı kabulü ayrı tutulur.
