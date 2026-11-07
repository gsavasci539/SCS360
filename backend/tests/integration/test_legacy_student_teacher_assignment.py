"""Teacher and parent flows work against revision 019's created-at-only table."""
from datetime import UTC, datetime
from uuid import uuid4

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import selectinload
from test_material_files import headers, materials_client  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401

from app.application.services.chatbot.context_service import ContextService
from app.core.uuid_type import CustomUUID
from app.infrastructure.models.models import (
    ChatConversation,
    ChatMessage,
    Parent,
    Permission,
    RolePermission,
    StudentParent,
    StudentTeacherAssignment,
    User,
    UserRole,
)


@pytest.fixture
async def legacy_assignments(materials_client):  # noqa: F811 - pytest imports a shared fixture
    client, sessions, data = materials_client
    engine = sessions.kw["bind"]
    if engine.dialect.name == "sqlite":
        # Only this disposable fixture's pool is affected. Checkout runs before
        # a session starts its physical transaction, including reused connections.
        @sa.event.listens_for(engine.sync_engine, "checkout")
        def enforce_foreign_keys(dbapi, *_):
            cursor = dbapi.cursor()
            try:
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.execute("PRAGMA foreign_keys")
                assert cursor.fetchone()[0] == 1
            finally:
                cursor.close()
    identifier = uuid4()
    async with sessions() as db:
        if engine.dialect.name == "sqlite":
            assert await db.scalar(sa.text("PRAGMA foreign_keys")) == 1
        def revision_019_table(connection):
            # This disposable fixture explicitly reproduces the shipped schema;
            # it does not derive the tested table from today's ORM metadata.
            connection.execute(sa.text("DROP TABLE student_teacher_assignments"))
            metadata = sa.MetaData()
            for name in ("students", "users"):
                sa.Table(name, metadata, autoload_with=connection)
            table = sa.Table("student_teacher_assignments", metadata,
                sa.Column("id", CustomUUID(), primary_key=True),
                sa.Column("student_id", CustomUUID(), sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False),
                sa.Column("teacher_id", CustomUUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
                sa.Column("subject_name", sa.String(100), nullable=False),
                sa.Column("is_primary_adviser", sa.Boolean(), nullable=False, server_default=sa.false()),
                sa.Column("office_hours", sa.String(50)), sa.Column("academic_year", sa.String(20)),
                sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()))
            sa.Index("idx_student_teacher_student", table.c.student_id)
            sa.Index("idx_student_teacher_teacher", table.c.teacher_id)
            table.create(connection)
            connection.execute(table.insert().values(id=identifier, student_id=data["children"][0].id,
                teacher_id=data["teacher"].id, subject_name="Legacy mathematics", is_primary_adviser=True,
                created_at=datetime(2024, 9, 1, 8, 30)))
            if connection.dialect.name == "sqlite":
                connection.execute(sa.text("UPDATE student_teacher_assignments SET id=:legacy WHERE id=:canonical"),
                    {"legacy": identifier.hex, "canonical": str(identifier)})
        await (await db.connection()).run_sync(revision_019_table)
        await db.commit()
    return client, sessions, {**data, "assignment_id": identifier}


async def test_legacy_assignment_select_insert_and_chatbot_context_preserve_original_record(legacy_assignments):
    _, sessions, data = legacy_assignments
    async with sessions() as db:
        row = (await db.execute(sa.select(StudentTeacherAssignment))).scalar_one()
        assert row.id == data["assignment_id"] and row.subject_name == "Legacy mathematics"
        assert row.created_at.replace(tzinfo=UTC) == datetime(2024, 9, 1, 8, 30, tzinfo=UTC)
        second = StudentTeacherAssignment(student_id=data["children"][1].id, teacher_id=data["teacher"].id,
            subject_name="New science", is_primary_adviser=False)
        db.add(second)
        await db.commit()
        await db.refresh(second)
        assert second.created_at is not None
        assert (await db.scalar(sa.select(sa.func.count(StudentTeacherAssignment.id)))) == 2
        parent = (await db.execute(sa.select(User).options(selectinload(User.roles)).where(User.id == data["user"].id))).scalar_one()
        context = await ContextService().build_context(parent, db)
        assert {str(row["id"]) for row in context.accessible_teachers} == {str(data["teacher"].id)}
        columns = await (await db.connection()).run_sync(lambda connection: {column["name"] for column in sa.inspect(connection).get_columns("student_teacher_assignments")})
        assert "updated_at" not in columns
        assert await db.scalar(sa.text("SELECT COUNT(*) FROM student_teacher_assignments WHERE created_at < '2025-01-01'")) == 1
        if db.bind.dialect.name == "sqlite":
            assert await db.scalar(sa.text("SELECT id FROM student_teacher_assignments WHERE subject_name='Legacy mathematics'")) == data["assignment_id"].hex


