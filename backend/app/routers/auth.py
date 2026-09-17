from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    RefreshRequest,
    ResetPasswordRequest,
)
from app.application.services.auth_service import AuthService
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.rate_limit import get_client_ip, limiter
from app.core.responses import success_response
from app.infrastructure.models.models import User

router = APIRouter(prefix="/api/auth", tags=["Auth"])


@router.post("/login")
@limiter.limit("5/minute")
async def login(request: Request, body: LoginRequest, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    ip = get_client_ip(request)
    user_agent = request.headers.get("user-agent")
    data = await service.login(body.email, body.password, ip, user_agent)
    return success_response(data, "Giriş başarılı")


@router.post("/refresh")
async def refresh(body: RefreshRequest, request: Request, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    ip = get_client_ip(request)
    user_agent = request.headers.get("user-agent")
    data = await service.refresh(body.refresh_token, ip, user_agent)
    return success_response(data, "Token yenilendi")


@router.post("/logout")
async def logout(
    body: RefreshRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = AuthService(db)
    await service.logout(body.refresh_token, user.id)
    return success_response(message="Çıkış yapıldı")


@router.get("/me")
async def me(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    data = await service.get_me(user)
    return success_response(data)


@router.post("/forgot-password")
@limiter.limit("3/minute")
async def forgot_password(
    request: Request, body: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)
):
    service = AuthService(db)
    await service.forgot_password(body.email)
    return success_response(message="Şifre sıfırlama bağlantısı gönderildi")


@router.post("/reset-password")
async def reset_password(body: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    await service.reset_password(body.token, body.new_password)
    return success_response(message="Şifre başarıyla güncellendi")
