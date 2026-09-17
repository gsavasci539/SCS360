# Yönetici Özeti

İnceleme tarihi: **2026-06-24**. Öncelik: güvenlik > veri bütünlüğü > geriye dönük
uyumluluk > test edilebilirlik > performans > kod kalitesi > dokümantasyon.

Repository; FastAPI + SQLAlchemy/Alembic/PostgreSQL backend, React/Vite/Zustand frontend,
Nginx reverse proxy, Docker Compose ve GitHub Actions katmanlarından oluşuyor. Çalışan backend
yolu `app/main.py` → birleşik router'lar → `app/infrastructure/models/models.py` şeklinde.
`app/services`, `app/repositories`, `app/domain/entities` ve birçok tekil router aktif uygulamaya
bağlı değil; eski mimariyle yeni birleşik katman aynı repository'de birlikte duruyor.

İlk beş kritik bulgu:

1. **Kritik / P0 — Sır sızıntısı:** uzak PostgreSQL kullanıcı/parolası hem config hem Compose'a
   gömülüydü. Koddan kaldırıldı. İlgili DB parolası ve erişim anahtarları altyapıda ayrıca
   **derhal döndürülmelidir**; git geçmişinden silme ihtiyacı geçmiş doğrulanamadığı için devam eder.
2. **Kritik / P0 — Tenant IDOR:** ödeme, makbuz, duyuru, bildirim, rapor export, kullanıcı rol/şube
   atama ve öğrenci/sınıf oluşturma yollarında yalnız nesne ID'siyle başka tenant verisine erişim
   mümkündü. Aktif endpoint'ler merkezi tenant filtresine bağlandı.
3. **Yüksek / P1 — Savunmasız bağımlılıklar:** başlangıçta `pip-audit`, 6 pakette 24 bilinen
   açık bildirdi. FastAPI/Starlette, python-jose, python-multipart, Jinja2 ve dev araçları uyumlu
   sürümlere yükseltildi; runtime taraması artık açık bulmuyor.
4. **Yüksek / P1 — Auth yaşam döngüsü:** refresh token tekrar kullanımı aileyi iptal etmiyor,
   eşzamanlı rotation yarışabiliyor ve parola sıfırlama aktif oturumları kapatmıyordu. Satır kilidi,
   aile iptali ve reset sonrası session revocation eklendi.
5. **Yüksek / P1 — Test/CI güvenilirliği:** integration testleri DB migrate/fixture olmadan uzak
   veya mevcut DB'ye bağlanıyordu; deploy workflow'ları sadece `echo` placeholder. CI migration ve
   dependency audit eklendi; tam transaction-isolated test DB hâlâ sonraki sprint işidir.

## Karar Özeti

### Hemen yapılmalı

- Sızmış PostgreSQL parolasını sağlayıcıda döndür; eski kullanıcıyı iptal et; bağlantı loglarını incele.
- Production `.env` içine benzersiz JWT anahtarı ve gerçek DB URL'si koy; `APP_ENV=production` ile
  fail-closed başlangıcı doğrula.
- Uygulanan tenant yamalarını staging'de iki farklı organizasyon ve iki farklı şubeyle negatif test et.
- `frontend/dist/**` dosyalarını elle değiştirme; build pipeline'dan yeniden üret.
- Deploy workflow'ları gerçek olmadığı için production deploy'u otomatik kabul etme.

### Sonraki sprint

- Refresh token'ı JavaScript erişimli localStorage'dan HttpOnly/Secure/SameSite cookie'ye aşamalı taşı.
- Integration setting sırlarını KMS/Vault/envelope encryption ile şifrele.
- PostgreSQL test container + her test için rollback fixture kur.
- Eski/ölü katmanları import analizi ve iki release gözleminden sonra kaldır.
- Gitleaks/Trivy/Dependabot veya eşdeğer secret/container taramalarını zorunlu CI gate yap.

### Refactor fırsatı

- Büyük `core_modules.py` ve `dashboard_reports.py` dosyalarını bounded-context router/service'lerine böl.
- Pydantic `dict` body'leri typed schema'lara taşı.
- Liste/bulk endpoint'lerde N+1 ve döngü içi sorguları toplu sorgulara dönüştür.
- Marka adını `EduPanel` / `Okul360` arasında tekleştir.

## Dosya Envanteri ve Modül Analizi