async def test_parent_teacher_list_and_connect_keep_student_and_actor_access_boundaries(legacy_assignments):
    client, sessions, data = legacy_assignments
    base = "/api/v1/chatbot"
    own = f'{base}/students/{data["children"][0].id}/teachers'
    listed = await client.get(own, headers=headers(data["user"]))
    assert listed.status_code == 200, listed.text
    teachers = listed.json()["data"]["teachers"]
    assert [row["teacher_id"] for row in teachers] == [str(data["teacher"].id)]
    assert teachers[0]["subject"] == "Legacy mathematics"
    foreign = await client.get(f'{base}/students/{data["stranger"].id}/teachers', headers=headers(data["user"]))
    assert foreign.status_code == 404, foreign.text
    command = {"student_id": str(data["children"][0].id), "teacher_id": str(data["teacher"].id),
        "teacher_name": "Temporary acceptance teacher", "initial_message": "Temporary acceptance teacher conversation", "created_via": "CHATBOT"}
    path = f"{base}/chat/conversations/connect-teacher"
    unassigned = await client.post(path, headers=headers(data["user"]), json={**command, "teacher_id": str(data["user"].id)})
    assert unassigned.status_code == 403, unassigned.text
    wrong_actor = await client.post(path, headers=headers(data["teacher"]), json=command)
    assert wrong_actor.status_code == 403, wrong_actor.text
    connected = await client.post(path, headers=headers(data["user"]), json=command)
    assert connected.status_code == 201, connected.text
    assert connected.json()["data"]["student_id"] == str(data["children"][0].id)
    reused = await client.post(path, headers=headers(data["user"]), json=command)
    assert reused.status_code == 201, reused.text
    assert reused.json()["data"]["conversation_id"] == connected.json()["data"]["conversation_id"]
    async with sessions() as db:
        conversation = (await db.execute(sa.select(ChatConversation))).scalar_one()
        assert conversation.teacher_id == data["teacher"].id and conversation.student_id == data["children"][0].id
        parent = await db.scalar(sa.select(Parent).where(Parent.user_id == data["user"].id))
        assert parent.id != data["user"].id and conversation.parent_id == data["user"].id
        messages = (await db.execute(sa.select(ChatMessage).where(ChatMessage.conversation_id == conversation.id))).scalars().all()
        assert len(messages) == 2 and all(message.sender_id == data["user"].id for message in messages)
        assert await db.scalar(sa.select(sa.func.count(StudentTeacherAssignment.id))) == 1


