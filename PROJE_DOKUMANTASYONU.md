# SCS360 Proje Dokümantasyonu

Bu doküman SCS360 projesinin tüm API'lerini, veritabanı tablolarını ve frontend ekranlarını içeren kapsamlı bir referanstır.

## Proje Genel Bakış

SCS360, anaokulu, kreş, etüt ve kurs merkezleri için yönetim sistemi olan kapsamlı bir eğitim yönetim platformudur.

## Backend API Endpoints

### Temel Bileşenler
- **API Base URL**: `/api`
- **Authentication**: JWT token based
- **Multi-tenancy**: Organization ve Branch bazlı izolasyon
- **Permission System**: Rol bazlı yetkilendirme

### API Modülleri

#### 1. Authentication (`/api/auth`)
- `POST /api/auth/login` - Kullanıcı girişi
- `POST /api/auth/refresh` - Token yenileme
- `POST /api/auth/logout` - Çıkış
- `GET /api/auth/me` - Mevcut kullanıcı bilgileri
- `POST /api/auth/forgot-password` - Şifre sıfırlama isteği
- `POST /api/auth/reset-password` - Şifre sıfırlama

#### 2. Organizations (`/api/organizations`)
- `GET /api/organizations` - Kurum listesi
- `POST /api/organizations` - Kurum oluşturma
- `GET /api/organizations/{org_id}` - Kurum detayı
- `PUT /api/organizations/{org_id}` - Kurum güncelleme
- `DELETE /api/organizations/{org_id}` - Kurum silme (pasife alma)

#### 3. Branches (`/api/branches`)
- `GET /api/branches` - Şube listesi
- `POST /api/branches` - Şube oluşturma
- `GET /api/branches/{branch_id}` - Şube detayı
- `PUT /api/branches/{branch_id}` - Şube güncelleme
- `DELETE /api/branches/{branch_id}` - Şube silme (pasife alma)

#### 4. Users (`/api/users`)
- `GET /api/users` - Kullanıcı listesi
- `POST /api/users` - Kullanıcı oluşturma
- `GET /api/users/{user_id}` - Kullanıcı detayı
- `PUT /api/users/{user_id}` - Kullanıcı güncelleme
- `DELETE /api/users/{user_id}` - Kullanıcı silme

#### 5. Students (`/api/students`)
- `POST /api/students` - Öğrenci oluşturma
- `GET /api/students` - Öğrenci listesi (filtreleme ile)
- `GET /api/students/{student_id}` - Öğrenci detayı
- `PUT /api/students/{student_id}` - Öğrenci güncelleme
- `DELETE /api/students/{student_id}` - Öğrenci silme
- `POST /api/students/import-excel` - Excel'den öğrenci içe aktarma
- `GET /api/students/export-excel` - Öğrencileri Excel'e dışa aktarma

#### 6. Classes (`/api/classes`)
- `POST /api/classes` - Sınıf oluşturma
- `GET /api/classes` - Sınıf listesi
- `GET /api/classes/{class_id}` - Sınıf detayı
- `PUT /api/classes/{class_id}` - Sınıf güncelleme
- `DELETE /api/classes/{class_id}` - Sınıf silme
- `POST /api/classes/{class_id}/transfer-students` - Öğrenci transferi

#### 7. Attendance (`/api/attendance`)
- `POST /api/attendance` - Yoklama oluşturma
- `GET /api/attendance` - Yoklama listesi (sınıf, öğrenci, tarih filtreleri ile)
- `GET /api/attendance/{attendance_id}` - Yoklama detayı
- `PUT /api/attendance/{attendance_id}` - Yoklama güncelleme
- `DELETE /api/attendance/{attendance_id}` - Yoklama silme
- `POST /api/attendance/bulk` - Toplu yoklama oluşturma (öğretmenler için)
- `POST /api/attendance/mark-all-present` - Tümünü "Geldi" işaretle

**İzinler:** `attendance.read`, `attendance.write`, `attendance.take`

#### 8. Debts (`/api/debts`)
- `GET /api/debts` - Borç listesi
- `GET /api/debts/{debt_id}` - Borç detayı
- `POST /api/debts` - Borç oluşturma
- `PUT /api/debts/{debt_id}` - Borç güncelleme
- `DELETE /api/debts/{debt_id}` - Borç silme

#### 9. Payments (`/api/payments`)

##### Basic Operations
- `POST /api/payments` - Ödeme oluşturma
- `GET /api/payments` - Ödeme listesi
- `GET /api/payments/{payment_id}` - Ödeme detayı
- `PUT /api/payments/{payment_id}` - Ödeme güncelleme
- `DELETE /api/payments/{payment_id}` - Ödeme silme

##### iyzico Integration
- `POST /api/payments/iyzico/initialize` - iyzico ödeme başlatma
- `POST /api/payments/iyzico/callback` - iyzico callback

##### Finance Operations
- `POST /api/payments/finances/invoices/generate-plan` - Taksit planı oluşturma
- `POST /api/payments/finances/payments/collect` - Ödeme toplama
- `GET /api/payments/finances/payments/{payment_id}/receipt-pdf` - Makbuz PDF
- `POST /api/payments/finances/reminders/send` - Ödeme hatırlatması gönderme

**İzinler:** `payments.read`, `payments.write`, `payments.create`, `payments.update`, `payments.delete`, `finance.invoices_manage`, `finance.collect_payment`

#### 10. Communications (`/api/communications`)

##### SMS Providers
- `GET /api/communications/sms-providers` - SMS sağlayıcı listesi
- `POST /api/communications/sms-providers` - SMS sağlayıcı oluşturma

##### Broadcast Jobs
- `GET /api/communications/broadcast-jobs` - Broadcast işleri listesi
- `POST /api/communications/broadcast-jobs` - Broadcast işi oluşturma
- `PUT /api/communications/broadcast-jobs/{job_id}` - Broadcast işi güncelleme
- `POST /api/communications/broadcast-jobs/{job_id}/send` - Broadcast gönderme
- `DELETE /api/communications/broadcast-jobs/{job_id}` - Broadcast iptal

##### Delivery Reports
- `GET /api/communications/delivery-reports` - Teslimat raporları
- `GET /api/communications/broadcast-jobs/{job_id}/delivery-summary` - Teslimat özeti

##### Message Templates
- `GET /api/communications/message-templates` - Mesaj şablonları
- `POST /api/communications/message-templates` - Şablon oluşturma

**İzinler:** `communications.read`, `communications.write`

#### 11. Parent Portal (`/api/parent`)
- `GET /api/parent/my-children` - Veli çocukları listesi
- `GET /api/parent/child/{id}/today-status` - Çocuğun günlük durumu
- `GET /api/parent/child/{id}/timeline` - Çocuk zaman çizelgesi
- `GET /api/parent/child/{id}/attendance` - Çocuk devamsızlık takvimi (aylık)
- `GET /api/parent/child/{id}/grades` - Çocuk notları
- `GET /api/parent/child/{id}/schedule` - Çocuk ders programı
- `GET /api/parent/child/{id}/homework` - Çocuk ödevleri
- `GET /api/parent/child/{id}/financial-invoices` - Çocuk finansal faturaları
- `GET /api/parent/child/{id}/medicine-requests` - Çocuk ilaç talepleri
- `POST /api/parent/child/{id}/excuse-request` - İzin talebi
- `POST /api/parent/child/{id}/medicine-requests` - İlaç talebi
- `POST /api/parent/payments/checkout-session` - Ödeme oturumu oluşturma

**İzinler:** `parent.view_children`, `parent.view_daily_report`, `parent.view_attendance`, `parent.view_finances`, `parent.send_excuse`, `parent.medicine_request`, `parent.make_payment`

