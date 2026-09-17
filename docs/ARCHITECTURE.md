# EduPanel — Mimari Dokümantasyon

Anaokulu, kreş, etüt ve kurs merkezleri için franchise uyumlu, çoklu şube destekli yönetim platformu.

---

## 1. Proje Mimarisi Özeti

```
┌─────────────────────────────────────────────────────────────────┐
│                        Nginx Reverse Proxy                       │
│              / → Frontend (React)  |  /api → FastAPI             │
└─────────────────────────────────────────────────────────────────┘
         │                                    │
         ▼                                    ▼
┌─────────────────┐              ┌──────────────────────────────┐
│    Frontend     │   REST/JWT   │         Backend (FastAPI)     │
│ Material Dash.  │◄────────────►│  Clean Architecture + DDD     │
│ Feature-based   │              │  PostgreSQL + SQLAlchemy 2.x    │
└─────────────────┘              └──────────────────────────────┘
                                              │
                         ┌────────────────────┼────────────────────┐
                         ▼                    ▼                    ▼
                   PostgreSQL            Outbox Worker         File Storage
                   (multi-tenant)        (Email/SMS/WA)        (uploads/)
```

**Temel prensipler:**
- Organization bazlı multi-tenancy, branch bazlı veri izolasyonu
- RBAC + permission bazlı erişim (backend'de zorunlu, frontend'de UX)
- Finansal işlemler transaction içinde, Decimal/NUMERIC, audit log
- Bildirimler Outbox Pattern ile asenkron gönderim
- Soft delete, structured logging, merkezi exception handling

---

## 2. Katman Mimarisi (Clean Architecture + DDD + Hexagonal)

### API / Presentation Layer (`app/routers/`)
- HTTP request/response, routing, schema validation
- İş kuralı içermez; use case/service çağırır
- Standart response: `{ success, message, data }`

### Application Layer (`app/application/`)
- Use case servisleri: `AuthService`, ileride `CreateStudentUseCase` vb.
- DTO/Schema: Pydantic modelleri
- Orchestration: transaction sınırları, birden fazla domain servisini koordine eder

### Domain Layer (`app/domain/`)
- İş kuralları: `DebtCalculator`, `ClassCapacityChecker`
- Value objects: `Money`
- Framework bağımsız; saf Python

### Infrastructure Layer (`app/infrastructure/`)
- SQLAlchemy modelleri ve repository implementasyonları
- Adapter'lar: Email, SMS, WhatsApp, PDF, CSV/Excel export, file storage
- Outbox worker

### Core Layer (`app/core/`)
- Config, security (JWT, bcrypt), database session
- Middleware, exception handlers, tenant resolver, permissions, rate limit

### Hexagonal (Ports & Adapters)
- **Port:** `NotificationProvider` (base.py), `FileStorage` (storage_base.py)
- **Adapter:** `SmtpEmailProvider`, `NetgsmSmsProvider`, `MetaWhatsAppProvider`, `LocalFileStorage`

---

## 3. Veritabanı İlişki Diyagramı (Metinsel)

```
organizations (1) ──< (N) branches
organizations (1) ──< (N) users
organizations (1) ──< (N) roles (org-specific override)
organizations (1) ──< (N) students, parents, classes, debts, ...

branches (1) ──< (N) classes
branches (1) ──< (N) students
branches (N) >──< (N) users  [user_branches]

classes (1) ──< (N) students
classes (N) >──< (N) users  [class_teachers — öğretmen ataması]

students (N) >──< (N) parents  [student_parents — M:N]
students (1) ──< (N) student_files
students (1) ──< (N) attendance_records
students (1) ──< (N) debts

debts (1) ──< (N) payments
payments (1) ──< (1) receipts

roles (N) >──< (N) permissions  [role_permissions]
users (N) >──< (N) roles  [user_roles]

announcements (1) ──< (N) announcement_recipients
notification_jobs (1) ──< (N) notification_recipients

users (1) ──< (N) refresh_tokens, password_reset_tokens, login_attempts
organizations (1) ──< (N) integration_settings, app_settings, audit_logs
```

**İzolasyon kuralları:**
- Super Admin: `organization_id IS NULL`, tüm veriye erişim
- Kurum Admini: `organization_id` filtresi
- Şube Yetkilisi: `branch_id IN user_branches`
- Öğretmen: `class_id IN class_teachers` → sadece kendi sınıf öğrencileri

---

## 4–9. PostgreSQL Şeması

Tam SQL dosyaları:
- `backend/sql/001_schema.sql` — ENUM, tablolar, FK, index, trigger
- `backend/sql/002_seed.sql` — roller, izinler, demo kurum/şube/sınıf, admin

**ENUM tipleri:** user_status, student_status, gender_type, parent_relation_type, attendance_status, debt_status, debt_type, payment_method, receipt_status, file_category, notification_channel, notification_status, announcement_audience, announcement_status, integration_provider, audit_action

