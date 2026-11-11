"""Atomic class/day edits, opaque row versions, and durable actor-bound retry receipts."""
import hashlib
import json
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import ConflictException, ForbiddenException
from app.infrastructure.models.models import (
    AttendanceRecord,
    AuditAction,
    AuditLog,
    ClassRoom,
    Student,
)
from app.infrastructure.repositories.base import BaseRepository

EVENT = "ATTENDANCE_BATCH_SAVED"


def version(row):
    def stamp(value):
        if value is None:
            return None
        return (value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)).isoformat()

    values = [str(row.id), str(row.organization_id), str(row.branch_id), str(row.class_id), str(row.student_id),
        row.attendance_date.isoformat(), row.status.value, row.notes,
        row.check_in_time.isoformat() if row.check_in_time else None, str(row.recorded_by),
        stamp(row.updated_at), stamp(row.deleted_at)]
    return hashlib.sha256(json.dumps(values, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


async def save(db, tenant, body):
    repo = BaseRepository(db, tenant)
    classroom = await repo.require_related(body.class_id, ClassRoom)
    table = ClassRoom.__table__
    await db.execute(table.update().where(table.c.id == classroom.id).values(updated_at=table.c.updated_at))
    digest = hashlib.sha256(json.dumps(body.model_dump(mode="json", exclude={"request_id"}),
        ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    prior = (await db.execute(select(AuditLog).where(AuditLog.id == body.request_id))).scalar_one_or_none()
    if prior:
        cache = prior.new_values or {}
        if prior.user_id != tenant.user_id or prior.entity_id != classroom.id or cache.get("event") != EVENT or cache.get("digest") != digest:
            raise ConflictException("İstek kimliği başka bir yoklama işleminde kullanılmış")
        return cache["response"]
    audit_table = AuditLog.__table__
    if (await db.execute(select(audit_table.c.id).where(audit_table.c.id == body.request_id))).first():
        raise ConflictException("İstek kimliği kullanılamıyor")
    created, updated, unchanged, changed = 0, 0, 0, []
    for item in body.records:
        student = await repo.get_by_id(item.student_id, Student)
        row = (await db.execute(select(AttendanceRecord).where(AttendanceRecord.student_id == student.id,
            AttendanceRecord.attendance_date == body.attendance_date).execution_options(populate_existing=True))).scalar_one_or_none()
        if row is not None:
            if row.deleted_at is not None or row.class_id != classroom.id or row.branch_id != classroom.branch_id:
                raise ConflictException("Bu tarihin yoklaması başka sınıfta veya arşivde; mevcut geçmiş değiştirilemez")
            if item.expected_version is None or item.expected_version != version(row):
                raise ConflictException("Yoklama başka bir işlemde değişmiş; kayıtları yenileyin")
            notes = item.notes if "notes" in item.model_fields_set else row.notes
            if row.status == item.status and row.notes == notes:
                unchanged += 1
            else:
                row.status, row.notes, row.updated_at = item.status, notes, datetime.now(UTC)
                updated += 1
        else:
            if item.expected_version is not None:
                raise ConflictException("Yoklama kaydı değişmiş veya kaldırılmış; kayıtları yenileyin")
            if student.class_id != classroom.id or student.branch_id != classroom.branch_id:
                raise ForbiddenException("Öğrenci seçili sınıfa ait olmalıdır")
            row = AttendanceRecord(organization_id=classroom.organization_id, branch_id=classroom.branch_id,
                class_id=classroom.id, student_id=student.id, attendance_date=body.attendance_date,
                status=item.status, notes=item.notes, recorded_by=tenant.user_id)
            db.add(row)
            created += 1
        changed.append(row)
    try:
        await db.flush()
        for row in changed:
            await db.refresh(row)
        response = {"created": created, "updated": updated, "unchanged": unchanged,
            "items": [{"id": str(row.id), "student_id": str(row.student_id), "version": version(row)} for row in changed]}
        db.add(AuditLog(id=body.request_id, organization_id=classroom.organization_id, branch_id=classroom.branch_id,
            user_id=tenant.user_id, action=AuditAction.UPDATE, entity_type="attendance_batch", entity_id=classroom.id,
            new_values={"event": EVENT, "digest": digest, "response": response}))
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise ConflictException("Yoklama eşzamanlı değişmiş; kayıtları yenileyip tekrar deneyin") from None
    return response
