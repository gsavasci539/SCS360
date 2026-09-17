from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID
from pydantic import BaseModel

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.permissions import require_permission
from app.core.responses import success_response
from app.domain.entities.user import User

router = APIRouter(prefix="/api/settings", tags=["Settings"])


class AppSettingCreate(BaseModel):
    key: str
    value: str
    description: Optional[str] = None


class AppSettingUpdate(BaseModel):
    value: str
    description: Optional[str] = None


@router.get("")
@require_permission("settings.view")
async def get_settings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all application settings"""
    from sqlalchemy import select
    from app.domain.entities.app_setting import AppSetting
    
    result = await db.execute(
        select(AppSetting).where(
            AppSetting.organization_id == current_user.organization_id
        )
    )
    settings = result.scalars().all()
    
    # Convert to dict
    settings_dict = {}
    for setting in settings:
        settings_dict[setting.key] = {
            "value": setting.value,
            "description": setting.description
        }
    
    return success_response(settings_dict)


@router.get("/{key}")
@require_permission("settings.view")
async def get_setting(
    key: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific setting"""
    from sqlalchemy import select
    from app.domain.entities.app_setting import AppSetting
    
    result = await db.execute(
        select(AppSetting).where(
            AppSetting.organization_id == current_user.organization_id,
            AppSetting.key == key
        )
    )
    setting = result.scalar_one_or_none()
    
    if not setting:
        # Try to get system-wide setting
        result = await db.execute(
            select(AppSetting).where(
                AppSetting.organization_id.is_(None),
                AppSetting.key == key
            )
        )
        setting = result.scalar_one_or_none()
    
    if not setting:
        return success_response(None, "Ayar bulunamadı", success=False)
    
    return success_response({
        "key": setting.key,
        "value": setting.value,
        "description": setting.description
    })


@router.post("")
@require_permission("settings.update")
async def create_setting(
    setting: AppSettingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new setting"""
    from sqlalchemy import select
    from app.domain.entities.app_setting import AppSetting
    
    # Check if setting already exists
    result = await db.execute(
        select(AppSetting).where(
            AppSetting.organization_id == current_user.organization_id,
            AppSetting.key == setting.key
        )
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        return success_response(None, "Bu ayar zaten mevcut", success=False)
    
    new_setting = AppSetting(
        organization_id=current_user.organization_id,
        key=setting.key,
        value=setting.value,
        description=setting.description
    )
    db.add(new_setting)
    await db.flush()
    await db.refresh(new_setting)
    
    return success_response({
        "key": new_setting.key,
        "value": new_setting.value,
        "description": new_setting.description
    }, "Ayar oluşturuldu")


@router.put("/{key}")
@require_permission("settings.update")
async def update_setting(
    key: str,
    setting: AppSettingUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a setting"""
    from sqlalchemy import select
    from app.domain.entities.app_setting import AppSetting
    
    result = await db.execute(
        select(AppSetting).where(
            AppSetting.organization_id == current_user.organization_id,
            AppSetting.key == key
        )
    )
    db_setting = result.scalar_one_or_none()
    
    if not db_setting:
        return success_response(None, "Ayar bulunamadı", success=False)
    
    if setting.value is not None:
        db_setting.value = setting.value
    if setting.description is not None:
        db_setting.description = setting.description
    
    await db.flush()
    await db.refresh(db_setting)
    
    return success_response({
        "key": db_setting.key,
        "value": db_setting.value,
        "description": db_setting.description
    }, "Ayar güncellendi")


@router.delete("/{key}")
@require_permission("settings.update")
async def delete_setting(
    key: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a setting"""
    from sqlalchemy import select
    from app.domain.entities.app_setting import AppSetting
    
    result = await db.execute(
        select(AppSetting).where(
            AppSetting.organization_id == current_user.organization_id,
            AppSetting.key == key
        )
    )
    db_setting = result.scalar_one_or_none()
    
    if not db_setting:
        return success_response(None, "Ayar bulunamadı", success=False)
    
    await db.delete(db_setting)
    await db.flush()
    
    return success_response(message="Ayar silindi")
