# 19 Kasım 2026 · Web karne formunda öğrenci seçimi

Web ve Android günlük karne formları öğrenciyi `/api/daily-reports/student-options` üzerinden seçiyor. Seçenekler aktif çalışma alanı, yetkili şube ve öğretmenin sınıf ya da bireysel öğrenci atamasına göre süzülüyor. Geçerli sınıfı bulunan öğrenciler adla veya numarayla aranabiliyor. API öğrenci kimliğini, seçim etiketini, öğrenci adını ve sınıf kimliğini döndürüyor. Android bir sınıf seçildiğinde isteği o sınıfla sınırlandırabiliyor.

Form, sunucudan seçilen öğrenciyle birlikte zorunlu tarihi gönderiyor. Karne yazma izni, seçim için yeterli. Kapsam dışındaki, sınıfsız ve farklı kurumdaki öğrenciler seçenek olarak dönmüyor.

Dört geçici SQLite API testi ve üç web testi ilk uygulamada geçti. TypeScript ve hedefli ESLint kontrolleri geçti. Android için eklenen sınıf filtresiyle, öğrenci dizini ve karne okuma izni bulunmayan karne yazarının kendi kapsamından öğrenci seçip karne oluşturabildiği geçici SQLite üzerinde tekrar doğrulandı. Hedefli Ruff kontrolü geçti.
