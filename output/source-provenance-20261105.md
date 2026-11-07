# Eksik üst anahtarların kaynak incelemesi — 5 Kasım 2026

Bu rapor yalnız kaynak, seed dosyası, yerel metin çıktıları ve okunabilir Git HEAD incelemesidir. Main veritabanına bağlanılmadı; hesap, kayıt veya ilişki değiştirilmedi. Test, seed, normalleştirme ve ödeme sağlayıcısı çalıştırılmadı.

Girdi: `output/main-missing-parent-recovery-candidates-20261105.json`, 21 ayrı `(tablo, anahtar)` ve 96 referans. UUID anahtarlar hem 36 karakter tireli hem 32 karakter hex biçimde, büyük/küçük harften bağımsız arandı. Tam eşleşmeler yalnız dört proje seed dosyasında bulundu. Ayrıntılı satır/alan/ID kanıtı ve dosya SHA256 değerleri `output/source-provenance-20261105.json` içindedir; kişisel alanlar ve parola değerleri dışarı aktarılmadı.

**Kesin bulgu:** 20 UUID anahtar girişinin tamamı kaynakta mevcut; bunlar 19 farklı UUID değeridir, çünkü `550e8400-…` hem kurum hem kullanıcı hedefi olarak kullanılmış. 19 üst anahtarın doğru tabloda açık SQL seed tanımı var. Kalan iki hedef için tanım bulunmadı: `organizations.id='1'` ve `users.id='550e8400-…'`.

| Eksik hedef | SQL üst kayıt tanımı | İlgili kaynak referansı |
|---|---|---|
| organizations / `1` | Bulunamadı | `backend/add_sample_chat_logs.py:27`, seçilen superadmin kullanıcısının boş kurum alanını doğrudan `1` yapar; `:103` örnek log kurumunu aynı değerden üretir. |
| users / `e0000000-0000-4000-8000-000000000004` | `backend/sql/002_seed.sql:135` | Aynı dosya `:146` user_roles satırı. |
| users / `e0000000-0000-4000-8000-000000000005` | `backend/sql/002_seed.sql:136` | Aynı dosya `:147` user_roles satırı. |
| users / `550e8400-e29b-41d4-a716-446655440000` | Kullanıcı tanımı bulunamadı; aynı ID kurum olarak tanımlı | `backend/scripts/seed_comprehensive_data.py:494–495`, ardından diğer dokuz borç sözlüğü; kurum ID'si created_by/updated_by alanlarına verilmiş. |
| organizations / `550e8400-e29b-41d4-a716-446655440000` | `database/seed.sql:11` | `seed_comprehensive_data.py:485`, borç/bildirim/duyuru sözlükleri. |
| branches / `660e8400-e29b-41d4-a716-446655440001` | `database/seed.sql:29` | `seed_comprehensive_data.py:486`, borç ve duyuru sözlükleri. |
| users / `990e8400-e29b-41d4-a716-446655440001` | `database/seed.sql:266` | `seed_comprehensive_data.py:801,829`, duyuru created_by. |
| users / `990e8400-e29b-41d4-a716-446655440003` | `database/seed.sql:282` | `seed_comprehensive_data.py:843`, duyuru created_by. |
| users / `990e8400-e29b-41d4-a716-446655440004` | `database/seed.sql:283` | `seed_comprehensive_data.py:815,857`, duyuru created_by. |
| classes / `aa0e8400-e29b-41d4-a716-446655440001` | `database/seed.sql:325` | `seed_comprehensive_data.py:807`, duyuru class_id. |
| classes / `aa0e8400-e29b-41d4-a716-446655440002` | `database/seed.sql:326` | `seed_comprehensive_data.py:849`, duyuru class_id. |
| students / `cc0e8400-e29b-41d4-a716-446655440006` | `database/seed.sql:354` | `seed_comprehensive_data.py:487`, ilk ek borç. |
| students / `cc0e8400-e29b-41d4-a716-446655440007` | `database/seed.sql:355` | `seed_comprehensive_data.py:501`. |
| students / `cc0e8400-e29b-41d4-a716-446655440008` | `database/seed.sql:356` | `seed_comprehensive_data.py:515`. |
| students / `cc0e8400-e29b-41d4-a716-446655440009` | `database/seed.sql:357` | `seed_comprehensive_data.py:529`. |
| students / `cc0e8400-e29b-41d4-a716-446655440010` | `database/seed.sql:358` | `seed_comprehensive_data.py:543`. |
| students / `cc0e8400-e29b-41d4-a716-446655440011` | `database/seed.sql:359` | `seed_comprehensive_data.py:557`. |
| students / `cc0e8400-e29b-41d4-a716-446655440012` | `database/seed.sql:360` | `seed_comprehensive_data.py:571`. |
| students / `cc0e8400-e29b-41d4-a716-446655440013` | `database/seed.sql:361` | `seed_comprehensive_data.py:585`. |
| students / `cc0e8400-e29b-41d4-a716-446655440014` | `database/seed.sql:362` | `seed_comprehensive_data.py:599`. |
| students / `cc0e8400-e29b-41d4-a716-446655440015` | `database/seed.sql:363` | `seed_comprehensive_data.py:613`, onuncu ek borç. |

