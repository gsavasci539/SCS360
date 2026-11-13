"""Unavailable reminders must never acknowledge delivery or create side effects."""
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from test_material_files import materials_client  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401
from app.core.security import create_access_token
from app.infrastructure.models.models import NotificationJob, Payment, Permission, Role, User


@pytest.mark.parametrize("permission,expected", [
    ("library.write", 503), ("library.read", 403), ("student.write", 403),
])
async def test_reminder_is_unavailable_without_delivery_or_information_leak(materials_client, permission, expected):
    client, sessions, data = materials_client
    async with sessions() as db:
        existing = (await db.execute(select(Permission).where(Permission.code == permission))).scalar_one_or_none()
        role = Role(name="Reminder acceptance", slug="reminder_" + uuid4().hex,
            organization_id=data["org"].id,
            permissions=[existing or Permission(code=permission, name=permission, module="library")])
        user = User(email=f"{uuid4().hex}@example.com", password_hash="unused",
            first_name="Reminder", last_name="Acceptance", organization_id=data["org"].id, roles=[role])
        db.add(user)
        await db.commit()
        auth = {"Authorization": "Bearer " + create_access_token(user.id)}

    for loan_id in (str(uuid4()), "not-a-loan"):
        path = f"/api/library/loans/{loan_id}/remind"
        assert (await client.post(path)).status_code == 401
        response = await client.post(path, headers=auth)
        assert response.status_code == expected, response.text
        if expected == 503:
            assert response.json()["success"] is False
            assert "Bildirim gönderilmedi" in response.json()["message"]
    async with sessions() as db:
        for model in (NotificationJob, Payment):
            assert (await db.execute(select(func.count()).select_from(model))).scalar_one() == 0
