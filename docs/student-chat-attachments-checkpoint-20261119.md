# 19 Kasım 2026 · Web öğrenci sohbetinde dosya eki

Ortak sohbet bileşeni veli, öğretmen ve yönetim ekranlarından PDF, PNG ve JPEG gönderiyor. Mesajlar öğrencinin mevcut sohbeti üzerinden yükleniyor. Ek, yetkili katılımcıya oturumlu istekle ve önbelleksiz indiriliyor. Eski yazılı sohbet çağrıları çalışmaya devam ediyor.

Yazılı ve ekli gönderimler işlem UUID'si ile doğrulanıyor. Yanıt kesilirse arayüz ayrı bir okuma isteğiyle kaydı kontrol ediyor. Kayıt bulunamazsa aynı kimlikle yeniden denenebiliyor. Mesajlar, uzun dosya adları ve düğmeler dar alanda satıra sığıyor. Yeni mesajlar yalnız liste sonu izlenirken otomatik kaydırılıyor.

Geçici SQLite'ta 6 hedefli test geçti. İlk eşzamanlı gönderim, yinelenen istek, özel indirme, başka öğrenci ve kurumun reddi, geçersiz ek, yazma hatasında geri alma ve eski metinli sohbet sınandı. Webde 3 bileşen testi, TypeScript ve hedefli ESLint geçti. PostgreSQL ve fiziksel cihaz kabulü bekliyor.

Sıradaki iş Kotlin veli öğrenci sohbetini bu API sözleşmesine bağlamak. Android genel sohbetinin dosya eki ayrı akışta mevcut.
