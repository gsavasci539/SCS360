"""Native finance receives the same scoped, fully pageable ledger as the web."""
from datetime import date
from decimal import Decimal
from uuid import uuid4

from test_finance_compatibility import auth, finance_client  # noqa: F401
from test_material_files import materials_client  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401
from app.infrastructure.models.models import Branch, Debt, DebtStatus, DebtType, Student, UserBranch


def debt(student, actor, **extra):
    return Debt(id=uuid4(), organization_id=student.organization_id, branch_id=student.branch_id,
        student_id=student.id, debt_type=DebtType.EDUCATION, description="Synthetic ledger note",
        amount=Decimal("100.01"), paid_amount=Decimal("0"), status=DebtStatus.UNPAID,
        due_date=date(2027, 1, 15), created_by=actor.id, updated_by=actor.id, **extra)


async def test_branch_ledger_pages_and_detail_share_real_labels(finance_client):  # noqa: F811
    client, sessions, data = finance_client
    child = data["children"][0]
    async with sessions() as db:
        branch = Branch(name="Synthetic second branch", organization_id=data["org"].id)
        db.add(branch); await db.flush()
        second = Student(first_name="Second", last_name="Branch", organization_id=data["org"].id, branch_id=branch.id)
        db.add(second); await db.flush()
        rows = [debt(child, data["accountant"]) for _ in range(102)]
        db.add_all([*rows, debt(second, data["accountant"]), debt(data["stranger"], data["accountant"])])
        await db.commit()
    seen = []
    for page, length in ((1, 100), (2, 2)):
        reply = await client.get("/api/debts", headers=auth(data["accountant"]), params={
            "branch_id": str(child.branch_id), "status": "UNPAID", "page": page, "page_size": 100})
        assert reply.status_code == 200, reply.text
        payload = reply.json()["data"]
        assert payload["total"] == 102 and len(payload["items"]) == length
        seen.extend(payload["items"])
    assert len({row["id"] for row in seen}) == 102
    for row in seen:
        assert row["organization_id"] == str(data["org"].id) and row["branch_id"] == str(child.branch_id)
        assert row["student_name"] == f"{child.first_name} {child.last_name}" and row["class_name"] == data["classroom"].name
        assert row["description"] == "Synthetic ledger note" and Decimal(row["remaining_amount"]) == Decimal("100.01")
        assert row["created_at"] and "invoice_number" not in row
    detail = await client.get(f'/api/debts/{seen[0]["id"]}', headers=auth(data["accountant"]))
    assert detail.json()["data"] == seen[0]
    all_rows = await client.get("/api/debts", headers=auth(data["accountant"]), params={"page_size": 100})
    assert all_rows.json()["data"]["total"] == 103
    denied = await client.get("/api/debts", headers=auth(data["accountant"]), params={"branch_id": str(data["other_branch"].id)})
    assert denied.status_code == 404
    assert (await client.get("/api/debts", headers=auth(data["user"]))).status_code == 403
    async with sessions() as db:
        db.add(UserBranch(user_id=data["accountant"].id, branch_id=data["branch"].id)); await db.commit()
    restricted = await client.get("/api/debts", headers=auth(data["accountant"]), params={"branch_id": str(branch.id)})
    assert restricted.status_code == 404
    restricted_all = await client.get("/api/debts", headers=auth(data["accountant"]), params={"page_size": 100})
    assert restricted_all.json()["data"]["total"] == 102


async def test_corrupt_foreign_student_link_never_exports_its_labels(finance_client):  # noqa: F811
    client, sessions, data = finance_client
    row = debt(data["children"][0], data["accountant"])
    row.student_id = data["stranger"].id
    async with sessions() as db:
        db.add(row); await db.commit()
    reply = await client.get(f"/api/debts/{row.id}", headers=auth(data["accountant"]))
    assert reply.status_code == 404, reply.text
    listing = await client.get("/api/debts", headers=auth(data["accountant"]))
    assert listing.json()["data"]["total"] == 0 and listing.json()["data"]["items"] == []
