# EduPanel Backend

FastAPI tabanlı okul yönetim sistemi backend API.

## Kurulum

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

## Veritabanı

Docker ile:
```bash
docker compose up db -d
```

SQL şema dosyaları `sql/` klasöründe. Seed:
```bash
python scripts/seed_demo_data.py
```

## Çalıştırma

```bash
uvicorn app.main:app --reload --port 8000
```

Worker:
```bash
python -m app.infrastructure.notifications.outbox_worker
```

## Test

```bash
pytest -v
```
