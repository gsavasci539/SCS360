from typing import Optional, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import BranchRepository
from app.domain.entities.branch import Branch
from app.core.exceptions import AppException


class BranchService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.branch_repo = BranchRepository()

    async def create_branch(
        self,
        organization_id: UUID,
        name: str,
        code: str,
        **kwargs
    ) -> Branch:
        # Check if code already exists for this organization
        existing = await self.branch_repo.get_by_code(self.db, code, organization_id)
        if existing:
            raise AppException("Bu şube kodu zaten kullanımda", status_code=400)
        
        branch_data = {
            "organization_id": organization_id,
            "name": name,
            "code": code,
            **kwargs
        }
        
        return await self.branch_repo.create(self.db, branch_data)

    async def update_branch(
        self,
        branch_id: UUID,
        **kwargs
    ) -> Branch:
        branch = await self.branch_repo.get(self.db, branch_id)
        if not branch:
            raise AppException("Şube bulunamadı", status_code=404)
        
        return await self.branch_repo.update(self.db, branch, kwargs)
