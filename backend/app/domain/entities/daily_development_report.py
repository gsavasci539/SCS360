from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel


class DailyDevelopmentReport(BaseModel):
    id: UUID
    student_id: UUID
    class_id: UUID
    date: datetime
    meal_status: Optional[str] = None  # ALL, HALF, NONE
    sleep_status: Optional[str] = None  # SLEPT_WELL, SHORT, NO_SLEEP
    mood: Optional[str] = None  # HAPPY, CALM, UNSETTLED, TIRED
    activities: Optional[List[str]] = None
    teacher_notes: Optional[str] = None
    recorded_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DailyDevelopmentReportCreate(BaseModel):
    student_id: UUID
    class_id: UUID
    date: datetime
    meal_status: Optional[str] = None
    sleep_status: Optional[str] = None
    mood: Optional[str] = None
    activities: Optional[List[str]] = None
    teacher_notes: Optional[str] = None


class DailyDevelopmentReportUpdate(BaseModel):
    meal_status: Optional[str] = None
    sleep_status: Optional[str] = None
    mood: Optional[str] = None
    activities: Optional[List[str]] = None
    teacher_notes: Optional[str] = None