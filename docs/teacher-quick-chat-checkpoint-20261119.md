# 19 Kasım 2026 · Öğretmen hızlı mesajı

Eski öğretmen panelindeki Hızlı mesaj düğmesi, yetkili öğrenci ve veli dizinini açıyor. Görüşme seçildiğinde paylaşılan mesaj formu gerçek API'ye yazar. Yanıt kaybında taslak pencerede kalır ve aynı işlem kimliğiyle kayıt kontrol edilir. Öğrenci ve mesaj okuma yetkileri giriş için, mesaj gönderme yetkisi yazmak için kullanılır.

Öğretmen 1, 2 ve 3 rol kodlarını kullanan hesaplarda sohbet kapsamı, mevcut izinlerle birlikte öğrenci atamasına göre belirlenir. Öğretmen ve yönetim sohbet dizinleri bu kuralı uygular.

İki hedefli Vitest ve beş geçici SQLite API testi geçti. Testler yetkisiz hızlı sohbet girişini, kayıp yazma yanıtından sonra tek kayıt doğrulamasını ve aynı şubedeki atanmamış öğrenciye gönderimin reddini kapsadı. TypeScript, test ESLint kontrolü ve hedefli Ruff geçti. Fiziksel cihaz ve PostgreSQL kabulü açık.

Sırada aynı paneldeki sabit bildirim sayısını yetkili okunmamış bildirim API'sine bağlamak var.
