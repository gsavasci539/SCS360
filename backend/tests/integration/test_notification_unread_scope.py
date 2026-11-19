from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from test_material_files import headers, materials_client  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401

from app.infrastructure.models.models import (
    Branch,
    NotificationChannel,
    NotificationJob,
    NotificationRecipient,
    NotificationStatus,
    Parent,
    Permission,
    Role,
    User,
)


async def test_unread_counter_and_mark_all_match_the_recipient_institution_and_branch(materials_client):  # noqa: F811
    client, sessions, data = materials_client
    teacher, guardian = data["teacher"], data["user"]
    count_url = "/api/notifications/unread-count"
    read_url = "/api/notifications/mark-all-read"
    assert (await client.get(count_url, headers=headers(teacher))).status_code == 403
    assert (await client.patch(read_url, headers=headers(teacher))).status_code == 403

    async with sessions() as db:
        role = await db.scalar(select(Role).options(selectinload(Role.permissions)).where(Role.slug == "teacher"))
        role.permissions.append(Permission(code="notification.read", name="Fixture read", module="notification"))
        branch = await db.get(Branch, data["branch"].id)
        member = await db.get(User, teacher.id, options=[selectinload(User.branches)])
        member.branches = [branch]
        another_branch = Branch(name="Outside assignment", organization_id=branch.organization_id)
        db.add(another_branch)
        await db.flush()
        parent = await db.scalar(select(Parent).where(Parent.user_id == guardian.id))
        jobs = {
            "assigned": NotificationJob(organization_id=branch.organization_id, branch_id=branch.id,
                channel=NotificationChannel.EMAIL, body="Fixture assigned"),
            "whole_org": NotificationJob(organization_id=branch.organization_id,
                channel=NotificationChannel.EMAIL, body="Fixture organization"),
            "another_branch": NotificationJob(organization_id=branch.organization_id, branch_id=another_branch.id,
                channel=NotificationChannel.EMAIL, body="Fixture another branch"),
            "foreign": NotificationJob(organization_id=data["stranger"].organization_id, branch_id=data["other_branch"].id,
                channel=NotificationChannel.EMAIL, body="Fixture foreign"),
        }
        db.add_all(jobs.values())
        await db.flush()

        def recipient(job, *, status=NotificationStatus.SENT, **identity):
            row = NotificationRecipient(notification_job_id=jobs[job].id, recipient_address="test@example.invalid",
                status=status, **identity)
            db.add(row)
            return row

        visible = [
            recipient("assigned", user_id=teacher.id),
            recipient("whole_org", user_id=teacher.id),
        ]
        hidden = [
            recipient("another_branch", user_id=teacher.id),
            recipient("foreign", user_id=teacher.id),
            recipient("assigned", user_id=teacher.id, status=NotificationStatus.PENDING),
            recipient("assigned", parent_id=parent.id),
        ]
        recipient("assigned", user_id=teacher.id, read_at=datetime.now(UTC))
        await db.commit()

    result = await client.get(count_url, headers=headers(teacher))
    assert result.status_code == 200, result.text
    assert result.json()["data"] == {"unread_count": 2}
    marked = await client.patch(read_url, headers=headers(teacher))
    assert marked.status_code == 200, marked.text
    assert (await client.get(count_url, headers=headers(teacher))).json()["data"] == {"unread_count": 0}
    assert (await client.get(count_url, headers=headers(guardian))).json()["data"] == {"unread_count": 1}
    async with sessions() as db:
        for row in visible:
            assert (await db.get(NotificationRecipient, row.id)).read_at is not None
        for row in hidden:
            assert (await db.get(NotificationRecipient, row.id)).read_at is None
