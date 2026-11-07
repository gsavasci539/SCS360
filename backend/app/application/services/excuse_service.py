"""Persist parent excuse requests and their administrative review."""
from datetime import UTC, datetime
from sqlalchemy import select

from app.application.services.parent_data_service import child
from app.core.exceptions import ConflictException, NotFoundException, ValidationException
from app.infrastructure.models.models import OperationalRecord
from app.infrastructure.repositories.base import BaseRepository


def serialize(row):
    return dict(row.data, id=str(row.id), status=row.status, created_at=row.created_at.isoformat())


async def create(db, user, student_id, body):
    _, student = await child(db, user, student_id)
    if body.end_date < body.start_date:
        raise ValidationException("Bitiş tarihi başlangıçtan önce olamaz")
    if not body.description.strip():
        raise ValidationException("Mazeret açıklaması gerekli")
    row = OperationalRecord(organization_id=student.organization_id, branch_id=student.branch_id,
        class_id=student.class_id, created_by=user.id, kind="STUDENT_EXCUSE", status="PENDING",
        data=dict(body.model_dump(mode="json"), student_id=str(student.id),
            student_name=f"{student.first_name} {student.last_name}", document_path=None))
    db.add(row)
    await db.flush()
    return serialize(row)


async def list_for_child(db, user, student_id):
    _, student = await child(db, user, student_id)
    rows = (await db.execute(select(OperationalRecord).where(OperationalRecord.kind == "STUDENT_EXCUSE",
        OperationalRecord.organization_id == student.organization_id,
        OperationalRecord.data["student_id"].as_string() == str(student.id))
        .order_by(OperationalRecord.created_at.desc()))).scalars()
    return [serialize(row) for row in rows]


async def review(db, tenant, request_id, status, comment):
    row = await BaseRepository(db, tenant).get_by_id(request_id, OperationalRecord, for_update=True)
    if row.kind != "STUDENT_EXCUSE":
        raise NotFoundException("Mazeret talebi bulunamadı")
    if row.status != "PENDING":
        raise ConflictException("Bu mazeret talebi değerlendirilmiş")
    row.status = status
    row.data = dict(row.data, review_comment=comment, reviewed_by=str(tenant.user_id),
        reviewed_at=datetime.now(UTC).isoformat())
    await db.flush()
    return serialize(row)