```text
SchoolManagement-master/
├── .github/workflows/
│   ├── backend-ci.yml
│   ├── frontend-ci.yml
│   ├── docker-build.yml
│   ├── deploy-staging.yml
│   └── deploy-production.yml
├── backend/
│   ├── app/
│   │   ├── application/
│   │   │   ├── schemas/
│   │   │   └── services/auth_service.py
│   │   ├── core/
│   │   │   ├── config.py, database.py, security.py
│   │   │   ├── dependencies.py, tenant.py, permissions.py
│   │   │   └── middleware.py, rate_limit.py, responses.py
│   │   ├── domain/
│   │   │   ├── entities/            # eski katman adayı
│   │   │   └── services/            # saf domain kuralları aktif
│   │   ├── infrastructure/
│   │   │   ├── models/models.py     # aktif ORM modeli
│   │   │   ├── repositories/base.py
│   │   │   ├── notifications/
│   │   │   ├── pdf/, reports/
│   │   │   └── storage/
│   │   ├── repositories/            # muhtemel eski katman
│   │   ├── routers/
│   │   │   ├── auth.py, organizations.py, users.py
│   │   │   ├── admin_crud.py, core_modules.py
│   │   │   ├── dashboard_reports.py, files_receipts.py
│   │   │   └── diğerleri            # main.py'ye bağlı değil
│   │   ├── services/                # muhtemel eski katman
│   │   └── main.py
│   ├── alembic/versions/
│   ├── tests/unit/, tests/integration/
│   ├── Dockerfile, .dockerignore
│   ├── requirements.txt, requirements-dev.txt
│   └── pyproject.toml, pytest.ini
├── frontend/
│   ├── src/
│   │   ├── App.tsx, main.tsx
│   │   ├── lib/api.ts, stores/auth.ts, routes/Guards.tsx
│   │   ├── config/navigation.tsx, config/resources.ts
│   │   ├── features/, components/, test/
│   │   └── styles/global.css         # tasarım varlığı
│   ├── public/                       # belirtilmemiş
│   ├── dist/                         # generated artifact
│   ├── package.json, package-lock.json
│   └── vite.config.ts, Dockerfile, nginx.conf
├── database/schema.sql, database/seed.sql
├── docs/
├── nginx/default.conf
├── docker-compose.yml
└── README.md
```

| Yol | Tür | Katman | Amaç | Ana bağımlılıklar | Risk | Durum |
|---|---|---|---|---|---|---|
| `backend/app/main.py` | Python | giriş | Middleware/router kaydı | FastAPI, SlowAPI | orta | aktif |
| `backend/app/core/config.py` | Python | config | Env ve güvenlik doğrulama | pydantic-settings | yüksek | aktif |
| `backend/app/core/database.py` | Python | veri | Engine/session/request transaction | SQLAlchemy, asyncpg | yüksek | aktif |
| `backend/app/core/security.py` | Python | güvenlik | bcrypt/JWT/token hash | python-jose, passlib | yüksek | aktif |
| `backend/app/core/dependencies.py` | Python | auth | Kullanıcı ve tenant context | FastAPI, ORM | yüksek | aktif |
| `backend/app/core/tenant.py` | Python | authz | Org/şube/izin kararları | UUID | yüksek | aktif |
| `backend/app/infrastructure/repositories/base.py` | Python | veri/authz | Merkezi tenant filtreleme | SQLAlchemy | kritik | aktif |
| `backend/app/application/services/auth_service.py` | Python | uygulama | Login/refresh/logout/reset | ORM, security | kritik | aktif |
| `backend/app/services/auth_service.py` | Python | eski uygulama | Eski auth taslağı | artık olmayan security API | yüksek | muhtemel ölü kod |
| `backend/app/infrastructure/models/models.py` | Python | ORM | Aktif DB modeli | SQLAlchemy/PostgreSQL | yüksek | aktif |
| `backend/app/domain/entities/**` | Python | eski ORM/domain | Paralel model katmanı | SQLAlchemy | orta | muhtemel ölü kod |
| `backend/app/repositories/**` | Python | eski veri | Paralel repository katmanı | eski entity'ler | orta | muhtemel ölü kod |
| `backend/app/routers/auth.py` | Python | API | Auth endpoint'leri/rate limit | AuthService | yüksek | aktif |
| `backend/app/routers/core_modules.py` | Python | API | Öğrenci/sınıf/yoklama/finans | ORM, BaseRepository | kritik | aktif |
| `backend/app/routers/dashboard_reports.py` | Python | API | Dashboard/report/duyuru | ORM, exporters | kritik | aktif |
| `backend/app/routers/files_receipts.py` | Python | API | Upload/makbuz/iletişim | storage, PDF | yüksek | aktif |
| `backend/app/routers/students.py` ve benzerleri | Python | eski API | Paralel endpoint'ler | eski repo/entity | yüksek | muhtemel ölü kod |
| `backend/alembic/versions/**` | Python | migration | DB şeması/seed | Alembic | yüksek | aktif |
| `backend/sql/**`, `database/**` | SQL | bootstrap | Alternatif şema/seed kopyaları | PostgreSQL | yüksek | doğrulama gerekli |
| `backend/tests/conftest.py` | Python | test | ASGI client/DB availability | pytest/httpx | yüksek | aktif |
| `frontend/src/lib/api.ts` | TypeScript | istemci veri | Axios/token refresh | axios, Zustand | yüksek | aktif |
| `frontend/src/stores/auth.ts` | TypeScript | state | localStorage auth session | Zustand persist | yüksek | aktif |
| `frontend/src/App.tsx` | TSX | routing | Uygulama route ağacı | React Router | orta | aktif |
| `frontend/src/config/**` | TSX/TS | UI config | Menü/kaynak metadata | React/lucide | orta | aktif |
| `frontend/vite.config.ts` | TypeScript | build/dev | Vite chunks ve dev proxy | Vite | yüksek | aktif |
| `frontend/package*.json` | JSON | dependency | npm lock ve scriptler | npm | yüksek | aktif |
| `frontend/dist/**` | generated | build | Derlenmiş frontend | Vite | orta | doğrulama gerekli; elle düzenlenmemeli |
| `frontend/src/styles/**` | CSS | tasarım | Görsel tema | CSS | korunacak | tasarım varlığı, değiştirilmemeli |
| `frontend/public/**`, görseller/ikonlar | asset | tasarım | Statik UI | belirtilmemiş | korunacak | tasarım varlığı, değiştirilmemeli |
| `docker-compose.yml` | YAML | deploy | Servis ağı/env/volume | Docker Compose | kritik | aktif |
| `nginx/default.conf` | Nginx | edge | Reverse proxy/header | Nginx | yüksek | aktif |
| `.github/workflows/deploy-*.yml` | YAML | CI/CD | Deploy iskeleti | GitHub Actions | yüksek | doğrulama gerekli |

