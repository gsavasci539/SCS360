import logging
import time
import uuid

import structlog
from fastapi import Request, Response
from fastapi.encoders import jsonable_encoder
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import get_settings
from app.core.exceptions import AppException
from app.core.responses import error_response
from app.core.web_session import ACCESS_COOKIE, require_csrf

settings = get_settings()


def setup_logging() -> None:
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    logging.basicConfig(format="%(message)s", level=logging.INFO)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        start = time.time()
        response = await call_next(request)
        duration = round((time.time() - start) * 1000, 2)
        logger = structlog.get_logger()
        logger.info(
            "request_completed",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=duration,
        )
        response.headers["X-Request-ID"] = request_id
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Apply response protections centrally, including API errors and preflights."""

    async def dispatch(self, request: Request, call_next) -> Response:
        if (
            request.cookies.get(ACCESS_COOKIE)
            and request.method.upper() not in {"GET", "HEAD", "OPTIONS"}
            and request.url.path != "/api/auth/web/login"
        ):
            try:
                require_csrf(request)
            except AppException as exc:
                from fastapi.responses import JSONResponse

                response = JSONResponse(status_code=exc.status_code, content=error_response(exc.message, exc.errors))
                response.headers.setdefault("X-Content-Type-Options", "nosniff")
                response.headers.setdefault("X-Frame-Options", "DENY")
                response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
                response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
                if request.url.path.startswith("/api/"):
                    response.headers["Cache-Control"] = "no-store, max-age=0"
                    response.headers["Pragma"] = "no-cache"
                origin = request.headers.get("origin")
                if origin and origin in settings.cors_origins_list:
                    response.headers["Access-Control-Allow-Origin"] = origin
                    response.headers["Access-Control-Allow-Credentials"] = "true"
                    response.headers["Vary"] = "Origin"
                return response
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store, max-age=0"
            response.headers["Pragma"] = "no-cache"
        return response


async def app_exception_handler(request: Request, exc: AppException) -> Response:
    from fastapi.responses import JSONResponse

    return JSONResponse(
        status_code=exc.status_code,
        content={**error_response(exc.message, exc.errors), "request_id": getattr(request.state, "request_id", None)},
        headers={"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None,
    )


async def http_exception_handler(request: Request, exc) -> Response:
    from fastapi.responses import JSONResponse
    message = exc.detail if isinstance(exc.detail, str) else "İstek tamamlanamadı"
    return JSONResponse(status_code=exc.status_code, headers=exc.headers,
        content=jsonable_encoder({**error_response(message), "detail": exc.detail,
            "request_id": getattr(request.state, "request_id", None)}))


async def request_validation_handler(request: Request, exc) -> Response:
    from fastapi.responses import JSONResponse
    errors = [{"loc": list(error["loc"]), "msg": error["msg"], "type": error["type"]} for error in exc.errors()]
    return JSONResponse(status_code=422, content={
        **error_response("Gönderilen bilgileri kontrol edin", errors), "detail": errors,
        "request_id": getattr(request.state, "request_id", None),
    })


async def generic_exception_handler(request: Request, exc: Exception) -> Response:
    from fastapi.responses import JSONResponse
    from sqlalchemy.exc import MultipleResultsFound

    logger = structlog.get_logger()
    request_id = getattr(request.state, "request_id", None)
    if isinstance(exc, MultipleResultsFound):
        logger.warning("ambiguous_database_record", path=request.url.path, request_id=request_id)
        return JSONResponse(status_code=409, content={
            **error_response("Birden fazla eski kayıt aynı kimlikle eşleşiyor; veri eşleştirmesi gerekli"), "request_id": request_id,
        }, headers={"X-Request-ID": request_id} if request_id else None)
    logger.exception("unhandled_exception", path=request.url.path, request_id=request_id)
    return JSONResponse(status_code=500, content={
        **error_response("Beklenmeyen bir hata oluştu"), "request_id": request_id,
    }, headers={"X-Request-ID": request_id} if request_id else None)