#### 12. Diğer API Modülleri
- **Health**: `/api/health` - Sistem sağlık kontrolü
- **Dashboard**: `/api/dashboard` - Dashboard verileri
- **Announcements**: `/api/announcements` - Duyurular
- **Appointments**: `/api/appointments` - Randevular
- **Bus**: `/api/bus` - Servis yönetimi
- **Canteen**: `/api/canteen` - Kantin işlemleri
- **Clubs**: `/api/clubs` - Kulüpler
- **Consents**: `/api/consents` - İzinler
- **Daily Reports**: `/api/daily-reports` - Günlük raporlar
- **Debts**: `/api/debts` - Borçlar
- **Devices**: `/api/devices` - Cihazlar
- **Exams**: `/api/exams` - Sınavlar
- **Expenses**: `/api/expenses` - Giderler
- **Files**: `/api/files` - Dosya yönetimi
- **Guidance**: `/api/guidance` - Rehberlik
- **Hardware**: `/api/hardware` - Donanım
- **HQ**: `/api/hq` - Merkez yönetimi
- **Homework**: `/api/homework` - Ödevler
- **Data Import**: `/api/data-import` - Veri içe aktarma
- **Infirmary**: `/api/infirmary` - Sağlık oda
- **Inventory**: `/api/inventory` - Envanter
- **Library**: `/api/library` - Kütüphane
- **Materials**: `/api/materials` - Materyaller
- **Messages**: `/api/messages` - Mesajlar
- **Operations**: `/api/operations` - Operasyonlar
- **Outbox**: `/api/outbox` - Giden kutusu
- **Parent Notices**: `/api/parent-notices` - Veli talepleri
- **Parents**: `/api/parents` - Veliler
- **Payroll**: `/api/payroll` - Maaş
- **Pickup**: `/api/pickup` - Teslim alma
- **RFID Cards**: `/api/rfid-cards` - RFID kartlar
- **Card Numbers**: `/api/card-numbers` - Kart numaraları
- **Security**: `/api/security` - Güvenlik
- **Settings**: `/api/settings` - Ayarlar
- **Staff Operations**: `/api/staff-operations` - Personel operasyonları
- **Surveys**: `/api/surveys` - Anketler
- **Teacher**: `/api/teacher` - Öğretmen işlemleri
- **Timetable**: `/api/timetable` - Ders programı
- **Tutoring**: `/api/tutoring` - Etüt
- **User Roles**: `/api/user-roles` - Kullanıcı rolleri
- **AI Analytics**: `/api/ai-analytics` - AI analitikleri

## Veritabanı Tabloları

### Temel Tablolar

#### 1. organizations
Kurum/okul bilgilerini tutar
- `id` (UUID) - Primary Key
- `name` - Kurum adı
- `legal_name` - Resmi ad
- `tax_number` - Vergi numarası
- `tax_office` - Vergi dairesi
- `phone` - Telefon
- `email` - E-posta
- `address` - Adres
- `city` - Şehir
- `country` - Ülke
- `logo_url` - Logo URL
- `website` - Web sitesi
- `is_active` - Aktif mi
- `created_by` - Oluşturan
- `updated_by` - Güncelleyen
- `created_at` - Oluşturma tarihi
- `updated_at` - Güncelleme tarihi
- `deleted_at` - Silme tarihi (soft delete)

#### 2. branches
Şube bilgilerini tutar
- `id` (UUID) - Primary Key
- `organization_id` - Kurum ID (FK)
- `name` - Şube adı
- `code` - Şube kodu
- `phone` - Telefon
- `email` - E-posta
- `address` - Adres
- `city` - Şehir
- `capacity` - Kapasite
- `is_active` - Aktif mi
- `created_by` - Oluşturan
- `updated_by` - Güncelleyen
- `created_at` - Oluşturma tarihi
- `updated_at` - Güncelleme tarihi
- `deleted_at` - Silme tarihi (soft delete)

#### 3. users
Kullanıcı hesaplarını tutar
- `id` (UUID) - Primary Key
- `organization_id` - Kurum ID (FK)
- `email` - E-posta (unique)
- `password_hash` - Şifre hash
- `first_name` - Ad
- `last_name` - Soyad
- `phone` - Telefon
- `position` - Pozisyon
- `department` - Departman
- `status` - Durum (ACTIVE, PASSIVE, BLOCKED)
- `is_super_admin` - Süper admin mi
- `last_login_at` - Son giriş
- `created_by` - Oluşturan
- `updated_by` - Güncelleyen
- `created_at` - Oluşturma tarihi
- `updated_at` - Güncelleme tarihi
- `deleted_at` - Silme tarihi (soft delete)

#### 4. roles
Rol tanımlarını tutar
- `id` (UUID) - Primary Key
- `name` - Rol adı
- `slug` - Rol slug
- `description` - Açıklama
- `is_system` - Sistem rolü mü
- `organization_id` - Kurum ID (FK)
- `created_at` - Oluşturma tarihi
- `updated_at` - Güncelleme tarihi
- `deleted_at` - Silme tarihi (soft delete)

#### 5. permissions
İzin tanımlarını tutar
- `id` (UUID) - Primary Key
- `code` - İzin kodu (unique)
- `name` - İzin adı
- `module` - Modül
- `description` - Açıklama
- `created_at` - Oluşturma tarihi

#### 6. role_permissions
Rol-izin ilişkilerini tutar
- `role_id` - Rol ID (FK, PK)
- `permission_id` - İzin ID (FK, PK)
- `created_at` - Oluşturma tarihi

#### 7. user_roles
Kullanıcı-rol ilişkilerini tutar
- `user_id` - Kullanıcı ID (FK, PK)
- `role_id` - Rol ID (FK, PK)
- `assigned_at` - Atama tarihi
- `assigned_by` - Atayan

#### 8. user_branches
Kullanıcı-şube ilişkilerini tutar
- `user_id` - Kullanıcı ID (FK, PK)
- `branch_id` - Şube ID (FK, PK)
- `assigned_at` - Atama tarihi
- `assigned_by` - Atayan

### Güvenlik Tabloları

#### 9. refresh_tokens
Refresh token'ları tutar
- `id` (UUID) - Primary Key
- `user_id` - Kullanıcı ID (FK)
- `token_hash` - Token hash
- `family_id` - Token ailesi ID
- `expires_at` - Son kullanma tarihi
- `revoked_at` - İptal tarihi
- `replaced_by` - Yerine geçen token
- `created_at` - Oluşturma tarihi
- `ip_address` - IP adresi
- `user_agent` - User agent

#### 10. password_reset_tokens
Şifre sıfırlama token'larını tutar
- `id` (UUID) - Primary Key
- `user_id` - Kullanıcı ID (FK)
- `token_hash` - Token hash
- `expires_at` - Son kullanma tarihi
- `used_at` - Kullanım tarihi
- `created_at` - Oluşturma tarihi

#### 11. login_attempts
Giriş denemelerini tutar
- `id` (UUID) - Primary Key
- `email` - E-posta
- `ip_address` - IP adresi
- `user_agent` - User agent
- `success` - Başarılı mı
- `failure_reason` - Başarısızlık sebebi
- `attempted_at` - Deneme tarihi

### Eğitim Tabloları

#### 12. classes
Sınıf bilgilerini tutar
- `id` (UUID) - Primary Key
- `organization_id` - Kurum ID (FK)
- `branch_id` - Şube ID (FK)
- `name` - Sınıf adı
- `code` - Sınıf kodu
- `description` - Açıklama
- `capacity` - Kapasite
- `academic_year` - Akademik yıl
- `teacher_id` - Öğretmen ID (FK)
- `is_active` - Aktif mi
- `created_by` - Oluşturan
- `updated_by` - Güncelleyen
- `created_at` - Oluşturma tarihi
- `updated_at` - Güncelleme tarihi
- `deleted_at` - Silme tarihi (soft delete)

