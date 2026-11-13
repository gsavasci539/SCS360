# Kurum sahibi erişim checkpoint — 13 Kasım 2026

Kurum sahibi, kendi kurumunun tüm modül sayfalarını ve şubelerini kullanabilir. API sorgularında kurum filtresi korunur; başka kuruma ait kayıtlar görünmez (404). Gerçek Root `super_admin` gerektiren SaaS/platform yönetimi ve sohbet denetimi kurum sahibine açılmaz. Kota ve yazma kuralları yürürlüktedir.

- Backend: permission unit 4/4; geçici SQLite tenant API 2/2 geçti; PostgreSQL varyantı 2 skip.
- Frontend: auth/navigation 76/76 geçti.
- Android native: owner navigation hedef testi 1/1 geçti; Gradle test başarılı.
- Bu kanıt sentetik/izole testtir; A26 fiziksel cihazı, canlı sağlayıcı veya satış/üretim kabulini temsil etmez.

Branch: `codex/source-sync-20261111`
- SCS360Mobile: `1b3a93a55e6aa7b6466c4d59c78eeb16b831e9dc`
- SCS360: `014bbafec088ddd664a1c33c0ec9d6e6bddc1148`

Sıradaki iş: mobil kalan modülleri işlem bazında web'in gerçek API/DTO/rol/kapsam davranışıyla karşılaştırıp düzeltmeye devam etmek. Gerçek cihaz ve sağlayıcı kabulini ayrı tut.
