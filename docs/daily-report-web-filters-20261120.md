# 20 Kasım 2026 · Web karne listesi filtreleri

Karne araması yetkili kayıtların tümüne sayfalama öncesi uygulanıyor. Öğrenci adı ve numarası, ruh hali, uyku, beslenme ve öğretmen notları aranabiliyor. Türkçe büyük ve küçük harfler eşleşiyor. Tarih filtresi aramayla birlikte çalışıyor. Web, filtre değiştiğinde ilk sayfayı istiyor ve geciken önceki yanıtları kullanmıyor.

Geçici SQLite üzerinde ad, numara, tarih, şube ve atama kapsamı ile sayfa toplamları doğrulandı. Hedefli web testleri, filtre değişiminde eski yanıtın listeyi değiştirmediğini ve yazma yetkisiyle liste isteği gönderilmediğini doğruladı. PostgreSQL kabulü açık.