#### 13. class_teachers
Sınıf-öğretmen ilişkilerini tutar
- `class_id` - Sınıf ID (FK, PK)
- `user_id` - Kullanıcı ID (FK, PK)
- `is_primary` - Birincil mi
- `assigned_at` - Atama tarihi
- `assigned_by` - Atayan

#### 14. students
Öğrenci bilgilerini tutar
- `id` (UUID) - Primary Key
- `organization_id` - Kurum ID (FK)
- `branch_id` - Şube ID (FK)
- `class_id` - Sınıf ID (FK)
- `student_number` - Öğrenci numarası
- `first_name` - Ad
- `last_name` - Soyad
- `gender` - Cinsiyet (MALE, FEMALE, OTHER)
- `birth_date` - Doğum tarihi
- `enrollment_date` - Kayıt tarihi
- `status` - Durum (ACTIVE, PASSIVE, GRADUATED, LEFT)
- `photo_url` - Fotoğraf URL
- `health_notes` - Sağlık notları
- `notes` - Notlar
- `created_by` - Oluşturan
- `updated_by` - Güncelleyen
- `created_at` - Oluşturma tarihi
- `updated_at` - Güncelleme tarihi
- `deleted_at` - Silme tarihi (soft delete)

#### 15. parents
Veli bilgilerini tutar
- `id` (UUID) - Primary Key
- `organization_id` - Kurum ID (FK)
- `user_id` - Kullanıcı ID (FK)
- `first_name` - Ad
- `last_name` - Soyad
- `relation_type` - İlişki türü (MOTHER, FATHER, GUARDIAN, OTHER)
- `phone` - Telefon
- `sms_phone` - SMS telefonu
- `whatsapp_phone` - WhatsApp telefonu
- `email` - E-posta
- `address` - Adres
- `receive_notifications` - Bildirim al mı
- `created_by` - Oluşturan
- `updated_by` - Güncelleyen
- `created_at` - Oluşturma tarihi
- `updated_at` - Güncelleme tarihi
- `deleted_at` - Silme tarihi (soft delete)

#### 16. student_parents
Öğrenci-veli ilişkilerini tutar
- `student_id` - Öğrenci ID (FK, PK)
- `parent_id` - Veli ID (FK, PK)
- `is_primary` - Birincil mi
- `is_emergency` - Acil durum mi
- `created_at` - Oluşturma tarihi

#### 17. student_files
Öğrenci dosyalarını tutar
- `id` (UUID) - Primary Key
- `organization_id` - Kurum ID (FK)
- `branch_id` - Şube ID (FK)
- `student_id` - Öğrenci ID (FK)
- `category` - Kategori (IDENTITY, HEALTH_REPORT, REGISTRATION_CONTRACT, PAYMENT_CONTRACT, PHOTO, OTHER)
- `file_name` - Dosya adı
- `original_name` - Orijinal ad
- `mime_type` - MIME tipi
- `file_size` - Dosya boyutu
- `storage_path` - Depolama yolu
- `uploaded_by` - Yükleyen
- `created_at` - Oluşturma tarihi
- `updated_at` - Güncelleme tarihi
- `deleted_at` - Silme tarihi (soft delete)

#### 18. attendance_records
Yoklama kayıtlarını tutar
- `id` (UUID) - Primary Key
- `organization_id` - Kurum ID (FK)
- `branch_id` - Şube ID (FK)
- `class_id` - Sınıf ID (FK)
- `student_id` - Öğrenci ID (FK)
- `attendance_date` - Yoklama tarihi
- `status` - Durum (PRESENT, ABSENT, EXCUSED, LATE, HALF_DAY)
- `check_in_time` - Giriş saati
- `notes` - Notlar
- `recorded_by` - Kaydeden
- `created_at` - Oluşturma tarihi
- `updated_at` - Güncelleme tarihi
- `deleted_at` - Silme tarihi (soft delete)

#### 19. grades
Notları tutar
- `id` (UUID) - Primary Key
- `organization_id` - Kurum ID (FK)
- `branch_id` - Şube ID (FK)
- `class_id` - Sınıf ID (FK)
- `student_id` - Öğrenci ID (FK)
- `teacher_id` - Öğretmen ID (FK)
- `subject` - Ders (MATHEMATICS, SCIENCE, TURKISH, SOCIAL_STUDIES, ENGLISH, PHYSICAL_EDUCATION, ART, MUSIC, COMPUTER, RELIGION, OTHER)
- `grade_type` - Not türü (EXAM, QUIZ, HOMEWORK, PROJECT, PARTICIPATION, MIDTERM, FINAL)
- `score` - Puan
- `max_score` - Maksimum puan
- `exam_date` - Sınav tarihi
- `term` - Dönem
- `notes` - Notlar
- `created_by` - Oluşturan
- `updated_by` - Güncelleyen
- `created_at` - Oluşturma tarihi
- `updated_at` - Güncelleme tarihi

#### 20. daily_development_reports
Günlük gelişim raporlarını tutar
- `id` (UUID) - Primary Key
- `student_id` - Öğrenci ID (FK)
- `class_id` - Sınıf ID (FK)
- `date` - Tarih
- `meal_status` - Yemek durumu (ALL, HALF, NONE)
- `sleep_status` - Uyku durumu (SLEPT_WELL, SHORT, NO_SLEEP)
- `mood` - Ruh hali (HAPPY, CALM, UNSETTLED, TIRED)
- `activities` - Aktiviteler (JSON)
- `teacher_notes` - Öğretmen notları
- `recorded_by` - Kaydeden
- `created_at` - Oluşturma tarihi
- `updated_at` - Güncelleme tarihi

### Finans Tabloları

#### 21. debts
Borçları tutar
- `id` (UUID) - Primary Key
- `organization_id` - Kurum ID (FK)
- `branch_id` - Şube ID (FK)
- `student_id` - Öğrenci ID (FK)
- `debt_type` - Borç türü (EDUCATION, FOOD, SERVICE, STATIONERY, ACTIVITY, OTHER)
- `description` - Açıklama
- `amount` - Tutar
- `paid_amount` - Ödenen tutar
- `status` - Durum (UNPAID, PARTIALLY_PAID, PAID, OVERDUE, CANCELLED)
- `due_date` - Son ödeme tarihi
- `created_by` - Oluşturan
- `updated_by` - Güncelleyen
- `created_at` - Oluşturma tarihi
- `updated_at` - Güncelleme tarihi
- `deleted_at` - Silme tarihi (soft delete)

#### 22. payments
Ödemeleri tutar
- `id` (UUID) - Primary Key
- `organization_id` - Kurum ID (FK)
- `branch_id` - Şube ID (FK)
- `student_id` - Öğrenci ID (FK)
- `debt_id` - Borç ID (FK)
- `amount` - Tutar
- `payment_method` - Ödeme yöntemi (CASH, CREDIT_CARD, BANK_TRANSFER, EFT, OTHER)
- `payment_date` - Ödeme tarihi
- `status` - Durum
- `notes` - Notlar
- `received_by` - Alan
- `cancelled_at` - İptal tarihi
- `cancelled_by` - İptal eden
- `cancel_reason` - İptal sebebi
- `created_at` - Oluşturma tarihi
- `updated_at` - Güncelleme tarihi

