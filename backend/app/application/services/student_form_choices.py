"""Minimal, tenant-scoped choices for admissions without registry-read grants."""
from sqlalchemy import func, or_, select

from app.core.exceptions import NotFoundException
from app.core.responses import paginate
from app.infrastructure.models.models import Branch, ClassRoom, Organization, Student
from app.infrastructure.repositories.base import BaseRepository


async def choices(db, tenant, kind, *, page, page_size, search=None, organization_id=None,
                  branch_id=None, selected_id=None, student_id=None):
    repo = BaseRepository(db, tenant)
    current = await repo.get_by_id(student_id, Student) if student_id else None
    org_id = organization_id if tenant.is_super_admin else tenant.organization_id
    if organization_id and not tenant.can_access_organization(organization_id):
        raise NotFoundException()
    model = {"organizations": Organization, "branches": Branch, "classes": ClassRoom}[kind]
    query = repo._org_filter(select(model).where(model.deleted_at.is_(None)), model)
    if kind != "organizations":
        if not org_id:
            return {**paginate([], 0, page, page_size), "selected": None}
        query = repo._branch_filter(query.where(model.organization_id == org_id), model)
    if kind == "classes":
        if not branch_id:
            return {**paginate([], 0, page, page_size), "selected": None}
        branch = await repo.get_by_id(branch_id, Branch)
        if branch.organization_id != org_id:
            raise NotFoundException()
        query = query.where(ClassRoom.branch_id == branch_id)
        students = Student.__table__
        roster = select(func.count()).select_from(students).where(
            students.c.class_id == ClassRoom.id, students.c.organization_id == ClassRoom.organization_id,
            students.c.branch_id == ClassRoom.branch_id, students.c.deleted_at.is_(None)).scalar_subquery()
        query = query.add_columns(roster.label("student_count"))
        available = roster < ClassRoom.capacity if branch.is_active else False
    else:
        available = True
    current_id = None if current is None else {"organizations": current.organization_id,
        "branches": current.branch_id, "classes": current.class_id}[kind]
    selected_query = query.where(model.id == selected_id)
    if kind == "organizations":
        selected_query = selected_query.where(model.is_active.is_(True))
    elif selected_id != current_id:
        selected_query = selected_query.where(model.is_active.is_(True), available)
    selected = (await db.execute(selected_query)).first() if selected_id else None
    query = query.where(model.is_active.is_(True), available)
    if search:
        expression = model.name.ilike(f"%{search}%")
        if kind == "classes":
            expression = or_(expression, ClassRoom.code.ilike(f"%{search}%"))
        query = query.where(expression)
    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
    rows = (await db.execute(query.order_by(model.name, model.id).offset((page - 1) * page_size).limit(page_size))).all()

    def choice(row):
        item = row[0]
        name = item.name
        if kind == "classes":
            name += f" ({row.student_count}/{item.capacity})" if item.capacity > 0 else f" ({row.student_count} öğrenci)"
        if not item.is_active:
            name += " (pasif, mevcut seçim)"
        return {"id": str(item.id), "name": name}

    return {**paginate([choice(row) for row in rows], total, page, page_size),
        "selected": choice(selected) if selected else None}
