# 19 Kasım 2026 · Günlük karne analizinin erişim kapsamı

Karne analizi, listeyle aynı kurum, şube ve öğrenci ataması kapsamını kullanıyor. Kurum çalışma alanı gerektiriyor. Silinmiş öğrencilerin kayıtları analize katılmıyor. Görülebilir karne yoksa bunu bildiriyor. Veritabanı hatası, analiz verisi yerine HTTP 503 dönüyor.

İki geçici SQLite API testi geçti. Yalnız yazma yetkisi olan kullanıcı analize erişemedi. Kendi şubesinde atanmamış öğrenci ve başka şubede bireysel ataması bulunan öğrenci analiz dışında kaldı. PostgreSQL kabulü açık.
