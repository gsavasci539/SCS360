"""Explicit, institution-scoped link between a contact and a login account."""
from sqlalchemy import exists, or_, select

from app.application.services.platform_service import audit, commit, lock_organization
from app.core.exceptions import ConflictException, ForbiddenException
from app.infrastructure.models.models import Parent, Role, User, UserRole, UserStatus
from app.infrastructure.repositories.base import BaseRepository


def candidates(organization_id, parent_id):
    users, roles, links, parents = User.__table__, Role.__table__, UserRole.__table__, Parent.__table__
    parent_role = exists(select(links.c.user_id).join(roles, roles.c.id == links.c.role_id).where(links.c.user_id == users.c.id,
        roles.c.slug == "parent", roles.c.deleted_at.is_(None), or_(roles.c.organization_id.is_(None), roles.c.organization_id == organization_id)))
    linked_elsewhere = exists(select(parents.c.id).where(parents.c.user_id == users.c.id, parents.c.deleted_at.is_(None), parents.c.id != parent_id))
    return select(users.c.id, users.c.first_name, users.c.last_name, users.c.email).where(users.c.organization_id == organization_id,
        users.c.deleted_at.is_(None), users.c.status == UserStatus.ACTIVE, users.c.is_super_admin.is_(False), parent_role, ~linked_elsewhere)


def require_manager(tenant):
    if not tenant.has_permission("parents.write") or not tenant.has_permission("users.write"):
        raise ForbiddenException("Veli ve kullanıcı yönetimi yetkileri gerekli")


async def options(db, tenant, parent_id, search, limit, offset):
    require_manager(tenant)
    parent = await BaseRepository(db, tenant).get_by_id(parent_id, Parent)
    query = candidates(parent.organization_id, parent.id)
    if search:
        query = query.where(or_(User.__table__.c.email.icontains(search, autoescape=True), User.__table__.c.first_name.icontains(search, autoescape=True), User.__table__.c.last_name.icontains(search, autoescape=True)))
    rows = (await db.execute(query.order_by(User.__table__.c.email, User.__table__.c.id).limit(limit).offset(offset))).all()
    return {"user_id": str(parent.user_id) if parent.user_id else None, "users": [{"id": str(row.id), "name": f"{row.first_name} {row.last_name}", "email": row.email} for row in rows]}


async def link(db, tenant, actor, parent_id, user_id):
    require_manager(tenant)
    parent = await BaseRepository(db, tenant).get_by_id(parent_id, Parent)
    org = await lock_organization(db, parent.organization_id)
    await db.refresh(parent)
    if user_id is not None and not (await db.execute(candidates(parent.organization_id, parent.id).where(User.__table__.c.id == user_id))).first():
        raise ConflictException("Etkin, veli rolündeki ve başka veli kaydına bağlı olmayan bir kurum kullanıcısı seçin")
    previous = str(parent.user_id) if parent.user_id else None
    parent.user_id, parent.updated_by = user_id, actor.id
    audit(db, actor, org, "PARENT_ACCOUNT_LINKED", {"parent_id": str(parent.id), "previous_user_id": previous, "user_id": str(user_id) if user_id else None})
    await commit(db)
    return {"parent_id": str(parent.id), "user_id": str(user_id) if user_id else None}
