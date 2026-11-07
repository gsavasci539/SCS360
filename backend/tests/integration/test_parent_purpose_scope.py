from datetime import date
from decimal import Decimal
import hashlib
import hmac
from types import SimpleNamespace
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from test_material_files import materials_client, headers  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401
from app.infrastructure.models.models import Branch, ClassRoom, Parent, Role, Student, StudentParent, User, Permission, Debt, DebtType, Grade, GradeType, SubjectType


async def test_duplicate_legacy_parent_contacts_aggregate_own_children_without_merging_accounts(materials_client):
    client, sessions, data = materials_client
    async with sessions() as db:
        extra = Parent(organization_id=data["org"].id, user_id=data["user"].id, first_name="Second", last_name="Contact")
        foreign = Parent(organization_id=data["stranger"].organization_id, user_id=data["user"].id, first_name="Corrupt", last_name="Foreign")
        child = Student(organization_id=data["org"].id, branch_id=data["branch"].id, first_name="Extra", last_name="Child")
        db.add_all([extra, foreign, child]); await db.flush()
        db.add_all([StudentParent(student_id=child.id, parent_id=extra.id),
            StudentParent(student_id=data["children"][0].id, parent_id=extra.id),
            StudentParent(student_id=data["stranger"].id, parent_id=foreign.id)])
        await db.commit()
    auth = headers(data["user"])
    children = await client.get("/api/parent/my-children", headers=auth)
    assert children.status_code == 200, children.text
    identifiers = [row["student_id"] for row in children.json()["data"]]
    assert set(identifiers) == {str(row.id) for row in data["children"]} | {str(child.id)} and len(identifiers) == 3
    for row in [*data["children"], child]:
        grades = await client.get(f"/api/parent/child/{row.id}/grades", headers=auth)
        assert grades.status_code == 200, grades.text
    empty = await client.get(f"/api/parent/child/{child.id}/insights", headers=auth)
    assert empty.status_code == 200, empty.text
    assert empty.json()["data"]["current_grade"] is None and empty.json()["data"]["confidence"] is None
    assert empty.json()["data"]["predicted_grade"] is None and "remaining_debt" not in empty.json()["data"]
    assert (await client.get(f"/api/parent/child/{child.id}/insights", headers=auth, params={"context": "finances"})).status_code == 403
    assert (await client.get(f'/api/parent/child/{data["stranger"].id}/grades', headers=auth)).status_code == 403
    async with sessions() as db:
        assert await db.get(Parent, extra.id) is not None and await db.get(Parent, foreign.id) is not None