**Trigger'lar:**
- `set_updated_at()` — tüm ana tablolarda `updated_at` otomatik güncelleme
- `generate_receipt_number()` — `RCP-YYYYMMDD-000001` formatında benzersiz makbuz no

**Seed:** `python scripts/seed_demo_data.py` — 25 öğrenci, veli, borç, ödeme, devamsızlık

---

## 10. API Endpoint Listesi

| Modül | Endpoint | Method |
|-------|----------|--------|
| **Auth** | `/api/auth/login` | POST |
| | `/api/auth/refresh` | POST |
| | `/api/auth/logout` | POST |
| | `/api/auth/me` | GET |
| | `/api/auth/forgot-password` | POST |
| | `/api/auth/reset-password` | POST |
| **Users** | `/api/users` | GET, POST |
| | `/api/users/{id}` | GET, PUT, DELETE |
| | `/api/users/{id}/roles` | POST |
| | `/api/users/{id}/branches` | POST |
| **Organizations** | `/api/organizations` | GET, POST |
| | `/api/organizations/{id}` | GET, PUT, DELETE |
| **Branches** | `/api/branches` | GET, POST |
| | `/api/branches/{id}` | GET, PUT, DELETE |
| **Students** | `/api/students` | GET, POST |
| | `/api/students/{id}` | GET, PUT, DELETE |
| | `/api/students/{id}/files` | GET, POST |
| | `/api/students/{id}/files/{file_id}` | DELETE |
| | `/api/students/{id}/parents` | GET, POST |
| | `/api/students/{id}/payments` | GET |
| | `/api/students/{id}/attendance` | GET |
| **Classes** | `/api/classes` | GET, POST |
| | `/api/classes/{id}` | GET, PUT, DELETE |
| | `/api/classes/{id}/students` | POST |
| | `/api/classes/{id}/students/{student_id}` | DELETE |
| | `/api/classes/{id}/occupancy` | GET |
| **Attendance** | `/api/attendance` | GET, POST |
| | `/api/attendance/bulk` | POST |
| | `/api/attendance/{id}` | PUT, DELETE |
| | `/api/attendance/reports/monthly` | GET |
| **Debts** | `/api/debts` | GET, POST |
| | `/api/debts/{id}` | GET, PUT, DELETE |
| | `/api/debts/{id}/recalculate-status` | POST |
| **Payments** | `/api/payments` | GET, POST |
| | `/api/payments/{id}` | GET |
| | `/api/payments/{id}/cancel` | POST |
| **Receipts** | `/api/receipts/{id}` | GET |
| | `/api/receipts/{id}/pdf` | GET |
| | `/api/receipts/{id}/print` | GET |
| | `/api/receipts/{id}/send-email` | POST |
| | `/api/receipts/{id}/send-sms` | POST |
| | `/api/receipts/{id}/send-whatsapp` | POST |
| **Announcements** | `/api/announcements` | GET, POST |
| | `/api/announcements/{id}` | GET, PUT, DELETE |
| | `/api/announcements/{id}/send` | POST |
| **Notifications** | `/api/notifications` | GET |
| | `/api/notifications/send` | POST |
| | `/api/notifications/{id}` | GET |
| | `/api/notifications/{id}/retry` | POST |
| | `/api/notifications/templates` | GET, POST |
| | `/api/notifications/templates/{id}` | PUT |
| **Reports** | `/api/reports/monthly-payments` | GET |
| | `/api/reports/debts` | GET |
| | `/api/reports/overdue-debts` | GET |
| | `/api/reports/attendance` | GET |
| | `/api/reports/class-occupancy` | GET |
| | `/api/reports/branch-performance` | GET |
| | `/api/reports/export/csv` | GET |
| | `/api/reports/export/excel` | GET |
| **Dashboard** | `/api/dashboard/summary` | GET |
| | `/api/dashboard/charts` | GET |
| **Settings** | `/api/settings` | GET, PUT |
| | `/api/settings/integrations` | GET, PUT |
| **Health** | `/health`, `/ready` | GET |

---

## 11. Frontend Sayfa Listesi

| Modül | Sayfa | Route |
|-------|-------|-------|
| Auth | Giriş | `/authentication/sign-in` |
| | Şifremi Unuttum | `/authentication/forgot-password` |
| | Şifre Sıfırla | `/authentication/reset-password` |
| | 403 / 404 | `/403`, `*` |
| Dashboard | Rol bazlı özet | `/dashboard` |
| Kurum | Liste / Ekle / Düzenle | `/organizations` |
| Şube | Liste / Ekle / Düzenle / Detay | `/branches` |
| Kullanıcı | Liste / Ekle / Düzenle / Rol matrix | `/users` |
| Öğrenci | Liste / Ekle / Düzenle / Detay | `/students` |
| Sınıf | Liste / Doluluk / Atama | `/classes` |
| Devamsızlık | Günlük / Toplu / Rapor | `/attendance` |
| Finans | Borçlar / Tahsilatlar / Makbuzlar | `/finance/*` |
| Duyuru | Liste / Oluştur / Gönder | `/announcements` |
| Bildirim | Log / Şablon / Provider | `/notifications` |
| Rapor | Hub + export | `/reports` |
| Ayarlar | Genel / SMTP / SMS / WA | `/settings` |

