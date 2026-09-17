from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, or_, select
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
        return query.where(model.organization_id == self.tenant.organization_id)

    def _branch_filter(self, query, model=None):
        model = model or self.model
        if self.tenant.is_super_admin or not self.tenant.branch_ids:
            return query
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
