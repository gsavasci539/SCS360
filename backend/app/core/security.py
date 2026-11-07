import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any, Callable
from uuid import UUID

import jwt
from jwt import InvalidTokenError as JWTError
from passlib.context import CryptContext
from fastapi import Security, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import get_settings

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt_sha256", "bcrypt"], deprecated="auto")
security = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except (ValueError, TypeError):
        # Missing or damaged legacy hashes must fail authentication instead of
        # turning a login attempt into an internal server error.
        return False


def create_access_token(subject: str | UUID, extra_claims: dict[str, Any] | None = None) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(subject), "exp": expire, "type": "access"}
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token_value() -> str:
    return secrets.token_urlsafe(64)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def decode_access_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM],
        options={"require": ["sub", "exp", "type"]})


def verify_access_token(token: str) -> dict[str, Any] | None:
    try:
        payload = decode_access_token(token)
        if payload.get("type") != "access":
            return None
        return payload
    except JWTError:
        return None


def create_password_reset_token_value() -> str:
    return secrets.token_urlsafe(48)


class PermissionChecker:
    def __init__(self, required_permission: str):
        self.required_permission = required_permission

    def __call__(self, credentials: HTTPAuthorizationCredentials = Security(security)) -> dict[str, Any]:
        if not credentials:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
        payload = verify_access_token(credentials.credentials)
        if not payload:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        
        permissions = payload.get("permissions", [])
        if self.required_permission not in permissions and "super_admin" not in permissions:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
        
        return payload


class TenantContext:
    def __init__(self):
        self.tenant_id: str | None = None
        self.user_id: str | None = None
        self.organization_id: str | None = None

    def set_context(self, tenant_id: str, user_id: str, organization_id: str | None = None):
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.organization_id = organization_id

    def get_tenant_id(self) -> str:
        return self.tenant_id or ""

    def get_user_id(self) -> str:
        return self.user_id or ""
