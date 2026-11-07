from datetime import UTC, datetime

from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import IntegrityError

from app.core.dates import school_today
from app.core.exceptions import ConflictException, ValidationException
from app.domain.entities.inventory import AssetAssignment, InventoryItem, InventoryLocation, MaintenanceRequest
from app.infrastructure.models.models import Branch, User
from app.infrastructure.repositories.base import BaseRepository


async def related_records(db, model, ids):
    if not ids:
        return {}
    rows = (await db.execute(select(model).where(model.id.in_(ids)))).scalars()
    return {row.id: row for row in rows if row is not None}


async def validate_item(db, tenant, body, item_id=None):
    repo = BaseRepository(db, tenant)
    await repo.get_by_id(body.branch_id, Branch)
    if not body.item_code.strip() or not body.item_name.strip():
        raise ValidationException("Demirbaş kodu ve adı gerekli")
    if body.location_id:
        location = await repo.get_by_id(body.location_id, InventoryLocation)
        if location.branch_id != body.branch_id:
            raise ValidationException("Konum ve demirbaş aynı şubede olmalı")
    # The current database contract makes item codes unique globally. Do not
    # disclose another institution's item; return a normal conflict response.
    table = InventoryItem.__table__
    duplicate = (await db.execute(select(table.c.id).where(table.c.item_code == body.item_code,
        table.c.id != item_id if item_id else True).limit(1))).first()
    if duplicate:
        raise ConflictException("Bu demirbaş kodu kullanılıyor")
    if item_id:
        existing = await repo.get_by_id(item_id, InventoryItem, for_update=True)
        if existing.branch_id != body.branch_id:
            previous_branch = await repo.get_by_id(existing.branch_id, Branch)
            next_branch = await repo.get_by_id(body.branch_id, Branch)
            if previous_branch.organization_id != next_branch.organization_id:
                raise ValidationException("Demirbaş farklı bir kuruma taşınamaz")
            active = (await db.execute(select(AssetAssignment.id).where(AssetAssignment.item_id == item_id,
                AssetAssignment.status == "ASSIGNED").limit(1))).first()
            if active:
                raise ConflictException("Aktif zimmeti bulunan demirbaş başka şubeye taşınamaz")


async def save_item(db, tenant, body, item_id=None):
    await validate_item(db, tenant, body, item_id)
    if item_id:
        row = await BaseRepository(db, tenant).get_by_id(item_id, InventoryItem, for_update=True)
        for key, value in body.model_dump().items():
            setattr(row, key, value)
    else:
        row = InventoryItem(**body.model_dump(), status="ACTIVE")
        db.add(row)
    try:
        await db.flush()
    except IntegrityError as error:
        raise ConflictException("Bu demirbaş kodu kullanılıyor") from error
    await db.refresh(row, attribute_names=["updated_at"])
    return {"id": str(row.id), "item_code": row.item_code, "item_name": row.item_name, "status": row.status,
        "created_at": row.created_at.isoformat(), "updated_at": row.updated_at.isoformat()}


async def assignee(db, tenant, item, user_id):
    repo = BaseRepository(db, tenant)
    branch = await repo.get_by_id(item.branch_id, Branch)
    user = await repo.get_by_id(user_id, User)
    if user.organization_id != branch.organization_id or getattr(user.status, "value", user.status) != "ACTIVE":
        raise ValidationException("Zimmet veya bakım sorumlusu kurumun aktif kullanıcısı olmalı")


async def assign(db, tenant, body):
    repo = BaseRepository(db, tenant)
    item = await repo.get_by_id(body.item_id, InventoryItem, for_update=True)
    await assignee(db, tenant, item, body.assigned_to)
    if item.status != "ACTIVE":
        raise ValidationException("Yalnızca aktif demirbaş zimmetlenebilir")
    table = AssetAssignment.__table__
    active = select(table.c.id).where(table.c.item_id == item.id, table.c.status == "ASSIGNED").exists()
    claimed = await db.execute(update(InventoryItem).where(InventoryItem.id == item.id, InventoryItem.status == "ACTIVE", ~active)
        .values(updated_at=datetime.now(UTC)).execution_options(synchronize_session=False))
    if claimed.rowcount != 1:
        raise ConflictException("Demirbaş zaten zimmetli; önce iade edilmeli")
    if body.return_date and body.return_date < school_today():
        raise ValidationException("Planlanan iade tarihi zimmet tarihinden önce olamaz")
    row = AssetAssignment(**body.model_dump(), assigned_date=school_today(), status="ASSIGNED")
    db.add(row)
    await db.flush()
    return {"id": str(row.id), "assigned_date": row.assigned_date.isoformat(), "status": row.status, "created_at": row.created_at.isoformat()}


