"""Remove only a database recorded by this disposable browser test run."""
import asyncio
import json
import os
from pathlib import Path
import re
import sys

from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine

ROOT = Path(__file__).resolve().parents[2]


async def cleanup(record_path):
    record = Path(record_path).resolve()
    if record.parent != (ROOT / ".codex-build").resolve() or not re.fullmatch(r"acceptance-[0-9a-f-]+\.json", record.name):
        raise RuntimeError("The test record must be a known workspace acceptance file")
    if not record.exists():
        return
    data = json.loads(record.read_text(encoding="utf-8"))
    name = data["database"]
    source = make_url(os.environ["ACCEPTANCE_DATABASE_URL"])
    if (not re.fullmatch(r"scs360_acceptance_browser_[0-9a-f]{32}", name)
        or name == source.database
        or source.drivername != "postgresql+asyncpg"
        or not (source.database or "").startswith("scs360_acceptance")
        or any(data[key] != getattr(source, key) for key in ("host", "port", "username"))
        or data["source_database"] != source.database):
        raise RuntimeError("The recorded test database does not match the disposable connection")
    engine = create_async_engine(source, isolation_level="AUTOCOMMIT")
    try:
        async with engine.connect() as connection:
            await connection.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
    finally:
        await engine.dispose()
    record.unlink()


if __name__ == "__main__":
    asyncio.run(cleanup(sys.argv[1]))
