# 19 Kasım 2026 · Web karne erişimi

Karne menüsü ve ana sayfa `daily_reports.read`, `academic.read`, `daily_reports.write` veya `academic.write` yetkilerinden biri olan kullanıcılara açılıyor. Yalnız yazma yetkisi olan kullanıcı kapsamındaki öğrenciyi seçip tarihli karne oluşturabiliyor. Karne listesi ve ayrıntısı okuma yetkisi gerektiriyor. Karne analizi mevcut `daily_reports.read` koşuluyla çağrılıyor.

On iki hedefli web testi, TypeScript ve hedefli ESLint geçti. Testler menü ve rota izinlerini, yazma rolü için liste ve analiz çağrılarının yapılmadığını, okuma rolü için kayıt düğmesinin görünmediğini ve tarihli karne isteğini doğruladı.
