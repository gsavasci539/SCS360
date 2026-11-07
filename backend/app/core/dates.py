"""School calendar dates must not depend on the server operating system timezone."""
from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.core.config import get_settings


def school_today(now: datetime | None = None):
    instant = now if now is not None else datetime.now(UTC)
    if instant.tzinfo is None:
        raise ValueError("A timezone-aware instant is required")
    return instant.astimezone(ZoneInfo(get_settings().BUSINESS_TIMEZONE)).date()


def school_datetime(instant: datetime):
    """Database timestamps without an offset represent UTC, including SQLite."""
    if instant.tzinfo is None:
        instant = instant.replace(tzinfo=UTC)
    return instant.astimezone(ZoneInfo(get_settings().BUSINESS_TIMEZONE))


def school_time():
    return school_datetime(datetime.now(UTC)).time()


def school_day_bounds(day):
    zone = ZoneInfo(get_settings().BUSINESS_TIMEZONE)
    start = datetime.combine(day, time.min, tzinfo=zone).astimezone(UTC)
    end = datetime.combine(day + timedelta(days=1), time.min, tzinfo=zone).astimezone(UTC)
    return start, end