async def test_teacher_parent_reads_own_other_branch_child_only_in_parent_purpose(materials_client, monkeypatch):
    client, sessions, data = materials_client
    async with sessions() as db:
        parent_role = (await db.execute(select(Role).options(selectinload(Role.permissions)).where(Role.slug == "parent"))).scalar_one()
        for code in ("parent.view_finances", "parent.view_attendance"):
            parent_role.permissions.append(Permission(code=code, name=code, module="parent"))
        actor = (await db.execute(select(User).options(selectinload(User.roles), selectinload(User.branches)).where(User.id == data["teacher"].id))).scalar_one()
        actor.roles.append(parent_role); actor.branches = [await db.get(Branch, data["branch"].id)]
        other = Branch(organization_id=data["org"].id, name="Own child other branch"); db.add(other); await db.flush()
        classroom = ClassRoom(organization_id=data["org"].id, branch_id=other.id, name="Own child classroom")
        db.add(classroom); await db.flush()
        child = Student(organization_id=data["org"].id, branch_id=other.id, class_id=classroom.id, first_name="Own", last_name="Other branch")
        stranger = Student(organization_id=data["org"].id, branch_id=other.id, first_name="Unlinked", last_name="Other branch")
        contact = Parent(organization_id=data["org"].id, user_id=actor.id, first_name="Teacher", last_name="Parent")
        db.add_all([child, stranger, contact]); await db.flush()
        db.add(StudentParent(student_id=child.id, parent_id=contact.id)); await db.commit()
        own_debt = Debt(organization_id=data["org"].id, branch_id=other.id, student_id=child.id,
            amount=Decimal("25.00"), paid_amount=0, debt_type=DebtType.EDUCATION, due_date=date.today())
        staff_debt = Debt(organization_id=data["org"].id, branch_id=data["branch"].id, student_id=data["children"][0].id,
            amount=Decimal("25.00"), paid_amount=0, debt_type=DebtType.EDUCATION, due_date=date.today())
        db.add_all([own_debt, staff_debt]); await db.commit()
        db.add(Grade(organization_id=data["org"].id, branch_id=other.id, class_id=classroom.id, student_id=child.id,
            subject=SubjectType.MATHEMATICS, grade_type=GradeType.EXAM, exam_date=date.today(), score=40, max_score=50))
        await db.commit()
    auth = headers(data["teacher"])
    assert (await client.get(f'/api/students/{data["children"][0].id}', headers=auth)).status_code == 200
    assert (await client.get(f"/api/students/{child.id}", headers=auth)).status_code in {403, 404}
    portal = await client.get("/api/parent/my-children", headers=auth)
    assert portal.status_code == 200 and [row["student_id"] for row in portal.json()["data"]] == [str(child.id)], portal.text
    assert (await client.get(f"/api/parent/child/{child.id}/grades", headers=auth)).status_code == 200
    academic = await client.get(f"/api/parent/child/{child.id}/insights", headers=auth, params={"context": "academic"})
    assert academic.status_code == 200 and academic.json()["data"]["current_grade"] == 80, academic.text
    assert "remaining_debt" not in academic.json()["data"]
    finances = await client.get(f"/api/parent/child/{child.id}/insights", headers=auth, params={"context": "finances"})
    assert finances.status_code == 200 and finances.json()["data"]["remaining_debt"] == 25, finances.text
    assert (await client.get(f'/api/ai/student-performance/{data["children"][0].id}', headers=auth, params={"context": "finances"})).status_code == 403
    invoices = await client.get(f"/api/parent/child/{child.id}/financial-invoices", headers=auth)
    assert invoices.status_code == 200 and invoices.json()["data"]["total_remaining"] == 25, invoices.text
    attendance = await client.get(f"/api/parent/child/{child.id}/attendance", headers=auth, params={"year": 2026, "month": 11})
    assert attendance.status_code == 200, attendance.text
    assert (await client.get(f"/api/parent/child/{child.id}/attendance", headers=auth, params={"year": 0, "month": 11})).status_code == 422
    for row in [data["children"][0], stranger, data["stranger"]]:
        assert (await client.get(f"/api/parent/child/{row.id}/grades", headers=auth)).status_code == 403
    # A parent request never mutates the next staff request's branch scope.
    assert (await client.get(f"/api/students/{child.id}", headers=auth)).status_code in {403, 404}
    from app.application.services import online_payment_service
    calls = []
    class Gateway(online_payment_service.IyzicoGateway):
        def __init__(self): super().__init__(SimpleNamespace(IYZICO_SECRET_KEY="local-parent-purpose-secret"))
        def configured(self): pass
        def require_organization(self, identifier): assert identifier == data["org"].id
        async def initialize(self, payload):
            calls.append(payload)
            result = {"status": "success", "conversationId": payload["conversationId"], "token": "temporary-parent-purpose-token",
                "paymentPageUrl": "https://sandbox-cpp.iyzipay.com/parent-purpose"}
            result["signature"] = hmac.new(self.settings.IYZICO_SECRET_KEY.encode(),
                f"{result['conversationId']}:{result['token']}".encode(), hashlib.sha256).hexdigest()
            return result
    monkeypatch.setattr(online_payment_service, "IyzicoGateway", Gateway)
    body = {"debt_id": str(own_debt.id), "amount": 25, "buyer": {"identityNumber": "ACCEPTANCE-ONLY", "registrationAddress": "Test", "city": "Test", "country": "Turkey"}}
    started = await client.post("/api/parent/payments/initialize", headers=auth, json=body)
    assert started.status_code == 200 and len(calls) == 1, started.text
    checkout_id = started.json()["data"]["conversation_id"]
    status = await client.get(f"/api/parent/payments/checkouts/{checkout_id}", headers=auth)
    assert status.status_code == 200 and status.json()["data"]["status"] == "PENDING", status.text
    assert "token" not in status.text
    assert (await client.post("/api/parent/payments/initialize", headers=auth, json={**body, "debt_id": str(staff_debt.id)})).status_code in {403, 404}
    # Having a teacher relationship must not grant guardian payment permission
    # for a classroom student's debt through the legacy shared route either.
    assert (await client.post("/api/payments/iyzico/initialize", headers=auth, json={**body, "debt_id": str(staff_debt.id)})).status_code == 403
    assert (await client.get(f"/api/payments/iyzico/debts/{staff_debt.id}", headers=auth)).status_code == 403
    assert len(calls) == 1
