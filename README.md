# SCS360 — Okul Yönetim Sistemi

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
