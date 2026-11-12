Backend debt create accepts optional request_id UUID: same actor/school/student/type/amount/due/description replays existing debt, changed/deleted/colliding request rejected409; organization lock and primary key enforce uniqueness. SQLite+PostgreSQL30 targeted regression PASS, final error-response adjustment6 PASS (overlapping tests, not36 unique). Android nonce/body integration remains OPEN. Android source unchanged; last signed debug APK600e36ac remains current.

Native invoice draft UI: six targeted UI/scope tests PASS5m41s, same-source debug APK/signature PASS2m17s. Bounded native scrollable form, blank amount/date/student defaults, 48dp actions and read-only controls; actual portal dialog closes on workspace switch. Previous AlertDialog idling scenario now passes with replacement form. Backend submission DTO, create idempotency, write-authorized student options and full feature acceptance remain OPEN.

Native finance presentation scope: 14/14 affected scope/cash/receipt tests PASS1m53s; same-source debug APK/signature PASS2m46s. Actor/organization/workspace/branch/role/permission/logout changes reset finance dialogs, while refresh preserves drafts. Receipt stale-session content hides. Prior full93Android/906backend checkpoint is historical; current full Android not rerun. Invoice AlertDialog test idling remains an explicit UI test limitation.

<!-- native-receipt-20261112:start -->
Current automated acceptance: backend906 unique PASS/2 intentionally database-specific SKIP across isolated SQLite and PostgreSQL runs; Android93/93PASS; actual Kotlin/FastAPI receipt/payment linking, lost-ACK replay and server PDF PASS. Same-source signed debug APK ready locally. Frontend unchanged: prior344PASS remains applicable. Physical A26/IME/Android print service, real provider/store acceptance and unfinished native feature parity remain open.
<!-- native-receipt-20261112:end -->

<!-- native-cash-20261112:start -->
Native cash/transfer ledger checkpoint: Android full90/90 PASS (16m49s); real Kotlin/FastAPI temporary SQLite lost-ACK replay and partial payments1 PASS/1PGdeselected (107.57s); backend integrity12 PASS/12PGdeselected. Same-source debug APK/signature PASS2m43s. Physical A26, actual provider/store acceptance, other finance rows/documents and portal-local context lifecycle remain open.
<!-- native-cash-20261112:end -->

<!-- native-finance-20261112:start -->
Native recorded finance summary accepted: full Android 82/82 PASS (17m48s), real Kotlin/FastAPI temporary SQLite acceptance 1 PASS/1 PostgreSQL deselected (115.55s), same-source debug APK/signature PASS (2m48s). Debt/payment row mutations, parent flows, physical A26 and actual provider/store acceptance remain open.
<!-- native-finance-20261112:end -->

# SCS360 — Okul Yönetim Sistemi

> Native registry kabulü (12 Kasım): tam Android74/74PASS,0skip13m5s; ardından yalnız test kaydırma/görsel kontrolleri güçlendirildi,10/10UI takip testi PASS. Aynı uygulama kaynağı gerçek FastAPI/geçiciSQLite ile CRUD,102öğrenci sayfalama,403/404/409/422, minimal yazma rolü, klinik not korunması ve Room sentinel aynılığı testini geçti. Üç gerçek pencere qualifierında sistem font2 ve48dp hedefler kontrol edildi; üç native PNG incelendi. Sınıf kaydetme rasteri senkron tutarsızlığından kanıta alınmadı; tam viewport geometri kontrolü geçti. Debug APK imzası doğrulandı; SHA256 79c6a7c512e7071453146e2c3087996955341eedef51c4517c745dfc8d24a8a1. Veli ilişkileri, özel rol native login/görünümü, diğer native işlemler ve gerçek cihaz/HTTPS/sağlayıcı/mağaza kabulü açık.


> Önceki native yoklama kabulü: gerçek FastAPI/geçiciSQLite/Kotlin HTTP senaryosu PASS; tam Android58/58PASS,0skip5m26s. Sonrasında yalnız test görsel/scroll çağrıları değişti; native render testi3pencere/2xfont ile ayrıca PASS ve görseller incelendi. Uygulama kaynağı değişmeden debug APK üretildi ve imza doğrulandı; SHA256 64f8121912246a1fc3ec82626cb20dfa24b4859389e506f81229f8a1367aa3ca. Aşağıdaki51test/APK önceki checkpointtir. Tüm native eşitleme, aylık yoklama, gerçek A26/HTTPS/ödeme kabulü tamamlanmadı.