`database/seed.sql:1–3` ve `database/comprehensive_seed.sql:1–4` açık demo/test seed uyarısı taşır. Bu, dosyaların amaçlanan niteliği için doğrudan kanıttır; kişi/kurum adlarına bakılarak çıkarım yapılmadı. Ancak Main'deki her satırın hangi komutla oluşturulduğunu veya sonradan gerçek iş verisiyle ilişkilendirilip ilişkilendirilmediğini kanıtlamaz. SQL'den hesapları yeniden oluşturmak ya da eşleşen çocukları silmek bu raporun sonucu değildir.

JSON'daki `seed_child_identifier_templates`, Main klonundaki karşılaştırma için yalnız şu ID/alan şablonlarını içerir:

- `seed_additional_debts`, `:483–622`: 10 borç, `jj…007–016`; öğrenci `cc…006–015`, kurum/şube ve audit aktörleri.
- `seed_notification_jobs`, `:645–764`: 10 bildirim işi, `mm…001–010`; aynı kurum hedefi.
- `seed_announcements`, `:789–858`: 5 duyuru, `nn…001–005`; kurum/şube/sınıf/aktör hedefleri.
- Bu `jj/mm/nn` kimlikleri kaynakta hex olmayan eski metin kimlikleridir; UUID gibi yeniden üretilmemeli. Main'deki eşitlikleri bu kaynak incelemesinde test edilmedi.

Manifestte literal `1` dışındaki 78 referansın hedef anahtarları seed kaynaklarında mevcut. Literal `1` için 18 referans var. Örnek chat helper'ının kullanıcı kurum ataması ve beş log üretmesi bu alt grup için somut mekanizma sunar; **10 parent, bir branch ve bir class satırının kökenini açıklayan kesin kanıt bulunmadı**. `seed_parent_ai_data.py:44,51,57` mevcut ilişkilendirilmiş öğrencileri okur, grade/attendance/report ekler; parent veya eksik kurum/sınıf/şube oluşturmaz ve bu 21 hedefin UUID literallerini içermez.

Git HEAD `d36d3c09` tek erişilebilir initial commit'tir. `database/seed.sql` içindeki eşleşmeler bu commit'te de mevcut. Yeni comprehensive Python/SQL ve backend SQL dosyaları için aynı HEAD'de eşleşme yok. `--all` geçmiş taraması bozuk eski `refs/codex/turn-diffs/...` nesne başvurusu nedeniyle tamamlanamıyor; Git onarımı yapılmadı. HEAD'deki zod bağımlılığı aynı yaygın örnek UUID'yi içeriyor; proje verisi kökeni olarak sayılmadı.

`output`, `tmp`, `.codex-build` altındaki SQL/dump/CSV/JSON/log metinlerinde, bu incelemenin tanı raporları ve PostgreSQL veri dizinleri hariç, UUID anahtarları için ek eşleşme bulunmadı. Önceki 18 DB/yedek incelemesinin 0 aday sonucu girdi raporundan alınmıştır; bu görevde yedek DB taraması tekrarlanmadı.

Sonraki güvenli adım, yalnız klonda manifest rowid→gerçek PK→bu kaynak şablonlarının alan eşitliğini ve tüm gelen/giden ilişkileri doğrulamaktır. Sonradan değişmiş iş satırları ayrı tutulmalı. Kayıp gerçek kimlik eşlemesi belirsizken otomatik geri yükleme, farklı kullanıcıya taşıma, silme veya ForeignKey kontrolünü kapatma yapılmamalı. Bu rapor Main onarımına yetki veya veri kaybının kabulü değildir.
