# 19 Kasım 2026 · Web karne formunda öğrenci seçimi

Yeni günlük karne formu, öğrenciyi `/api/daily-reports/student-options` üzerinden seçiyor. Seçenekler aktif çalışma alanı, yetkili şube ve öğretmenin sınıf ya da bireysel öğrenci atamasına göre süzülüyor. Geçerli sınıfı bulunan öğrenciler adla veya numarayla aranabiliyor. Sayfa değiştiğinde seçili öğrenci yeniden doğrulanabiliyor. API yalnızca seçimde kullanılan kimlik ve etiketi döndürüyor.

Form, sunucudan seçilen öğrenciyle birlikte zorunlu tarihi gönderiyor. Karne yazma izni, seçim için yeterli. Kapsam dışındaki, sınıfsız ve farklı kurumdaki öğrenciler seçenek olarak dönmüyor.

Dört geçici SQLite API testi ve üç web testi geçti. TypeScript, hedefli ESLint ve Ruff kontrolleri geçti. Sırada Android günlük karne öğrenci seçiminin aynı kapsamlı uçla doğrulanması var.
