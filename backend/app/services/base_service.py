from typing import Generic, TypeVar, Optional, List, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.base_repository import BaseRepository

ModelType = TypeVar("ModelType")
RepositoryType = TypeVar("RepositoryType", bound=BaseRepository)


class BaseService(Generic[ModelType, RepositoryType]):
    def __init__(self, repository: RepositoryType):
        self.repository = repository

    async def get(self, db: AsyncSession, id: UUID) -> Optional[ModelType]:
        return await self.repository.get(db, id)

    async def get_multi(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[ModelType]:
        return await self.repository.get_multi(db, skip, limit, filters)

    async def create(
        self,
        db: AsyncSession,
        obj_in: Dict[str, Any]
    ) -> ModelType:
        return await self.repository.create(db, obj_in)

    async def update(
        self,
        db: AsyncSession,
        db_obj: ModelType,
        obj_in: Dict[str, Any]
    ) -> ModelType:
        return await self.repository.update(db, db_obj, obj_in)

    async def delete(self, db: AsyncSession, id: UUID) -> Optional[ModelType]:
        return await self.repository.delete(db, id)

    async def soft_delete(self, db: AsyncSession, id: UUID) -> Optional[ModelType]:
        return await self.repository.soft_delete(db, id)

    async def count(self, db: AsyncSession, filters: Optional[Dict[str, Any]] = None) -> int:
        return await self.repository.count(db, filters)