Anaokulu, kreş, etüt ve kurs merkezleri için franchise uyumlu, çoklu şube destekli yönetim platformu.

## Windows'ta yerel çalıştırma

Mevcut bağımlılıklar ve `backend/.env` hazırken proje kökünden:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start-local.ps1
```

Arayüz: http://127.0.0.1:5173 — API belgeleri: http://127.0.0.1:8000/api/docs.
Betik servisleri arka planda, yalnız bu bilgisayardan erişilecek şekilde başlatır; API hazır olma ve arayüz proxy kontrollerini yapar. Mevcut SCS360 servislerini tekrar başlatmaz, başka uygulamaların portlarını kapatmaz. Loglar `.codex-build/local` içindedir. Veritabanı migration'ları güncel olmalıdır; betik örnek kullanıcı/veri oluşturmaz.

Durdurmak için:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/stop-local.ps1
```

Yalnız bu betiğin başlattığı, kimliği ve başlangıç zamanı doğrulanan süreçler durdurulur. Backend kodu veya ortam ayarları değiştiğinde durdurup yeniden başlatın.

## Teknoloji Stack

| Katman | Teknoloji |
|--------|-----------|
| Backend | Python, FastAPI, SQLAlchemy 2.x, Alembic, PostgreSQL |
| Frontend | React, TypeScript, Vite, Axios, Zustand |
| DevOps | Docker, Docker Compose, Nginx, GitHub Actions |

## Hızlı Başlangıç

### Gereksinimler
- Docker & Docker Compose
- Node.js 20+ (yerel frontend geliştirme)
- Python 3.12+ (yerel backend geliştirme)

### Docker ile Çalıştırma

```bash
cp .env.compose.example .env
cp backend/.env.production.example backend/.env
# backend/.env içindeki JWT_SECRET_KEY değerini benzersiz ve en az 32 karakter yapın.
docker compose up --build -d
```

Güvenli bir anahtar üretmek için: `python -c "import secrets; print(secrets.token_urlsafe(48))"`.
Production/staging ortamında `APP_ENV=production` kullanılır; zayıf/örnek JWT anahtarıyla uygulama
başlamayı reddeder. Gerçek sırları repository'ye eklemeyin.

| Servis | URL |
|--------|-----|
| Uygulama | http://localhost |
| API | http://localhost/api |
| API Docs | http://localhost/api/docs |
| Health | http://localhost/health |

### İsteğe Bağlı Demo Giriş (yalnız yerel geliştirme)

Demo verisi varsayılan olarak kapalıdır. Yalnız yerel ortamda `.env` içindeki
`SEED_DEMO_DATA=true` seçeneğiyle etkinleştirin; production'da etkinleştirmeyin.

| Alan | Değer |
|------|-------|
| E-posta | admin@demo.com |
| Şifre | Admin123* |
| Rol | Super Admin |

### Yerel Geliştirme

**Backend:**
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env
alembic upgrade head
python scripts/seed_demo_data.py
uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm ci
cp .env.example .env
npm run dev
```

### Doğrulama

```bash
# Backend
cd backend
ruff check app tests
black --check app tests
mypy app --ignore-missing-imports
pytest -v
pip-audit -r requirements.txt

# Frontend
cd frontend
npm ci
npm run lint
npm test
npm audit --audit-level=high
npm run build
```

**Worker:**
```bash
cd backend
python -m app.infrastructure.notifications.outbox_worker
```

## Proje Yapısı

```
school-management/
├── backend/          # FastAPI (Clean Architecture)
├── frontend/         # React + Material Dashboard
├── nginx/            # Reverse proxy
├── .github/workflows/# CI/CD
└── docker-compose.yml
```

## Rollback Planı (Production)

Bu repository'de production deploy hedefi ve `docker-compose.prod.yml` belirtilmemiştir;
mevcut deploy workflow'ları yalnız iskelet/placeholder durumundadır. Production açılmadan önce:

1. immutable image tag ve önceki sürüm tag'i kaydedilmeli,
2. migration öncesi doğrulanmış yedek alınmalı,
3. yalnız reversible migration için `alembic downgrade -1` denenmeli,
4. `/health`, `/ready`, login, öğrenci listesi ve dashboard smoke testi çalıştırılmalı,
5. başarısızlıkta önceki image tag'e dönülüp incident kaydı açılmalıdır.

## Branch Stratejisi

- `main` → production (manuel onaylı deploy)
- `develop` → staging
- `feature/*`, `bugfix/*`, `hotfix/*`

## Lisans

Özel yazılım — tüm hakları saklıdır.
