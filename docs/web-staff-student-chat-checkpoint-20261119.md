# 19 Kasım 2026 · Web öğretmen ve yönetim öğrenci sohbeti

Öğretmen portalı ve yönetim paneli Android ile aynı sayfalı öğrenci-veli dizinini kullanıyor. Şube seçenekleri, ilgili hesap için görünür ve bağlı öğrenci-veli kayıtlarından geliyor. Arama öğrenciye, veliye veya sınıfa göre yapılabiliyor. Şube veya kurum değişince önceki kapsamın görüşmesi ve istekleri kapanıyor.

Gönderim, kayıt doğrulaması ve dosya indirme seçilen öğrenci, veli ve şubeye bağlı. Salt okur hesapta mesaj ve dosya gönderim denetimleri gizleniyor.

Dokuz hedefli Vitest testi, üç geçici SQLite API testi ve bir Edge uçtan uca testi geçti. Edge testi, yalıtılmış FastAPI üzerinde yetkili öğretmenin şubeye göre aramasını, dosya gönderimini ve indirilen baytların eşleşmesini doğruladı. Görüşme 360 × 780 ve 640 × 360 sentetik ekranlarda kontrol edildi. Yatay kontrolde tarayıcı kök yazı boyutu yüzde 200'e çıkarıldı. TypeScript, hedefli ESLint ve Ruff geçti.

Fiziksel cihaz ve iOS kabulü açık. Sırada web sohbetinde yüklenen ve indirilen dosya baytlarını Android ile aynı SHA-256 doğrulamasından geçirmek var.
