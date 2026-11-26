from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    ProfileUpdate,
    RefreshRequest,
    ResetPasswordRequest,
    WebLoginRequest,
)
from app.application.services.auth_service import AuthService
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.exceptions import UnauthorizedException
from app.core.rate_limit import get_client_ip, limiter
from app.core.responses import success_response
from app.core.security import hash_token
from app.core.web_session import (
    CSRF_COOKIE,
    REFRESH_COOKIE,
    REMEMBER_COOKIE,
    clear_session_cookies,
    cookie_secure,
    new_csrf_token,
    require_allowed_origin,
    require_csrf,
    set_session_cookies,
)
from app.infrastructure.models.models import RefreshToken, User

router = APIRouter(prefix="/api/auth", tags=["Auth"])


@router.post("/web/login")
@limiter.limit("5/minute")
async def web_login(
    request: Request, body: WebLoginRequest, response: Response,
    db: AsyncSession = Depends(get_db, scope="function"),
):
    require_allowed_origin(request)
    data = await AuthService(db).login(body.email, body.password, get_client_ip(request), request.headers.get("user-agent"))
    csrf_token = new_csrf_token()
    set_session_cookies(response, data["access_token"], data["refresh_token"], csrf_token, body.remember)
    return success_response({"user": data["user"], "csrf_token": csrf_token}, "Giriş başarılı")


@router.get("/web/csrf")
async def web_csrf(request: Request, response: Response):
    csrf_token = request.cookies.get(CSRF_COOKIE) or new_csrf_token()
    response.set_cookie(
        CSRF_COOKIE, csrf_token, secure=cookie_secure(),
        httponly=False, samesite="lax", path="/api",
    )
    return success_response({"csrf_token": csrf_token})


@router.post("/web/refresh")
@limiter.limit("10/minute")
async def web_refresh(request: Request, response: Response, db: AsyncSession = Depends(get_db, scope="function")):
    require_csrf(request)
    refresh_token = request.cookies.get(REFRESH_COOKIE)
    if not refresh_token:
        raise UnauthorizedException("Web oturumu sona erdi")
    data = await AuthService(db).refresh(refresh_token, get_client_ip(request), request.headers.get("user-agent"))
    csrf_token = request.cookies.get(CSRF_COOKIE) or new_csrf_token()
    set_session_cookies(response, data["access_token"], data["refresh_token"], csrf_token, request.cookies.get(REMEMBER_COOKIE) == "1")
    return success_response({"user": data["user"], "csrf_token": csrf_token}, "Oturum yenilendi")


@router.post("/web/logout")
async def web_logout(
    request: Request, response: Response, db: AsyncSession = Depends(get_db, scope="function"),
):
    require_csrf(request)
    refresh_token = request.cookies.get(REFRESH_COOKIE)
    if refresh_token:
        user_id = await db.scalar(select(RefreshToken.user_id).where(RefreshToken.token_hash == hash_token(refresh_token)))
        if user_id:
            await AuthService(db).logout(refresh_token, user_id)
    clear_session_cookies(response)
    return success_response(message="Çıkış yapıldı")


@router.post("/login")
@limiter.limit("5/minute")
async def login(request: Request, body: LoginRequest, db: AsyncSession = Depends(get_db, scope="function")):
    service = AuthService(db)
    ip = get_client_ip(request)
    user_agent = request.headers.get("user-agent")
    data = await service.login(body.email, body.password, ip, user_agent)
    return success_response(data, "Giriş başarılı")


@router.post("/refresh")
async def refresh(body: RefreshRequest, request: Request, db: AsyncSession = Depends(get_db, scope="function")):
    service = AuthService(db)
    ip = get_client_ip(request)
    user_agent = request.headers.get("user-agent")
    data = await service.refresh(body.refresh_token, ip, user_agent)
    return success_response(data, "Token yenilendi")


@router.post("/logout")
async def logout(
    body: RefreshRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    service = AuthService(db)
    await service.logout(body.refresh_token, user.id)
    return success_response(message="Çıkış yapıldı")


@router.get("/me")
async def me(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db, scope="function")):
    service = AuthService(db)
    data = await service.get_me(user)
    return success_response(data)


@router.put("/me")
@limiter.limit("10/minute")
async def update_me(
    request: Request, body: ProfileUpdate, user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    email = await AuthService(db).update_profile(user.id, body)
    return success_response({"id": str(user.id), "email": email}, "Profil güncellendi")


@router.post("/change-password")
@limiter.limit("5/minute")
async def change_password(
    request: Request, body: ChangePasswordRequest, user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    await AuthService(db).change_password(user.id, body.current_password, body.new_password)
    return success_response({"id": str(user.id)}, "Şifre güncellendi")


@router.post("/forgot-password")
@limiter.limit("3/minute")
async def forgot_password(
    request: Request, body: ForgotPasswordRequest, db: AsyncSession = Depends(get_db, scope="function")
):
    service = AuthService(db)
    await service.forgot_password(body.email)
    return success_response(message="Hesap kayıtlıysa şifre sıfırlama bağlantısı gönderim kuyruğuna alındı")


@router.post("/reset-password")
@limiter.limit("5/minute")
async def reset_password(
    request: Request,
    body: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db, scope="function"),
):
    service = AuthService(db)
    await service.reset_password(body.token, body.new_password)
    return success_response(message="Şifre başarıyla güncellendi")
