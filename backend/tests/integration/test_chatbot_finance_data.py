from datetime import UTC, date, datetime, timedelta

from test_saas_platform import platform_client  # noqa: F401
from test_material_files import materials_client, headers  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401
from app.application.services.chatbot.intent_schemas import ChatbotIntent
from app.core.dates import school_today, school_day_bounds
from app.infrastructure.models.models import Debt, DebtType, Payment, PaymentMethod


async def grant_finance(sessions):
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from app.infrastructure.models.models import Permission, Role
    async with sessions() as db:
        role = (await db.execute(select(Role).where(Role.slug == "parent").options(selectinload(Role.permissions)))).scalar_one()
        role.permissions.append(Permission(code="parent.view_finances", name="Own child finance", module="parent"))
        await db.commit()


async def test_chatbot_payment_period_and_selected_child_exclude_cancellations_other_children_and_school(platform_client, monkeypatch):
    from app.routers import chatbot
    operation = {"value": "summary"}
    async def intent(query, context):
        return ChatbotIntent(intent="PAYMENTS", operation=operation["value"], period="today", confidence=1)
    monkeypatch.setattr(chatbot.intent_service, "detect_intent_with_fallback", intent)
    client, sessions, data = platform_client
    await grant_finance(sessions)
    lower, upper = school_day_bounds(school_today())
    async with sessions() as db:
        debts = [Debt(organization_id=child.organization_id, branch_id=child.branch_id, student_id=child.id,
            debt_type=DebtType.EDUCATION, amount=2000, paid_amount=0, due_date=school_today()) for child in [*data["children"], data["stranger"]]]
        db.add_all(debts); await db.flush()
        for debt, amount, when, cancelled, note in [(debts[0], 25, lower + timedelta(hours=1), False, "Own first"),
            (debts[0], 5, upper - timedelta(microseconds=1), False, "Own last"),
            (debts[0], 75, lower + timedelta(hours=2), True, "Cancelled secret"),
            (debts[0], 11, lower - timedelta(microseconds=1), False, "Previous day"),
            (debts[0], 3, upper, False, "Next day"),
            (debts[1], 70, lower + timedelta(hours=3), False, "Sibling secret"),
            (debts[2], 999, lower + timedelta(hours=3), False, "Foreign secret")]:
            db.add(Payment(organization_id=debt.organization_id, branch_id=debt.branch_id, student_id=debt.student_id, debt_id=debt.id,
                amount=amount, payment_method=PaymentMethod.CASH, payment_date=when,
                cancelled_at=when if cancelled else None, received_by=data["root"].id, notes=note))
        await db.commit()
    body = {"query": "Bugünkü ödemeler", "role": "parent", "student_id": str(data["children"][0].id)}
    result = await client.post("/api/v1/chatbot/process-query", headers=headers(data["user"]), json=body)
    assert result.status_code == 200 and "30.00 TL" in result.json()["data"]["response_markdown"], result.text
    operation["value"] = "list"
    result = await client.post("/api/v1/chatbot/process-query", headers=headers(data["user"]), json=body)
    assert result.status_code == 200, result.text
    answer = result.json()["data"]["response_markdown"]
    assert "Own first" in answer and "Own last" in answer, answer
    assert all(value not in answer for value in ["Cancelled secret", "Sibling secret", "Foreign secret", "Previous day", "Next day"]), answer


async def test_chatbot_debt_original_paid_and_remaining_amounts_are_distinct_and_deleted_rows_are_ignored(platform_client, monkeypatch):
    from app.routers import chatbot
    async def intent(query, context):
        return ChatbotIntent(intent="DEBT", confidence=1)
    monkeypatch.setattr(chatbot.intent_service, "detect_intent_with_fallback", intent)
    client, sessions, data = platform_client; child = data["children"][0]
    await grant_finance(sessions)
    async with sessions() as db:
        common = {"organization_id": child.organization_id, "branch_id": child.branch_id, "student_id": child.id,
            "debt_type": DebtType.EDUCATION, "due_date": school_today()}
        db.add_all([Debt(**common, amount=100, paid_amount=25), Debt(**common, amount=900, paid_amount=0, deleted_at=datetime.now(UTC))]); await db.commit()
    result = await client.post("/api/v1/chatbot/process-query", headers=headers(data["user"]),
        json={"query": "Borçlar", "role": "parent", "student_id": str(child.id)})
    assert result.status_code == 200, result.text
    answer = result.json()["data"]["response_markdown"]
    assert "Toplam borç: 100.00 TL" in answer and "Ödenen: 25.00 TL" in answer and "Kalan: 75.00 TL" in answer, answer


