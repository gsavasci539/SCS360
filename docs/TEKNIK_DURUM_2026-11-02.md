# Teknik durum — 2 Kasım 2026

> Bu belge önceki doğrulama turunun tarihsel kaydıdır. Güncel sonuçlar ve açık kabul maddeleri [satış öncesi kabul raporundadır](SATIS_ONCESI_KABUL_2026-11-02.md).

## Doğrulanan sonuçlar

- Backend: `python -m pytest -q --disable-warnings` — 29 test geçti.
- Frontend: `npm test -- --run` — 4 dosyada 21 test geçti.
- Frontend: `npm run build` — TypeScript kontrolü ve Vite derlemesi başarılı.
- `ruff check app --select F821,F823` — tanımsız/değer atanmamış değişken hatası yok.
- `pip check` — kurulu Python bağımlılıklarında çatışma yok.
- `alembic heads` — tek başlık: 020. Bu kontrol migration'ların boş PostgreSQL üzerinde uygulanabildiğini doğrulamaz.

## Bu incelemede giderilen hatalar

- Ortak yanıt fonksiyonuna `success=False` gönderen çok sayıdaki endpoint'in TypeError üretmesi giderildi. Mevcut JSON sözleşmesi korundu.
- Sınıf, dashboard, sınav, materyal, ders programı, güvenlik, öğrenci ve operasyon endpoint'lerinde eksik importlar tamamlandı.
- Borç listesinde sorgu sonucunun yanlış değişkenden okunması düzeltildi.
- Ödev oluşturmada geçersiz `UUID.uuid4()` çağrısı düzeltildi.
- Chatbot takip mesajı yalnızca kısa, bağlama bağlı komutlarda önceki konuyu kullanıyor. Yeni konu içeren “Borçları göster” mesajının notlar konusunu devralması önlendi; borç eşleştirmesi genişletildi.
- Güven puanının sabit değerine bağlı kırılgan testler, geçerli aralık ve niyet davranışını denetleyecek şekilde güncellendi. Konu değişimi ve hata yanıtı için regresyon testleri eklendi.
- Ollama varsayılan OpenAI uyumlu adresine `/v1` eklendi.
- Eksik backend ve frontend Dockerfile dosyaları oluşturuldu. Sağlık kontrolü curl yerine Python standart kitaplığını kullanıyor.
- Docker Compose backend/worker bağlantısı konteyner içi PostgreSQL adresine bağlandı; kök ortamda DATABASE_URL ile değiştirilebilir.
- Nginx `/ready` yönlendirmesi gerçek `/api/ready` endpoint'ine düzeltildi.

## Üretim öncesi tamamlanması gereken işler

1. `backend/app/routers/parent_portal.py`: not, ders programı, ödev, materyal, iletişim, duyuru, etkinlik ve haftalık rapor bölümlerinde örnek veri blokları var. Veritabanına bağlı sorgulara ve öğrenci/kurum erişim testlerine dönüştürülmeli.
2. `backend/app/routers/homework.py` ve `outbox.py`: bellek içi kayıtlar yeniden başlatmada kaybolur. Kalıcı veri modeli, migration ve kurum/şube kapsamı gerekir. Ayrı ödev endpoint'leri farklı veri kaynakları kullanıyor.
3. Birden fazla router aynı HTTP yöntemini ve yolu kaydediyor. Özellikle `ai_analytics.py` ve ödeme/borç/öğrenci kayıtları incelenmeli. Çalışan ilk endpoint davranışı doğrulanmadan kopyaları silmek veri akışını değiştirebilir.
4. Ödeme iadesi/iptali, bildirim sağlayıcıları ve bazı PDF üretimleri için TODO alanları var. Gerçek sağlayıcı kimlik bilgileriyle sandbox kabul testleri yapılmalı; gerçek finansal işlem yapılmadı.
5. Docker çalıştırılabilir komutu bu ortamda bulunmadığından imajlar oluşturulup compose ayağa kaldırılarak doğrulanamadı. Yeni Dockerfile dosyaları uçtan uca Docker doğrulaması bekliyor. PostgreSQL şema başlangıcı ve migration zinciri temiz bir test veritabanında denenmeli.
6. Frontend ana JavaScript parçası için boyut uyarısı var; sayfa bazlı lazy loading uygulanabilir.
7. Testler tüm iş akışlarını kapsamıyor. Gerçek tarayıcıda rol bazlı öğrenci/veli/öğretmen, tahsilat, rapor ve chatbot gezinme kabul testleri henüz bu incelemede yapılmadı.
8. Çalışma ağacında inceleme öncesinden çok sayıda kaynak ve veritabanı değişikliği bulunuyor. Bunlar korunmuştur; sürüm kontrolüne alınmadan önce kullanıcı değişiklikleriyle birlikte gözden geçirilmelidir.

Bu rapor üretime hazır olunduğuna dair onay değildir. Testlerin geçmesi, örnek veri kullanan modüllerin tamamlandığı anlamına gelmez.
