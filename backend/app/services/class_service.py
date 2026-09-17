from typing import Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import ClassRepository
from app.domain.entities.class_ import Class
from app.core.exceptions import AppException


class ClassService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.class_repo = ClassRepository()

    async def create_class(
        self,
        organization_id: UUID,
        branch_id: UUID,
        name: str,
        code: str,
        **kwargs
    ) -> Class:
        # Check if code already exists for this organization
        existing = await self.class_repo.get_by_code(self.db, code, organization_id)
        if existing:
            raise AppException("Bu sınıf kodu zaten kullanımda", status_code=400)
        
        class_data = {
            "organization_id": organization_id,
            "branch_id": branch_id,
            "name": name,
            "code": code,
            **kwargs
        }
        
        return await self.class_repo.create(self.db, class_data)

    async def update_class(
        self,
        class_id: UUID,
        **kwargs
    ) -> Class:
        cls = await self.class_repo.get(self.db, class_id)
        if not cls:
            raise AppException("Sınıf bulunamadı", status_code=404)
        
        return await self.class_repo.update(self.db, cls, kwargs)
