# 19 Kasım 2026 · Öğrenci listesinde öğretmen ve kurum sahibi kapsamı

Web ve native istemcilerin kullandığı `/api/students` listesi ortak öğrenci erişim kuralını kullanıyor. Öğretmenin doğrudan atandığı öğrenciler, başka bir sınıfta veya sınıfsız olsalar da yetkili şube kapsamı içinde listeleniyor. Aynı hesap öğretmen ve kurum sahibi rollerini taşıyorsa kurum sahibinin tüm kendi kurumuna erişimi korunuyor. Açık sınıf, şube ve sınıfsız öğrenci filtreleri çalışıyor.

12 geçici SQLite API testi ve 2 birim testi geçti. Yeni regresyon doğrudan atamayı, sınıfsız öğrenciyi, atama dışındaki öğrenciyi, açık filtreleri, şube sınırını ve birleşik kurum sahibi rolünü kapsadı. Yoklama düzenleyicisi, öğretmen özeti ve birleşik öğretmen/veli kapsamı da doğrulandı. Hedefli Ruff ve Git diff kontrolleri geçti. PostgreSQL ve fiziksel cihaz kabulü açık.

Sırada öğretmen portalının sınıf, günlük program ve bekleyen işler API izinlerini web ve Android çağrılarıyla karşılaştırmak var.
