from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    success: bool = True
    message: str = "İşlem başarılı"
    data: T | None = None


class ErrorResponse(BaseModel):
    success: bool = False
    message: str
    errors: list[Any] = []


class PaginatedData(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int


class NotFoundException(Exception):
    pass


def success_response(data: Any = None, message: str = "İşlem başarılı", *, success: bool = True) -> dict:
    return {"success": success, "message": message, "data": data}


def error_response(message: str, errors: list | None = None) -> dict:
    return {"success": False, "message": message, "errors": errors or []}


def paginate(items: list, total: int, page: int, page_size: int) -> dict:
    total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }
