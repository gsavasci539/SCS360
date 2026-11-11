"""Provider-specific credentials inside the existing encrypted school account envelope."""
import hashlib
import hmac
import json
from datetime import UTC, datetime
from urllib.parse import urlparse, urlunparse
from uuid import uuid4

from sqlalchemy import select

from app.application.services import school_payment_merchant as merchants
from app.application.services.payment_providers import FIELDS, HostedGateway
from app.application.services.platform_service import lock_organization
from app.core.config import get_settings
from app.core.exceptions import (
    AppException,
    ConflictException,
    ForbiddenException,
    ValidationException,
)
from app.infrastructure.models.models import AuditAction, AuditLog, SchoolPaymentMerchant


def callback_url(provider):
    original = get_settings().SCHOOL_PAYMENT_CALLBACK_URL
    if provider == "iyzico":
        return original
    parsed = urlparse(original)
    if not merchants.valid_callback(original):
        return ""
    return urlunparse(parsed._replace(path=f"/api/payments/{provider}/callback"))


def gateway(values):
    if values.get("provider") == "iyzico":
        return merchants.SchoolGateway(values)
    return HostedGateway(values)


def from_account(organization_id, row, credentials):
    provider = credentials.get("provider", "iyzico")
    values = {**credentials, "version": 2, "organization_id": str(organization_id), "environment": row.environment,
        "merchant_account_id": str(row.id), "merchant_scope": "school:" + str(row.id),
        "callback_url": callback_url(provider), "portal_url": get_settings().SCHOOL_PAYMENT_PORTAL_URL}
    adapter = gateway(values)
    adapter.configured()
    return {"gateway": adapter, "merchant_account_id": row.id, "merchant_scope": values["merchant_scope"],
        "merchant_snapshot": merchants.seal_school_secret(values)}


def from_snapshot(organization_id, checkout, values):
    if (values.get("organization_id") != str(organization_id) or str(checkout.organization_id) != str(organization_id)
        or values.get("merchant_account_id") != str(checkout.merchant_account_id)
        or values.get("merchant_scope") != checkout.merchant_scope
        or values.get("merchant_scope") != "school:" + str(checkout.merchant_account_id)):
        raise AppException("Sağlayıcı ödeme hesabı kurumla eşleşmiyor", status_code=503)
    adapter = gateway(values)
    adapter.configured()
    return {"gateway": adapter, "merchant_account_id": checkout.merchant_account_id,
        "merchant_scope": checkout.merchant_scope, "merchant_snapshot": checkout.merchant_snapshot}


async def update_account(db, tenant, body):
    if not await merchants.can_manage(db, tenant):
        raise ForbiddenException("Kurum ödeme hesabını yalnız kurum sahibi yönetebilir")
    await lock_organization(db, tenant.organization_id)
    row = await merchants.current(db, tenant.organization_id)
    old = merchants.open_school_secret(row.credentials_ciphertext) if row and row.credentials_ciphertext else {}
    provider = body.provider or old.get("provider", "iyzico")
    supplied = {key: value.get_secret_value().strip() for key, value in (body.credentials or {}).items() if value.get_secret_value().strip()}
    for key in ("api_key", "secret_key"):
        value = getattr(body, key)
        if value is not None and value.get_secret_value().strip():
            supplied[key] = value.get_secret_value().strip()
    if provider not in FIELDS or set(supplied) - set(FIELDS[provider]):
        raise ValidationException("Sağlayıcının beklediği anahtar alanlarını kullanın")
    digest = hmac.new(get_settings().JWT_SECRET_KEY.encode(), json.dumps({"actor": str(tenant.user_id),
        "organization": str(tenant.organization_id), "provider": provider, "environment": body.environment,
        "enabled": body.enabled, "replace_account": body.replace_account, "revision": body.expected_revision,
        "credentials": supplied}, sort_keys=True, separators=(",", ":")).encode(), hashlib.sha256).hexdigest()
    prior = (await db.execute(select(AuditLog).where(AuditLog.id == body.request_id))).scalar_one_or_none()
    if prior:
        cache = prior.new_values or {}
        if prior.user_id != tenant.user_id or prior.organization_id != tenant.organization_id or cache.get("event") != "SCHOOL_PROVIDER_UPDATED" or not hmac.compare_digest(cache.get("digest", ""), digest):
            raise ConflictException("İstek kimliği başka bir işlemde kullanılmış")
        return cache["response"]
    table = AuditLog.__table__
    if (await db.execute(select(table.c.id).where(table.c.id == body.request_id))).first():
        raise ConflictException("İstek kimliği kullanılamıyor")
    if body.expected_revision != merchants.revision(row):
        raise ConflictException("Ödeme hesabı değişmiş; güncel ayarları yükleyin")
    if row and (provider != old.get("provider", "iyzico") or body.environment != row.environment) and not body.replace_account:
        raise ConflictException("Sağlayıcı veya ortam değişikliği için yeni hesap seçimini onaylayın")
    fresh = row is None or body.replace_account
    credentials = {"provider": provider} if fresh else {**old, "provider": provider}
    credentials.update(supplied)
    if (body.enabled or supplied) and not all(credentials.get(field) for field in FIELDS[provider]):
        raise ValidationException("Seçili sağlayıcının bütün üye işyeri anahtarları gerekli")
    encrypted = merchants.seal_school_secret(credentials)
    if body.enabled:
        if get_settings().APP_ENV == "production" and body.environment != "LIVE":
            raise ValidationException("Üretim kurumunda sandbox ödeme açılamaz")
        gateway({**credentials, "organization_id": str(tenant.organization_id), "environment": body.environment,
            "callback_url": callback_url(provider), "portal_url": get_settings().SCHOOL_PAYMENT_PORTAL_URL}).configured()
    stamp = datetime.now(UTC)
    if fresh:
        if row:
            row.is_current = False
            await db.flush()
        row = SchoolPaymentMerchant(id=uuid4(), organization_id=tenant.organization_id, is_current=True,
            enabled=body.enabled, environment=body.environment, credentials_ciphertext=encrypted,
            created_by=tenant.user_id, updated_by=tenant.user_id, created_at=stamp, updated_at=stamp)
        db.add(row)
    else:
        row.enabled, row.environment, row.credentials_ciphertext = body.enabled, body.environment, encrypted
        row.updated_by, row.updated_at = tenant.user_id, stamp
    await db.flush()
    response = await merchants.status(db, tenant)
    db.add(AuditLog(id=body.request_id, organization_id=tenant.organization_id, user_id=tenant.user_id,
        action=AuditAction.UPDATE, entity_type="school_payment_merchant", entity_id=row.id,
        new_values={"event": "SCHOOL_PROVIDER_UPDATED", "digest": digest, "response": response}))
    await db.flush()
    return response
