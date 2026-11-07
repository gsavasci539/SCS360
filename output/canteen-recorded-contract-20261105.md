# Kantin kayıt özeti — uygulama öncesi kabul taslağı

Bu dosya çalıştırılmayan taslaktır. Backend uygulama kaynakları ve mevcut testler değiştirilmedi. Ortak hizmet ile iki kayıtlı `/ai/canteen-analysis` işleyicisinin ve chatbot `CanteenHandler` entegrasyonu, devam eden tam backend testi bitene kadar bekleyecek.

## Kaynak ve anlam

- `CanteenWalletTransaction`: `COMPLETED` durumundaki `DEBIT` ve `SALE` hareketleri kayıtlı satış tutarıdır. `CREDIT` yalnız bakiye yüklemesidir; satışa eklenmez.
- `CanteenOrder`: katalog ürün satırlarının ayrı tarihsel dökümüdür. İki tablo arasında kalıcı hareket/sipariş bağlantısı yoktur. Toplamlar birleştirilmez, tarih/tutar benzerliğiyle tekilleştirme yapılmaz. Sadece siparişi bulunan eski kayıtlar korunur ve ayrı gösterilir.
- Hareket/sipariş adedi fiş veya benzersiz sepet adedi değildir: personel POS sepeti her ürün için ayrı `purchase()` çağırır. DTO ve metinler kayıt/satır adedi demeli; fiş sayısı iddia etmemeli.
- Kantin modellerinde maliyet veya satış anı maliyet kaydı, stok miktarı ve para birimi alanı yok. Kâr, marj, stok sağlığı, güven puanı ve trend uydurulmaz. DTO para birimi eklerse bunun kayıtlı alan olmadığı açıkça belgelenmeli; mevcut TL gösterimi yeni bir döviz desteği iddiası doğurmamalı.
- Bakiye hareketinin tarihsel şube alanı yoktur; mevcut öğrenci/şube bağından kapsam belirlenir. Geçmiş şube değişimini tahmin etmek kapsam dışıdır.

## Asgari ortak DTO

`analysis_type: recorded_canteen`, `period_start`, `period_end_exclusive`, `timezone`, `as_of`, `data_source: canteen_wallet_transactions`, `sale_record_count`, `sales_amount`, `wallet_debit_amount`, `direct_sale_amount`, `topup_record_count`, `topup_amount`, `daily_average`, `invalid_sale_amount_count`, `invalid_topup_amount_count`, `requires_review`, `history_status`.

`catalog_orders` ayrı nesnesi: `data_source: canteen_orders`, `record_count`, `quantity`, `amount`, `invalid_amount_count`, `invalid_quantity_count`, `included_in_sales_total: false`. Bu nesneye katalog ürün dökümü eklenirse ürünler tek toplu sorguda okunur; N+1 sorgu ve eski notlardan ürün/adet çıkarımı yapılmaz.

Uyumluluk gerekirse `total_sales = sales_amount`, `order_count = catalog_orders.record_count`, `inventory_status: unknown`, `trend: recorded|insufficient_data`, `recommendations: []`. `order_count` hareket veya fiş adedine sessizce dönüştürülmez. Eski sahte sıfır alanları gerçek veri yokken doldurulmaz. Kâr alanları kaldırılır veya `null` olur.

Tutarlar sonlu, negatif olmayan `Decimal` olarak okunur ve kanonik iki basamaklı dize döner. Gerçek sıfır korunur; veri olmayan alanda tutar/ortalama `null`, kayıt adedi `0`, `history_status: no_history` olur. Geçersiz satış tutarı yalnız ilgili satış toplamlarını ve ortalamayı bilinmiyor yapar; geçerli yüklemeyi veya ayrı katalog toplamını bozmaz. Bozuk yükleme de satış toplamını sıfırlamaz. Geçersiz satırlar silinmez veya düzeltilmiş gibi gösterilmez.

## Kapsam, tarih ve hata davranışı

