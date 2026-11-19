# 19 Kasım 2026 · Öğretmen paneli bildirim sayısı

Öğretmen panelindeki sayaç, bildirim okuma yetkisi olan hesaplarda sunucudaki okunmamış sayıyı gösterir. Sıfır yalnızca API sıfırı doğruladığında görünür. Bağlantı hatası ve geçersiz yanıt ayrı bir durum olarak gösterilir. Hesap, kurum veya şube kapsamı değiştiğinde önceki istek iptal edilir.

Sayım ve tümünü okundu işaretleme aynı kurum, şube ve alıcı koşullarını kullanır. Veli kendi hesabına bağlı kayıtları görmeye devam eder. Platform yöneticisi kurum çalışma alanı seçer.

Dört Vitest testi ve bir geçici SQLite API testi geçti. API testi izin reddini, kendi alıcısını, kurum geneli ve atanmış şube kayıtlarını, kapsam dışı satırların korunmasını ve okundu işaretinden sonra doğrulanan sıfırı kapsadı. TypeScript ve hedefli lint kontrolleri geçti. Fiziksel cihaz ve PostgreSQL kabulü açık.

Sırada öğretmen panelindeki sınıf ve yoklama özetini atanmış öğrencilere ve kayıtlı yoklamalara dayandırmak var.
