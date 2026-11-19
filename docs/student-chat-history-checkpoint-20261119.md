# 19 Kasım 2026 · Öğrenci sohbeti geçmişi

Web ve Kotlin Android, öğrenci sohbetinde son 50 kaydı yükler. Daha eski sayfanın sınırı en eski görünen mesajın UUID'sidir. API bu kimliği aynı konuşmada doğrular ve sayfaları zaman damgası ile UUID üzerinden sıralar. Parametresiz istek eski dizi biçimini ve okundu davranışını sürdürür. Sayfalı istek yalnız dönen gelen iletileri okundu işaretler.

Web eski sayfayı eklerken kaydırma konumunu korur. Android aynı mesaj anahtarlarıyla eski sayfayı listenin başına ekler. Önceki öğrenci, veli, şube ve dosya doğrulaması geçerlidir.

Geçici SQLite'ta beş API testi, webde dokuz Vitest ve bir Edge testi, Android'de dört sentetik Compose ve geçici FastAPI ile bir Kotlin kabul testi geçti. API testi aynı zaman damgalı kayıtları, başka öğrenciye ait sayfa sınırının reddini ve okundu sayacını kapsadı. Edge, öğretmen geçmişini 50 kayıt sınırıyla açıp dosya gönderme ve indirmeyi doğruladı. TypeScript, hedefli ESLint ve Ruff geçti. PostgreSQL ve fiziksel cihaz kabulü açık.

Sıradaki iş eski web öğretmen panelindeki hızlı sohbetin taslağı sunucu kaydı olmadan kapatan gönderimini gerçek, yetki kontrollü görüşme akışına bağlamak.