#### 23. receipts
Makbuzları tutar
- `id` (UUID) - Primary Key
- `organization_id` - Kurum ID (FK)
- `branch_id` - Şube ID (FK)
- `student_id` - Öğrenci ID (FK)
- `payment_id` - Ödeme ID (FK, unique)
- `receipt_number` - Makbuz numarası (unique)
- `status` - Durum (ACTIVE, CANCELLED)
- `issued_at` - Düzenleme tarihi
- `issued_by` - Düzenleyen
- `pdf_path` - PDF yolu
- `remaining_debt` - Kalan borç
- `created_at` - Oluşturma tarihi
- `updated_at` - Güncelleme tarihi

#### 24. expenses
Giderleri tutar
- `id` (UUID) - Primary Key
- `organization_id` - Kurum ID (FK)
- `branch_id` - Şube ID (FK)
- `description` - Açıklama
- `category` - Kategori
- `amount` - Tutar
- `expense_date` - Gider tarihi
- `status` - Durum
- `notes` - Notlar
- `created_by` - Oluşturan
- `updated_by` - Güncelleyen
- `created_at` - Oluşturma tarihi
- `updated_at` - Güncelleme tarihi
- `deleted_at` - Silme tarihi (soft delete)

### İletişim Tabloları

#### 25. announcements
Duyuruları tutar
- `id` (UUID) - Primary Key
- `organization_id` - Kurum ID (FK)
- `branch_id` - Şube ID (FK)
- `class_id` - Sınıf ID (FK)
- `student_id` - Öğrenci ID (FK)
- `title` - Başlık
- `content` - İçerik
- `audience` - Hedef kitle (ALL_PARENTS, BRANCH_PARENTS, CLASS_PARENTS, SINGLE_STUDENT)
- `channels` - Kanallar (JSON)
- `status` - Durum (DRAFT, SCHEDULED, SENT, CANCELLED)
- `scheduled_at` - Planlanan tarih
- `sent_at` - Gönderim tarihi
- `created_by` - Oluşturan
- `created_at` - Oluşturma tarihi
- `updated_at` - Güncelleme tarihi
- `deleted_at` - Silme tarihi (soft delete)

#### 26. announcement_recipients
Duyuru alıcılarını tutar
- `id` (UUID) - Primary Key
- `announcement_id` - Duyuru ID (FK)
- `parent_id` - Veli ID (FK)
- `student_id` - Öğrenci ID (FK)
- `channel` - Kanal (EMAIL, SMS, WHATSAPP)
- `status` - Durum (PENDING, SENT, FAILED, CANCELLED)
- `sent_at` - Gönderim tarihi
- `error_message` - Hata mesajı
- `created_at` - Oluşturma tarihi

#### 27. message_templates
Mesaj şablonlarını tutar
- `id` (UUID) - Primary Key
- `organization_id` - Kurum ID (FK)
- `code` - Şablon kodu
- `name` - Şablon adı
- `channel` - Kanal (EMAIL, SMS, WHATSAPP)
- `subject` - Konu
- `body_template` - İçerik şablonu
- `is_active` - Aktif mi
- `created_at` - Oluşturma tarihi
- `updated_at` - Güncelleme tarihi
- `deleted_at` - Silme tarihi (soft delete)

#### 28. notification_jobs
Bildirim işlerini tutar
- `id` (UUID) - Primary Key
- `organization_id` - Kurum ID (FK)
- `branch_id` - Şube ID (FK)
- `channel` - Kanal (EMAIL, SMS, WHATSAPP)
- `template_code` - Şablon kodu
- `subject` - Konu
- `body` - İçerik
- `status` - Durum (PENDING, SENT, FAILED, CANCELLED)
- `retry_count` - Yeniden deneme sayısı
- `max_retries` - Maksimum deneme
- `scheduled_at` - Planlanan tarih
- `processed_at` - İşleme tarihi
- `reference_type` - Referans türü
- `reference_id` - Referans ID
- `created_by` - Oluşturan
- `created_at` - Oluşturma tarihi
- `updated_at` - Güncelleme tarihi

#### 29. notification_recipients
Bildirim alıcılarını tutar
- `id` (UUID) - Primary Key
- `notification_job_id` - Bildirim işi ID (FK)
- `parent_id` - Veli ID (FK)
- `user_id` - Kullanıcı ID (FK)
- `recipient_name` - Alıcı adı
- `recipient_address` - Alıcı adresi
- `status` - Durum (PENDING, SENT, FAILED, CANCELLED)
- `provider_response` - Sağlayıcı yanıtı (JSON)
- `error_message` - Hata mesajı
- `sent_at` - Gönderim tarihi
- `created_at` - Oluşturma tarihi
- `updated_at` - Güncelleme tarihi

#### 30. chat_messages
Sohbet mesajlarını tutar
- `id` (UUID) - Primary Key
- `sender_id` - Gönderen ID (FK)
- `receiver_id` - Alıcı ID (FK)
- `class_id` - Sınıf ID (FK)
- `content` - İçerik
- `attachment_url` - Ek URL
- `is_read` - Okundu mu
- `sent_at` - Gönderim tarihi
- `created_at` - Oluşturma tarihi
- `updated_at` - Güncelleme tarihi

### Sistem Tabloları

#### 31. integration_settings
Entegrasyon ayarlarını tutar
- `id` (UUID) - Primary Key
- `organization_id` - Kurum ID (FK)
- `provider` - Sağlayıcı (SMTP, NETGSM, TWILIO, META_WHATSAPP, OTHER)
- `config` - Konfigürasyon (JSON)
- `is_active` - Aktif mi
- `updated_by` - Güncelleyen
- `created_at` - Oluşturma tarihi
- `updated_at` - Güncelleme tarihi

#### 32. app_settings
Uygulama ayarlarını tutar
- `id` (UUID) - Primary Key
- `organization_id` - Kurum ID (FK)
- `setting_key` - Ayar anahtarı
- `setting_value` - Ayar değeri (JSON)
- `description` - Açıklama
- `updated_by` - Güncelleyen
- `created_at` - Oluşturma tarihi
- `updated_at` - Güncelleme tarihi

#### 33. audit_logs
Denetim loglarını tutar
- `id` (UUID) - Primary Key
- `organization_id` - Kurum ID (FK)
- `branch_id` - Şube ID (FK)
- `user_id` - Kullanıcı ID (FK)
- `action` - Aksiyon (CREATE, UPDATE, DELETE, LOGIN, LOGOUT, PAYMENT, CANCEL_PAYMENT, SEND_NOTIFICATION, OTHER)
- `entity_type` - Varlık türü
- `entity_id` - Varlık ID
- `old_values` - Eski değerler (JSON)
- `new_values` - Yeni değerler (JSON)
- `ip_address` - IP adresi
- `user_agent` - User agent
- `created_at` - Oluşturma tarihi

### Donanım Tabloları

#### 34. card_numbers
Kart numaralarını tutar
- `id` (String) - Primary Key
- `organization_id` - Kurum ID
- `branch_id` - Şube ID
- `card_number` - Kart numarası
- `status` - Durum (AVAILABLE, ASSIGNED, DAMAGED, LOST)
- `notes` - Notlar
- `purchased_date` - Satın alma tarihi
- `supplier` - Tedarikçi
- `created_at` - Oluşturma tarihi
- `updated_at` - Güncelleme tarihi

#### 35. devices
Cihazları tutar
- `id` (String) - Primary Key
- `organization_id` - Kurum ID
- `branch_id` - Şube ID
- `name` - Cihaz adı
- `device_type` - Cihaz türü (TURNSTILE, CARD_READER, DOOR_LOCK, ATTENDANCE_KIOSK, CANTEEN_TERMINAL)
- `serial_number` - Seri numarası
- `ip_address` - IP adresi
- `location` - Konum
- `status` - Durum (ACTIVE, INACTIVE, MAINTENANCE, BROKEN)
- `last_heartbeat` - Son kalp atışı
- `notes` - Notlar
- `created_at` - Oluşturma tarihi
- `updated_at` - Güncelleme tarihi

