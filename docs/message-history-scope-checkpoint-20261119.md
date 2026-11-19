# 19 Kasım 2026 mesaj geçmişi kapsamı

Sohbet özeti, geçmiş, okundu, silme ve gönderim doğrulama aynı kurum, şube ve katılımcı denetimini kullanıyor. Şube seçimi, özet ile geçmişte aynı kayıtları gösterir. Platform yöneticisinin gönderimi ve geçmişi seçtiği kuruma bağlıdır.

038 şema değişikliği yeni mesajlara kurum ve varsa şube damgası ekler. Eski kayıtların sütunları boş kalır. Eski mesajlarda mevcut öğrenci görüşmesi, sınıf veya alıcının şube bağı kapsamı belirler. Bağlamı doğrulanamayan kayıtlar şube seçili görünümde gösterilmez.

Geçici SQLite'ta 9 test geçti. Bunlar mevcut veli-öğretmen akışını, platform kurum seçimini, şubeler arası görünürlüğü, sayfalama ve okundu denetimini, eşzamanlı gönderim tekrarını ve eski kaydı koruyan tekrarlanabilir 038 şema değişikliğini kapsıyor. PostgreSQL çalıştırılmadı. 038 herhangi bir çalışma veritabanına uygulanmadı.

Sırada mevcut Kotlin genel sohbet ekranını bu liste, geçmiş, alıcı ve gönderim doğrulama uçlarına bağlamak var.
