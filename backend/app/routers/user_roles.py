from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.permissions import require_permission
from app.core.responses import success_response
from app.domain.entities.user import User
from app.services import UserService

router = APIRouter(prefix="/api/users", tags=["User Roles"])


@router.post("/{user_id}/roles")
@require_permission("users.assign_roles")
async def assign_user_roles(
    user_id: UUID,
    role_ids: List[UUID],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = UserService(db)
    await service.assign_roles(user_id, role_ids)
    return success_response(message="Roller atandı")


@router.get("/{user_id}/roles")
@require_permission("users.view")
async def get_user_roles(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = UserService(db)
    roles = await service.get_user_roles(user_id)
    return success_response(roles)


@router.post("/{user_id}/branches")
@require_permission("users.assign_branches")
async def assign_user_branches(
    user_id: UUID,
    branch_ids: List[UUID],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = UserService(db)
    await service.assign_branches(user_id, branch_ids)
    return success_response(message="Şubeler atandı")
