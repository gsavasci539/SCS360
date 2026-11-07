"""School-owned payment accounts, write-only credentials and immutable snapshots."""
from datetime import UTC, datetime
import hashlib
import hmac
import json
from types import SimpleNamespace
from urllib.parse import urlparse
from uuid import UUID, uuid4

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import select

from app.application.services.online_payment_service import IyzicoGateway as _Gateway
from app.application.services.platform_service import lock_organization
from app.core.config import get_settings
from app.core.exceptions import AppException, ConflictException, ForbiddenException, ValidationException
from app.domain.entities.saas import OrganizationSubscription
from app.infrastructure.models.models import AuditAction, AuditLog, SchoolPaymentMerchant

HOSTS = {"SANDBOX": "https://sandbox-api.iyzipay.com", "LIVE": "https://api.iyzipay.com"}


def cipher():
    try:
        return Fernet(get_settings().SCHOOL_PAYMENT_ENCRYPTION_KEY.encode())
    except (ValueError, TypeError, AttributeError) as exc:
        raise AppException("Okul ödeme şifreleme anahtarı yapılandırılmamış", status_code=503) from exc


def seal_school_secret(values):
    return cipher().encrypt(json.dumps(values, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).decode()


def open_school_secret(ciphertext):
    try:
        value = json.loads(cipher().decrypt(ciphertext.encode()))
        if not isinstance(value, dict):
            raise ValueError("Invalid envelope")
        return value
    except (InvalidToken, ValueError, TypeError, AttributeError) as exc:
        raise AppException("Okul ödeme kaydı okunamadı; kurum sahibi kontrol etmeli", status_code=503) from exc


def valid_callback(value):
    try:
        url = urlparse(value)
        local = get_settings().APP_ENV in {"development", "test"} and url.hostname in {"127.0.0.1", "localhost"}
        port = url.port
        return bool(url.hostname and not url.username and not url.password and not url.query and not url.fragment
            and url.path == "/api/payments/iyzico/callback" and (port is None or port > 0)
            and (url.scheme == "https" or (local and url.scheme == "http")))
    except (TypeError, ValueError):
        return False


def valid_portal(value):
    try:
        url = urlparse(value)
        local = get_settings().APP_ENV in {"development", "test"} and url.hostname in {"127.0.0.1", "localhost"}
        port = url.port
        return bool(url.hostname and not url.username and not url.password and not url.query and not url.fragment
            and url.path in {"", "/"} and (url.scheme == "https" or (local and url.scheme == "http")) and (port is None or port > 0))
    except (TypeError, ValueError):
        return False


def revision(row):
    if row is None:
        return None
    content = [str(row.id), row.enabled, row.environment, row.credentials_ciphertext, str(row.updated_at)]
    return hashlib.sha256(json.dumps(content, separators=(",", ":")).encode()).hexdigest()


async def current(db, organization_id):
    return (await db.execute(select(SchoolPaymentMerchant).where(SchoolPaymentMerchant.organization_id == organization_id,
        SchoolPaymentMerchant.is_current.is_(True)).execution_options(populate_existing=True))).scalar_one_or_none()


async def can_manage(db, tenant):
    if tenant.organization_id is None or tenant.is_super_admin:
        return False
    if tenant.platform_admin:
        return True
    table = OrganizationSubscription.__table__
    owner = (await db.execute(select(table.c.owner_user_id).where(table.c.organization_id == tenant.organization_id))).scalar_one_or_none()
    return owner == tenant.user_id if owner is not None else "owner" in tenant.role_slugs


class SchoolGateway(_Gateway):
    def __init__(self, values):
        if values.get("environment") not in HOSTS or not all(isinstance(values.get(field), str) and 1 <= len(values[field]) <= 2048
            for field in ("api_key", "secret_key")):
            raise AppException("Okul ödeme hesabının şifreli anahtar bilgileri incelenmeli", status_code=503)
        self.portal_url = values["portal_url"]
        super().__init__(SimpleNamespace(APP_ENV=get_settings().APP_ENV, IYZICO_API_KEY=values["api_key"],
            IYZICO_SECRET_KEY=values["secret_key"], IYZICO_BASE_URL=HOSTS[values["environment"]],
            IYZICO_CALLBACK_URL=values["callback_url"], IYZICO_ORGANIZATION_ID=values["organization_id"], IYZICO_PAYMENT_ENABLED=True))

    def configured(self):
        super().configured()
        if not valid_callback(self.settings.IYZICO_CALLBACK_URL) or not valid_portal(self.portal_url):
            raise AppException("Okul ödeme dönüş ve portal adresleri yapılandırılmalı", status_code=503)
        if self.settings.IYZICO_BASE_URL == HOSTS["LIVE"] and (urlparse(self.settings.IYZICO_CALLBACK_URL).scheme != "https" or urlparse(self.portal_url).scheme != "https"):
            raise AppException("Canlı okul ödemesi için HTTPS dönüş ve portal adresleri gerekli", status_code=503)


def snapshot_gateway(gateway, organization_id, merchant_scope):
    gateway.configured()
    settings = gateway.settings
    environment = "LIVE" if urlparse(settings.IYZICO_BASE_URL).hostname == "api.iyzipay.com" else "SANDBOX"
    account = merchant_scope.removeprefix("school:") if merchant_scope.startswith("school:") else None
    values = {"version": 1, "organization_id": str(UUID(str(organization_id))), "merchant_account_id": account,
        "merchant_scope": merchant_scope, "environment": environment, "api_key": settings.IYZICO_API_KEY,
        "secret_key": settings.IYZICO_SECRET_KEY, "callback_url": settings.IYZICO_CALLBACK_URL,
        "portal_url": getattr(gateway, "portal_url", None) or get_settings().SCHOOL_PAYMENT_PORTAL_URL}
    SchoolGateway(values).configured()
    return seal_school_secret(values)


async def resolve_gateway(db, organization_id, checkout=None):
    organization_id = UUID(str(organization_id))
    if checkout is not None and getattr(checkout, "merchant_snapshot", None):
        values = open_school_secret(checkout.merchant_snapshot)
        account_id = getattr(checkout, "merchant_account_id", None)
        expected = str(account_id) if account_id else None
        if (values.get("version") != 1 or values.get("organization_id") != str(organization_id)
            or str(checkout.organization_id) != str(organization_id) or values.get("merchant_scope") != checkout.merchant_scope
            or values.get("merchant_account_id") != expected or values.get("environment") not in HOSTS
            or not all(isinstance(values.get(field), str) and values[field] for field in ("api_key", "secret_key", "callback_url", "portal_url"))):
            raise AppException("Okul ödeme oturumu hesapla eşleşmiyor", status_code=503)
        gateway = SchoolGateway(values); gateway.configured()
        return {"gateway": gateway, "merchant_account_id": account_id, "merchant_scope": checkout.merchant_scope,
            "merchant_snapshot": checkout.merchant_snapshot}
    if checkout is not None:
        if getattr(checkout, "merchant_account_id", None) is not None or getattr(checkout, "merchant_scope", None) not in {None, "legacy:" + str(organization_id)}:
            raise AppException("Eski ödeme hesabı incelenmeli", status_code=503)
    else:
        row = await current(db, organization_id)
        if row:
            if not row.enabled:
                raise AppException("Bu kurumda online öğrenci ödemesi kapalı", status_code=503)
            credentials = open_school_secret(row.credentials_ciphertext)
            values = {"organization_id": str(organization_id), "environment": row.environment,
                "api_key": credentials.get("api_key"), "secret_key": credentials.get("secret_key"),
                "callback_url": get_settings().SCHOOL_PAYMENT_CALLBACK_URL, "portal_url": get_settings().SCHOOL_PAYMENT_PORTAL_URL}
            gateway = SchoolGateway(values); gateway.configured()
            scope = "school:" + str(row.id)
            return {"gateway": gateway, "merchant_account_id": row.id, "merchant_scope": scope,
                "merchant_snapshot": snapshot_gateway(gateway, organization_id, scope)}
    # Keep monkeypatchable legacy adapters and old callback behavior separate.
    from app.application.services import online_payment_service
    gateway = online_payment_service.IyzicoGateway()
    if checkout is None:
        gateway.require_organization(organization_id)
    else:
        try:
            bound = UUID(str(gateway.settings.IYZICO_ORGANIZATION_ID))
        except (AttributeError, TypeError, ValueError):
            bound = None
        if bound != organization_id:
            raise AppException("Eski ödeme hesabının kurum bağlantısı incelenmeli", status_code=503)
    gateway.configured()
    return {"gateway": gateway, "merchant_account_id": None, "merchant_scope": "legacy:" + str(organization_id), "merchant_snapshot": None}


async def status(db, tenant):
    manager = await can_manage(db, tenant)
    if not manager and (tenant.is_super_admin or not tenant.organization_id or not tenant.has_any_permission(["finance.read", "finance.write", "parent.make_payment"])):
        raise ForbiddenException("Ödeme hesabını kurum sahibi seçilmiş kurum bağlamında yönetebilir")
    available = False
    try:
        await resolve_gateway(db, tenant.organization_id)
        available = True
    except AppException:
        pass
    if not manager:
        return {"can_manage": False, "available": available}
    row = await current(db, tenant.organization_id)
    encrypted = False
    try: cipher(); encrypted = True
    except AppException: pass
    configured = False
    if row and row.credentials_ciphertext:
        try:
            keys = open_school_secret(row.credentials_ciphertext)
            configured = all(isinstance(keys.get(field), str) and 1 <= len(keys[field]) <= 2048 for field in ("api_key", "secret_key"))
        except AppException: pass
    settings = get_settings()
    return {"can_manage": True, "configured": configured, "enabled": bool(row and row.enabled),
        "environment": row.environment if row else None, "account_id": str(row.id) if row else None,
        "revision": revision(row), "has_api_key": configured, "has_secret_key": configured,
        "callback_configured": valid_callback(settings.SCHOOL_PAYMENT_CALLBACK_URL),
        "portal_configured": valid_portal(settings.SCHOOL_PAYMENT_PORTAL_URL), "encryption_configured": encrypted,
        "production_compatible": not row or settings.APP_ENV != "production" or row.environment == "LIVE",
        "available": available, "updated_at": row.updated_at.replace(tzinfo=UTC).isoformat() if row and row.updated_at else None}


async def update(db, tenant, body):
    if not await can_manage(db, tenant):
        raise ForbiddenException("Okul ödeme hesabını yalnız kurum sahibi yönetebilir")
    await lock_organization(db, tenant.organization_id)
    values = body.model_dump(mode="json", exclude={"api_key", "secret_key", "request_id"})
    for field in ("api_key", "secret_key"):
        value = getattr(body, field)
        values[field] = value.get_secret_value() if value is not None else None
    digest = hmac.new(get_settings().JWT_SECRET_KEY.encode(), json.dumps({"actor": str(tenant.user_id), "organization": str(tenant.organization_id), "body": values},
        sort_keys=True, separators=(",", ":")).encode(), hashlib.sha256).hexdigest()
    previous = (await db.execute(select(AuditLog).where(AuditLog.id == body.request_id))).scalar_one_or_none()
    if previous:
        audit = previous.new_values or {}
        if previous.user_id != tenant.user_id or previous.organization_id != tenant.organization_id or audit.get("event") != "SCHOOL_PAYMENT_MERCHANT_UPDATED" or not hmac.compare_digest(audit.get("digest", ""), digest):
            raise ConflictException("İstek kimliği başka bir işlemde kullanılmış")
        return audit["response"]
    table = AuditLog.__table__
    if (await db.execute(select(table.c.id).where(table.c.id == body.request_id))).first():
        raise ConflictException("İstek kimliği kullanılamıyor")
    row = await current(db, tenant.organization_id)
    if body.expected_revision != revision(row):
        raise ConflictException("Ödeme hesabı değişmiş; güncel ayarları yükleyin")
    if row and body.environment != row.environment and not body.replace_account:
        raise ConflictException("Ortam değişikliği için yeni sağlayıcı hesabını açıkça seçin")
    fresh = row is None or body.replace_account
    credentials = {}
    if row and not fresh and row.credentials_ciphertext and (body.enabled or values["api_key"] or values["secret_key"]):
        credentials = open_school_secret(row.credentials_ciphertext)
    for field in ("api_key", "secret_key"):
        if values[field] is not None:
            credentials[field] = values[field]
    if (body.enabled or fresh and (values["api_key"] or values["secret_key"])) and not all(credentials.get(field) for field in ("api_key", "secret_key")):
        raise ValidationException("İlk kurulum veya yeni hesap için API ve gizli anahtar birlikte gerekli")
    encrypted = seal_school_secret(credentials) if credentials else (row.credentials_ciphertext if row and not fresh else None)
    if body.enabled:
        if get_settings().APP_ENV == "production" and body.environment != "LIVE":
            raise ValidationException("Üretim kurumunda sandbox ödeme açılamaz")
        cipher()
        SchoolGateway({"organization_id": str(tenant.organization_id), "environment": body.environment, **credentials,
            "callback_url": get_settings().SCHOOL_PAYMENT_CALLBACK_URL, "portal_url": get_settings().SCHOOL_PAYMENT_PORTAL_URL}).configured()
    now = datetime.now(UTC)
    if fresh:
        if row:
            row.is_current = False
            await db.flush()
        row = SchoolPaymentMerchant(id=uuid4(), organization_id=tenant.organization_id, is_current=True,
            environment=body.environment, enabled=body.enabled, credentials_ciphertext=encrypted,
            created_by=tenant.user_id, updated_by=tenant.user_id, created_at=now, updated_at=now)
        db.add(row)
    else:
        row.enabled, row.environment, row.credentials_ciphertext = body.enabled, body.environment, encrypted
        row.updated_by, row.updated_at = tenant.user_id, now
    await db.flush()
    response = await status(db, tenant)
    db.add(AuditLog(id=body.request_id, organization_id=tenant.organization_id, user_id=tenant.user_id,
        action=AuditAction.UPDATE, entity_type="school_payment_merchant", entity_id=row.id,
        new_values={"event": "SCHOOL_PAYMENT_MERCHANT_UPDATED", "digest": digest, "response": response}))
    await db.flush()
    return response
