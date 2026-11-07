"""Validate the holder, branch and device together before granting entry."""
from sqlalchemy import or_, select

from app.application.services.operations_service import identifier
from app.infrastructure.models.models import (Branch, ClassRoom, ClassTeacher, Device, Role,
    RfidCard, Student, User, UserBranch, UserRole)
from app.core.dates import school_today
from app.core.exceptions import ValidationException
from app.core.teaching import teacher_class_condition


async def device_at_branch(db, device_id):
    row = (await db.execute(select(Device).where(Device.id == device_id))).scalar_one_or_none()
    if row is None or not row.branch_id or not row.organization_id:
        return None
    branch = (await db.execute(select(Branch).where(Branch.id == identifier(row.branch_id),
        Branch.organization_id == identifier(row.organization_id), Branch.deleted_at.is_(None)))).scalar_one_or_none()
    return row if branch is not None else None


async def check(db, holder_id, card_type, device_id):
    if card_type not in {"STUDENT", "STAFF"}:
        return {"access_granted": False, "reason": "Geçersiz kart türü"}
    device = await device_at_branch(db, device_id)
    if device is None or device.status != "ACTIVE":
        return {"access_granted": False, "reason": "Aktif ve erişilebilir bir cihaz gerekli"}
    model = Student if card_type == "STUDENT" else User
    holder = (await db.execute(select(model).where(model.id == identifier(holder_id),
        model.deleted_at.is_(None)))).scalar_one_or_none()
    if holder is None or getattr(holder.status, "value", holder.status) != "ACTIVE":
        return {"access_granted": False, "reason": "Aktif ve erişilebilir bir kart sahibi gerekli"}
    if holder.organization_id != identifier(device.organization_id):
        return {"access_granted": False, "reason": "Kart sahibi bu kuruma ait değil"}
    branch_id = identifier(device.branch_id)
    if card_type == "STUDENT":
        allowed = holder.branch_id == branch_id
    else:
        membership = select(UserRole.user_id).join(Role, Role.id == UserRole.role_id).where(
            UserRole.user_id == holder.id, Role.slug != "parent", Role.deleted_at.is_(None),
            or_(Role.organization_id.is_(None), Role.organization_id == holder.organization_id))
        linked = or_(User.id.in_(select(UserBranch.user_id).where(UserBranch.branch_id == branch_id)),
            User.id.in_(select(ClassRoom.teacher_id).where(ClassRoom.branch_id == branch_id, ClassRoom.deleted_at.is_(None))),
            User.id.in_(select(ClassTeacher.user_id).join(ClassRoom, ClassRoom.id == ClassTeacher.class_id)
                .where(ClassRoom.branch_id == branch_id, ClassRoom.deleted_at.is_(None))),
            select(ClassRoom.id).where(ClassRoom.branch_id == branch_id, ClassRoom.deleted_at.is_(None),
                teacher_class_condition(ClassRoom, holder.id)).exists())
        allowed = (await db.execute(select(User.id).where(User.id == holder.id, User.id.in_(membership), linked))).scalar_one_or_none() is not None
    return {"access_granted": allowed, "reason": "Geçişe izin verildi" if allowed else "Kart sahibinin bu şubeye erişimi yok"}


async def validate_log(db, body):
    device = await device_at_branch(db, body.device_id)
    if device is None or identifier(device.branch_id) != body.branch_id:
        raise ValidationException("Cihaz ve kayıt şubesi eşleşmiyor")
    card = (await db.execute(select(RfidCard).where(RfidCard.card_number == body.card_number,
        RfidCard.organization_id == device.organization_id, RfidCard.branch_id == device.branch_id))).scalar_one_or_none()
    if card is None:
        if body.access_status == "GRANTED":
            raise ValidationException("Kayıtlı kart olmadan geçiş onaylanamaz")
        return device, None
    if body.holder_id is None or identifier(card.holder_id) != body.holder_id:
        raise ValidationException("Kart ve kart sahibi eşleşmiyor")
    if body.access_status == "GRANTED":
        if card.status != "ACTIVE" or (card.expiry_date and card.expiry_date < school_today()):
            raise ValidationException("Kart aktif değil veya kullanım süresi dolmuş")
        result = await check(db, body.holder_id, card.card_type, device.id)
        if not result["access_granted"]:
            raise ValidationException(result["reason"])
    return device, card