**Tasarım beyanı:** `frontend/src/styles/**`, `frontend/public/**`, görsel/ikon dosyaları ve
`frontend/dist/**` içerikleri değiştirilmedi. `dist` yalnız generated artifact olarak işaretlendi.

## Önceliklendirilmiş Sorun Listesi

### P0

#### Gömülü gerçek DB sırrı

- **Etkilenen:** `backend/app/core/config.py`, `docker-compose.yml`.
- **Teknik neden:** repository içinde uzak host, kullanıcı ve parola literal olarak bulunuyordu.
- **Etki:** DB ele geçirilmesi, veri sızıntısı/değiştirme.
- **Kök neden:** örnek config ile runtime secret ayrımının yapılmaması.
- **Çözüm:** literal kaldırıldı; `.env` + production secret validation uygulandı. Altyapı parolası
  repository dışında döndürülmeli.
- **Risk:** koddan silmek geçmişteki/clone'lardaki sırrı geçersiz kılmaz.
- **Rollback:** yeni secret başarısızsa yalnız önceki image'a dönme; **eski parolayı geri açma**.

#### Tenant IDOR ve hedef kapsamı ihlalleri

- **Etkilenen:** `core_modules.py`, `dashboard_reports.py`, `files_receipts.py`, `users.py`,
  `infrastructure/repositories/base.py`.
- **Teknik neden:** ID ile sorgular org/branch predicate'i içermiyor; create/update foreign key'leri
  request'ten doğrulanmadan alınıyordu.
- **Etki:** çapraz tenant okuma/yazma, yanlış veli grubuna duyuru, finans verisi ifşası.
- **Kök neden:** authz'nin endpoint'lere dağılması.
- **Çözüm:** `BaseRepository.get_by_id/require_related`; org+branch filtreleri; scope ilişki kontrolü.
- **Risk:** daha önce yanlış tenant ID'si gönderen istemci artık 403/404/validation alır; bu güvenli
  davranış değişikliğidir.
- **Rollback:** güvenlik yamasını geri alma; yalnız hatalı scope kuralını feature flag ile gevşet.

### P1

#### Auth rotation ve parola sıfırlama oturumları

- **Etkilenen:** `application/services/auth_service.py`, `core/dependencies.py`.
- **Neden/etki:** refresh reuse algılanmıyor, race aynı token'dan iki session üretebiliyor, reset
  mevcut refresh token'larını geçerli bırakıyordu.
- **Çözüm:** `SELECT ... FOR UPDATE`, token-family revocation, user status kontrolü, reset sonrası
  tüm refresh token'larının iptali, UUID claim validation.
- **Rollback:** DB şema değişmedi; önceki image'a dönüş mümkündür. Rotation sırasında açık oturumlar
  yeniden login isteyebilir.

#### JavaScript erişimli token saklama

- **Etkilenen:** `frontend/src/stores/auth.ts`, `frontend/src/lib/api.ts`.
- **Neden/etki:** access ve refresh token localStorage'da; başarılı XSS tüm oturumu çalabilir.
- **Çözüm:** Aşama 1'de backend opsiyonel HttpOnly refresh cookie + body response uyumu; Aşama 2'de
  frontend refresh token persistence kaldırma; Aşama 3'te legacy body token kapatma.
- **Risk:** CSRF koruması, SameSite ve cross-origin deploy birlikte tasarlanmalı.
- **Rollback:** feature flag ile body refresh token sözleşmesini bir release daha açık tut.

#### Request lifecycle otomatik commit

