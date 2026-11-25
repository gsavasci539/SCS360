from __future__ import annotations

import hmac
import secrets

from fastapi import Request, Response

from app.core.config import get_settings
from app.core.exceptions import ForbiddenException

settings = get_settings()

ACCESS_COOKIE = "scs360_access"
REFRESH_COOKIE = "scs360_refresh"
CSRF_COOKIE = "scs360_csrf"
REMEMBER_COOKIE = "scs360_remember"
CSRF_HEADER = "X-CSRF-Token"


def cookie_secure() -> bool:
    return settings.APP_ENV.strip().lower() in {"staging", "production"}


def new_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def require_allowed_origin(request: Request) -> None:
    origin = request.headers.get("origin")
    if not origin or origin not in settings.cors_origins_list:
        raise ForbiddenException("Web oturum isteğinin kaynağı doğrulanamadı")


def require_csrf(request: Request) -> None:
    require_allowed_origin(request)
    cookie_token = request.cookies.get(CSRF_COOKIE, "")
    header_token = request.headers.get(CSRF_HEADER, "")
    if not cookie_token or not header_token or not hmac.compare_digest(cookie_token, header_token):
        raise ForbiddenException("Web oturum güvenlik doğrulaması başarısız")


def set_session_cookies(response: Response, access_token: str, refresh_token: str, csrf_token: str, remember: bool) -> None:
    secure = cookie_secure()
    common = {"secure": secure, "samesite": "lax"}
    response.set_cookie(
        ACCESS_COOKIE, access_token, max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        httponly=True, path="/api", **common,
    )
    response.set_cookie(
        REFRESH_COOKIE, refresh_token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60 if remember else None,
        httponly=True, path="/api/auth/web", **common,
    )
    response.set_cookie(
        REMEMBER_COOKIE, "1" if remember else "0",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60 if remember else None,
        httponly=True, path="/api/auth/web", **common,
    )
    response.set_cookie(
        CSRF_COOKIE, csrf_token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60 if remember else None,
        httponly=False, path="/api", **common,
    )


def clear_session_cookies(response: Response) -> None:
    secure = cookie_secure()
    common = {"secure": secure, "samesite": "lax"}
    response.delete_cookie(ACCESS_COOKIE, path="/api", **common)
    response.delete_cookie(REFRESH_COOKIE, path="/api/auth/web", **common)
    response.delete_cookie(REMEMBER_COOKIE, path="/api/auth/web", **common)
    response.delete_cookie(CSRF_COOKIE, path="/api", **common)
