"""Date and period resolution service for natural language date expressions."""

import logging
from datetime import date as date_type, datetime, timedelta
from typing import Optional

from app.application.services.chatbot.intent_schemas import DateRange

logger = logging.getLogger(__name__)


class DateResolutionService:
    """Service for resolving natural language date expressions to date ranges."""

    def __init__(self, reference_date: Optional[date_type] = None):
        self.reference_date = reference_date or date_type.today()

    def resolve_period(self, period: Optional[str]) -> Optional[DateRange]:
        """
        Resolve natural language period to date range.

        Args:
            period: Natural language period (today, this_week, this_month, etc.)

        Returns:
            DateRange or None if period is invalid
        """
        if not period:
            return None

        period_lower = period.lower().strip()

        try:
            if period_lower in ["today", "bugün"]:
                return self._today()

            elif period_lower in ["yesterday", "dün"]:
                return self._yesterday()

            elif period_lower in ["tomorrow", "yarın"]:
                return self._tomorrow()

            elif period_lower in ["this_week", "bu hafta", "hafta"]:
                return self._this_week()

            elif period_lower in ["last_week", "geçen hafta"]:
                return self._last_week()

            elif period_lower in ["next_week", "gelecek hafta"]:
                return self._next_week()

            elif period_lower in ["this_month", "bu ay", "ay"]:
                return self._this_month()

            elif period_lower in ["last_month", "geçen ay"]:
                return self._last_month()

            elif period_lower in ["next_month", "gelecek ay"]:
                return self._next_month()

            elif period_lower in ["this_year", "bu yıl", "yıl"]:
                return self._this_year()

            elif period_lower in ["last_year", "geçen yıl"]:
                return self._last_year()

            elif period_lower in ["last_7_days", "son 7 gün", "son 7 gün"]:
                return self._last_n_days(7)

            elif period_lower in ["last_30_days", "son 30 gün", "son 30 gün"]:
                return self._last_n_days(30)

            elif period_lower in ["last_90_days", "son 90 gün", "son 90 gün"]:
                return self._last_n_days(90)

            else:
                logger.warning(f"Unknown period: {period}")
                return None

        except Exception as e:
            logger.exception(f"Error resolving period '{period}': {e}")
            return None

    def _today(self) -> DateRange:
        """Today's date range."""
        return DateRange(
            start_date=self.reference_date,
            end_date=self.reference_date,
            description="Bugün"
        )

    def _yesterday(self) -> DateRange:
        """Yesterday's date range."""
        yesterday = self.reference_date - timedelta(days=1)
        return DateRange(
            start_date=yesterday,
            end_date=yesterday,
            description="Dün"
        )

    def _tomorrow(self) -> DateRange:
        """Tomorrow's date range."""
        tomorrow = self.reference_date + timedelta(days=1)
        return DateRange(
            start_date=tomorrow,
            end_date=tomorrow,
            description="Yarın"
        )

    def _this_week(self) -> DateRange:
        """This week's date range (Monday to Sunday)."""
        # Get Monday of current week
        days_since_monday = self.reference_date.weekday()  # Monday = 0
        monday = self.reference_date - timedelta(days=days_since_monday)
        sunday = monday + timedelta(days=6)
        return DateRange(
            start_date=monday,
            end_date=sunday,
            description="Bu hafta"
        )

    def _last_week(self) -> DateRange:
        """Last week's date range."""
        this_week = self._this_week()
        last_week_start = this_week.start_date - timedelta(days=7)
        last_week_end = this_week.start_date - timedelta(days=1)
        return DateRange(
            start_date=last_week_start,
            end_date=last_week_end,
            description="Geçen hafta"
        )

    def _next_week(self) -> DateRange:
        """Next week's date range."""
        this_week = self._this_week()
        next_week_start = this_week.end_date + timedelta(days=1)
        next_week_end = next_week_start + timedelta(days=6)
        return DateRange(
            start_date=next_week_start,
            end_date=next_week_end,
            description="Gelecek hafta"
        )

    def _this_month(self) -> DateRange:
        """This month's date range."""
        first_day = self.reference_date.replace(day=1)
        
        # Get last day of month
        if self.reference_date.month == 12:
            next_month_first = self.reference_date.replace(year=self.reference_date.year + 1, month=1, day=1)
        else:
            next_month_first = self.reference_date.replace(month=self.reference_date.month + 1, day=1)
        
        last_day = next_month_first - timedelta(days=1)
        
        return DateRange(
            start_date=first_day,
            end_date=last_day,
            description="Bu ay"
        )

    def _last_month(self) -> DateRange:
        """Last month's date range."""
        if self.reference_date.month == 1:
            # January -> December of previous year
            last_month_first = self.reference_date.replace(year=self.reference_date.year - 1, month=12, day=1)
            last_month_last = self.reference_date.replace(year=self.reference_date.year - 1, month=12, day=31)
        else:
            # Any other month
            last_month_first = self.reference_date.replace(month=self.reference_date.month - 1, day=1)
            # Last day of previous month
            if self.reference_date.month == 3:
                # March -> February (handle leap year)
                year = self.reference_date.year
                if (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0):
                    last_day = 29
                else:
                    last_day = 28
            elif self.reference_date.month in [5, 7, 10, 12]:
                # May, July, October, December -> previous month has 30 days
                last_day = 30
            else:
                # April, June, September, November -> previous month has 31 days
                last_day = 31
            
            last_month_last = self.reference_date.replace(month=self.reference_date.month - 1, day=last_day)
        
        return DateRange(
            start_date=last_month_first,
            end_date=last_month_last,
            description="Geçen ay"
        )

    def _next_month(self) -> DateRange:
        """Next month's date range."""
        if self.reference_date.month == 12:
            # December -> January of next year
            next_month_first = self.reference_date.replace(year=self.reference_date.year + 1, month=1, day=1)
            next_month_last = self.reference_date.replace(year=self.reference_date.year + 1, month=1, day=31)
        else:
            # Any other month
            next_month_first = self.reference_date.replace(month=self.reference_date.month + 1, day=1)
            # Get last day of next month
            if next_month_first.month == 2:
                # February
                year = next_month_first.year
                if (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0):
                    last_day = 29
                else:
                    last_day = 28
            elif next_month_first.month in [4, 6, 9, 11]:
                # April, June, September, November
                last_day = 30
            else:
                # January, March, May, July, August, October, December
                last_day = 31
            
            next_month_last = next_month_first.replace(day=last_day)
        
        return DateRange(
            start_date=next_month_first,
            end_date=next_month_last,
            description="Gelecek ay"
        )

    def _this_year(self) -> DateRange:
        """This year's date range."""
        first_day = self.reference_date.replace(month=1, day=1)
        last_day = self.reference_date.replace(month=12, day=31)
        return DateRange(
            start_date=first_day,
            end_date=last_day,
            description="Bu yıl"
        )

    def _last_year(self) -> DateRange:
        """Last year's date range."""
        first_day = self.reference_date.replace(year=self.reference_date.year - 1, month=1, day=1)
        last_day = self.reference_date.replace(year=self.reference_date.year - 1, month=12, day=31)
        return DateRange(
            start_date=first_day,
            end_date=last_day,
            description="Geçen yıl"
        )

    def _last_n_days(self, n: int) -> DateRange:
        """Last n days date range."""
        end_date = self.reference_date
        start_date = self.reference_date - timedelta(days=n - 1)
        return DateRange(
            start_date=start_date,
            end_date=end_date,
            description=f"Son {n} gün"
        )