#### 36. rfid_cards
RFID kartlarını tutar
- `id` (String) - Primary Key
- `organization_id` - Kurum ID
- `branch_id` - Şube ID
- `card_number` - Kart numarası
- `card_type` - Kart türü (STUDENT, STAFF)
- `holder_id` - Sahip ID
- `holder_name` - Sahip adı
- `status` - Durum (ACTIVE, INACTIVE, BLOCKED)
- `issue_date` - Veriliş tarihi
- `expiry_date` - Son kullanma tarihi
- `created_at` - Oluşturma tarihi
- `updated_at` - Güncelleme tarihi

### Ders Programı Tabloları

#### 37. timetable_slots
Ders programı zamanlarını tutar
- `id` (UUID) - Primary Key
- `day` - Gün
- `start_time` - Başlangıç saati
- `end_time` - Bitiş saati
- `is_break` - Ara mı
- `created_at` - Oluşturma tarihi
- `updated_at` - Güncelleme tarihi

#### 38. classroom_assignments
Sınıf atamalarını tutar
- `id` (UUID) - Primary Key
- `class_id` - Sınıf ID (FK)
- `teacher_id` - Öğretmen ID (FK)
- `subject_id` - Ders ID
- `room_number` - Oda numarası
- `capacity` - Kapasite
- `created_at` - Oluşturma tarihi
- `updated_at` - Güncelleme tarihi

#### 39. timetables
Ders programlarını tutar
- `id` (UUID) - Primary Key
- `class_id` - Sınıf ID (FK)
- `slot_id` - Zaman ID (FK)
- `classroom_assignment_id` - Sınıf atama ID (FK)
- `academic_year` - Akademik yıl
- `semester` - Dönem
- `is_active` - Aktif mi
- `created_at` - Oluşturma tarihi
- `updated_at` - Güncelleme tarihi

## Frontend Ekranları ve API İlişkileri

### Yönetim Bölümü

#### 1. Dashboard (`/dashboard`)
**Kullanılan API'ler:**
- `GET /api/dashboard/summary` - Özet istatistikler (öğrenci sayısı, tahsilat, devamsızlık)
- `GET /api/dashboard/charts` - Aylık tahsilat grafiği
- `GET /api/dashboard/overview` - Genel bakış verileri
- `GET /api/ai/insights-report` - AI öngörüler ve öncelikli aksiyonlar
- `GET /api/admin/students` - Öğrenci listesi (chat için)
- `GET /api/users` - Kullanıcı listesi (chat için)

**İzinler:** `dashboard.view`

#### 2. Organizations (`/organizations`)
**Kullanılan API'ler:**
- `GET /api/organizations` - Kurum listesi
- `POST /api/organizations` - Kurum oluşturma
- `GET /api/organizations/{id}` - Kurum detayı
- `PUT /api/organizations/{id}` - Kurum güncelleme
- `DELETE /api/organizations/{id}` - Kurum silme

**İzinler:** `org.read`, `org.write`

#### 3. Branches (`/branches`)
**Kullanılan API'ler:**
- `GET /api/branches` - Şube listesi
- `POST /api/branches` - Şube oluşturma
- `GET /api/branches/{id}` - Şube detayı
- `PUT /api/branches/{id}` - Şube güncelleme
- `DELETE /api/branches/{id}` - Şube silme

**İzinler:** `branch.read`, `branch.write`

#### 4. Users (`/users`)
**Kullanılan API'ler:**
- `GET /api/users` - Kullanıcı listesi
- `POST /api/users` - Kullanıcı oluşturma
- `GET /api/users/{id}` - Kullanıcı detayı
- `PUT /api/users/{id}` - Kullanıcı güncelleme
- `DELETE /api/users/{id}` - Kullanıcı silme

**İzinler:** `users.read`, `users.write`

#### 5. Roles (`/roles`)
**Kullanılan API'ler:**
- `GET /api/roles` - Rol listesi
- `POST /api/roles` - Rol oluşturma
- `GET /api/roles/{id}` - Rol detayı
- `PUT /api/roles/{id}` - Rol güncelleme
- `DELETE /api/roles/{id}` - Rol silme
- `GET /api/roles/{id}/permissions` - Rol yetkileri

**İzinler:** `users.read`, `users.write`

#### 6. Staff (`/staff`)
**Kullanılan API'ler:**
- `GET /api/staff` - Personel listesi
- `POST /api/staff` - Personel oluşturma
- `GET /api/staff/{id}` - Personel detayı
- `PUT /api/staff/{id}` - Personel güncelleme

**İzinler:** `users.read`, `users.write`

#### 7. Teacher Portal (`/teacher`)
**Kullanılan API'ler:**
- `GET /api/dashboard/summary` - Öğretmen özeti
- `GET /api/dashboard/overview` - Genel bakış
- `GET /api/students` - Öğrenci listesi
- `GET /api/users` - Kullanıcı listesi

**İzinler:** `dashboard.view`

### Eğitim Bölümü

#### 8. Students (`/students`)
**Kullanılan API'ler:**
- `GET /api/students` - Öğrenci listesi (arama, sayfalama ile)
- `POST /api/students` - Öğrenci oluşturma
- `GET /api/students/{id}` - Öğrenci detayı
- `PUT /api/students/{id}` - Öğrenci güncelleme
- `DELETE /api/students/{id}` - Öğrenci silme
- `POST /api/students/import-excel` - Excel'den içe aktarma
- `GET /api/students/export-excel` - Excel'e dışa aktarma
- `GET /api/ai/students-overview` - AI öğrenci analizi

**İzinler:** `students.read`, `students.write`, `students.import`, `students.export`

#### 9. Student Detail (`/students/{id}`)
**Kullanılan API'ler:**
- `GET /api/students/{id}` - Öğrenci detayı
- `GET /api/students/{id}/files` - Öğrenci dosyaları
- `GET /api/students/{id}/parents` - Öğrenci velileri
- `GET /api/attendance?student_id={id}` - Öğrenci yoklaması

**İzinler:** `students.read`

#### 10. Parents (`/parents`)
**Kullanılan API'ler:**
- `GET /api/parents` - Veli listesi
- `POST /api/parents` - Veli oluşturma
- `GET /api/parents/{id}` - Veli detayı
- `PUT /api/parents/{id}` - Veli güncelleme

**İzinler:** `parents.read`, `parents.write`

#### 11. Classes (`/classes`)
**Kullanılan API'ler:**
- `GET /api/classes` - Sınıf listesi
- `POST /api/classes` - Sınıf oluşturma
- `GET /api/classes/{id}` - Sınıf detayı
- `PUT /api/classes/{id}` - Sınıf güncelleme
- `DELETE /api/classes/{id}` - Sınıf silme
- `POST /api/classes/{id}/transfer-students` - Öğrenci transferi

**İzinler:** `classes.read`, `classes.write`

#### 12. Class Detail (`/classes/{id}`)
**Kullanılan API'ler:**
- `GET /api/classes/{id}` - Sınıf detayı
- `GET /api/students?class_id={id}` - Sınıf öğrencileri
- `GET /api/attendance?class_id={id}` - Sınıf yoklaması

**İzinler:** `classes.read`, `students.read`

#### 13. Class Occupancy (`/classes/occupancy`)
**Kullanılan API'ler:**
- `GET /api/classes` - Sınıf listesi
- `GET /api/students` - Öğrenci sayıları

**İzinler:** `classes.read`

#### 14. Assign Students (`/classes/{id}/assign`)
**Kullanılan API'ler:**
- `GET /api/students` - Öğrenci listesi
- `POST /api/classes/{id}/transfer-students` - Öğrenci atama

