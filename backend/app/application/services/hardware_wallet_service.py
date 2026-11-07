"""Authenticated RFID operations use the same atomic student wallet."""
from sqlalchemy import select

from app.application.services import canteen_wallet_service as wallets
from app.core.exceptions import ValidationException, NotFoundException
from app.core.dates import school_today
from app.infrastructure.models.models import RfidCard, Student
from app.infrastructure.repositories.base import BaseRepository
from app.application.services.operations_service import identifier


async def card(db, tenant, number):
    if tenant.organization_id is None:
        raise ValidationException("Kart işlemi için kurum bağlamı gerekli")
    row = (await db.execute(select(RfidCard).where(RfidCard.card_number == number,
        RfidCard.organization_id == str(tenant.organization_id)))).scalar_one_or_none()
    if row is None:
        raise NotFoundException("Kart bulunamadı")
    if row.status != "ACTIVE" or (row.expiry_date and row.expiry_date < school_today()):
        raise ValidationException("Kart aktif değil veya kullanım süresi dolmuş")
    if row.card_type != "STUDENT":
        raise ValidationException("Bu işlem için öğrenci cüzdan kartı gerekli")
    student = await BaseRepository(db, tenant).get_by_id(identifier(row.holder_id), Student)
    if student.organization_id != identifier(row.organization_id) or student.branch_id != identifier(row.branch_id):
        raise ValidationException("Kart ve öğrenci kurum/şube bilgileri eşleşmiyor")
    return row


async def balance(db, tenant, number):
    row = await card(db, tenant, number)
    student, wallet = await wallets.wallet(db, tenant, row.holder_id)
    return dict(wallets.serialize(student, wallet), card_number=row.card_number, holder_id=row.holder_id,
        holder_name=f"{student.first_name} {student.last_name}", holder_type=row.card_type, card_status=row.status)
