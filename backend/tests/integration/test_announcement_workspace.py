from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from test_material_files import materials_client, headers  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401
from app.infrastructure.notifications.base import SAFE_PROVIDER_ERROR
from app.infrastructure.models.models import (
    Announcement, AnnouncementAudience, AnnouncementStatus, Branch, NotificationJob, NotificationRecipient,
    NotificationChannel, NotificationStatus, Parent, Permission, Role, User,
)


async def test_announcement_draft_and_branch_status_listing_do_not_enqueue_notifications(materials_client):
    client, sessions, data = materials_client
    async with sessions() as db:
        owner = User(organization_id=data["org"].id, email="announcement-root@example.invalid", first_name="Test",
            last_name="Operator", password_hash="unused", is_super_admin=True)
        second = Branch(organization_id=data["org"].id, name="Second branch")
        db.add_all([owner, second])
        await db.flush()
        for branch_id, title in ((data["branch"].id, "Published first"), (second.id, "Published second"),
            (None, "School-wide publication")):
            db.add(Announcement(organization_id=data["org"].id, branch_id=branch_id, title=title,
                content=title + " content", audience=AnnouncementAudience.ALL_PARENTS, channels=[],
                status=AnnouncementStatus.SENT, created_by=owner.id))
        await db.commit()
    auth = {**headers(owner), "X-SCS360-Organization-Id": str(data["org"].id)}
    branch = str(data["branch"].id)
    draft = await client.post("/api/announcements", headers=auth, json={"title": "Draft title", "content": "Draft content",
        "audience": "BRANCH_PARENTS", "channels": [], "branch_id": branch})
    assert draft.status_code == 200, draft.text
    item = await client.get(f'/api/announcements/{draft.json()["data"]["id"]}', headers=auth)
    assert item.status_code == 200, item.text
    assert item.json()["data"]["branch_id"] == branch and item.json()["data"]["status"] == "DRAFT"
    published = await client.get("/api/announcements", headers=auth, params={"branch_id": branch, "status": "SENT"})
    assert published.status_code == 200, published.text
    assert {row["content"] for row in published.json()["data"]} == {"Published first content", "School-wide publication content"}
    limited = await client.get("/api/announcements", headers=auth, params={"branch_id": branch, "status": "DRAFT", "limit": 1})
    assert limited.status_code == 200, limited.text
    assert [row["id"] for row in limited.json()["data"]] == [draft.json()["data"]["id"]]
    foreign = await client.get("/api/announcements", headers=auth, params={"branch_id": str(data["other_branch"].id)})
    assert foreign.status_code in {403, 404}, foreign.text
    async with sessions() as db:
        assert await db.scalar(select(func.count()).select_from(NotificationJob)) == 0