async def test_revoked_finance_permission_cannot_be_recovered_by_chat_role_or_child_permission(platform_client, monkeypatch):
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from app.infrastructure.models.models import Role
    from app.routers import chatbot
    async def intent(query, context):
        return ChatbotIntent(intent="PAYMENTS", operation="summary", period="today", confidence=1)
    monkeypatch.setattr(chatbot.intent_service, "detect_intent_with_fallback", intent)
    client, sessions, data = platform_client
    await grant_finance(sessions)
    auth = headers(data["user"])
    async with sessions() as db:
        role = (await db.execute(select(Role).where(Role.slug == "parent").options(selectinload(Role.permissions)))).scalar_one()
        role.permissions = [permission for permission in role.permissions if permission.code != "parent.view_finances"]
        await db.commit()
    for path in ("/api/v1/chatbot/process-query", "/api/parent/chatbot"):
        result = await client.post(path, headers=auth, json={"query": "Bilgiler", "role": "SUPER_ADMIN", "student_id": str(data["children"][0].id)})
        assert result.status_code == 200 and "yetkiniz" in result.json()["data"]["response_markdown"], result.text


async def test_teacher_guardian_finance_uses_explicit_parent_scope_without_opening_staff_class_payments(platform_client, monkeypatch):
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from app.infrastructure.models.models import Branch, ClassRoom, Parent, Role, Student, StudentParent, User
    from app.routers import chatbot
    async def intent(query, context):
        return ChatbotIntent(intent="PAYMENTS", operation="summary", period="today", confidence=1)
    monkeypatch.setattr(chatbot.intent_service, "detect_intent_with_fallback", intent)
    client, sessions, data = platform_client
    await grant_finance(sessions)
    async with sessions() as db:
        teacher = (await db.execute(select(User).where(User.id == data["teacher"].id).options(selectinload(User.roles), selectinload(User.branches)))).scalar_one()
        parent_role = (await db.execute(select(Role).where(Role.slug == "parent"))).scalar_one()
        teacher.roles.append(parent_role); teacher.branches = [await db.get(Branch, data["branch"].id)]
        branch = Branch(organization_id=data["org"].id, name="Other own-school branch"); db.add(branch); await db.flush()
        classroom = ClassRoom(organization_id=data["org"].id, branch_id=branch.id, name="Guardian class"); db.add(classroom); await db.flush()
        child = await db.get(Student, data["children"][0].id); child.branch_id, child.class_id = branch.id, classroom.id
        parent = Parent(organization_id=data["org"].id, user_id=teacher.id, first_name="Teacher", last_name="Guardian"); db.add(parent); await db.flush()
        db.add(StudentParent(parent_id=parent.id, student_id=child.id))
        debt = Debt(organization_id=data["org"].id, branch_id=branch.id, student_id=child.id, debt_type=DebtType.EDUCATION, amount=100, paid_amount=50, due_date=school_today())
        db.add(debt); await db.flush()
        db.add(Payment(organization_id=debt.organization_id, branch_id=debt.branch_id, student_id=debt.student_id, debt_id=debt.id,
            amount=50, payment_method=PaymentMethod.CASH, received_by=data["root"].id)); await db.commit()
    body = {"query": "Bugünkü ödemeler", "role": "ADMIN", "student_id": str(child.id)}
    staff = await client.post("/api/v1/chatbot/process-query", headers=headers(teacher), json=body)
    assert staff.status_code == 200 and "yetkiniz" in staff.json()["data"]["response_markdown"], staff.text
    parent = await client.post("/api/parent/chatbot", headers=headers(teacher), json=body)
    assert parent.status_code == 200 and "50.00 TL" in parent.json()["data"]["response_markdown"], parent.text
    forbidden = await client.post("/api/parent/chatbot", headers=headers(data["root"]), json=body)
    assert forbidden.status_code == 403, forbidden.text
