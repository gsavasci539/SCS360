# 19 Kasım 2026 · Android öğretmen ve yönetim sohbeti

Öğretmen ve yönetim ekranları sayfalı öğrenci-veli dizininden görüşme açar. Dizin, gerçek veli hesabına bağlı kayıtları kurum, şube ve öğrenci erişimine göre getirir. Öğrenci, veli ve sınıf adına göre aranabilir.

Görüşme geçmişi, metin ve dosya gönderimi, kayıt doğrulaması ve indirme aynı öğrenci, veli ve şube kimliklerini kullanır. Gönderim yetkisi olan hesaplar PDF, PNG veya JPEG ekleyebilir. Gönderim sonucu aynı UUID ile okunur. Oturumlu indirmede dosyanın SHA-256 özeti doğrulanır.

Geçici SQLite üzerinde dört API testi ve altı hedefli Android testi geçti. Android kapsamı iki yerel HTTP testi, üç sentetik Compose testi ve bir gerçek FastAPI kabul testidir. Geçici SQLite kabulünde yönetimin gönderdiği belgeyi veli kendi öğrenci görüşmesinden indirdi. Okuma yetkili öğretmenin düzenleme düğmeleri yatay ve büyük yazılı sentetik ekranda gizlendi.

Fiziksel A26, iOS ve imzalı mağaza sürümünün kabulü açık. Sırada web öğretmen ve yönetim öğrenci-veli seçicilerinin sayfalı dizini kullanması var.
