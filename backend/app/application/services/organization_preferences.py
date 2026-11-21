from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.platform_service import lock_organization
from app.core.config import get_settings
from app.core.exceptions import ConflictException, ForbiddenException, NotFoundException, ValidationException
from app.infrastructure.models.models import AppSetting, Organization


UPLOAD_KEYS = ("max_upload_size_mb", "allowed_file_types")
NOTICE_KEYS = ("receipt_email_enabled", "overdue_reminders_enabled", "failed_notification_alerts_enabled")


class PreferencePatch(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    school_name: str | None = Field(default=None, min_length=1, max_length=255)
    academic_year: str | None = Field(default=None, pattern=r"^\d{4}-\d{4}$")
    default_currency: Literal["TRY", "EUR", "USD"] | None = None
    max_upload_size_mb: StrictInt | None = Field(default=None, ge=1)
    allowed_file_types: str | None = Field(default=None, min_length=1, max_length=255)
    receipt_email_enabled: StrictBool | None = None
    overdue_reminders_enabled: StrictBool | None = None
    failed_notification_alerts_enabled: StrictBool | None = None


class PreferencesUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    organization_id: UUID
    changes: PreferencePatch
    expected: dict[str, str | int | bool | None]


async def _setting_rows(db: AsyncSession, organization_id: UUID, keys):
    rows = (await db.scalars(select(AppSetting).where(
        AppSetting.organization_id == organization_id,
        AppSetting.setting_key.in_(keys),
    ))).all()
    return {row.setting_key: row for row in rows}


def _upload_limits(saved: dict) -> tuple[int, list[str]]:
    config = get_settings()
    extensions = list(dict.fromkeys(config.allowed_file_types_list))
    value = saved.get("max_upload_size_mb")
    maximum = min(value, config.MAX_UPLOAD_SIZE_MB) if type(value) is int and value > 0 else config.MAX_UPLOAD_SIZE_MB
    value = saved.get("allowed_file_types")
    if isinstance(value, str):
        configured = {item.strip().lower() for item in value.split(",") if item.strip()}
        extensions = [item for item in extensions if item in configured]
    return maximum, extensions


async def student_document_limits(db: AsyncSession, organization_id: UUID) -> tuple[int, list[str]]:
    rows = await _setting_rows(db, organization_id, UPLOAD_KEYS)
    return _upload_limits({key: row.setting_value for key, row in rows.items()})


def _snapshot(organization: Organization, rows: dict) -> dict:
    saved = {key: row.setting_value for key, row in rows.items()}
    config = get_settings()
    maximum, extensions = _upload_limits(saved)
    name, academic_year, currency = (saved.get(key) for key in ("school_name", "academic_year", "default_currency"))
    return {
        "organization_id": str(organization.id),
        "values": {
            "school_name": name if isinstance(name, str) and name.strip() else organization.name,
            "academic_year": academic_year if isinstance(academic_year, str) and academic_year.strip() else None,
            "default_currency": currency if currency in ("TRY", "EUR", "USD") else "TRY",
            "max_upload_size_mb": maximum,
            "allowed_file_types": ",".join(extensions),
            **{key: saved[key] if type(saved.get(key)) is bool else None for key in NOTICE_KEYS},
        },
        "upload_policy": {"max_size_mb": config.MAX_UPLOAD_SIZE_MB,
                          "allowed_extensions": list(dict.fromkeys(config.allowed_file_types_list))},
    }


async def read_preferences(db: AsyncSession, organization_id: UUID | None) -> dict:
    if organization_id is None:
        raise ForbiddenException("Önce bir kurum seçin")
    organization = await db.scalar(select(Organization).where(
        Organization.id == organization_id, Organization.deleted_at.is_(None),
    ))
    if organization is None:
        raise NotFoundException("Kurum bulunamadı")
    return _snapshot(organization, await _setting_rows(db, organization_id, PreferencePatch.model_fields))


async def save_preferences(
    db: AsyncSession, organization_id: UUID | None, actor_id: UUID, payload: PreferencesUpdate,
) -> dict:
    if organization_id is None:
        raise ForbiddenException("Önce bir kurum seçin")
    if payload.organization_id != organization_id:
        raise ForbiddenException("Seçili kurum değişti")
    changes = payload.changes.model_dump(exclude_unset=True)
    if not changes or set(changes) != set(payload.expected):
        raise ValidationException("Değişen her tercih için önceki değeri gönderin")
    organization = await lock_organization(db, organization_id)
    rows = await _setting_rows(db, organization_id, PreferencePatch.model_fields)
    snapshot = _snapshot(organization, rows)
    if "academic_year" in changes and changes["academic_year"] is not None:
        start, end = map(int, changes["academic_year"].split("-"))
        if end != start + 1:
            raise ValidationException("Akademik yıl ardışık iki yıldan oluşmalıdır")
    if "max_upload_size_mb" in changes and changes["max_upload_size_mb"] is not None:
        if changes["max_upload_size_mb"] > snapshot["upload_policy"]["max_size_mb"]:
            raise ValidationException("Yükleme boyutu sunucu üst sınırını geçemez")
    if "allowed_file_types" in changes and changes["allowed_file_types"] is not None:
        available = snapshot["upload_policy"]["allowed_extensions"]
        configured = {item.strip().lower() for item in changes["allowed_file_types"].split(",") if item.strip()}
        if not configured or not configured.issubset(available):
            raise ValidationException("Yalnız sunucunun izin verdiği uzantıları seçin")
        changes["allowed_file_types"] = ",".join(item for item in available if item in configured)
    for key in ("school_name", "default_currency", *UPLOAD_KEYS):
        if key in changes and changes[key] is None:
            raise ValidationException("Zorunlu kurum tercihleri boş bırakılamaz")
    current = snapshot["values"]
    for key, value in changes.items():
        if current[key] != value and (type(current[key]) is not type(payload.expected[key]) or current[key] != payload.expected[key]):
            raise ConflictException("Kurum tercihleri değişti. Güncel değerleri yükleyip tekrar deneyin")
    for key, value in changes.items():
        if current[key] == value:
            continue
        if key not in rows:
            rows[key] = AppSetting(organization_id=organization_id, setting_key=key)
            db.add(rows[key])
        rows[key].setting_value = value
        rows[key].updated_by = actor_id
    await db.flush()
    return _snapshot(organization, rows)