async def test_targeted_announcement_queues_once_after_an_eligible_address_exists(materials_client):
    client, sessions, data = materials_client
    async with sessions() as db:
        owner = User(organization_id=data["org"].id, email="announcement-sender@example.invalid", first_name="Test",
            last_name="Sender", password_hash="unused", is_super_admin=True)
        db.add(owner)
        await db.commit()
    auth = {**headers(owner), "X-SCS360-Organization-Id": str(data["org"].id)}
    form = {"title": "Initial title", "content": "Initial content", "audience": "SINGLE_STUDENT",
        "student_id": str(data["children"][0].id), "channels": ["EMAIL"]}
    targets = await client.get("/api/announcements/targets", headers=auth,
        params={"kind": "students", "search": "No match", "selected_id": form["student_id"]})
    assert targets.status_code == 200, targets.text
    assert [row["id"] for row in targets.json()["data"]["items"]] == [form["student_id"]]
    unauthorized_target = await client.get("/api/announcements/targets", headers=auth,
        params={"kind": "students", "search": "No match", "selected_id": str(data["stranger"].id)})
    assert unauthorized_target.status_code == 200 and unauthorized_target.json()["data"]["items"] == []
    created = await client.post("/api/announcements", headers=auth, json=form)
    assert created.status_code == 200, created.text
    identifier = created.json()["data"]["id"]
    path = f"/api/announcements/{identifier}"
    changed = await client.put(path, headers=auth, json={**form, "audience": "CLASS_PARENTS",
        "class_id": str(data["classroom"].id), "student_id": None})
    assert changed.status_code == 200 and changed.json()["data"]["id"] == identifier, changed.text
    detail = await client.get(path, headers=auth)
    assert detail.json()["data"]["class_id"] == str(data["classroom"].id)
    assert detail.json()["data"]["student_id"] is None
    assert detail.json()["data"]["branch_id"] == str(data["branch"].id)
    rejected = await client.post(path + "/send", headers=auth)
    assert rejected.status_code in {400, 422}, rejected.text
    assert (await client.get(path, headers=auth)).json()["data"]["status"] == "DRAFT"
    async with sessions() as db:
        parent = (await db.execute(select(Parent).where(Parent.user_id == data["user"].id))).scalar_one()
        parent.email = "isolated-recipient@example.invalid"
        parent.receive_notifications = True
        await db.commit()
    for expected_retry in (False, True):
        queued = await client.post(path + "/send", headers=auth)
        assert queued.status_code == 200, queued.text
        assert queued.json()["data"] == {"announcement_id": identifier, "jobs_created": 1, "already_queued": expected_retry}
    async with sessions() as db:
        assert await db.scalar(select(func.count()).select_from(NotificationJob)) == 1
        assert await db.scalar(select(func.count()).select_from(NotificationRecipient)) == 1

    async with sessions() as db:
        job = (await db.execute(select(NotificationJob))).scalar_one()
        recipient = (await db.execute(select(NotificationRecipient))).scalar_one()
        job.status = NotificationStatus.FAILED
        job.retry_count = 3
        job.locked_until = datetime.now(UTC) + timedelta(minutes=5)
        recipient.status = NotificationStatus.FAILED
        recipient.error_message = "Isolated transport error"
        job_id = job.id
        await db.commit()
    reports = await client.get(path + "/results", headers=auth)
    assert reports.json()["data"] == [{"job_id": str(job_id), "channel": "EMAIL", "sent": 0, "failed": 1,
                                      "pending": 0, "error": SAFE_PROVIDER_ERROR}]
    locked = await client.post(path + "/retry", headers=auth)
    assert locked.json()["data"] == {"announcement_id": identifier, "recipients_retried": 0}
    async with sessions() as db:
        job = await db.get(NotificationJob, job_id)
        job.locked_until = None
        await db.commit()
    for expected_count in (1, 0):
        retry = await client.post(path + "/retry", headers=auth)
        assert retry.status_code == 200, retry.text
        assert retry.json()["data"] == {"announcement_id": identifier, "recipients_retried": expected_count}
    async with sessions() as db:
        job = await db.get(NotificationJob, job_id)
        recipient = (await db.execute(select(NotificationRecipient))).scalar_one()
        assert job.status == NotificationStatus.PENDING and job.retry_count == 0
        assert recipient.status == NotificationStatus.PENDING and recipient.error_message is None


