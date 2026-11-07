from uuid import uuid4

from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient
import pytest

from app.core.dependencies import get_tenant_context
from app.core.permissions import require_permission
from app.core.tenant import TenantContext
from app.core.exceptions import AppException
from app.core.middleware import app_exception_handler


@pytest.mark.asyncio
async def test_decorator_injects_context_for_endpoints_without_tenant_parameter():
    app = FastAPI()
    app.add_exception_handler(AppException, app_exception_handler)
    tenant = TenantContext(user_id=uuid4(), permissions={"parents.write"})
    app.dependency_overrides[get_tenant_context] = lambda: tenant

    @app.post("/records")
    @require_permission("parents.write")
    async def create_record():
        return {"created": True}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        assert (await client.post("/records")).status_code == 200
        tenant.permissions.clear()
        assert (await client.post("/records")).status_code == 403


def test_equivalent_permission_names_work_in_both_directions():
    for existing, requested in [("students.read", "student.read"), ("student.read", "students.read")]:
        tenant = TenantContext(user_id=uuid4(), permissions={existing})
        assert tenant.has_permission(requested)
        assert not tenant.has_permission("student.write")


@pytest.mark.asyncio
async def test_openapi_keeps_the_runtime_handler_for_duplicate_routes():
    from fastapi import APIRouter
    from app.core.routing import RouterRegistry

    app = FastAPI()
    router = APIRouter()

    @router.get("/records/{record_id}", operation_id="first_handler")
    async def first(record_id: str):
        return {"handler": "first"}

    @router.get("/records/{other_id}", operation_id="unreachable_handler")
    async def second(other_id: str):
        return {"handler": "second"}

    registry = RouterRegistry(app)
    registry.include(router)
    assert len(registry.shadowed) == 1
    assert list(app.openapi()["paths"]) == ["/records/{record_id}"]
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        assert (await client.get("/records/123")).json() == {"handler": "first"}