- **Etkilenen:** `backend/app/core/database.py`.
- **Neden/etki:** her başarılı request yield sonrası commit; servis sınırları görünmez, audit kayıtları
  auth hatasında rollback oluyordu, uzun endpoint'lerde transaction büyüyor.
- **Çözüm:** Aşama 1 servislerde açık `flush`/transaction testleri; Aşama 2 write use-case'lerde
  `async with session.begin()`; Aşama 3 dependency auto-commit kaldırma.
- **Rollback:** feature flag veya endpoint bazlı geçiş; tek seferde kaldırma breaking olur.

#### Bağımlılık açıkları

- **Etkilenen:** `requirements.txt`, `requirements-dev.txt`.
- **Etki:** JWT, multipart, template ve ASGI parsing açıkları.
- **Çözüm:** doğrulanmış sürümlere yükseltildi; CI `pip-audit` eklendi.
- **Rollback:** güvenlik açığı olan sürüme dönme; uyumsuzlukta güvenli ara sürüm/patched fork kullan.

### P2

- **Test izolasyonu:** CI migration eklendi ancak test başına rollback fixture ve seeded tenant matrisi yok.
- **Integration secrets:** `IntegrationSetting.config` JSONB içinde sırlar plaintext; UI yalnız maskeliyor.
- **Forgot password:** token üretiliyor ancak mail queue/provider'a teslim edilmiyor; kullanıcıya generic
  mesaj doğru olsa da iş akışı tamamlanmıyor.
- **N+1:** bulk attendance ve rapor döngülerinde her kayıt/şube için sorgu var.
- **CI kalite gate:** repo genelinde 204 mypy hatası ve ruff/black borcu var; çoğu muhtemel ölü katmanda.
- **Container:** image tag'leri digest ile pinli değil; SBOM/signing/trivy gate yok.
- **Upload:** imza/structure validation eklendi; antivirüs, quarantine ve content-disposition politikası yok.

### P3

- README marka/endpoint/deploy isimleri kısmen çelişkili.
- `database/*.sql`, `backend/sql/*.sql`, Alembic üç ayrı şema/seed kaynağı; drift riski.
- `frontend/dist/**` repository'de tutuluyor.
- Deprecated Pydantic class `Config` kullanımları ve büyük router dosyaları bakım maliyeti yaratıyor.

## Kod Düzeltmeleri ve Refactor Planı

Aşağıdaki kritik diff'ler uygulandı; yollar repository köküne göredir. Tasarım dosyasına diff yoktur.

### Secret/config — uygulandı

Tam yol: `C:\Users\gurs01tr\Downloads\SchoolManagement-master\backend\app\core\config.py`

```diff
--- backend/app/core/config.py
+++ backend/app/core/config.py
@@
-DATABASE_URL = "postgresql+asyncpg://<committed-user>:<committed-password>@<remote-host>/..."
-JWT_SECRET_KEY = "change_me"
+DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/school_management"
+JWT_SECRET_KEY = "development-only-change-me"
+@model_validator(mode="after")
+def validate_security_settings(self):
+    if self.APP_ENV in {"production", "staging"} and (...weak secret...):
+        raise ValueError("JWT_SECRET_KEY must be a unique secret of at least 32 characters")
```

Tam yol: `C:\Users\gurs01tr\Downloads\SchoolManagement-master\docker-compose.yml`

```diff
--- docker-compose.yml
+++ docker-compose.yml
@@
-env_file: ./backend/.env.example
-DATABASE_URL: postgresql+asyncpg://<committed-credential>@<remote-host>/...
-SEED_DEMO_DATA: "true"
-volumes: ["./backend:/app", "upload_data:/app/uploads"]
+env_file: ./backend/.env
+APP_ENV: ${APP_ENV:-production}
+SEED_DEMO_DATA: ${SEED_DEMO_DATA:-false}
+volumes: ["upload_data:/app/uploads"]
+expose: ["5006"]
```

### Tenant ve veri bütünlüğü — uygulandı

Tam yol: `C:\Users\gurs01tr\Downloads\SchoolManagement-master\backend\app\infrastructure\repositories\base.py`

```diff
--- backend/app/infrastructure/repositories/base.py
+++ backend/app/infrastructure/repositories/base.py
@@
-query = select(model).where(model.id == id, model.deleted_at.is_(None))
+query = select(model).where(model.id == id)
+if hasattr(model, "deleted_at"):
+    query = query.where(model.deleted_at.is_(None))
+query = self._org_filter(query, model)
+if for_update:
+    query = query.with_for_update()
@@
+async def require_related(self, id, model=None):
+    return await self.get_by_id(id, model)
```

Tam yol: `C:\Users\gurs01tr\Downloads\SchoolManagement-master\backend\app\routers\core_modules.py`

