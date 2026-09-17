from typing import Optional, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import OrganizationRepository
from app.domain.entities.organization import Organization
from app.core.exceptions import AppException


class OrganizationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.org_repo = OrganizationRepository()

    async def create_organization(
        self,
        name: str,
        tax_number: str,
        tax_office: str,
        **kwargs
    ) -> Organization:
        # Check if tax number already exists
        existing = await self.org_repo.get_by_tax_number(self.db, tax_number)
        if existing:
            raise AppException("Bu vergi numarası zaten kullanımda", status_code=400)
        
        org_data = {
            "name": name,
            "tax_number": tax_number,
            "tax_office": tax_office,
            **kwargs
        }
        
        return await self.org_repo.create(self.db, org_data)

    async def update_organization(
        self,
        org_id: UUID,
        **kwargs
    ) -> Organization:
        org = await self.org_repo.get(self.db, org_id)
        if not org:
            raise AppException("Organizasyon bulunamadı", status_code=404)
        
        return await self.org_repo.update(self.db, org, kwargs)
