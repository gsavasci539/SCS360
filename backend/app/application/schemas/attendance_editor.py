from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.infrastructure.models.models import AttendanceStatus


class AttendanceEditRow(BaseModel):
    model_config = ConfigDict(extra="forbid")
    student_id: UUID
    status: AttendanceStatus
    notes: str | None = Field(default=None, max_length=5000)
    expected_version: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")


class AttendanceBatchSave(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: UUID
    class_id: UUID
    attendance_date: date
    records: list[AttendanceEditRow] = Field(min_length=1, max_length=5000)

    @model_validator(mode="after")
    def unique_students(self):
        identifiers = [row.student_id for row in self.records]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("Aynı öğrenci tek istekte bir kez bulunabilir")
        return self