```diff
--- backend/app/routers/core_modules.py
+++ backend/app/routers/core_modules.py
@@ create_student
-organization_id=UUID(body.organization_id)
-branch_id=UUID(body.branch_id)
+branch = await repo.require_related(UUID(body.branch_id), Branch)
+if UUID(body.organization_id) != branch.organization_id:
+    raise ValidationException("Şube ve organizasyon eşleşmiyor")
+organization_id=branch.organization_id
+branch_id=branch.id
@@ take_payment
-debt = await repo.get_by_id(UUID(body.debt_id), Debt)
+debt = await repo.get_by_id(UUID(body.debt_id), Debt, for_update=True)
```

### Auth rotation — uygulandı

Tam yol: `C:\Users\gurs01tr\Downloads\SchoolManagement-master\backend\app\application\services\auth_service.py`

```diff
--- backend/app/application/services/auth_service.py
+++ backend/app/application/services/auth_service.py
@@ refresh
-select(RefreshToken).where(token_hash == ..., revoked_at IS NULL, expires_at > now)
+select(RefreshToken).where(token_hash == ...).with_for_update()
+if old_token.revoked_at is not None:
+    UPDATE refresh_tokens SET revoked_at = now WHERE family_id = ... AND revoked_at IS NULL
+    COMMIT
+    raise UnauthorizedException("Refresh token yeniden kullanıldı; oturum sonlandırıldı")
@@ reset_password
+UPDATE refresh_tokens SET revoked_at = now
+WHERE user_id = reset_token.user_id AND revoked_at IS NULL
```

### Duyuru/rapor/makbuz IDOR — uygulandı

Tam yol: `C:\Users\gurs01tr\Downloads\SchoolManagement-master\backend\app\routers\dashboard_reports.py`

```diff
--- backend/app/routers/dashboard_reports.py
+++ backend/app/routers/dashboard_reports.py
@@
-result = await db.execute(select(Debt).where(Debt.deleted_at.is_(None)))
+query = repo._branch_filter(repo._org_filter(select(Debt)..., Debt), Debt)
+result = await db.execute(query)
@@ send_announcement
-select(Parent).join(StudentParent)
+select(Parent).join(StudentParent).join(Student)
+  .where(Parent.organization_id == announcement.organization_id,
+         Student.organization_id == announcement.organization_id)
```

### Upload/XSS — uygulandı

Tam yol: `C:\Users\gurs01tr\Downloads\SchoolManagement-master\backend\app\routers\files_receipts.py`

```diff
--- backend/app/routers/files_receipts.py
+++ backend/app/routers/files_receipts.py
@@ _validate_upload
+if ext in signatures and not content.startswith(signatures[ext]):
+    raise ValidationException("Dosya içeriği uzantısıyla eşleşmiyor")
+if ext == "docx":
+    # [Content_Types].xml ve word/document.xml zorunlu
@@ print_receipt
-ctx = await _build_receipt_context(db, receipt)
+raw_ctx = await _build_receipt_context(db, receipt)
+ctx = {key: escape(str(value), quote=True) for key, value in raw_ctx.items()}
```

### Aşama 1 (uyumlu) / Aşama 2 (temizlik)

- **Auth service:** Aşama 1 aktif `application/services/auth_service.py`; Aşama 2, tüm importlar ve iki
  release telemetry doğrulandıktan sonra eski `app/services/auth_service.py` kaldırma.
- **Token cookie:** Aşama 1 body + cookie dual-write; Aşama 2 frontend cookie; Aşama 3 body refresh kaldırma.
- **DB transaction:** Aşama 1 write service'lerde explicit transaction; Aşama 2 `get_db` auto-commit kaldırma.
- **Şema:** Aşama 1 Alembic tek kaynak ilanı; Aşama 2 duplicate SQL bootstrap dosyalarını arşivleme.

## Güvenlik Sertleştirme Bölümü

