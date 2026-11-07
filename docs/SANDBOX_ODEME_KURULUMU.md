# iyzico ödeme kurulumu ve sandbox kabulü

SCS360 üyelik gelirleri ile okulların öğrenci tahsilatları ayrı merchant hesaplarıdır. Sandbox hesabı veya API anahtarı yoksa ödeme aktif gösterilmez. Hazır/başkasına ait anahtar, uydurma tahsilat veya test verisi mevcut okulun finans kayıtlarına eklenmez.

## Önce ayar durumunu görün

Backend klasöründe:

```powershell
./.venv/Scripts/python.exe scripts/payment_preflight.py
```

Bu komut veritabanına veya sağlayıcıya bağlanmaz. Yalnız eksik/geçersiz **ayar adlarını**, ortamı ve kapalı/açık durumunu raporlar; anahtarları göstermez. İsteğe bağlı `--target saas` veya `--target school` tek alanı kontrol eder. Çıkış kodu 0, seçilen yapılandırma açık ve yerel doğrulamaları geçmişse döner; sağlayıcı ödemesinin kabul edildiği anlamına gelmez. `/api/ready` yalnız veritabanı/şema hazırlığını ölçer.

Platform yönetimindeki **Online ödeme kurulumu** alanı aynı güvenli durumu gösterir. Kurulum eksikse alan adları listelenir. `iyzico Sandbox · test ortamı`, gerçek ayarlar tamamlanıp açık bayrağı verilmişse görünür. Sağlayıcı kabulü yine ayrıca yapılır.

## Hesaplar ve adresler

iyzico sandbox hesabınızdan alınan API ve secret key değerlerini yalnız `backend/.env` içindeki doğru alana yazın. Sohbete, komut satırı argümanlarına, ekran görüntüsüne veya sürüm kontrolüne koymayın.

| Amaç | Anahtarlar | Diğer zorunlu ayarlar |
| --- | --- | --- |
| SCS360 üyelik ödemesi | `SAAS_IYZICO_API_KEY`, `SAAS_IYZICO_SECRET_KEY` | `SAAS_IYZICO_CALLBACK_URL`, `SAAS_PORTAL_URL`, `SAAS_CHECKOUT_ENCRYPTION_KEY` |
| Tek kuruma bağlı mevcut öğrenci ödeme hesabı | `IYZICO_API_KEY`, `IYZICO_SECRET_KEY` | `IYZICO_CALLBACK_URL`, açıkça seçilen `IYZICO_ORGANIZATION_ID` |

Üyelik callback yolu `/api/subscription/iyzico/callback`, öğrenci ödeme callback yolu `/api/payments/iyzico/callback` olmalıdır. Portal adresi frontend'in kök adresidir. Sandbox API adresi `https://sandbox-api.iyzipay.com` olur.

Resmî iyzico CF-Initialize belgesi callback için geçerli SSL sertifikası ister; CF-Retrieve ödeme tamamlandığında callback'e token gönderildiğini açıklar. Sağlayıcı kabulünde erişilebilir HTTPS callback kullanın. Kodun development/test ortamında loopback HTTP kabul etmesi, iyzico'nun bu adresle kabul testinin geçtiği anlamına gelmez. [CF-Initialize](https://docs.iyzico.com/en/payment-methods/checkoutform/cf-implementation/cf-initialize), [CF-Retrieve](https://docs.iyzico.com/en/payment-methods/checkoutform/cf-implementation/cf-retrieve).

## Koruyarak hazırlama

`configure_payment_sandbox.py` önce **yazmadan** hazırlık planı gösterir. Anahtar argümanı kabul etmez. Mevcut sırları ve ilgisiz satırları korur; mevcut callback/merchant/kurum ayarını başka bir değere sessizce değiştirmez. SaaS Fernet anahtarını yalnız eksikse üretir; mevcut anahtarı döndürmez veya değiştirmez.

```powershell
./.venv/Scripts/python.exe scripts/configure_payment_sandbox.py --target saas
```

Callback ve portal henüz tanımlı değilse gerçek HTTPS adreslerini `--callback-url` ve `--portal-url` seçenekleriyle açıkça verin. Öğrenci hesabı için `--target school --organization-id` sonrasında seçtiğiniz mevcut kurumun gerçek UUID'sini girin; komut okul seçmez veya kurum oluşturmaz. Böylece bir SaaS merchant'ı bütün okullara otomatik uygulanmaz.

`--write` eklenmedikçe dosya değişmez. Yazma öncesinde aynı klasörde, Git tarafından yok sayılan `.env.sandbox-backup-*` yedeği oluşur. Dosya bu sırada değişmişse yazma reddedilir. Anahtarlar olmadan temel adresler hazırlanabilir; açık bayrağı false kalır ve durum `needs_configuration` olur.

Tam ayarlar mevcutsa ve **yalnız development/test ortamında**, ayrıca `--activate --write` açıkça verilerek ilgili bayrak açılabilir. Eksik/geçersiz ayar varsa etkinleştirme reddedilir; production/staging sandbox'a çevrilmez. Bu komut sağlayıcı isteği, ödeme veya DB değişikliği yapmaz. Değişiklik sonrasında backend kontrollü yeniden başlatılmalı ve preflight tekrar okunmalıdır.

## Kurum başına ayrı canlı merchant

Yeni kurum merchant kayıtları için `SCHOOL_PAYMENT_ENCRYPTION_KEY` ayrı ve kalıcı bir Fernet anahtarıdır; `SCHOOL_PAYMENT_CALLBACK_URL` sunucunun öğrenci ödeme callback adresidir. Merchant anahtarlarını mobil uygulamaya veya frontend'e koymayın. Kurum panelindeki şifreli merchant akışı ve ilgili migration kabulü, yukarıdaki tek kuruma bağlı eski `IYZICO_*` ayarlarından ayrıdır. Yeni kurumlara eski veya SaaS anahtarı kopyalanmaz. Canlı hesap/sağlayıcı kabulü olmadan gerçek ödeme açık sayılmaz.

## Sağlayıcı kabulünün tamamlanması

Anahtarları girmenin ardından yalnız geçici kabul veritabanındaki okul/üyelik ve ödeme talepleriyle hosted checkout deneyin. Kart bilgileri sağlayıcının sayfasında girilir. İmza, tutar, para birimi, conversation/basket eşleşmesi ve fraud onayı doğrulanmalıdır. Aynı sonuç tekrarında tek tahsilat/makbuz veya tek üyelik dönemi oluşmalı; inceleme/ret sonucunda erişim/borç yanlışlıkla açılmamalıdır. Sağlayıcı sonucu kesinleşmeden ikinci ödeme göndermeyin.

Üretim sandbox sonucu ile okul borcunu kapatmamalı veya ücretli üyelik açmamalıdır. Bu geliştirme sırasında gerçek sağlayıcı ödemesi veya üretim dağıtımı yapılmadı. Şu an kullanıcıya ait sandbox hesabı/anahtarlar bulunmadığından dış sağlayıcı kabulü tamamlanmış değildir.