**İzinler:** `classes.write`

#### 15. Attendance (`/attendance`)
**Kullanılan API'ler:**
- `GET /api/classes` - Sınıf listesi
- `GET /api/students?class_id={id}` - Sınıf öğrencileri
- `POST /api/attendance/bulk` - Toplu yoklama oluşturma
- `POST /api/attendance/mark-all-present` - Tümünü "Geldi" işaretle
- `GET /api/ai/attendance-analysis` - AI devamsızlık analizi

**İzinler:** `attendance.read`, `attendance.write`, `attendance.take`

#### 16. Bulk Attendance (`/attendance/bulk`)
**Kullanılan API'ler:**
- `GET /api/classes` - Sınıf listesi
- `GET /api/students?class_id={id}` - Sınıf öğrencileri
- `POST /api/attendance/bulk` - Toplu yoklama

**İzinler:** `attendance.take`

#### 17. Student Attendance (`/attendance/student/{id}`)
**Kullanılan API'ler:**
- `GET /api/attendance?student_id={id}` - Öğrenci yoklaması
- `GET /api/students/{id}` - Öğrenci detayı

**İzinler:** `attendance.read`

#### 18. Monthly Attendance Report (`/attendance/monthly`)
**Kullanılan API'ler:**
- `GET /api/attendance` - Yoklama verileri
- `GET /api/dashboard/attendance-summary` - Yoklama özeti

**İzinler:** `attendance.read`

#### 19. Homework (`/homework`)
**Kullanılan API'ler:**
- `GET /api/homework` - Ödev listesi
- `POST /api/homework` - Ödev oluşturma
- `GET /api/homework/{id}` - Ödev detayı
- `PUT /api/homework/{id}` - Ödev güncelleme

**İzinler:** `students.read`, `students.write`

#### 20. Library (`/library`)
**Kullanılan API'ler:**
- `GET /api/library` - Kütüphane listesi
- `POST /api/library` - Kütüphane kaydı
- `GET /api/library/{id}` - Kütüphane detayı

**İzinler:** `students.read`, `students.write`

#### 21. Daily Reports (`/daily-reports`)
**Kullanılan API'ler:**
- `GET /api/daily-reports` - Günlük raporlar
- `POST /api/daily-reports` - Rapor oluşturma
- `GET /api/daily-reports/{id}` - Rapor detayı

**İzinler:** `students.read`, `students.write`

#### 22. Exams (`/exams`)
**Kullanılan API'ler:**
- `GET /api/exams` - Sınav listesi
- `POST /api/exams` - Sınav oluşturma
- `GET /api/exams/{id}` - Sınav detayı

**İzinler:** `students.read`, `students.write`

#### 23. Materials (`/materials`)
**Kullanılan API'ler:**
- `GET /api/materials` - Materyal listesi
- `POST /api/materials` - Materyal oluşturma
- `GET /api/materials/{id}` - Materyal detayı

**İzinler:** `students.read`, `students.write`

#### 24. Timetable (`/timetable`)
**Kullanılan API'ler:**
- `GET /api/timetable` - Ders programı
- `GET /api/timetable/{class_id}` - Sınıf programı

**İzinler:** `students.read`

### Veli Portalı

#### 25. Parent Dashboard (`/parent/dashboard`)
**Kullanılan API'ler:**
- `GET /api/parent/my-children` - Çocuklarım
- `GET /api/parent/child/{id}/today-status` - Günlük durum
- `GET /api/dashboard/summary` - Özet veriler

**İzinler:** `parent.view_children`, `parent.view_daily_report`

#### 26. My Children (`/parent/children`)
**Kullanılan API'ler:**
- `GET /api/parent/my-children` - Çocuklarım listesi
- `GET /api/parent/child/{id}/today-status` - Günlük durum

**İzinler:** `parent.view_children`

#### 27. Academic Status (`/parent/academic`)
**Kullanılan API'ler:**
- `GET /api/parent/child/{id}/grades` - Notlar
- `GET /api/parent/child/{id}/homework` - Ödevler

**İzinler:** `parent.view_children`

#### 28. Schedule (`/parent/schedule`)
**Kullanılan API'ler:**
- `GET /api/parent/child/{id}/schedule` - Ders programı

**İzinler:** `parent.view_children`

#### 29. Parent Homework (`/parent/homework`)
**Kullanılan API'ler:**
- `GET /api/parent/child/{id}/homework` - Ödevler

**İzinler:** `parent.view_children`

#### 30. Parent Materials (`/parent/materials`)
**Kullanılan API'ler:**
- `GET /api/materials` - Materyaller

**İzinler:** `parent.view_children`

#### 31. Parent Attendance (`/parent/attendance`)
**Kullanılan API'ler:**
- `GET /api/attendance?student_id={id}` - Devamsızlık
- `GET /api/parent/child/{id}/attendance` - Çocuk devamsızlığı

**İzinler:** `parent.view_attendance`

#### 32. Parent Finances (`/parent/finances`)
**Kullanılan API'ler:**
- `GET /api/debts?student_id={id}` - Borçlar
- `GET /api/payments?student_id={id}` - Ödemeler
- `GET /api/receipts?student_id={id}` - Makbuzlar

**İzinler:** `parent.view_finances`

#### 33. Health (`/parent/health`)
**Kullanılan API'ler:**
- `GET /api/parent/child/{id}/health` - Sağlık bilgileri
- `POST /api/parent/child/{id}/excuse-request` - İzin talebi
- `POST /api/parent/child/{id}/medicine-request` - İlaç talebi

**İzinler:** `parent.view_children`

#### 34. Communication (`/parent/communication`)
**Kullanılan API'ler:**
- `GET /api/messages` - Mesajlar
- `GET /api/announcements` - Duyurular

**İzinler:** `parent.view_children`

#### 35. Chat (`/parent/chat`)
**Kullanılan API'ler:**
- `GET /api/messages` - Mesaj geçmişi
- `POST /api/messages` - Mesaj gönderme
- `GET /api/parent/my-children` - Çocuklarım

**İzinler:** `parent.view_children`

#### 36. Parent Announcements (`/parent/announcements`)
**Kullanılan API'ler:**
- `GET /api/announcements` - Duyurular
- `GET /api/announcements/{id}` - Duyuru detayı

**İzinler:** `parent.view_children`

#### 37. Activities (`/parent/activities`)
**Kullanılan API'ler:**
- `GET /api/clubs` - Kulüpler
- `GET /api/parent/child/{id}/activities` - Aktiviteler

**İzinler:** `parent.view_children`

#### 38. Parent Reports (`/parent/reports`)
**Kullanılan API'ler:**
- `GET /api/parent/child/{id}/reports` - Raporlar
- `GET /api/daily-reports?student_id={id}` - Günlük raporlar

**İzinler:** `parent.view_children`

### İletişim Bölümü

#### 39. Parent Notices (`/parent-notices`)
**Kullanılan API'ler:**
- `GET /api/parent-notices` - Veli talepleri
- `POST /api/parent-notices` - Talep oluşturma
- `PUT /api/parent-notices/{id}` - Talep güncelleme

**İzinler:** `students.read`, `students.write`

#### 40. Appointments (`/appointments`)
**Kullanılan API'ler:**
- `GET /api/appointments` - Randevular
- `POST /api/appointments` - Randevu oluşturma
- `PUT /api/appointments/{id}` - Randevu güncelleme

**İzinler:** `students.read`, `students.write`

#### 41. Announcements (`/announcements`)
**Kullanılan API'ler:**
- `GET /api/announcements` - Duyuru listesi
- `POST /api/announcements` - Duyuru oluşturma
- `GET /api/announcements/{id}` - Duyuru detayı
- `PUT /api/announcements/{id}` - Duyuru güncelleme
- `DELETE /api/announcements/{id}` - Duyuru silme
- `POST /api/announcements/{id}/send` - Duyuru gönderme