- Hizmet `TenantContext` alır. Gerçek kurum, silinmemiş öğrenci/şube, seçili personel şubeleri ve mevcut ilişki kapsamı açık filtrelerdir. ORM alan projeksiyonları mevcut tenant guard ile uyumlu kalır. Yalnız yardımcı tablonun `branch_id` alanına güvenilmez.
- Chatbot mevcut `canteen.read` veya veli modundaki `parent.view_finances` politikasını korur. Analiz uç noktası mevcut `AnalysisPermission('/canteen-analysis')` şartını korur; salt `finance.read` ile genişletilmez.
- Veli modunda `parent_student_ids` ve varsa doğrulanmış `intent.student_id` birlikte uygulanır; diğer çocuğu seçmek kurum toplamı döndürmez. Öğrenci seçimi yetkisizse boş toplam sunmak yerine mevcut erişim reddi kullanılır.
- İstemci yetkisine uymayan POS/kasa/yükleme/ürün yönetimi eylemleri önerilmez; salt okuyana işlem yetkisi verilmez. Veli kendi portalına yönlenir.
- Yerel okul günü `[başlangıç, bitiş)` esas alınır. Hareket `created_at` zamanları okul günü UTC sınırlarıyla, siparişlerin `order_date` tarihleri eşdeğer yerel tarihlerle filtrelenir. Varsayılan 30 gün bugün dahil tam 30 gündür; yarınki/future kayıtlar bugünkü özete katılmaz.
- Özet `wallet()` çağırmaz: fonksiyon cüzdan yoksa oluşturur. GET/chatbot özeti hiçbir cüzdan, satış veya yükleme kaydı yazmaz.
- SQL hatası analizde genel mesajlı `503` olur; `200 + sıfır` ve ham hata metni olmaz. Chatbot desteklenen genel hata metnini döndürür, sahte satış/kâr üretmez. Beklenen erişim reddi SQL hatasına çevrilmez.
- Yalnız gerekli para/tarih/tür/durum/scope alanları projekte edilir; kullanılmayan bozuk eski UUID/enum alanları tüm özeti çökertmez.

## Sonraki hedef entegrasyon senaryoları

1. **Çift sayım ve eksik kanal:** Tamamlanmış DEBIT `15.00`, SALE `20.00`, CREDIT `100.00`; eşlenmemiş katalog satırları `15.00` ve eski `7.00`. Sonuç satış `35.00`, satış kayıt adedi `2`, yükleme `100.00`, katalog `22.00`/`2`. Sonuç `57.00`, `135.00` veya `157.00` olamaz. Kâr/marj yok. Kaynaklar açıklanır.
2. **Durum ve kapsam:** PENDING/CANCELLED satışları; başka kurumun, başka personel şubesinin ve silinmiş öğrencinin hareket/siparişleri dışarıda. Ana kurumdaki geçerli sıfır kaydı korunur.
3. **Seçili veli çocuğu:** İki çocuk için farklı hareketler oluşturulur; seçili çocuk yalnız kendi toplamını verir. Bağsız çocuk reddedilir. Mevcut izne sahip olmayan veli analize erişemez; chatbot guardian politikası genişletilmez.
4. **Takvim sınırları:** Sabit okul tarihiyle ay/yıl geçişinde tam N yerel gün; gece UTC/İstanbul farkı; başlangıç anı dahil ve bitiş anı hariç. Gelecekteki hareket/sipariş hariç. Sipariş tarihi ve hareket zamanı aynı dönem kapsamını izler.
5. **Boş ve salt okunur:** Boş hareketler bilinmeyen tutar/ortalama ve gerçek `0` adet döndürür; öncesi/sonrası StudentWallet ve iki kantin tablosunun satır sayısı aynı kalır.
6. **Bozuk eski tutar:** NaN/Infinity/negatif satış toplamı `null`, inceleme sayacı pozitif; geçerli katalog ve yükleme kendi doğru tutarını korur. Bozuk veritabanı satırı aynen saklı kalır. Geçersiz yükleme satış toplamını etkilemez.
7. **Eski kayıt uyumluluğu:** Gereksiz işleyen/ürün/hareket UUID alanları bozuk olsa da gereken geçerli tutar ve kapsam alanları okunur; kullanılmayan UUID nesneleştirilmez. Katalog ürünü bulunamıyorsa toplam kaybolmaz, ürün adı uydurulmaz.
8. **Hata ve kayıtlı işleyiciler:** Paylaşılan hizmet sorgusuna SQL hatası enjekte edildiğinde HTTP `503` ve genel mesaj; gizli sorgu/sağlayıcı/hata metni yok. Her iki mevcut FastAPI kayıt nesnesi aynı gerçek hizmeti çağırır; yalnız modüldeki son Python adına test yazılıp ilk kayıt atlanmaz.
9. **Chatbot doğruluğu:** Gerçek dönem açıklaması, kayıt adedi ve ayrı katalog kapsamı gösterilir; varsayılan `%36`, net kâr, tarih aralığı ne olursa olsun `Bugünkü` veya satır adedine `fiş` denmez. Seçili çocuk filtresi gerçek hizmete aktarılır. SQL hatası sahte rapora dönüşmez.

Taslak testler henüz çalıştırılmadı; onay ve backend kaynak dondurmasının bitişinden sonra tek hedef dosyada somutlaştırılacak.