async def return_assignment(db, tenant, assignment_id, notes):
    repo = BaseRepository(db, tenant)
    row = await repo.get_by_id(assignment_id, AssetAssignment)
    await repo.get_by_id(row.item_id, InventoryItem, for_update=True)
    await db.refresh(row, with_for_update=True)
    if row.status != "RETURNED":
        row.status, row.return_date = "RETURNED", school_today()
        if notes is not None:
            row.notes = notes
        await db.flush()
    return {"id": str(row.id), "status": row.status, "return_date": row.return_date.isoformat() if row.return_date else None}


async def maintenance(db, tenant, body):
    item = await BaseRepository(db, tenant).get_by_id(body.item_id, InventoryItem)
    if not body.issue_description.strip():
        raise ValidationException("Bakım talebinin açıklaması gerekli")
    if body.assigned_to:
        await assignee(db, tenant, item, body.assigned_to)
    row = MaintenanceRequest(**body.model_dump(), reported_by=tenant.user_id, status="PENDING")
    db.add(row)
    await db.flush()
    return {"id": str(row.id), "priority": row.priority, "status": row.status, "created_at": row.created_at.isoformat()}


async def resolve(db, tenant, request_id, notes):
    row = await BaseRepository(db, tenant).get_by_id(request_id, MaintenanceRequest, for_update=True)
    if row.status != "RESOLVED":
        row.status, row.resolved_at, row.resolution_notes = "RESOLVED", datetime.now(UTC), notes
        await db.flush()
    instant = row.resolved_at
    if instant is not None and instant.tzinfo is None:
        instant = instant.replace(tzinfo=UTC)
    return {"id": str(row.id), "status": row.status, "resolved_at": instant.isoformat() if instant else None}


async def options(db, tenant, branch_id, item_search, user_search):
    branches = (await db.execute(select(Branch.id, Branch.name).where(Branch.deleted_at.is_(None)).order_by(Branch.name, Branch.id))).all()
    result = {"branches": [{"id": str(row.id), "name": row.name} for row in branches if row.id is not None], "items": [], "locations": [], "users": []}
    if branch_id is None:
        return result
    branch = await BaseRepository(db, tenant).get_by_id(branch_id, Branch)
    item_query = select(InventoryItem).where(InventoryItem.branch_id == branch.id, InventoryItem.status == "ACTIVE")
    if item_search.strip():
        value = "%" + item_search.strip() + "%"
        item_query = item_query.where(or_(InventoryItem.item_name.ilike(value), InventoryItem.item_code.ilike(value)))
    items = [row for row in (await db.execute(item_query.order_by(InventoryItem.item_code, InventoryItem.id).limit(101))).scalars() if row is not None]
    assigned = AssetAssignment.__table__
    assigned_ids = set((await db.execute(select(assigned.c.item_id).where(assigned.c.item_id.in_([row.id for row in items]),
        assigned.c.status == "ASSIGNED"))).scalars()) if items else set()
    user_query = select(User.id, User.first_name, User.last_name).where(User.organization_id == branch.organization_id, User.deleted_at.is_(None), User.status == "ACTIVE")
    if user_search.strip():
        value = "%" + user_search.strip() + "%"
        user_query = user_query.where(or_(User.first_name.ilike(value), User.last_name.ilike(value), User.email.ilike(value)))
    users = [row for row in (await db.execute(user_query.order_by(User.last_name, User.first_name, User.id).limit(101))).all() if row.id is not None]
    locations = (await db.execute(select(InventoryLocation).where(InventoryLocation.branch_id == branch.id)
        .order_by(InventoryLocation.location_name, InventoryLocation.id))).scalars()
    result.update(items=[{"id": str(row.id), "name": row.item_name, "code": row.item_code, "is_assigned": row.id in assigned_ids} for row in items[:100]],
        more_items=len(items) > 100, more_users=len(users) > 100,
        users=[{"id": str(row.id), "name": f"{row.first_name} {row.last_name}"} for row in users[:100]],
        locations=[{"id": str(row.id), "name": row.location_name} for row in locations if row is not None])
    return result


async def statistics(db):
    rows = (await db.execute(select(InventoryItem.id, InventoryItem.status))).all()
    ids = [row.id for row in rows]
    active_ids = [row.id for row in rows if row.status == "ACTIVE"]
    assignments, maintenance = AssetAssignment.__table__, MaintenanceRequest.__table__
    assigned = (await db.execute(select(func.count(func.distinct(assignments.c.item_id))).where(assignments.c.item_id.in_(active_ids),
        assignments.c.status == "ASSIGNED"))).scalar_one() if active_ids else 0
    pending = (await db.execute(select(func.count(maintenance.c.id)).where(maintenance.c.item_id.in_(ids),
        maintenance.c.status != "RESOLVED"))).scalar_one() if ids else 0
    recommendations = []
    if pending:
        recommendations.append(f"Açık bakım talebi sayısı: {pending}.")
    if not ids:
        recommendations.append("İlk demirbaşı kaydedip konum ve zimmet bilgilerini ekleyin.")
    return {"total_items": len(ids), "assigned_count": assigned, "available_count": len(active_ids) - assigned,
        "pending_maintenance": pending, "source": "DATABASE_AND_RULES", "recommendations": recommendations}