async def test_connect_reuses_oldest_account_thread_and_never_another_guardians_contact_key(legacy_assignments):
    from app.application.services import parent_data_service, teacher_chat_service
    from app.core.tenant import TenantContext

    client, sessions, data = legacy_assignments
    async with sessions() as db:
        parent = await db.scalar(sa.select(Parent).where(Parent.user_id == data["user"].id))
        assert parent.id != data["user"].id
        other = User(id=parent.id, organization_id=data["org"].id, email="other-guardian@assignment.invalid",
            password_hash="unused", first_name="Other", last_name="Guardian")
        db.add(other)
        await db.flush()
        role_id = await db.scalar(sa.select(UserRole.role_id).where(UserRole.user_id == data["user"].id))
        db.add(UserRole(user_id=other.id, role_id=role_id))
        other_parent = Parent(user_id=other.id, organization_id=data["org"].id, first_name="Other", last_name="Guardian")
        db.add(other_parent)
        await db.flush()
        db.add(StudentParent(parent_id=other_parent.id, student_id=data["children"][0].id))
        shared = dict(student_id=data["children"][0].id, teacher_id=data["teacher"].id, is_active=True,
            subject_context="Disposable existing conversation")
        foreign = ChatConversation(parent_id=other.id, created_at=datetime(2023, 1, 1, tzinfo=UTC),
            last_message="Other guardian private history", **shared)
        oldest = ChatConversation(parent_id=data["user"].id, created_at=datetime(2024, 1, 1, tzinfo=UTC), **shared)
        duplicate = ChatConversation(parent_id=data["user"].id, created_at=datetime(2025, 1, 1, tzinfo=UTC),
            last_message="Preserve duplicate legacy thread", **shared)
        db.add_all([foreign, oldest, duplicate])
        await db.flush()
        db.add(ChatMessage(conversation_id=foreign.id, sender_id=other.id, recipient_id=data["teacher"].id,
            sender_role="PARENT", content="Other guardian private history", is_read=False))
        await db.commit()
    body = {"student_id": str(data["children"][0].id), "teacher_id": str(data["teacher"].id),
        "teacher_name": "Untrusted display label", "initial_message": "Current guardian own history", "created_via": "CHATBOT"}
    path = "/api/v1/chatbot/chat/conversations/connect-teacher"
    for _ in range(2):
        reply = await client.post(path, headers=headers(data["user"]), json=body)
        assert reply.status_code == 201, reply.text
        assert reply.json()["data"]["conversation_id"] == str(oldest.id)
    async with sessions() as db:
        assert await db.scalar(sa.select(sa.func.count(ChatConversation.id))) == 3
        assert (await db.get(ChatConversation, duplicate.id)).last_message == "Preserve duplicate legacy thread"
        assert (await db.get(ChatConversation, foreign.id)).last_message == "Other guardian private history"
        assert await db.scalar(sa.select(sa.func.count(ChatMessage.id)).where(ChatMessage.conversation_id == foreign.id)) == 1
        parent_history = await parent_data_service.chat_history(db, data["user"], data["children"][0].id, data["teacher"].id)
        teacher = TenantContext(user_id=data["teacher"].id, organization_id=data["org"].id,
            role_slugs={"teacher"}, branch_ids=[data["branch"].id])
        teacher_history = await teacher_chat_service.history(db, teacher, data["children"][0].id, data["user"].id)
        for history in (parent_history, teacher_history):
            assert len(history) == 2
            assert all(message["content"] == "Current guardian own history" for message in history)


async def test_related_parent_needs_current_send_permission_before_any_conversation_or_message(legacy_assignments):
    client, sessions, data = legacy_assignments
    async with sessions() as db:
        role_id = await db.scalar(sa.select(UserRole.role_id).where(UserRole.user_id == data["user"].id))
        permission_id = await db.scalar(sa.select(Permission.id).where(Permission.code == "parent.send_message"))
        assert permission_id is not None
        await db.execute(sa.delete(RolePermission).where(RolePermission.role_id == role_id, RolePermission.permission_id == permission_id))
        await db.commit()
    body = {"student_id": str(data["children"][0].id), "teacher_id": str(data["teacher"].id),
        "teacher_name": "Untrusted display label", "initial_message": "Current permission acceptance", "created_via": "CHATBOT"}
    path = "/api/v1/chatbot/chat/conversations/connect-teacher"
    denied = await client.post(path, headers=headers(data["user"]), json=body)
    assert denied.status_code == 403, denied.text
    async with sessions() as db:
        assert await db.scalar(sa.select(sa.func.count(ChatConversation.id))) == 0
        assert await db.scalar(sa.select(sa.func.count(ChatMessage.id))) == 0
        db.add(RolePermission(role_id=role_id, permission_id=permission_id))
        await db.commit()
    accepted = await client.post(path, headers=headers(data["user"]), json=body)
    assert accepted.status_code == 201, accepted.text
    async with sessions() as db:
        assert await db.scalar(sa.select(sa.func.count(ChatConversation.id))) == 1
        assert await db.scalar(sa.select(sa.func.count(ChatMessage.id))) == 1
