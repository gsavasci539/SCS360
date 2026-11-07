"""Exercise registered read endpoints on a disposable SQLite snapshot.

Run from backend: .venv/Scripts/python scripts/audit_api_smoke.py
No writes are made to the source database and no payment/send endpoints are called.
The report contains statuses/errors, never response bodies or access tokens.
"""
import asyncio
import contextlib
import io
import json
import logging
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import traceback
import warnings

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


async def audit():
    from httpx import ASGITransport, AsyncClient
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from app.main import app
    from app.core.database import AsyncSessionLocal, engine
    from app.core.security import create_access_token
    from app.infrastructure.models.models import User, Role

    engine.echo = False
    logging.disable(logging.CRITICAL)
    warnings.filterwarnings("ignore")
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        schema = app.openapi()
        async with AsyncSessionLocal() as db:
            users = (await db.execute(select(User).options(
                selectinload(User.roles).selectinload(Role.permissions)
            ).where(User.deleted_at.is_(None)))).scalars().all()
        identities = {}
        for user in users:
            if user is None or user.id is None:
                continue
            role = "super_admin" if user.is_super_admin else (user.roles[0].slug if user.roles else "none")
            identities.setdefault(role, user)
        report = []
        for role, user in identities.items():
            requested_roles = os.environ.get("AUDIT_ROLES", "").split(",")
            if requested_roles != [""] and role not in requested_roles:
                continue
            token = create_access_token(user.id)
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://audit",
                                   headers={"Authorization": f"Bearer {token}"}) as client:
                for path, operations in schema["paths"].items():
                    if "get" not in operations or "{" in path:
                        continue
                    if any(word in path for word in ("iyzico", "export", "download", "receipt-pdf")):
                        continue
                    operation = operations["get"]
                    if any(p.get("required") for p in operation.get("parameters", [])):
                        continue
                    row = {"role": role, "path": path}
                    try:
                        response = await asyncio.wait_for(client.get(path), timeout=8)
                        row["status"] = response.status_code
                        if response.status_code >= 400:
                            row["detail"] = response.text[:350]
                    except Exception as exc:
                        row["status"] = 500
                        row["error"] = str(exc)[:1000]
                        row["trace"] = traceback.format_exc(limit=5)
                    report.append(row)
            destination = ROOT.parent / "docs" / os.environ.get("AUDIT_REPORT", "api-smoke-results.json")
            destination.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"Completed role: {role}; checks: {len(report)}", file=sys.__stdout__, flush=True)
    await engine.dispose()
    return report


def main():
    # SQLite backup also includes committed WAL contents.
    with tempfile.TemporaryDirectory(prefix="scs360-audit-", ignore_cleanup_errors=True) as temporary:
        snapshot = Path(temporary) / "snapshot.db"
        with contextlib.closing(sqlite3.connect(f"file:{ROOT / 'school_management.db'}?mode=ro", uri=True)) as source:
            with contextlib.closing(sqlite3.connect(snapshot)) as target:
                source.backup(target)
        os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{snapshot.as_posix()}"
        os.environ["APP_ENV"] = "development"
        from alembic import command
        from alembic.config import Config
        command.upgrade(Config(str(ROOT / "alembic.ini")), "head")
        report = asyncio.run(audit())
    destination = ROOT.parent / "docs" / os.environ.get("AUDIT_REPORT", "api-smoke-results.json")
    destination.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    statuses = {}
    for row in report:
        statuses[row["status"]] = statuses.get(row["status"], 0) + 1
    print(json.dumps({"checks": len(report), "statuses": statuses, "report": str(destination)}))
    for row in report:
        if row["status"] >= 500:
            print(json.dumps({key: row[key] for key in ("role", "path", "error") if key in row}))
    if any(row["status"] not in {200, 403} for row in report):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
