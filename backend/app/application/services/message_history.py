"""Read boundaries for existing participant conversations and newly scoped messages."""
from dataclasses import replace
from uuid import UUID

from sqlalchemy import and_, case, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.message_contacts import message_branches, recipient_query
from app.core.student_access import accessible_student_ids
from app.core.tenant import TenantContext
from app.core.tenant_guard import scope_filters
from app.infrastructure.models.models import ChatConversation, ChatMessage, User


def message_partner(user_id: UUID):
    rows = ChatMessage.__table__.c
    return case((rows.sender_id == user_id, rows.recipient_id), else_=rows.sender_id)


async def message_visibility(db: AsyncSession, tenant: TenantContext, branch_id: UUID | None):
    branch_ids = await message_branches(db, tenant, branch_id)
    actor = tenant.user_id
    messages = ChatMessage.__table__
    rows, threads, users = messages.c, ChatConversation.__table__.c, User.__table__.c
    partner = message_partner(actor)
    student_ids = await accessible_student_ids(db, tenant)
    branches, students, classes, _ = scope_filters(replace(tenant, branch_ids=branch_ids), student_ids)
    # Child-specific conversations require both a visible student and the
    # recorded participants. A platform actor can only participate in the
    # selected institution, even though their account belongs to the platform.
    thread = select(threads.id).where(
        threads.student_id.in_(students),
        or_(
            and_(threads.parent_id == rows.sender_id, threads.teacher_id == rows.recipient_id),
            and_(threads.teacher_id == rows.sender_id, threads.parent_id == rows.recipient_id),
        ),
    ).correlate(messages)
    has_thread = rows.conversation_id.in_(thread)
    recorded_org = rows.organization_id == tenant.organization_id
    same_org = select(users.id).where(users.organization_id == tenant.organization_id, users.deleted_at.is_(None))
    platform = select(users.id).where(users.is_super_admin.is_(True), users.deleted_at.is_(None))
    conditions = [
        or_(rows.sender_id == actor, rows.recipient_id == actor),
        partner != actor,
        or_(recorded_org, rows.organization_id.is_(None)),
        or_(partner.in_(same_org), and_(partner.in_(platform), or_(recorded_org, has_thread))),
        or_(rows.conversation_id.is_(None), has_thread),
        or_(rows.class_id.is_(None), rows.class_id.in_(classes)),
        or_(rows.branch_id.is_(None), rows.branch_id.in_(branches)),
    ]
    if branch_ids:
        contacts = await recipient_query(db, tenant, branch_id, for_history=True)
        conditions.append(or_(
            rows.branch_id.is_not(None), rows.class_id.is_not(None), rows.conversation_id.is_not(None),
            partner.in_(contacts.with_only_columns(users.id)),
        ))
    return and_(*conditions)
