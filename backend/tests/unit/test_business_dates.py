from datetime import UTC, date, datetime

import pytest

from app.core.config import get_settings
from app.core.dates import school_today
from app.core.dates import school_datetime, school_day_bounds, school_time


def test_turkish_school_day_starts_before_utc_midnight(monkeypatch):
    monkeypatch.setattr(get_settings(), "BUSINESS_TIMEZONE", "Europe/Istanbul")
    assert school_today(datetime(2026, 11, 2, 20, 59, tzinfo=UTC)) == date(2026, 11, 2)
    assert school_today(datetime(2026, 11, 2, 21, 0, tzinfo=UTC)) == date(2026, 11, 3)


def test_business_day_uses_configured_timezone(monkeypatch):
    monkeypatch.setattr(get_settings(), "BUSINESS_TIMEZONE", "America/New_York")
    assert school_today(datetime(2026, 11, 3, 1, 0, tzinfo=UTC)) == date(2026, 11, 2)
    with pytest.raises(ValueError):
        school_today(datetime(2026, 11, 3, 1, 0))


def test_database_naive_timestamps_and_school_midnight_bounds(monkeypatch):
    monkeypatch.setattr(get_settings(), "BUSINESS_TIMEZONE", "Europe/Istanbul")
    assert school_datetime(datetime(2026, 11, 2, 22, 30)).date() == date(2026, 11, 3)
    assert school_day_bounds(date(2026, 11, 3)) == (
        datetime(2026, 11, 2, 21, tzinfo=UTC), datetime(2026, 11, 3, 21, tzinfo=UTC))


def test_day_bounds_follow_dst_in_the_configured_timezone(monkeypatch):
    monkeypatch.setattr(get_settings(), "BUSINESS_TIMEZONE", "America/New_York")
    start, end = school_day_bounds(date(2026, 11, 1))
    assert (end - start).total_seconds() == 25 * 60 * 60


def test_mobile_bus_and_infirmary_defaults_share_the_school_calendar_and_clock(monkeypatch):
    from uuid import uuid4
    from app.core import dates
    from app.routers.bus import BusAttendanceCreate
    from app.routers.infirmary import InfirmaryVisitCreate
    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2027, 1, 3, 22, 30, tzinfo=UTC)
    monkeypatch.setattr(get_settings(), "BUSINESS_TIMEZONE", "Europe/Istanbul")
    monkeypatch.setattr(dates, "datetime", FrozenDateTime)
    assert BusAttendanceCreate(route_id=uuid4(), student_id=uuid4()).attendance_date == date(2027, 1, 4)
    visit = InfirmaryVisitCreate(student_id=uuid4())
    assert visit.visit_date == date(2027, 1, 4)
    assert visit.visit_time.hour == 1 and visit.visit_time.minute == 30
    assert school_time() == visit.visit_time