**İzinler:** `announcements.read`, `announcements.write`

#### 42. Announcement Detail (`/announcements/{id}`)
**Kullanılan API'ler:**
- `GET /api/announcements/{id}` - Duyuru detayı
- `GET /api/communications/broadcast-jobs/{id}/delivery-summary` - Teslimat özeti

**İzinler:** `announcements.read`

#### 43. Notifications (`/notifications`)
**Kullanılan API'ler:**
- `GET /api/communications/broadcast-jobs` - Broadcast işleri
- `GET /api/communications/delivery-reports` - Teslimat raporları

**İzinler:** `notification.read`

#### 44. Outbox (`/outbox`)
**Kullanılan API'ler:**
- `GET /api/communications/broadcast-jobs` - Broadcast işleri
- `GET /api/communications/broadcast-jobs/{id}` - İş detayı
- `PUT /api/communications/broadcast-jobs/{id}` - İş güncelleme
- `POST /api/communications/broadcast-jobs/{id}/send` - Gönderme
- `DELETE /api/communications/broadcast-jobs/{id}` - İptal

**İzinler:** `notification.read`, `notification.write`

#### 45. Outbox Detail (`/outbox/{id}`)
**Kullanılan API'ler:**
- `GET /api/communications/broadcast-jobs/{id}` - İş detayı
- `GET /api/communications/broadcast-jobs/{id}/delivery-summary` - Teslimat özeti
- `GET /api/communications/delivery-reports?broadcast_job_id={id}` - Teslimat raporları

**İzinler:** `notification.read`

#### 46. Templates (`/notifications/templates`)
**Kullanılan API'ler:**
- `GET /api/communications/message-templates` - Şablon listesi
- `POST /api/communications/message-templates` - Şablon oluşturma

**İzinler:** `notification.read`, `notification.write`

#### 47. Template Form (`/notifications/templates/{id}`)
**Kullanılan API'ler:**
- `GET /api/communications/message-templates/{id}` - Şablon detayı
- `PUT /api/communications/message-templates/{id}` - Şablon güncelleme
- `DELETE /api/communications/message-templates/{id}` - Şablon silme

**İzinler:** `notification.write`

### Operasyon Bölümü

#### 48. Transport (`/transport`)
**Kullanılan API'ler:**
- `GET /api/bus` - Servis listesi
- `POST /api/bus` - Servis oluşturma
- `GET /api/bus/{id}` - Servis detayı

**İzinler:** `students.read`, `students.write`

#### 49. Canteen (`/canteen`)
**Kullanılan API'ler:**
- `GET /api/canteen` - Kantin ürünleri
- `POST /api/canteen` - Ürün oluşturma
- `PUT /api/canteen/{id}` - Ürün güncelleme

**İzinler:** `canteen.read`, `canteen.write`

#### 50. Canteen Sales (`/canteen/sales`)
**Kullanılan API'ler:**
- `GET /api/canteen/sales` - Satış kayıtları
- `POST /api/canteen/sales` - Satış oluşturma

**İzinler:** `canteen.write`

#### 51. Card Balance (`/canteen/card-balance`)
**Kullanılan API'ler:**
- `GET /api/rfid-cards` - Kart bilgileri
- `POST /api/canteen/balance` - Bakiye yükleme

**İzinler:** `canteen.read`, `canteen.write`

#### 52. Canteen Receipt (`/canteen/receipt`)
**Kullanılan API'ler:**
- `GET /api/canteen/receipts` - Makbuzlar
- `GET /api/canteen/receipts/{id}` - Makbuz detayı

**İzinler:** `canteen.read`

### Finans Bölümü

#### 53. Debts (`/finance/debts`)
**Kullanılan API'ler:**
- `GET /api/debts` - Borç listesi (sayfalama, filtreleme ile)
- `GET /api/debts/{id}` - Borç detayı
- `POST /api/debts` - Borç oluşturma
- `PUT /api/debts/{id}` - Borç güncelleme
- `DELETE /api/debts/{id}` - Borç silme

**İzinler:** `finance.read`, `finance.write`, `debts.read`, `debts.write`

#### 54. Payments (`/finance/payments`)
**Kullanılan API'ler:**
- `GET /api/payments` - Ödeme listesi
- `POST /api/payments` - Ödeme oluşturma
- `GET /api/payments/{id}` - Ödeme detayı
- `PUT /api/payments/{id}` - Ödeme güncelleme
- `DELETE /api/payments/{id}` - Ödeme silme
- `POST /api/payments/{id}/cancel` - Ödeme iptali
- `GET /api/ai/payment-forecast` - AI ödeme tahmini

**İzinler:** `finance.read`, `finance.write`, `payments.read`, `payments.write`

#### 55. Payment Form (`/finance/payments/new`)
**Kullanılan API'ler:**
- `GET /api/debts` - Borç listesi
- `POST /api/payments` - Ödeme oluşturma

**İzinler:** `finance.write`, `payments.create`

#### 56. Student Payments (`/finance/students/{id}`)
**Kullanılan API'ler:**
- `GET /api/debts?student_id={id}` - Öğrenci borçları
- `GET /api/payments?student_id={id}` - Öğrenci ödemeleri
- `GET /api/receipts?student_id={id}` - Öğrenci makbuzları

**İzinler:** `finance.read`

#### 57. Expenses (`/finance/expenses`)
**Kullanılan API'ler:**
- `GET /api/expenses` - Gider listesi
- `POST /api/expenses` - Gider oluşturma
- `GET /api/expenses/{id}` - Gider detayı
- `PUT /api/expenses/{id}` - Gider güncelleme
- `DELETE /api/expenses/{id}` - Gider silme

**İzinler:** `finance.read`, `finance.write`

#### 58. Receipts (`/finance/receipts`)
**Kullanılan API'ler:**
- `GET /api/receipts` - Makbuz listesi
- `GET /api/receipts/{id}` - Makbuz detayı
- `GET /api/ai/payment-forecast` - AI finansal öngörü

**İzinler:** `finance.read`, `receipt.read`

#### 59. Receipt Print (`/finance/receipts/{id}`)
**Kullanılan API'ler:**
- `GET /api/receipts/{id}` - Makbuz detayı
- `GET /api/receipts/{id}/pdf` - PDF indir
- `GET /api/payments/finances/payments/{payment_id}/receipt-pdf` - Makbuz PDF

**İzinler:** `finance.read`

#### 60. Payment (`/payment`)
**Kullanılan API'ler:**
- `POST /api/payments/iyzico/initialize` - iyzico ödeme başlatma
- `POST /api/payments/iyzico/callback` - iyzico callback

**İzinler:** `payments.create`

### Analiz Bölümü

#### 61. Reports (`/reports`)
**Kullanılan API'ler:**
- `GET /api/dashboard/financial-summary` - Finansal özet
- `GET /api/dashboard/attendance-summary` - Yoklama özeti
- `GET /api/dashboard/reports` - Raporlar

**İzinler:** `report.read`

#### 62. AI Analytics (`/ai/analytics`)
**Kullanılan API'ler:**
- `GET /api/ai/insights-report` - AI öngörüler
- `GET /api/ai/students-overview` - Öğrenci analizi
- `GET /api/ai/attendance-analysis` - Devamsızlık analizi
- `GET /api/ai/payment-forecast` - Ödeme tahmini

**İzinler:** `ai.view`

### Sistem Bölümü

