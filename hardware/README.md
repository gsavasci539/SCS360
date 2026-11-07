# RFID Hardware Integration

Bu proje, SCS360 sistemi için RFID kart okuyucu ve turnike donanımlarının entegrasyonunu içerir.

## Donanım Bileşenleri

### Gerekli Donanım
- **Wemos D1 Mini** (ESP8266 tabanlı)
- **MFRC522 RFID Okuyucu Modülü**
- **Jumper Kablolar**
- **Breadboard (opsiyonel)**
- **5V Güç Kaynağı**
- **LED'ler (Yeşil, Kırmızı)**
- **Buzzer**
- **Röle (Turnike ve Kapı Kilidi için)**
- **LCD Ekran (Opsiyonel - Kantin ve Yoklama Kiosku için)**

## Cihaz Türleri

Projede 5 farklı cihaz türü bulunmaktadır:

### 1. Turnike Cihazı (`turnstile-device/`)
- **Özellikler**: Kart okuma, erişim kontrolü, turnike röle kontrolü
- **Kullanım**: Okul girişlerinde, turnike geçişlerinde
- **Pin Konfigürasyonu**:
  - SS_PIN: D2
  - RST_PIN: D1
  - BUZZER_PIN: D3
  - TURNSTILE_RELAY_PIN: D4
  - LED_GREEN_PIN: D5
  - LED_RED_PIN: D6

### 2. Kantin Terminali (`canteen-terminal/`)
- **Özellikler**: Kart okuma, bakiye sorgulama, ödeme işleme
- **Kullanım**: Kantin ödemelerinde
- **Pin Konfigürasyonu**:
  - SS_PIN: D2
  - RST_PIN: D1
  - BUZZER_PIN: D3
  - LED_GREEN_PIN: D5
  - LED_RED_PIN: D6

### 3. Kart Okuyucu (`card-reader/`)
- **Özellikler**: Kart okuma, kart bilgisi görüntüleme, basit loglama
- **Kullanım**: Genel kart okuma amaçları
- **Pin Konfigürasyonu**:
  - SS_PIN: D2
  - RST_PIN: D1
  - BUZZER_PIN: D3
  - LED_GREEN_PIN: D5
  - LED_RED_PIN: D6

### 4. Kapı Kilidi (`door-lock/`)
- **Özellikler**: Kart okuma, erişim kontrolü, kapı kilidi röle kontrolü
- **Kullanım**: Oda veya kapı erişim kontrolü
- **Pin Konfigürasyonu**:
  - SS_PIN: D2
  - RST_PIN: D1
  - BUZZER_PIN: D3
  - DOOR_LOCK_RELAY_PIN: D4
  - LED_GREEN_PIN: D5
  - LED_RED_PIN: D6

### 5. Yoklama Kiosku (`attendance-kiosk/`)
- **Özellikler**: Kart okuma, yoklama işaretleme, LCD ekran desteği
- **Kullanım**: Öğrenci ve personel yoklaması
- **Pin Konfigürasyonu**:
  - SS_PIN: D2
  - RST_PIN: D1
  - BUZZER_PIN: D3
  - LED_GREEN_PIN: D5
  - LED_RED_PIN: D6
  - LCD I2C (Opsiyonel): SDA=D4, SCL=D7

## Kurulum Adımları

### 1. Arduino IDE Kurulumu

1. Arduino IDE'yi indirin ve kurun: https://www.arduino.cc/en/software
2. Arduino IDE'de:
   - File > Preferences
   - "Additional Boards Manager URLs" kısmına ekleyin:
     ```
     http://arduino.esp8266.com/stable/package_esp8266com_index.json
     ```
3. Tools > Board > Boards Manager
4. "esp8266" arayın ve "esp8266 by ESP8266 Community" paketini kurun

### 2. Kütüphanelerin Kurulumu

Arduino IDE'de şu kütüphaneleri kurun:

1. **ESP8266WiFi** (ESP8266 ile birlikte gelir)
2. **ESP8266HTTPClient** (ESP8266 ile birlikte gelir)
3. **ArduinoJson** (versiyon 6.x)
   - Sketch > Include Library > Manage Libraries
   - "ArduinoJson" arayın ve kurun
4. **MFRC522**
   - Sketch > Include Library > Manage Libraries
   - "MFRC522" arayın ve kurun

### 3. Donanım Bağlantıları

#### MFRC522 RFID Okuyucu Bağlantıları

| MFRC522 Pin | Wemos D1 Pin |
|-------------|--------------|
| SDA (SS)    | D2           |
| SCK         | D5           |
| MOSI        | D7           |
| MISO        | D6           |
| RST         | D1           |
| 3.3V        | 3.3V         |
| GND         | GND          |

#### LED ve Buzzer Bağlantıları

