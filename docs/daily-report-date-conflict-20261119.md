# 19 Kasım 2026 · Karne tarihi ve yinelenen kayıt

Karne oluşturma aynı öğrenci ve tarih için koşullu ekleme yapıyor. PostgreSQL’de aynı öğrencinin eşzamanlı yazımları öğrenci satırı kilitlenerek sıralanıyor. SQLite koşulu ekleme sorgusunun içinde değerlendiriyor. Bu akış eski şemada tekillik kısıtı varsaymıyor ve geçmiş kayıtlara dokunmuyor.

Geçici SQLite üzerinde dört API testi geçti. Eşzamanlı iki isteğin biri 409 döndü ve tarih filtresinde tek kayıt kaldı. Aynı öğrenciye başka bir tarihte karne açılabildi. Toplu kayıtta istek sırası korundu ve bir çakışmada işlem bütünüyle geri alındı. PostgreSQL kabulü açık.
