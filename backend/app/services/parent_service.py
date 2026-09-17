from typing import Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import ParentRepository
from app.domain.entities.parent import Parent
from app.core.exceptions import AppException


class ParentService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.parent_repo = ParentRepository()

    async def create_parent(
        self,
        organization_id: UUID,
        first_name: str,
        last_name: str,
        phone: str,
        **kwargs
    ) -> Parent:
        parent_data = {
            "organization_id": organization_id,
            "first_name": first_name,
            "last_name": last_name,
            "phone": phone,
            **kwargs
        }
        
        return await self.parent_repo.create(self.db, parent_data)

    async def update_parent(
        self,
        parent_id: UUID,
        **kwargs
    ) -> Parent:
        parent = await self.parent_repo.get(self.db, parent_id)
        if not parent:
            raise AppException("Veli bulunamadı", status_code=404)
        
        return await self.parent_repo.update(self.db, parent, kwargs)
