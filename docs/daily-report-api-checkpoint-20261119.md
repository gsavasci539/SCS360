# 19 Kasım 2026 · Günlük karne API sözleşmesi

Günlük karne listesi seçilen şubeye göre filtrelenebiliyor. Sayfalama aynı tarihteki raporları kayıt kimliğiyle sıralıyor. Kayıt ve ayrıntı uçları sunucunun kimliğini, öğrenciyi, sınıfı, tarihi ve gözlemleri dönüyor.

040 numaralı Alembic değişikliği PostgreSQL’de beslenme gözlemlerini metin alanına taşıyor. Web ve Android’in kahvaltı, öğle ve ara öğün gözlemleri aynı kayda sığıyor. Üretim veritabanında işlem yapılmadı.

Geçici SQLite’da beş API testi geçti. Üç öğünün kaydı, ayrıntıdan okuma, şube filtresi, yetki reddi, aynı gün için ikinci kaydın reddi ve öğretmen görevleri kapsandı. PostgreSQL ve SQLite için çevrimdışı migration çıktısı doğrulandı. PostgreSQL kabul ortamı açık.
