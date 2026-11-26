from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import false, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenException, NotFoundException
from app.core.tenant import TenantContext


class BaseRepository:
    model = None

    def __init__(self, db: AsyncSession, tenant: TenantContext):
        self.db = db
        self.tenant = tenant

    def _org_filter(self, query, model=None):
        model = model or self.model
        if self.tenant.is_super_admin:
            return query
        if not self.tenant.organization_id:
            raise ForbiddenException()
        if getattr(model, "__tablename__", None) == "organizations":
            return query.where(model.id == self.tenant.organization_id)
        if hasattr(model, "organization_id"):
            return query.where(model.organization_id == self.tenant.organization_id)
        from app.infrastructure.models.models import Branch, Student
        if hasattr(model, "branch_id"):
            return query.where(model.branch_id.in_(select(Branch.id).where(Branch.organization_id == self.tenant.organization_id)))
        if hasattr(model, "student_id"):
            return query.where(model.student_id.in_(select(Student.id).where(Student.organization_id == self.tenant.organization_id)))
        if hasattr(model, "club_id"):
            from app.domain.entities.clubs import SchoolClub
            clubs = select(SchoolClub.id).join(Branch, Branch.id == SchoolClub.branch_id).where(Branch.organization_id == self.tenant.organization_id)
            return query.where(model.club_id.in_(clubs))
        if getattr(model, "__tablename__", None) in {"asset_assignments", "maintenance_requests"}:
            from app.domain.entities.inventory import InventoryItem
            items = select(InventoryItem.id).join(Branch, Branch.id == InventoryItem.branch_id).where(Branch.organization_id == self.tenant.organization_id)
            return query.where(model.item_id.in_(items))
        raise ForbiddenException("Kayıt için kurum kapsamı çözülemedi")

    def _branch_filter(self, query, model=None):
        model = model or self.model
        if self.tenant.has_institution_wide_branch_access:
            return query
        if not self.tenant.branch_ids:
            student_ids = self.db.info.get("accessible_student_ids") if self.db is not None else None
            if student_ids is not None:
                from app.infrastructure.models.models import Student
                students = Student.__table__
                student_branches = select(students.c.branch_id).where(
                    students.c.id.in_(student_ids), students.c.organization_id == self.tenant.organization_id,
                    students.c.deleted_at.is_(None), students.c.branch_id.is_not(None),
                )
                if getattr(model, "__tablename__", None) == "branches":
                    return query.where(model.id.in_(student_branches))
                if hasattr(model, "branch_id"):
                    return query.where(or_(model.branch_id.in_(student_branches), model.branch_id.is_(None)))
            if getattr(model, "__tablename__", None) == "branches":
                return query.where(false())
            if hasattr(model, "branch_id"):
                return query.where(model.branch_id.is_(None))
            return query
        if getattr(model, "__tablename__", None) == "branches":
            return query.where(model.id.in_(self.tenant.branch_ids))
        return query.where(
            or_(model.branch_id.in_(self.tenant.branch_ids), model.branch_id.is_(None))
        )

    async def get_by_id(self, id: UUID, model=None, *, for_update: bool = False):
        model = model or self.model
        query = select(model).where(model.id == id)
        if hasattr(model, "deleted_at"):
            query = query.where(model.deleted_at.is_(None))
        query = self._org_filter(query, model)
        if for_update:
            query = query.with_for_update()
        result = await self.db.execute(query)
        item = result.scalar_one_or_none()
        if not item:
            raise NotFoundException()
        if hasattr(item, "branch_id") and not self.tenant.can_access_branch(item.branch_id):
            accessible_student_ids = self.db.info.get("accessible_student_ids") if self.db is not None else None
            student_id = getattr(item, "student_id", None)
            if student_id is None and getattr(model, "__tablename__", None) == "students":
                student_id = item.id
            if accessible_student_ids is None or student_id not in accessible_student_ids:
                raise ForbiddenException()
        if getattr(model, "__tablename__", None) == "branches" and not self.tenant.can_access_branch(item.id):
            raise ForbiddenException()
        return item

    async def require_related(self, id: UUID, model=None):
        """Load a tenant-scoped related record before accepting its foreign key."""
        return await self.get_by_id(id, model)

    async def soft_delete(self, item):
        item.deleted_at = datetime.now(UTC)
        item.updated_by = self.tenant.user_id

    async def paginate(self, query, page: int, page_size: int):
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0
        offset = (page - 1) * page_size
        items = (await self.db.execute(query.offset(offset).limit(page_size))).scalars().all()
        return items, total
