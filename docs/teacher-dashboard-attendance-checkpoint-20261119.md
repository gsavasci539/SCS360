# 19 Kasım 2026 · Öğretmen paneli sınıf ve yoklama özeti

Eski öğretmen paneli, aktif kurum ve yetkili şube kapsamındaki atanmış sınıfları ve öğrencileri `/api/teacher/dashboard-summary` üzerinden gösteriyor. Doğrudan öğrenci atamaları da özete giriyor. Kurum sahibi yönetim panelini kullanmaya devam ediyor.

Katılım oranı yalnızca bugünün kayıtlı yoklamalarından hesaplanıyor. Geç gelenler katılmış, yarım gün yarım katılmış sayılıyor. İzinli öğrenciler paydadan çıkarılıyor. Kayıt yoksa veya oran hesaplanamıyorsa ekranda çizgi görünüyor. Yoklama okuma yetkisi olmayan hesaplara API yoklama özeti vermiyor.

Altı Vitest testi, bir geçici SQLite API testi, TypeScript, hedefli ESLint ve Ruff geçti. API testi doğrudan atamayı, yetki reddini, atanmadığı sınıfı, kapsam dışı şube ve kurumu, pasif öğrenciyi, silinmiş ve önceki tarihli yoklamayı kapsadı. PostgreSQL ve fiziksel cihaz kabulü açık.

Sırada eski öğretmen rollerinin yoklama listesindeki ve toplu yoklama düzenleyicisindeki öğrenci ve sınıf kapsamını API üzerinden doğrulamak var.