---

## 12. Creative Tim Material Dashboard Entegrasyon Planı

1. **Klonlama:** `material-dashboard-react` → `frontend/` (mevcut)
2. **Demo temizliği:** RTL, billing, notifications demo route'ları kaldırıldı
3. **Korunan yapı:** `examples/Sidenav`, `DashboardLayout`, `MDBox`, `MDInput`, `DataTable`, tema
4. **Yeni yapı:** `features/*` modülleri, `store/authStore`, `routes/sidenavRoutes`
5. **Auth:** Template sign-in sayfası `useAuthStore` ile bağlandı
6. **Sidebar:** Permission bazlı filtreleme (`hasAnyPermission`)
7. **API:** Axios interceptor + refresh token rotation
8. **TypeScript:** Aşamalı geçiş; şu an JS + PropTypes, interface dosyaları eklenebilir

---

## 13. CI/CD Pipeline Planı

| Workflow | Tetikleyici | Adımlar |
|----------|-------------|---------|
| `backend-ci.yml` | PR, push | Ruff, Black, Mypy, Pytest, coverage |
| `frontend-ci.yml` | PR, push | npm ci, ESLint, Prettier, build, Vitest |
| `docker-build.yml` | PR, push main/develop | Backend + frontend image build, compose validate |
| `deploy-staging.yml` | push `develop` | Migration, deploy, health check |
| `deploy-production.yml` | push `main` | Manuel approval, backup, migration, deploy, rollback notu |

**Branch stratejisi:** `main` (prod), `develop` (staging), `feature/*`, `bugfix/*`, `hotfix/*`

---

## 14. Docker ve Deployment Planı

**Servisler:** db (PostgreSQL 16), backend (uvicorn), worker (outbox), frontend (nginx static), nginx (reverse proxy)

**Volume'lar:** `postgres_data`, `upload_data`

**Nginx:** `/api` → backend:8000, `/` → frontend:80, gzip, cache headers

**Health:** `/health` (liveness), `/ready` (DB bağlantısı)

**Rollback:** Önceki image tag, `alembic downgrade -1` (reversible migration), smoke test

---

## 15. Güvenlik Planı

| Alan | Uygulama |
|------|----------|
| Kimlik doğrulama | JWT access + refresh token rotation |
| Şifre | bcrypt hash |
| Yetkilendirme | RBAC + permission + org/branch scope |
| API | Rate limiting (login 5/dk), CORS whitelist |
| Veri | SQLAlchemy parametreli sorgular, soft delete |
| Dosya | MIME/boyut kontrolü, private path, yetki kontrolü |
| Log | Hassas veri maskelenir |
| Finans | Transaction, audit log, iptal ters kayıt |
| Secret | `.env` / integration_settings JSONB |

---

## 16. Bildirim Mimarisi

```
[Use Case] ──transaction──► [DB: payment/receipt/announcement]
                │
                └──► [notification_jobs: PENDING]
                              │
                    [outbox_worker] ──► [dispatcher]
                              │              │
                              │    ┌─────────┼─────────┐
                              │    ▼         ▼         ▼
                              │  Email    SMS    WhatsApp
                              │  (SMTP)  (Netgsm)  (Meta)
                              ▼
                    [notification_recipients: SENT/FAILED]
                    retry_count++, max_retries=3
```

**Adapter Pattern:** `app/infrastructure/notifications/base.py` → provider implementasyonları

**Senaryolar:** Ödeme sonrası, duyuru, borç hatırlatma, geciken borç (scheduled job)

---

## 17. Geliştirme Sırası

1. ✅ Proje mimarisi ve klasör yapısı
2. ✅ PostgreSQL şema + Alembic + seed
3. ✅ Backend core (config, security, middleware, tenant)
4. ✅ Auth + RBAC + organization/branch isolation
5. ✅ Öğrenci, veli, sınıf, devamsızlık modülleri
6. ✅ Borç, tahsilat, makbuz modülleri
7. ✅ Bildirim outbox + adapter'lar
8. ✅ Duyuru, rapor, dashboard API
9. ✅ Frontend template entegrasyonu + auth + route guard
10. ✅ Liste sayfaları (generic createListPage)
11. 🔄 Dashboard API entegrasyonu, detay formları, PDF/export
12. 🔄 Test coverage genişletme
13. 🔄 Production hardening

---

## Klasör Yapısı

```
school-management/
├── backend/
│   ├── app/
│   │   ├── core/
│   │   ├── domain/
│   │   ├── application/
│   │   ├── infrastructure/
│   │   └── routers/
│   ├── alembic/
│   ├── sql/
│   ├── scripts/
│   └── tests/
├── frontend/
│   └── src/features/
├── nginx/
├── docs/
└── .github/workflows/
```