- **Secret management:** `.env.example` runtime olmaktan çıkarıldı; production secret minimumu doğrulanıyor.
  Production için Docker/Kubernetes secret veya Vault/KMS kullanın; [Docker secrets rehberi](https://docs.docker.com/compose/how-tos/use-secrets/).
- **Auth/JWT/refresh:** erişim token kısa ömürlü; opaque refresh hash DB'de. Reuse family revocation eklendi.
  Sonraki adım issuer/audience/key rotation (`kid`) ve HttpOnly cookie.
- **Parola sıfırlama:** token hash + expiry + one-time + session revocation var. Mail teslimi ve aynı
  kullanıcı için eski reset token'larını topluca iptal etme eklenmeli. [OWASP Forgot Password](https://cheatsheetseries.owasp.org/cheatsheets/Forgot_Password_Cheat_Sheet.html).
- **Permission/tenant:** kararlar server-side; frontend `can()` yalnız görünürlük sağlar, güvenlik sınırı değildir.
  Negatif tenant contract testleri zorunlu olmalı.
- **Upload:** uzantı + imza/DOCX structure + boyut var. AV scan, quarantine, random filename, auth'lu
  download ve `Content-Disposition: attachment` sürdürülmeli. [OWASP File Upload](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html).
- **Rate limit/brute force:** login/forgot limitleri gerçek client IP zincirine bağlandı; backend host portu
  kapatıldı. Çok instance için Redis-backed distributed limiter gerekir.
- **Logging/audit/PII:** request ID var; token/parola/body loglanmamalı. Audit log append-only ve retention/
  erişim politikası belirtilmemiş.
- **CORS/proxy/headers:** CSP, nosniff, frame deny, referrer ve permissions policy eklendi. TLS/HSTS edge
  terminasyonu repository'de belirtilmemiş; HTTPS katmanında HSTS ekleyin.
- **Dependency/container:** `pip-audit` temiz; npm audit CI'ye eklendi. Images non-root/multi-stage backend.
  Digest pin, SBOM, signature ve Trivy sıradaki adım.

## Test Stratejisi

### Mevcut durum

- Backend: **22 geçti, 1 atlandı**. Atlanan test yerel PostgreSQL yokluğu nedeniyle DB integration testidir.
- Runtime `pip-audit`: **bilinen açık yok** (2026-06-24 taraması).
- Frontend: doğrudan Node giriş noktasıyla **2 test dosyası / 4 test geçti**, ESLint geçti.
- Frontend type-check, pnpm ile yarım/uyumsuz kurulumdaki `lucide-react` type resolution nedeniyle başarısız;
  canonical doğrulama `npm ci && npm run build` ile CI'da tekrarlanmalı.
- Docker Compose: bu makinede Docker executable olmadığı için çalıştırılamadı.
- Repo-geneli mypy: 46 dosyada 204 hata; çoğu muhtemel eski katmanda. Active/legacy ayrımı yapılmadan gate olmaz.

### Eksik/önerilen testler (en az sekiz)

| Test yolu | Tür | Senaryo |
|---|---|---|
| `backend/tests/unit/test_security_hardening.py` | unit, mevcut | Production placeholder JWT reddi |
| aynı dosya | unit, mevcut | sahte PDF/DOCX içerik doğrulama |
| `backend/tests/unit/test_auth_rotation.py` | unit | aynı refresh token'ı iki kez kullanınca aile iptali |
| aynı dosya | unit | parola reset sonrası tüm refresh token'ları revoked |
| `backend/tests/integration/test_tenant_isolation.py` | integration | org A token + org B payment/receipt ID → 404/403 |
| aynı dosya | integration | branch A kullanıcı + branch B student/class create/update → reddedilir |
| `backend/tests/integration/test_payment_concurrency.py` | integration | iki eşzamanlı ödeme kalan borcu aşamaz |
| `backend/tests/integration/test_announcement_scope.py` | integration | CLASS/SINGLE_STUDENT yalnız hedef velileri kuyruğa alır |
| `frontend/src/test/api-refresh.test.ts` | lib | paralel 401'ler tek refresh çağrısı paylaşır |
| aynı dosya | lib | refresh failure store'u temizler ve login'e yönlendirir |
| `frontend/src/test/guards.test.tsx` | component | permission yoksa `/forbidden` |
| `frontend/src/test/upload.test.tsx` | component | multipart upload hata mesajı ve retry |

### İzolasyon ve flaky riskleri

- CI PostgreSQL'e `alembic upgrade head` eklendi. Sonraki adım session-scope schema + test başına outer
  transaction/savepoint rollback veya her worker için benzersiz DB.
- Saat testlerinde injectable clock/frozen time; concurrency testlerinde gerçek PostgreSQL kullanın.
- Rate-limit state'ini testler arasında resetleyin; test sırasına güvenmeyin.
- Seed ID'lerini ortak production/demo seed'e bağlamayın; factory fixture kullanın.

## Migration ve Backward Compatibility Planı

| Değişiklik | Risk | Uyumluluk etkisi | Geçiş yöntemi | Rollback |
|---|---|---|---|---|
| Secret/env fail-closed | orta | zayıf production env artık başlamaz | secret oluştur, sonra image deploy | önceki image; eski sırrı açma |
| Tenant FK doğrulama | orta | hatalı cross-scope request reddedilir | staging negatif test + log gözlem | kural bazlı flag |
| Refresh rotation/reuse | orta | reuse halinde yeniden login | backend önce, frontend sonra | önceki backend image |
| Password reset revocation | düşük | tüm cihazlarda logout | kullanıcı iletişimi | eski image (önerilmez) |
| FastAPI/Starlette upgrade | orta | internal `app.routes` şekli değişti | OpenAPI/contract/smoke test | güvenli ara sürüm |
| Multipart/JWT/Jinja upgrade | düşük-orta | parser edge-case farkı | upload/auth regression | güvenli patched sürüm |
| Backend host portunu kapatma | orta | doğrudan `:5006` erişimi biter | Nginx `/api` üzerinden eriş | localhost-only bind |
| HttpOnly refresh cookie (plan) | yüksek | auth contract değişir | dual-write feature flag | legacy body flag |
| Explicit transaction (plan) | yüksek | commit zamanı değişir | endpoint bazlı rollout | auto-commit dependency |

Deployment sırası: secret rotation → DB backup → dependency/image build → migration → backend → worker →
frontend/Nginx → health/ready → auth/tenant/finance smoke → gözlem. Bu patch yeni DB migration gerektirmiyor.

## Kod İnceleme ve QA Kontrol Listesi

### PR

- [ ] Değişen endpoint için org ve branch negatif testi var.
- [ ] Request body typed schema; raw `dict` gerekçelendirilmiş.
- [ ] Migration upgrade/downgrade veya “migration yok” notu var.
- [ ] UI/design asset değişmedi; generated `dist` elle düzenlenmedi.
- [ ] Yeni dependency lockfile ve audit sonucu incelendi.

### Güvenlik

- [ ] Secret/token/parola log veya response'a girmiyor.
- [ ] Object lookup tenant predicate içeriyor.
- [ ] Upload adı/içeriği/boyutu ve download auth kontrolü var.
- [ ] Auth error kullanıcı varlığını sızdırmıyor.
- [ ] Rate limit proxy IP spoofing'e açık değil.

### Regression / smoke

- [ ] Login, refresh rotation, logout, forgot/reset.
- [ ] İki org/iki branch ile öğrenci list/create/update.
- [ ] Borç, eşzamanlı tahsilat, iptal, makbuz PDF/print.
- [ ] Duyuru ALL/BRANCH/CLASS/SINGLE hedef sayıları.
- [ ] Upload PDF/JPEG/PNG/DOCX ve sahte uzantı reddi.
- [ ] Dashboard/report/export tenant toplamları.

### Release öncesi/sonrası

- [ ] `pip-audit`, `npm audit`, image/secret scan temiz.
- [ ] Immutable image digest ve rollback tag kayıtlı.
- [ ] Backup restore tatbikatı yapılmış.
- [ ] 401/403/404/429/5xx, DB pool, latency ve notification failure dashboard'u izleniyor.
- [ ] Login failure/reuse detection anomalileri alarm üretiyor.

## Dokümantasyon İyileştirmeleri

README'de düzeltilenler: `npm start` → `npm run dev`, `npm install` → `npm ci`, API docs yolu,
`.env` hazırlığı, demo seed'in varsayılan kapalı olması, test/audit komutları ve gerçek olmayan production
rollback dosyası. Hâlâ tamamlanması gerekenler:

```text
README.md
├── Ürün adı ve desteklenen kullanıcı rolleri
├── Architecture (aktif katmanlar + legacy etiketi)
├── Local development (DB dahil)
├── Environment variable reference (secret değerleri olmadan)
├── Database migration/seed policy
├── Test/quality/security commands
├── Docker development
├── Production deployment (gerçek hedef belirtildiğinde)
├── Backup/restore/rollback
└── Troubleshooting
```

Önerilen belgeler:

- `docs/ARCHITECTURE.md`: aktif/legacy import haritasını güncelle.
- `SECURITY.md`: disclosure kanalı, secret rotation, desteklenen sürümler.
- `OPERATIONS.md`: backup, restore, deploy, rollback, key rotation, incident.
- `docs/DATA_CLASSIFICATION.md`: öğrenci/veli/finans PII retention ve erişim.

Örnek changelog:

```text
## [Unreleased] - 2026-06-24
### Security
- Remove committed database credentials and enforce production secret validation.
- Enforce organization/branch scope for finance, reports, announcements and user assignments.
- Detect refresh-token reuse and revoke token families.
- Upgrade vulnerable backend runtime dependencies.
### Fixed
- Prevent concurrent payments from over-applying debt balances.
- Validate upload content and escape receipt print output.
```

Örnek commit'ler:

- `fix(security): remove committed secrets and fail closed in production`
- `fix(authz): enforce tenant scope across active object lookups`
- `fix(auth): rotate refresh tokens atomically and revoke reset sessions`
- `fix(finance): lock debt rows during payment mutations`
- `build(deps): upgrade vulnerable FastAPI auth and multipart stack`
- `test(security): add production config and upload regression coverage`
- `docs(operations): align setup and rollback guidance with repository state`

## Önerilen Komutlar

### Backend

```bash
cd backend
python -m pip install -r requirements-dev.txt  # runtime + dev bağımlılıkları
ruff check app tests                           # lint/import/bugbear
black --check app tests                       # format kontrolü
mypy app --ignore-missing-imports              # type borcunu ölçer; şu an gate değil
pytest tests/unit -v                           # DB'siz unit testler
pytest tests/integration -v                    # migrate edilmiş izole PostgreSQL gerekir
pip-audit -r requirements.txt                  # runtime CVE taraması
alembic upgrade head                           # migration
```

### Frontend

```bash
cd frontend
npm ci                                         # package-lock'a birebir kurulum
npm run lint                                   # ESLint
npm test                                       # Vitest
npm audit --omit=dev --audit-level=high        # production dependency audit
npm run build                                  # TypeScript + Vite; dist'i yeniden üretir
```

### Repo / Container / Security

```bash
docker compose config                          # env interpolation ve compose doğrulama
docker compose build --pull                    # temiz image build
trivy fs --scanners vuln,secret,misconfig .    # filesystem/dependency/misconfig
trivy image edupanel-backend:<immutable-tag>   # image taraması
gitleaks detect --source . --no-banner         # secret scan
```

Trivy/Gitleaks sürümü repository'de belirtilmemiştir; CI action sürümünü resmi release ve SHA ile pinleyin.

## Mermaid Diyagramları

```mermaid
flowchart LR
  Browser["React / Vite SPA"] --> Edge["Nginx reverse proxy + security headers"]
  Edge --> API["FastAPI app/main.py"]
  API --> Guards["JWT + PermissionChecker + TenantContext"]
  Guards --> Routers["Active combined routers"]
  Routers --> Repo["BaseRepository tenant filters"]
  Routers --> Auth["Application AuthService"]
  Repo --> ORM["Infrastructure ORM models"]
  Auth --> ORM
  ORM --> PG[(PostgreSQL)]
  Routers --> Storage["Local upload volume"]
  Routers --> Outbox["Notification jobs"]
  Worker["Outbox worker"] --> Outbox
  Legacy["Legacy services/repositories/entities"] -. "muhtemel ölü kod" .-> API
```

```mermaid
flowchart TD
  A["1. DB secret rotation ve erişim inceleme"] --> B["2. Staging env + fail-closed startup"]
  B --> C["3. Dependency/image build + audit"]
  C --> D["4. Tenant/auth/finance regression"]
  D --> E["5. Backend + worker rollout"]
  E --> F["6. Frontend/Nginx rollout"]
  F --> G["7. Smoke + telemetry gözlemi"]
  G --> H["8. HttpOnly cookie ve explicit transaction fazı"]
  H --> I["9. Legacy katman kaldırma doğrulaması"]
```

## Uygulama Sırası

1. Dış altyapıda sızmış DB kimliğini iptal et/döndür; yeni secret'ı repository dışında dağıt.
2. Mevcut yamayı staging'de `APP_ENV=production` ile başlat; zayıf secret testinin fail ettiğini doğrula.
3. Migration/backup kontrolü, `pip-audit`, `npm audit`, unit ve contract testlerini çalıştır.
4. İki tenant/iki branch negatif IDOR testlerini ve eşzamanlı ödeme testini tamamla.
5. Backend ve worker'ı immutable tag ile deploy et; sonra frontend/Nginx'i yayınla.
6. 401/403/429/5xx, refresh reuse, DB pool ve notification telemetry'yi en az bir release izle.
7. HttpOnly cookie dual-mode geçişini uygula.
8. Explicit transaction geçişini endpoint bazında tamamla.
9. Aktif import/telemetry doğrulamasından sonra legacy router/service/repository/entity katmanını kaldır.
10. `frontend/dist/**` gerekiyorsa yalnız doğrulanmış `npm run build` çıktısıyla yeniden üret; elle patch yazma.

## Frontend Tamamlama Notu

24 Haziran 2026 tarihli ikinci geçişte görsel stil dosyaları ve mevcut tasarım sınıfları değiştirilmeden frontend davranışları güçlendirildi:

- Doğrudan URL erişimlerine modül ve yazma yetkisi korumaları eklendi; hatalı `students:write`, `users:write` ve `roles:write` kontrolleri kanonik izin adlarıyla düzeltildi.
- “Beni hatırla” gerçek davranış kazandı: varsayılan oturum `sessionStorage`, açık tercih ise `localStorage` kullanıyor; çıkış iki alanı da temizliyor ve eski Zustand kaydı okunabiliyor.
- Üretime gömülü demo kullanıcı/şifre kaldırıldı; demo yalnız açık geliştirme değişkenleriyle etkinleştirilebilir.
- API refresh eşzamanlılığı korunurken FormData sınırı, timeout, güvenli geri dönüş URL'si ve indirme hata bildirimleri düzeltildi.
- Yoklama notlarının kaybolması, UTC kaynaklı gün/ay sapması, state dizilerini yerinde sıralama ve ayarlar–entegrasyon API sözleşmesi uyuşmazlığı giderildi.
- Pasif “Dışa aktar” düğmeleri CSV üretimine bağlandı; CSV formül enjeksiyonuna karşı hücre koruması eklendi.
- Modal odak tuzağı/odak iadesi, toast timer temizliği, tablo aksiyon adları, profil menüsü klavye davranışı ve form etiket ilişkileri iyileştirildi.
- `src/styles/**`, görseller, ikonlar ve tasarım asset'leri değiştirilmedi.

Doğrulama sonucu: 12 Vitest testi geçti; ESLint, TypeScript build ve Vite production build başarılı; yerel tarayıcı duman testinde giriş ve şifre kurtarma akışı çalıştı, konsolda hata/uyarı görülmedi.
