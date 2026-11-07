from uuid import uuid4

from httpx import ASGITransport, AsyncClient
from fastapi import Depends, FastAPI
from sqlalchemy import func, select

from app.infrastructure.models.models import Parent
from app.main import app
from test_saas_platform import platform_client  # noqa: F401
from test_material_files import materials_client, headers  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401


async def test_a_successful_parent_response_is_visible_to_the_next_database_connection_before_headers(platform_client):
    _, sessions, data = platform_client
    marker = "Committed-" + uuid4().hex
    observed = []

    async def instrumented(scope, receive, send):
        async def inspect(message):
            if message["type"] == "http.response.start" and message["status"] == 200:
                async with sessions() as db:
                    observed.append(await db.scalar(select(func.count(Parent.id)).where(Parent.first_name == marker)))
            await send(message)
        await app(scope, receive, inspect)

    auth = {**headers(data["root"]), "X-SCS360-Organization-Id": str(data["org"].id)}
    async with AsyncClient(transport=ASGITransport(app=instrumented), base_url="http://test") as client:
        created = await client.post(f'/api/students/{data["children"][0].id}/parents', headers=auth,
            json={"first_name": marker, "last_name": "Boundary", "relation_type": "GUARDIAN"})
    assert created.status_code == 200, created.text
    assert observed == [1], "A 200 response must never precede the database commit"


async def test_a_deferred_unique_constraint_returns_a_conflict_and_rolls_back(portal_db, monkeypatch):
    from app.core import database
    from app.core.exceptions import AppException
    from app.core.middleware import app_exception_handler
    from app.infrastructure.models.models import Permission
    sessions, _ = portal_db
    sessions.configure(autoflush=False)
    monkeypatch.setattr(database, "AsyncSessionLocal", sessions)
    local = FastAPI()
    local.add_exception_handler(AppException, app_exception_handler)

    @local.post("/deferred")
    async def deferred(db=Depends(database.get_db, scope="function")):
        db.add(Permission(code="students.read", name="Duplicate", module="students"))
        return {"success": True}

    async with AsyncClient(transport=ASGITransport(app=local, raise_app_exceptions=False), base_url="http://test") as client:
        response = await client.post("/deferred")
    assert response.status_code == 409, response.text
    async with sessions() as db:
        assert await db.scalar(select(func.count(Permission.id)).where(Permission.code == "students.read")) == 1
