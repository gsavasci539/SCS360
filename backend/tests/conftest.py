import asyncio
import os
from pathlib import Path
import tempfile

# Set before importing application settings. Direct pytest invocations must
# never inherit the developer's working database or delivery configuration.
_test_directory = tempfile.TemporaryDirectory(prefix="scs360-pytest-", ignore_cleanup_errors=True)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{Path(_test_directory.name).as_posix()}/test.db"
os.environ["APP_ENV"] = "test"
os.environ["SEED_DEMO_DATA"] = "false"
os.environ["NOTIFICATION_DELIVERY_ENABLED"] = "false"
os.environ["PRIVATE_UPLOAD_DIR"] = str(Path(_test_directory.name) / "private")

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.database import Base, engine
from app.main import app


def pytest_sessionstart(session):
    # ASGITransport does not run FastAPI lifespan. Use the production logger
    # configuration rather than Rich's default traceback with local values.
    from app.core.middleware import setup_logging
    setup_logging()
    async def prepare():
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        await engine.dispose()
    asyncio.run(prepare())


def pytest_sessionfinish(session, exitstatus):
    asyncio.run(engine.dispose())
    _test_directory.cleanup()


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def database_available():
    """Skip DB-backed integration tests locally when PostgreSQL is not running."""
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    except (OSError, SQLAlchemyError) as exc:
        pytest.skip(f"Test PostgreSQL is unavailable: {exc}")
