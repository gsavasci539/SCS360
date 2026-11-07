"""Hosted payment receipts must snapshot the student's whole real open ledger."""
import asyncio
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.application.services import online_payment_service as payments
from app.core.dates import school_today
from app.infrastructure.models.models import Debt, DebtStatus, DebtType, Payment, PaymentCheckout, Receipt
from test_material_files import materials_client  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401


class Gateway:
    def __init__(self, organization_id, rows):
        self.settings = SimpleNamespace(IYZICO_ORGANIZATION_ID=str(organization_id))
        self.rows = rows
    async def retrieve(self, token, identifier):
        checkout = self.rows[token]
        assert checkout.id == identifier
        return {"status": "success", "paymentStatus": "SUCCESS", "token": token,
            "conversationId": str(identifier), "basketId": str(checkout.debt_id),
            "paymentId": f"isolated-proof-{identifier}", "price": str(checkout.amount),
            "paidPrice": str(checkout.amount), "currency": "TRY", "fraudStatus": 1}
    def verify(self, result): return True  # The existing signature/environment tests cover this boundary.


@pytest.fixture
async def ledger(portal_db):
    sessions, data = portal_db
    sessions.configure(autoflush=False)
    async with sessions() as db:
        def debt(amount, **values):
            return Debt(organization_id=data["org"].id, branch_id=data["branch"].id,
                student_id=data["children"][0].id, debt_type=DebtType.EDUCATION,
                amount=Decimal(amount), paid_amount=0, due_date=school_today(), **values)
        selected, sibling = debt("100"), debt("50")
        db.add_all([selected, sibling, debt("300", status=DebtStatus.CANCELLED), debt("400", deleted_at=datetime.now(UTC)),
            Debt(organization_id=data["stranger"].organization_id, branch_id=data["other_branch"].id,
                student_id=data["stranger"].id, debt_type=DebtType.EDUCATION, amount=500, paid_amount=0, due_date=school_today())])
        await db.flush()
        attempt = PaymentCheckout(organization_id=data["org"].id, debt_id=selected.id, created_by=data["user"].id,
            amount=25, currency="TRY", token_hash=payments.token_hash("ledger-one"))
        db.add(attempt); await db.commit()
    return sessions, data, selected, sibling, attempt


async def test_online_receipt_snapshots_student_total_with_autoflush_disabled(ledger):
    sessions, data, selected, _, attempt = ledger
    gateway = Gateway(data["org"].id, {"ledger-one": attempt})
    async with sessions() as db:
        first = await payments.reconcile(db, "ledger-one", gateway); await db.commit()
    assert first["status"] == "SUCCESS"
    async with sessions() as db:
        receipt = (await db.execute(select(Receipt))).scalar_one()
        assert receipt.remaining_debt == Decimal("125"), receipt.remaining_debt
        assert (await db.get(Debt, selected.id)).paid_amount == 25
        repeated = await payments.reconcile(db, "ledger-one", gateway); await db.commit()
    assert repeated["payment_id"] == first["payment_id"]
    async with sessions() as db:
        assert await db.scalar(select(func.count(Receipt.id))) == 1


async def test_parallel_callbacks_have_serialized_whole_student_balance_snapshots(ledger):
    sessions, data, _, sibling, first = ledger
    second = PaymentCheckout(organization_id=data["org"].id, debt_id=sibling.id, created_by=data["user"].id,
        amount=40, currency="TRY", token_hash=payments.token_hash("ledger-two"))
    async with sessions() as db: db.add(second); await db.commit()
    gateway = Gateway(data["org"].id, {"ledger-one": first, "ledger-two": second})
    async def run(token):
        async with sessions() as db:
            result = await payments.reconcile(db, token, gateway); await db.commit(); return result
    results = await asyncio.gather(run("ledger-one"), run("ledger-two"))
    assert all(row["status"] == "SUCCESS" for row in results)
    async with sessions() as db:
        balances = list((await db.execute(select(Receipt.remaining_debt))).scalars())
        assert len(balances) == 2 and min(balances) == Decimal("85")
        assert max(balances) in {Decimal("110"), Decimal("125")}


async def test_invalid_sibling_balance_preserves_provider_proof_for_review_without_partial_ledger(ledger):
    sessions, data, selected, sibling, attempt = ledger
    async with sessions() as db:
        row = await db.get(Debt, sibling.id)
        row.paid_amount = Decimal("NaN") if db.bind.dialect.name == "postgresql" else Decimal("Infinity")
        await db.commit()
    async with sessions() as db:
        result = await payments.reconcile(db, "ledger-one", Gateway(data["org"].id, {"ledger-one": attempt}))
        await db.commit()
    assert result["status"] == "REVIEW", result
    async with sessions() as db:
        saved = await db.get(PaymentCheckout, attempt.id)
        assert saved.provider_payment_id == f"isolated-proof-{attempt.id}" and saved.status == "REVIEW"
        assert (await db.get(Debt, selected.id)).paid_amount == 0
        assert not (await db.get(Debt, sibling.id)).paid_amount.is_finite()
        assert await db.scalar(select(func.count(Payment.id))) == 0
        assert await db.scalar(select(func.count(Receipt.id))) == 0