#### 63. RFID Cards (`/rfid-cards`)
**Kullanılan API'ler:**
- `GET /api/rfid-cards` - Kart listesi
- `POST /api/rfid-cards` - Kart oluşturma
- `PUT /api/rfid-cards/{id}` - Kart güncelleme
- `DELETE /api/rfid-cards/{id}` - Kart silme

**İzinler:** `settings.read`, `settings.write`

#### 64. Devices (`/devices`)
**Kullanılan API'ler:**
- `GET /api/devices` - Cihaz listesi
- `POST /api/devices` - Cihaz oluşturma
- `GET /api/devices/{id}` - Cihaz detayı
- `PUT /api/devices/{id}` - Cihaz güncelleme

**İzinler:** `settings.read`, `settings.write`

#### 65. Settings (`/settings`)
**Kullanılan API'ler:**
- `GET /api/settings` - Ayarlar
- `PUT /api/settings` - Ayar güncelleme

**İzinler:** `settings.read`, `settings.write`

#### 66. Security (`/security`)
**Kullanılan API'ler:**
- `GET /api/security` - Güvenlik ayarları
- `PUT /api/security` - Güvenlik güncelleme

**İzinler:** `settings.read`, `settings.write`

### Diğer Ekranlar

#### 67. Consents (`/consents`)
**Kullanılan API'ler:**
- `GET /api/consents` - İzin listesi
- `POST /api/consents` - İzin oluşturma

**İzinler:** `students.read`, `students.write`

#### 68. Guidance (`/guidance`)
**Kullanılan API'ler:**
- `GET /api/guidance` - Rehberlik kayıtları
- `POST /api/guidance` - Kayıt oluşturma

**İzinler:** `students.read`, `students.write`

#### 69. Health (`/health`)
**Kullanılan API'ler:**
- `GET /api/health` - Sağlık kayıtları
- `POST /api/health` - Kayıt oluşturma

**İzinler:** `students.read`, `students.write`

#### 70. Infirmary (`/infirmary`)
**Kullanılan API'ler:**
- `GET /api/infirmary` - Sağlık oda kayıtları
- `POST /api/infirmary` - Kayıt oluşturma

**İzinler:** `students.read`, `students.write`

#### 71. Inventory (`/inventory`)
**Kullanılan API'ler:**
- `GET /api/inventory` - Envanter listesi
- `POST /api/inventory` - Envanter oluşturma

**İzinler:** `settings.read`, `settings.write`

#### 72. Clubs (`/clubs`)
**Kullanılan API'ler:**
- `GET /api/clubs` - Kulüp listesi
- `POST /api/clubs` - Kulüp oluşturma

**İzinler:** `students.read`, `students.write`

#### 73. Surveys (`/surveys`)
**Kullanılan API'ler:**
- `GET /api/surveys` - Anket listesi
- `POST /api/surveys` - Anket oluşturma

**İzinler:** `students.read`, `students.write`

#### 74. Tutoring (`/tutoring`)
**Kullanılan API'ler:**
- `GET /api/tutoring` - Etüt kayıtları
- `POST /api/tutoring` - Kayıt oluşturma

**İzinler:** `students.read`, `students.write`

#### 75. Payroll (`/payroll`)
**Kullanılan API'ler:**
- `GET /api/payroll` - Maaş listesi
- `POST /api/payroll` - Maaş oluşturma

**İzinler:** `finance.read`, `finance.write`

#### 76. User Create (`/users/create`)
**Kullanılan API'ler:**
- `POST /api/users` - Kullanıcı oluşturma
- `GET /api/roles` - Roller

**İzinler:** `users.write`

#### 77. User Detail (`/users/{id}`)
**Kullanılan API'ler:**
- `GET /api/users/{id}` - Kullanıcı detayı
- `PUT /api/users/{id}` - Kullanıcı güncelleme
- `DELETE /api/users/{id}` - Kullanıcı silme

**İzinler:** `users.read`, `users.write`

#### 78. Staff Detail (`/staff/{id}`)
**Kullanılan API'ler:**
- `GET /api/staff/{id}` - Personel detayı
- `PUT /api/staff/{id}` - Personel güncelleme

**İzinler:** `users.read`, `users.write`

#### 79. Organization Detail (`/organizations/{id}`)
**Kullanılan API'ler:**
- `GET /api/organizations/{id}` - Kurum detayı
- `PUT /api/organizations/{id}` - Kurum güncelleme

**İzinler:** `org.read`, `org.write`

#### 80. Library Detail (`/library/{id}`)
**Kullanılan API'ler:**
- `GET /api/library/{id}` - Kütüphane detayı
- `PUT /api/library/{id}` - Kayıt güncelleme

**İzinler:** `students.read`, `students.write`

#### 81. Role Permissions (`/roles/{id}/permissions`)
**Kullanılan API'ler:**
- `GET /api/roles/{id}/permissions` - Rol yetkileri
- `POST /api/roles/{id}/permissions` - Yetki atama
- `DELETE /api/roles/{id}/permissions/{permission_id}` - Yetki kaldırma

**İzinler:** `users.write`

## Teknoloji Stack

### Backend
- **Framework**: FastAPI (Python)
- **Database**: PostgreSQL / SQLite
- **ORM**: SQLAlchemy
- **Authentication**: JWT
- **Payment Integration**: iyzico
- **Architecture**: Layered Architecture (Domain, Application, Infrastructure)

### Frontend
- **Framework**: React with TypeScript
- **UI Library**: Custom components
- **State Management**: React Context
- **HTTP Client**: Axios
- **Routing**: React Router

## İzin Sistemi

Sistem rol bazlı yetkilendirme (RBAC) kullanır. Temel izin modülleri:

- `dashboard.view` - Dashboard görüntüleme
- `org.read` / `org.write` - Kurum okuma/yazma
- `branch.read` / `branch.write` - Şube okuma/yazma
- `users.read` / `users.write` - Kullanıcı okuma/yazma
- `students.read` / `students.write` - Öğrenci okuma/yazma
- `students.import` / `students.export` - Öğrenci içe/dışa aktarma
- `parents.read` / `parents.write` - Veli okuma/yazma
- `classes.read` / `classes.write` - Sınıf okuma/yazma
- `attendance.read` / `attendance.write` / `attendance.take` - Yoklama işlemleri
- `finance.read` / `finance.write` - Finans işlemleri
- `debts.read` / `debts.write` - Borç işlemleri
- `payments.read` / `payments.write` / `payments.create` / `payments.update` / `payments.delete` - Ödeme işlemleri
- `announcements.read` / `announcements.write` - Duyuru işlemleri
- `notification.read` / `notification.write` - Bildirim işlemleri
- `canteen.read` / `canteen.write` - Kantin işlemleri
- `settings.read` / `settings.write` - Ayar işlemleri
- `parent.view_children` - Veli çocuk görüntüleme
- `parent.view_attendance` - Veli yoklama görüntüleme
- `parent.view_finances` - Veli finans görüntüleme

## Özel Özellikler

### Multi-Tenancy
- Organization bazlı veri izolasyonu
- Branch bazlı erişim kontrolü
- Tenant context üzerinden veri filtreleme

### Güvenlik
- JWT token authentication
- Refresh token mekanizması
- Rate limiting
- Password reset flow
- Login attempt tracking
- Audit logging

### İletişim
- Multi-channel notifications (SMS, Email, WhatsApp)
- Message templates
- Broadcast jobs
- Delivery reports
- Parent-teacher chat

### Finans
- Debt management
- Payment processing
- iyzico integration
- Receipt generation (PDF)
- Installment plans
- Expense tracking

### Operasyon
- RFID card management
- Device management
- Attendance kiosk integration
- Canteen operations
- Transport management

Bu doküman SCS360 projesinin tüm bileşenlerini kapsayan kapsamlı bir referans olarak kullanılabilir.