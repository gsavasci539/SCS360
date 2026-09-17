import logging
import time
import uuid

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import get_settings
from app.core.exceptions import AppException
from app.core.responses import error_response

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


async def app_exception_handler(request: Request, exc: AppException) -> Response:
    from fastapi.responses import JSONResponse

    return JSONResponse(
        status_code=exc.status_code,
        content=error_response(exc.message, exc.errors),
    )


async def generic_exception_handler(request: Request, exc: Exception) -> Response:
    from fastapi.responses import JSONResponse

    logger = structlog.get_logger()
    logger.exception("unhandled_exception", path=request.url.path)
    message = str(exc) if settings.APP_ENV == "development" else "Beklenmeyen bir hata oluştu"
    return JSONResponse(status_code=500, content=error_response(message))
