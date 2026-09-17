# Okul360 Proje Dokümantasyonu

Bu doküman Okul360 projesindeki tüm ekranları, yetkileri ve API endpointlerini içerir.

## 📋 İçindekiler

1. [Ekranlar ve Yollar](#ekranlar-ve-yollar)
2. [Yetkiler ve İzinler](#yetkiler-ve-izinler)
3. [API Endpoint'leri](#api-endpointleri)
4. [Rol Tanımları](#rol-tanımları)

---

## 🖥️ Ekranlar ve Yollar

### Yönetim

| Ekran Adı | Yol | İzin | Açıklama |
|-----------|-----|-------|----------|
| Genel Bakış | `/dashboard` | `dashboard.view` | Ana dashboard |
| Kurumlar | `/organizations` | `org.read` | Organizasyon yönetimi |
| Şubeler | `/branches` | `branch.read` | Şube yönetimi |
| Kullanıcılar | `/users` | `users.read` | Kullanıcı yönetimi |
| Rol ve Yetkiler | `/roles` | `users.read` | Rol ve yetki yönetimi |
| Personel & Nöbet | `/staff` | `users.read` | Personel yönetimi |
| Öğretmen Paneli | `/teacher` | - | Öğretmen paneli |

### Eğitim

| Ekran Adı | Yol | İzin | Açıklama |
|-----------|-----|-------|----------|
| Öğrenciler | `/students` | `students.read` | Öğrenci yönetimi |
| Veliler | `/parents` | `parents.read` | Veli yönetimi |
| Sınıflar & Program | `/classes` | `classes.read` | Sınıf ve program yönetimi |
| Yoklama | `/attendance` | `attendance.read` | Yoklama yönetimi |
| Ödev & Notlandırma | `/homework` | `students.read` | Ödev ve not yönetimi |
| Kütüphane & Zimmet | `/library` | `students.read` | Kütüphane yönetimi |
| Günlük Karne | `/daily-reports` | `students.read` | Günlük raporlar |

### Veli Portalı

| Ekran Adı | Yol | İzin | Açıklama |
|-----------|-----|-------|----------|
| Genel Bakış | `/parent/dashboard` | `parent.view_children` | Veli dashboard |
| Çocuğum | `/parent/children` | `parent.view_children` | Çocuk bilgileri |
| Akademik Durum | `/parent/academic` | `parent.view_children` | Akademik durum |
| Ders Programı | `/parent/schedule` | `parent.view_children` | Ders programı |
| Ödevler | `/parent/homework` | `parent.view_children` | Ödev bilgileri |
| Ders Materyalleri | `/parent/materials` | `parent.view_children` | Materyaller |
| Devamsızlık | `/parent/attendance` | `parent.view_attendance` | Devamsızlık bilgileri |
| Ödemeler | `/parent/finances` | `parent.view_finances` | Ödeme bilgileri |
| Sağlık ve İzinler | `/parent/health` | `parent.view_children` | Sağlık bilgileri |
| İletişim Geçmişi | `/parent/communication` | `parent.view_children` | İletişim geçmişi |
| Canlı Sohbet | `/parent/chat` | `parent.view_children` | Canlı sohbet |
| Okul Duyuruları | `/parent/announcements` | `parent.view_children` | Duyurular |
| Kulüp ve Aktiviteler | `/parent/activities` | `parent.view_children` | Aktiviteler |
| Haftalık Raporlar | `/parent/reports` | `parent.view_children` | Haftalık raporlar |

### İletişim

| Ekran Adı | Yol | İzin | Açıklama |
|-----------|-----|-------|----------|
| Veli Talepleri & İlaç | `/parent-notices` | `students.read` | Veli talepleri |
| Randevu & PTC | `/appointments` | `students.read` | Randevu yönetimi |
| Duyurular | `/announcements` | `announcements.read` | Duyuru yönetimi |
| Bildirimler | `/notifications` | `notification.read` | Bildirim yönetimi |
| Giden Kutusu (Outbox) | `/outbox` | `notification.read` | Giden kutusu |
| Şablonlar | `/notifications/templates` | `notification.read` | Şablon yönetimi |

### Operasyon

| Ekran Adı | Yol | İzin | Açıklama |
|-----------|-----|-------|----------|
| Servis & Ulaşım | `/transport` | `students.read` | Servis yönetimi |
| Kantin Ürünleri | `/canteen` | `canteen.write` | Kantin ürün yönetimi |
| Kantin Satış | `/canteen/sales` | `canteen.write` | Kantin satış ekranı |
| Kart Bakiye Yükleme | `/canteen/card-balance` | `canteen.read` | Kart bakiye yükleme |

### Finans

| Ekran Adı | Yol | İzin | Açıklama |
|-----------|-----|-------|----------|
| Borçlar | `/finance/debts` | `debts.read` | Borç yönetimi |
| Tahsilatlar | `/finance/payments` | `payments.read` | Tahsilat yönetimi |
| Giderler & Harcamalar | `/finance/expenses` | `finance.read` | Gider yönetimi |
| Makbuzlar | `/finance/receipts` | `receipt.read` | Makbuz yönetimi |

### Analiz

| Ekran Adı | Yol | İzin | Açıklama |
|-----------|-----|-------|----------|
| Raporlar | `/reports` | `report.read` | Rapor yönetimi |

### Sistem

| Ekran Adı | Yol | İzin | Açıklama |
|-----------|-----|-------|----------|
| RFID Kartlar | `/rfid-cards` | `settings.read` | RFID kart yönetimi |
| Cihazlar | `/devices` | `settings.read` | Cihaz yönetimi |
| Ayarlar | `/settings` | `settings.read` | Sistem ayarları |

---

## 🔐 Yetkiler ve İzinler

### Temel İzinler

| İzin Kodu | İzin Adı | Modül | Açıklama |
|-----------|----------|-------|----------|
| `users.read` | Read Users | users | Kullanıcıları görüntüleme |
| `users.write` | Write Users | users | Kullanıcıları yönetme |
| `students.read` | Read Students | students | Öğrencileri görüntüleme |
| `students.write` | Write Students | students | Öğrencileri yönetme |
| `parents.read` | Read Parents | parents | Velileri görüntüleme |
| `parents.write` | Write Parents | parents | Velileri yönetme |
| `classes.read` | Read Classes | classes | Sınıfları görüntüleme |
| `classes.write` | Write Classes | classes | Sınıfları yönetme |
| `attendance.read` | Read Attendance | attendance | Yoklamaları görüntüleme |
| `attendance.write` | Write Attendance | attendance | Yoklamaları yönetme |
| `payments.read` | Read Payments | payments | Ödemeleri görüntüleme |
| `payments.write` | Write Payments | payments | Ödemeleri yönetme |
| `debts.read` | Read Debts | debts | Borçları görüntüleme |
| `debts.write` | Write Debts | debts | Borçları yönetme |
| `announcements.read` | Read Announcements | communications | Duyuruları görüntüleme |
| `announcements.write` | Write Announcements | communications | Duyuruları yönetme |
| `dashboard.view` | View Dashboard | DASHBOARD | Dashboard görüntüleme |
| `homework.read` | Ödevleri görüntüleme | homework | Ödevleri görüntüleme |
| `homework.write` | Ödevleri oluşturma/düzenleme | homework | Ödevleri yönetme |
| `library.read` | Kütüphane kitaplarını görüntüleme | library | Kütüphane görüntüleme |
| `library.write` | Kütüphane kitaplarını yönetme | library | Kütüphane yönetme |
| `daily_reports.read` | Günlük raporları görüntüleme | daily_reports | Günlük raporlar |
| `parent_notices.read` | Veli bildirimlerini görüntüleme | parent_notices | Veli bildirimleri |
| `parent_notices.write` | Veli bildirimlerini oluşturma/düzenleme | parent_notices | Veli bildirimleri yönetme |
| `appointments.read` | Randevuları görüntüleme | appointments | Randevular |
| `appointments.write` | Randevuları oluşturma/düzenleme | appointments | Randevular yönetme |
| `bus.read` | Servis bilgilerini görüntüleme | bus | Servis bilgileri |
| `bus.write` | Servis bilgilerini yönetme | bus | Servis yönetme |
| `outbox.read` | Giden kutusunu görüntüleme | outbox | Giden kutusu |
| `parent.view_children` | Çocuk bilgilerini görüntüleme | parent_portal | Çocuk bilgileri |
| `parent.view_daily_report` | Günlük gelişim raporlarını görüntüleme | parent_portal | Günlük raporlar |
| `parent.view_attendance` | Devamsızlık Bilgilerini görüntüleme | parent_portal | Devamsızlık |
| `parent.view_finances` | Ödeme bilgilerini görüntüleme | parent_portal | Ödemeler |
| `parent.send_excuse` | Mazeret talebi gönderme | parent_portal | Mazeret talebi |
| `parent.medicine_request` | İlaç talebi oluşturma | parent_portal | İlaç talebi |
| `parent.make_payment` | Ödeme başlatma | parent_portal | Ödeme başlatma |
| `report.read` | Raporları görüntüleme | reports | Raporlar |
| `canteen.read` | Kantin ürünlerini görüntüleme | canteen | Kantin görüntüleme |
| `canteen.write` | Kantin ürünlerini yönetme | canteen | Kantin yönetme |
| `org.read` | Organizasyonları görüntüleme | org | Organizasyonlar |
| `branch.read` | Şubeleri görüntüleme | branch | Şubeler |
| `notification.read` | Bildirimleri görüntüleme | notification | Bildirimler |
| `notification.write` | Bildirimleri yönetme | notification | Bildirim yönetimi |
| `receipt.read` | Makbuzları görüntüleme | receipt | Makbuzlar |
| `finance.read` | Finansal verileri görüntüleme | finance | Finans |
| `settings.read` | Ayarları görüntüleme | settings | Ayarlar |

---

## 🔌 API Endpoint'leri

### Authentication

| Endpoint | Method | İzin | Açıklama |
|----------|--------|-------|----------|
| `/api/auth/login` | POST | - | Kullanıcı girişi |
| `/api/auth/logout` | POST | - | Çıkış |
| `/api/auth/forgot-password` | POST | - | Şifremi unuttum |
| `/api/auth/reset-password` | POST | - | Şifre sıfırlama |

### Users

| Endpoint | Method | İzin | Açıklama |
|----------|--------|-------|----------|
| `/api/users` | GET | `user.read` | Kullanıcı listesi |
| `/api/users` | POST | `user.write` | Kullanıcı oluşturma |
| `/api/users/{id}` | GET | `user.read` | Kullanıcı detay |
| `/api/users/{id}` | PUT | `user.write` | Kullanıcı güncelleme |
| `/api/users/{id}` | DELETE | `user.write` | Kullanıcı silme |
| `/api/users/{id}/roles` | GET | `user.read` | Kullanıcı rolleri |
| `/api/users/{id}/branches` | GET | `user.read` | Kullanıcı şubeleri |

### Students

| Endpoint | Method | İzin | Açıklama |
|----------|--------|-------|----------|
| `/api/students` | GET | `students.read` | Öğrenci listesi |
| `/api/students` | POST | `students.create` | Öğrenci oluşturma |
| `/api/students/{id}` | GET | `students.read` | Öğrenci detay |
| `/api/students/{id}` | PUT | `students.write` | Öğrenci güncelleme |
| `/api/students/{id}` | DELETE | `students.write` | Öğrenci silme |

### Canteen

| Endpoint | Method | İzin | Açıklama |
|----------|--------|-------|----------|
| `/api/canteen/products` | GET | `canteen.read` | Kantin ürünleri listesi |
| `/api/canteen/products` | POST | `canteen.write` | Ürün oluşturma |
| `/api/canteen/products/{id}` | PUT | `canteen.write` | Ürün güncelleme |
| `/api/canteen/products/{id}` | DELETE | `canteen.write` | Ürün silme |
| `/api/canteen/dietary-restrictions` | GET | `canteen.read` | Diyet kısıtlamaları |
| `/api/canteen/pos/checkout` | POST | `canteen.write` | Satış işlemi |
| `/api/canteen/student/{id}/wallet` | GET | `canteen.read` | Öğrenci cüzdan bilgisi |

### Hardware

| Endpoint | Method | İzin | Açıklama |
|----------|--------|-------|----------|
| `/api/hardware/card/balance` | POST | `canteen.read` | Kart bakiye sorgulama |
| `/api/hardware/payment/process` | POST | - | Kart ile ödeme |
| `/api/hardware/wifi/card-read` | POST | - | WiFi kart okuma |
| `/api/hardware/wifi/card-reads` | GET | - | WiFi kart okumaları |

### RFID Cards

| Endpoint | Method | İzin | Açıklama |
|----------|--------|-------|----------|
| `/api/rfid-cards` | GET | `canteen.read` | RFID kart listesi |
| `/api/rfid-cards` | POST | `settings.write` | Kart oluşturma |
| `/api/rfid-cards/{id}` | GET | `settings.read` | Kart detay |
| `/api/rfid-cards/{id}` | PUT | `settings.write` | Kart güncelleme |
| `/api/rfid-cards/{id}` | DELETE | `settings.write` | Kart silme |
| `/api/rfid-cards/number/{card_number}` | GET | `settings.read` | Kart numarası ile sorgulama |

### Roles

| Endpoint | Method | İzin | Açıklama |
|----------|--------|-------|----------|
| `/api/roles` | GET | `user.read` | Rol listesi |
| `/api/roles` | POST | `user.write` | Rol oluşturma |
| `/api/roles/{id}` | GET | `user.read` | Rol detay |
| `/api/roles/{id}` | PUT | `user.write` | Rol güncelleme |
| `/api/roles/{id}` | DELETE | `user.write` | Rol silme |
| `/api/roles/{id}/permissions` | GET | `user.write` | Rol izinleri |
| `/api/roles/{id}/permissions` | PUT | `user.write` | Rol izinleri güncelleme |

---

## 👥 Rol Tanımları

### Canteen Staff (Kantin Personeli)

**Açıklama:** Kantin personeli - sadece kantin ekranlarına erişim

**İzinler:**
- `canteen.read` - Kantin ürünlerini görüntüleme
- `canteen.write` - Kantin ürünlerini yönetme
- `students.read` - Öğrenci bilgilerini görüntüleme

**Erişilebilir Ekranlar:**
- Kantin Ürünleri (`/canteen`)
- Kantin Satış (`/canteen/sales`)
- Kart Bakiye Yükleme (`/canteen/card-balance`)

**Giriş Bilgileri:**
- Email: `kantin@okul360.com`
- Şifre: `canteen123`

### Super Admin

**Açıklama:** Sistem yöneticisi - tüm yetkilere sahip

**İzinler:** Tüm izinler

**Erişilebilir Ekranlar:** Tüm ekranlar

### Parent (Veli)

**Açıklama:** Veli portalı kullanıcısı

**İzinler:**
- `parent.view_children` - Çocuk bilgilerini görüntüleme
- `parent.view_daily_report` - Günlük raporları görüntüleme
- `parent.view_attendance` - Devamsızlık bilgilerini görüntüleme
- `parent.view_finances` - Ödeme bilgilerini görüntüleme
- `parent.send_excuse` - Mazeret talebi gönderme
- `parent.medicine_request` - İlaç talebi oluşturma
- `parent.make_payment` - Ödeme başlatma

**Erişilebilir Ekranlar:** Veli Portalı bölümündeki tüm ekranlar

---

## 📊 Veritabanı Tabloları

### Temel Tablolar

- `users` - Kullanıcılar
- `roles` - Roller
- `permissions` - İzinler
- `role_permissions` - Rol-izin ilişkileri
- `user_roles` - Kullanıcı-rol ilişkileri
- `organizations` - Organizasyonlar
- `branches` - Şubeler
- `students` - Öğrenciler
- `parents` - Veliler
- `classes` - Sınıflar
- `canteen_products` - Kantin ürünleri
- `canteen_dietary_restrictions` - Diyet kısıtlamaları
- `canteen_orders` - Kantin siparişleri
- `canteen_wallet_transactions` - Cüzdan işlemleri
- `rfid_cards` - RFID kartları
- `devices` - Cihazlar

---

## 🚀 Teknoloji Stack

### Backend
- **Framework:** FastAPI
- **Database:** SQLite (geliştirme), PostgreSQL (production)
- **ORM:** SQLAlchemy (async)
- **Authentication:** JWT
- **Password Hashing:** Bcrypt

### Frontend
- **Framework:** React
- **Language:** TypeScript
- **Routing:** React Router
- **State Management:** Zustand
- **UI Components:** Custom components with Lucide icons
- **HTTP Client:** Axios

---

## 📝 Notlar

1. **Kantin Kullanıcısı:** Özel olarak oluşturulmuş bir kullanıcıdır ve sadece kantin ile ilgili ekranlara erişebilir.
2. **İzin Sistemi:** Rol tabanlı erişim kontrolü (RBAC) kullanılır.
3. **Navigasyon:** Kullanıcının izinlerine göre dinamik olarak filtrelenir.
4. **API Güvenliği:** Tüm endpoint'ler izin kontrolü ile korunmaktadır.

---

*Dokümantasyon son güncelleme: 2026-09-08*