async def test_unassigned_staff_cannot_create_or_read_branchless_announcements_and_notifications(materials_client):
    client, sessions, data = materials_client
    async with sessions() as db:
        permissions = []
        for code in ("announcement.read", "announcement.write", "notification.read", "notification.write"):
            permission = await db.scalar(select(Permission).where(Permission.code == code))
            if permission is None:
                permission = Permission(code=code, name=code, module="communications")
                db.add(permission)
                await db.flush()
            permissions.append(permission)
        role = Role(name="Unassigned communications staff", slug="unassigned-communications",
            organization_id=data["org"].id, permissions=permissions)
        actor = User(organization_id=data["org"].id, email="unassigned-communications@test.invalid",
            first_name="Unassigned", last_name="Staff", password_hash="unused", roles=[role])
        wide_role = await db.scalar(select(Role).where(Role.slug == "org_admin",
            Role.organization_id == data["org"].id))
        if wide_role is None:
            wide_role = Role(name="Organization communications admin", slug="org_admin",
                organization_id=data["org"].id, permissions=permissions)
        else:
            await db.refresh(wide_role, ["permissions"])
            existing_permission_ids = {item.id for item in wide_role.permissions}
            wide_role.permissions.extend(item for item in permissions if item.id not in existing_permission_ids)
        wide_actor = User(organization_id=data["org"].id, email="org-admin-communications@test.invalid",
            first_name="Organization", last_name="Admin", password_hash="unused", roles=[wide_role])
        announcement = Announcement(organization_id=data["org"].id, title="Private school-wide draft",
            content="Private broadcast body", audience=AnnouncementAudience.ALL_PARENTS, channels=["EMAIL"],
            status=AnnouncementStatus.DRAFT, created_by=data["user"].id)
        job = NotificationJob(organization_id=data["org"].id, channel=NotificationChannel.EMAIL,
            body="Private notification body", subject="Private notification", status=NotificationStatus.FAILED,
            created_by=data["user"].id)
        db.add_all([role, actor, wide_role, wide_actor, announcement, job])
        await db.flush()
        db.add(NotificationRecipient(notification_job_id=job.id, recipient_address="private-recipient@test.invalid",
            status=NotificationStatus.FAILED))
        await db.commit()

    auth = headers(actor)
    announcement_path = f"/api/announcements/{announcement.id}"
    notification_path = f"/api/notifications/{job.id}"
    assert (await client.get("/api/announcements", headers=auth)).json()["data"] == []
    assert (await client.get("/api/announcements/targets", headers=auth,
        params={"kind": "branches"})).json()["data"]["items"] == []
    assert (await client.get(announcement_path, headers=auth)).status_code == 404
    assert (await client.get(announcement_path + "/results", headers=auth)).status_code == 404
    assert (await client.post(announcement_path + "/send", headers=auth)).status_code == 404
    assert (await client.post(announcement_path + "/retry", headers=auth)).status_code == 404
    assert (await client.delete(announcement_path, headers=auth)).status_code == 404

    draft = await client.post("/api/announcements", headers=auth, json={"title": "Forbidden broadcast",
        "content": "Must not be queued", "audience": "ALL_PARENTS", "channels": ["EMAIL"]})
    assert draft.status_code == 403, draft.text
    assert (await client.get("/api/notifications", headers=auth)).json()["data"] == []
    assert (await client.get(notification_path, headers=auth)).status_code == 404
    assert (await client.delete(notification_path, headers=auth)).status_code == 404
    assert (await client.post(notification_path + "/retry", headers=auth)).status_code == 404
    assert (await client.get("/api/notifications/branch-options", headers=auth)).json()["data"] == []

    notification = await client.post("/api/notifications", headers=auth, json={"title": "Forbidden",
        "type": "EMAIL", "target_audience": "PARENTS", "content": "Must not be queued"})
    assert notification.status_code == 403, notification.text
    manual = await client.post("/api/notifications/send", headers=auth, json={"channel": "EMAIL",
        "subject": "Forbidden", "body": "Must not be queued", "recipients": [
            {"address": "private-recipient@test.invalid", "name": "Private"}]})
    assert manual.status_code == 403, manual.text

    wide_auth = headers(wide_actor)
    wide_draft = await client.post("/api/announcements", headers=wide_auth, json={"title": "Authorized broadcast",
        "content": "Institution scope remains explicit", "audience": "ALL_PARENTS", "channels": []})
    assert wide_draft.status_code == 200, wide_draft.text
    async with sessions() as db:
        assert await db.scalar(select(func.count()).select_from(NotificationJob)) == 1
        assert await db.scalar(select(func.count()).select_from(NotificationRecipient)) == 1
