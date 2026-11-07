from collections.abc import AsyncGenerator
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings
from app.core.exceptions import ConflictException
from app.core.uuid_type import CustomUUID

settings = get_settings()

# SQLite doesn't support connection pooling
is_sqlite = settings.DATABASE_URL.startswith("sqlite")

engine_kwargs = {
    "echo": settings.APP_ENV == "development",
    "pool_pre_ping": True,
}

if not is_sqlite:
    engine_kwargs.update({
        "pool_size": 10,
        "max_overflow": 20,
    })

engine = create_async_engine(settings.DATABASE_URL, **engine_kwargs)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    type_annotation_map = {UUID: CustomUUID()}
    __mapper_args__ = {"eager_defaults": True}
    __table_args__ = {"extend_existing": True}


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Use Depends(get_db, scope="function") to commit before HTTP headers."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except IntegrityError as exc:
            await session.rollback()
            raise ConflictException("Kayıt başka bir kayıtla veya bağlı verilerle çakışıyor; bilgileri yenileyip tekrar deneyin") from exc
        except Exception:
            await session.rollback()
            raise
