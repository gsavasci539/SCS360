from sqlalchemy import func, select

from test_material_files import materials_client, headers  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401
from app.infrastructure.models.models import (
    Announcement, AnnouncementAudience, AnnouncementStatus, Branch, NotificationJob, User,
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
