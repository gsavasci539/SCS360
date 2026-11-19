# 19 Kasım 2026 · Eski öğretmen rollerinde yoklama erişimi

`teacher1`, `teacher2` ve `teacher3` hesapları ortak öğrenci ve sınıf kapsamı denetiminde öğretmen olarak değerlendiriliyor. Yoklama listesi ve toplu düzenleyici, atanmış öğrencileri ve sınıfları kullanıyor. Aynı hesap kurum sahibi rolüne de sahipse kendi kurumundaki kayıtları kurum sahibi yetkisiyle görmeye devam ediyor.

On geçici SQLite testi geçti. Üç eski rol için atanmış kaydın okunması ve düzenlenmesi, atama dışındaki sınıfa yazma isteğinin reddi ve kurum sahibi rolü eklendiğinde kurum kapsamının korunması doğrulandı. Öğretmen sohbeti, doğrudan atama, ödev ve kurum sahibi regresyonlarından dört geçici SQLite testi daha geçti. Ruff ve Git diff kontrolü geçti. PostgreSQL ve fiziksel cihaz kabulü açık.

Sıradaki kontrol `/api/students` üzerindeki ek sınıf filtresi. Doğrudan öğrenci atamalarının ve öğretmen rolü de taşıyan kurum sahibinin öğrenci listesinin ortak kapsamla tutarlı olduğunu doğrula.
