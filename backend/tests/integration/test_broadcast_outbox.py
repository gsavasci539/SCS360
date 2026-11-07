import asyncio
from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from test_material_files import materials_client  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401
from app.core.security import create_access_token
from app.infrastructure.models.models import (NotificationJob, NotificationRecipient, NotificationStatus,
    Parent, Permission, Role, StudentParent, User)
from app.infrastructure.notifications.base import ProviderResult
from app.infrastructure.notifications.outbox_worker import process_pending_jobs


def auth(user):
    return {"Authorization": "Bearer " + create_access_token(user.id)}


@pytest.fixture
async def broadcast_client(materials_client):
    client, sessions, data = materials_client
    async with sessions() as db:
        permissions = [Permission(code=code, name=code, module="communications") for code in ("communications.read", "communications.write")]
        role = Role(name="Manager", slug="org_admin", organization_id=data["org"].id, permissions=permissions)
        foreign_role = Role(name="Manager", slug="org_admin", organization_id=data["other_branch"].organization_id, permissions=permissions)
        manager = User(first_name="Manager", last_name="Test", email="manager@test.invalid", password_hash="unused",
            organization_id=data["org"].id, roles=[role])
        foreign = User(first_name="Other", last_name="Manager", email="other-manager@test.invalid", password_hash="unused",
            organization_id=data["other_branch"].organization_id, roles=[foreign_role])
        db.add_all([manager, foreign])
        parent = (await db.execute(select(Parent).where(Parent.user_id == data["user"].id))).scalar_one()
        parent.email, parent.phone = "linked-parent@test.invalid", "+905300000001"
        outsider = Parent(first_name="Foreign", last_name="Parent", organization_id=foreign.organization_id,
            email="foreign-parent@test.invalid", phone="+905300000002")
        db.add(outsider)
        await db.flush()
        db.add(StudentParent(parent_id=outsider.id, student_id=data["stranger"].id))
        await db.commit()
    data = {**data, "manager": manager, "foreign_manager": foreign}
    yield client, sessions, data


def payload(data):
    return {"title": "Kabul duyurusu", "message_content": "Yarın veli toplantısı var.", "target_audience": "CLASS_PARENTS",
        "target_class_id": str(data["classroom"].id), "channel": "EMAIL"}


async def test_broadcast_deduplicates_real_contacts_and_queues_without_claiming_delivery(broadcast_client):
    client, sessions, data = broadcast_client
    response = await client.post("/api/communications/broadcast-jobs", headers=auth(data["manager"]), json=payload(data))
    assert response.status_code == 200, response.text
    draft = response.json()["data"]
    assert draft["status"] == "DRAFT" and draft["total_recipients"] == 1 and draft["sent_count"] == 0
    path = f'/api/communications/broadcast-jobs/{draft["id"]}'
    responses = await asyncio.gather(*[client.post(path + "/send", headers=auth(data["manager"])) for _ in range(2)])
    assert sorted(response.status_code for response in responses) == [200, 409], [response.text for response in responses]
    summary = (await client.get(path + "/delivery-summary", headers=auth(data["manager"]))).json()["data"]
    assert summary["total"] == 1 and summary["sent"] == 0 and summary["pending"] == 1
    reports = (await client.get("/api/communications/delivery-reports", headers=auth(data["manager"]))).json()["data"]
    assert len(reports) == 1 and reports[0]["recipient_phone"] == "linked-parent@test.invalid" and reports[0]["status"] == "PENDING"
    assert (await client.get(path + "/delivery-summary", headers=auth(data["foreign_manager"]))).status_code == 404
    assert (await client.get("/api/communications/broadcast-jobs", headers=auth(data["foreign_manager"]))).json()["data"] == []
    async with sessions() as db:
        jobs = (await db.execute(select(NotificationJob))).scalars().all()
        assert len(jobs) == 1 and jobs[0].status == NotificationStatus.PENDING
        jobs[0].max_retries = 1
        await db.commit()
    class FailedProvider:
        async def dispatch(self, *args):
            return ProviderResult(success=False, message="Mock provider unavailable")
    await process_pending_jobs(sessions, FailedProvider())
    listing = (await client.get("/api/communications/broadcast-jobs?status=FAILED", headers=auth(data["manager"]))).json()["data"]
    assert len(listing) == 1 and listing[0]["failed_count"] == 1 and listing[0]["sent_count"] == 0
    async with sessions() as db:
        job = (await db.execute(select(NotificationJob))).scalar_one()
        job.status, job.scheduled_at = NotificationStatus.PENDING, datetime.now(UTC)
        await db.commit()
    class SuccessfulProvider:
        async def dispatch(self, *args):
            return ProviderResult(success=True, message="Mock accepted", response={"test": True})
    await process_pending_jobs(sessions, SuccessfulProvider())
    listing = (await client.get("/api/communications/broadcast-jobs?status=COMPLETED&end_date=2030-01-01", headers=auth(data["manager"]))).json()["data"]
    assert len(listing) == 1 and listing[0]["sent_count"] == 1
    summary = (await client.get(path + "/delivery-summary", headers=auth(data["manager"]))).json()["data"]
    assert summary["sent"] == 1 and summary["delivered"] == 0
    assert (await client.delete(path, headers=auth(data["manager"]))).status_code == 409


async def test_broadcast_validation_editing_and_cancellation_are_real(broadcast_client):
    client, sessions, data = broadcast_client
    response = await client.post("/api/communications/broadcast-jobs", headers=auth(data["manager"]), json=payload(data))
    path = "/api/communications/broadcast-jobs/" + response.json()["data"]["id"]
    assert (await client.put(path, headers=auth(data["manager"]), json={"title": "Düzeltilen başlık"})).status_code == 200
    assert (await client.put(path, headers=auth(data["manager"]), json={"status": "COMPLETED"})).status_code == 422
    assert (await client.put(path, headers=auth(data["manager"]), json={"title": None})).status_code == 422
    assert (await client.post(path + "/send", headers=auth(data["user"]))).status_code == 403
    assert (await client.post(path + "/send", headers=auth(data["manager"]))).status_code == 200
    cancelled = await client.delete(path, headers=auth(data["manager"]))
    assert cancelled.status_code == 200 and cancelled.json()["data"]["status"] == "CANCELLED"
    async with sessions() as db:
        assert (await db.execute(select(NotificationJob))).scalar_one().status == NotificationStatus.CANCELLED
        assert (await db.execute(select(NotificationRecipient))).scalar_one().status == NotificationStatus.CANCELLED
    bad = {**payload(data), "target_class_id": None}
    assert (await client.post("/api/communications/broadcast-jobs", headers=auth(data["manager"]), json=bad)).status_code == 422
