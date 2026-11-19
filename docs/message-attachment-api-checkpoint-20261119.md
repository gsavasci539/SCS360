# 19 Kasım 2026 özel sohbet eki API'si

`POST /api/messages/send-file`, PDF, PNG ve JPEG dosyalarını mevcut yükleme boyutu sınırı ve imza doğrulamasıyla alır. Metin isteğe bağlıdır. Dosya özel depoda atomik yazılır. Gönderim kimliği, aynı metin ve dosya için tek kayıt döndürür. Farklı içerikle yeniden kullanım 409 döner. Başarısız depolamada mesaj kaydı geri alınır.

Oturumlu `GET /api/messages/{id}/attachment` yalnızca kapsam içindeki mesaj katılımcılarına dosya verir. Dosya bir indirme yanıtıyla gönderilir. Yanıt adı ve SHA256 değeri gönderim sonucunda ve geçmişte bulunur. Önceki dış bağlantılar veritabanında korunur. İstemciye yalnızca özel depoda doğrulanan ek adresi sunulur.

Geçici SQLite'ta 9 test geçti. Eşzamanlı tekrar, dosya sınırları, depolama hatası, kapsam dışı okuma, metin gönderimi, alıcı kapsamı ve geçici 039 şema değişikliği kapsandı. PostgreSQL çalıştırılmadı. 039 çalışma veritabanlarına uygulanmadı.

Sırada Kotlin dosya seçici, özet doğrulamalı oturumlu indirme ve aynı gönderim kimliğiyle sonuç kurtarma var. Ardından web arayüzündeki ilgili akışlar eşitlenecek.