| Bileşen | Wemos D1 Pin |
|---------|--------------|
| Yeşil LED | D5 |
| Kırmızı LED | D6 |
| Buzzer | D3 |

**Not**: LED'ler için 220Ω direnç kullanın.

#### Röle Bağlantıları (Turnike ve Kapı Kilidi)

| Röle | Wemos D1 Pin |
|------|--------------|
| IN   | D4           |
| VCC  | 5V           |
| GND  | GND          |

### 4. Yazılım Konfigürasyonu

Her cihazın `.ino` dosyasında şu konfigürasyonları yapın:

```cpp
// WiFi Ayarları
const char* WIFI_SSID = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

// API Ayarları
const char* API_BASE_URL = "http://YOUR_SERVER_IP:8000";
const char* API_KEY = "YOUR_API_KEY";

// Cihaz Ayarları
const char* DEVICE_ID = "DEVICE_TYPE_001";  // Her cihaz için benzersiz
const char* DEVICE_TYPE = "DEVICE_TYPE";    // TURNSTILE, CANTEEN_TERMINAL, vb.
const char* BRANCH_ID = "YOUR_BRANCH_ID";  // Şube UUID'si
```

### 5. Kodun Yüklenmesi

1. İlgili cihaz klasörüne gidin (örn: `turnstile-device/`)
2. `.ino` dosyasını Arduino IDE ile açın
3. Tools > Board > "LOLIN(WEMOS) D1 R2 & mini" seçin
4. Tools > Port > Wemos D1'nin bağlı olduğu portu seçin
5. Upload butonuna tıklayın

## API Entegrasyonu

Backend API endpoint'leri `backend/app/routers/hardware.py` dosyasında tanımlanmıştır.

### Endpoint'ler

#### Cihaz Kaydı
```
POST /api/hardware/devices/register
```

#### Cihaz Heartbeat
```
POST /api/hardware/devices/{device_id}/heartbeat
```

#### Erişim Kontrolü
```
POST /api/hardware/access/check
```

#### Erişim Loglama
```
POST /api/hardware/access/log
```

#### Kart Bakiyesi Sorgulama
```
POST /api/hardware/card/balance
```

#### Kart Ödeme İşleme
```
POST /api/hardware/payment/process
```

#### Kart Bakiye Yükleme
```
POST /api/hardware/card/topup
```

## Frontend Entegrasyonu

Kart bakiye yükleme arayüzü `frontend/src/features/operations/CardBalancePage.tsx` dosyasında bulunur.

### Kullanım

1. Sisteme giriş yapın
2. `/canteen/card-balance` sayfasına gidin
3. Kart numarasını girin veya kart okutun
4. Kart bilgileri görüntülenir
5. Bakiye yükleme işlemi yapın

## Sorun Giderme

### WiFi Bağlantı Sorunu
- WiFi SSID ve şifresini kontrol edin
- Wemos D1'nin güç kaynağının yeterli olduğundan emin olun (en az 1A)
- Router sinyal gücünü kontrol edin

### RFID Okuyucu Çalışmıyor
- Bağlantıları kontrol edin
- 3.3V güç kaynağının yeterli olduğundan emin olun
- MFRC522 kütüphanesinin doğru kurulduğunu kontrol edin

### API Bağlantı Sorunu
- API_BASE_URL'nin doğru olduğundan emin olun
- Sunucunun çalıştığını ve erişilebilir olduğunu kontrol edin
- Güvenlik duvarı ayarlarını kontrol edin

### Röle Çalışmıyor
- Röle modülünün doğru bağlandığını kontrol edin
- Röle için yeterli güç kaynağı kullanın (5V)
- Röle pin konfigürasyonunu kontrol edin

## Güvenlik Notları

1. **API Key**: Her cihaz için benzersiz API anahtarı kullanın
2. **WiFi**: Güçlü WiFi şifresi kullanın
3. **HTTPS**: Mümkünse HTTPS kullanın (SSL sertifikası gerektirir)
4. **Fiziksel Güvenlik**: Cihazları güvenli yerlere monte edin
5. **Güç Kaynağı**: Güvenilir güç kaynakları kullanın

## Bakım

### Düzenli Görevler
- Cihaz heartbeat loglarını kontrol edin
- WiFi bağlantılarını izleyin
- Donanımın fiziksel durumunu kontrol edin
- Güç kaynaklarını test edin

### Güncellemeler
- Arduino kodlarını düzenli olarak güncelleyin
- Kütüphaneleri güncel tutun
- API değişikliklerini takip edin

## Destek

Sorunlar için:
- Proje dokümantasyonunu inceleyin
- GitHub issues kısmını kontrol edin
- Geliştirici ekibiyle iletişime geçin

## Lisans

Bu proje SCS360 projesinin bir parçasıdır.
