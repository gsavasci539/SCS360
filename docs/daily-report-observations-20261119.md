# 19 Kasım 2026 · Günlük karne gözlemleri

Karne analizi web formundaki kodları ve Android formundaki Türkçe kayıtları ortak sonuçlara eşliyor. Ruh hali ve uyku oranları ilgili alanda tanınan kayıtlarla hesaplanıyor. Android’in ayrı yazdığı kahvaltı, öğle yemeği ve ara öğün, beslenme oranında ayrı öğün sayılıyor. Süre yazılmış bir uyku kaydı uyunduğunu gösteriyor. Uyku kalitesi süreye bakılarak çıkarılmıyor.

Eksik ve tanınmayan değerler oranlara veya takip notlarına katılmıyor. Gözlem bulunmadığında API oranı `null` dönüyor ve web `Gözlem yok` gösteriyor. Kaydedilmiş gözlemlerden hesaplanan gerçek `%0` görünür kalıyor. Takip kartları kaydedilmiş gözlem sayılarını gösteriyor.

Geçici SQLite iki API testi ve üç hedefli web testi geçti. TypeScript, hedefli ESLint ve Ruff geçti. PostgreSQL ve fiziksel A26 kabulü açık.
