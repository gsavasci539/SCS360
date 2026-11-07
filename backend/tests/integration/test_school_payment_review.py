import asyncio
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select

from app.infrastructure.models.models import (AuditAction, AuditLog, Branch, Debt, DebtType, NotificationJob,
    Payment, PaymentCheckout, Receipt, Role, Student, User, UserRole)
from test_school_checkout_durability import school_checkout_client, payment, start, callback  # noqa: F401
from test_school_payment_merchants import merchant_client, body as merchant_body, configure  # noqa: F401
from test_material_files import materials_client, headers  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401


@pytest.fixture
async def review_client(school_checkout_client):
    client, sessions, data, provider = school_checkout_client
    request = payment(data)
    assert (await start(client, data, request)).status_code == 200
    async with sessions() as db:
        debt = await db.get(Debt, data["debt"].id); debt.paid_amount = 90
        await db.commit()
    result = await callback(client, provider, request["request_id"])
    assert result.status_code == 200 and result.json()["data"]["status"] == "PAID_REVIEW", result.text
    async with sessions() as db:
        debt = await db.get(Debt, data["debt"].id); debt.paid_amount = 0
        await db.commit()
    return client, sessions, {**data, "checkout_id": request["request_id"]}, provider


async def detail(client, data, actor=None):
    reply = await client.get(f'/api/payments/iyzico/checkouts/{data["checkout_id"]}/review', headers=headers(actor or data["finance"]))
    assert reply.status_code == 200, reply.text
    return reply.json()["data"]


def request(values, **extra):
    return {"request_id": str(uuid4()), "expected_revision": values["revision"], "action": "APPLY", "reason": "Checked original verified payment", **extra}


async def post(client, data, body, actor=None):
    return await client.post(f'/api/payments/iyzico/checkouts/{data["checkout_id"]}/review', headers=headers(actor or data["finance"]), json=body)


async def test_review_apply_atomic_replay_preserves_original_checkout_and_records_actual_reviewer(review_client):
    client, sessions, data, provider = review_client
    values = await detail(client, data)
    assert values["can_apply"] is True and values["can_refund"] is True
    body = request(values)
    replies = await asyncio.gather(post(client, data, body), post(client, data, body))
    assert all(reply.status_code == 200 for reply in replies), [reply.text for reply in replies]
    assert replies[0].json()["data"] == replies[1].json()["data"]
    assert replies[0].json()["data"]["status"] == "COMPLETED"
    async with sessions() as db:
        ledger = (await db.execute(select(Payment))).scalar_one()
        assert ledger.received_by == data["finance"].id
        receipt = (await db.execute(select(Receipt))).scalar_one()
        assert receipt.issued_by == data["finance"].id and receipt.remaining_debt == 125
        assert (await db.get(PaymentCheckout, UUID(data["checkout_id"]))).created_by == data["user"].id
        assert await db.scalar(select(func.count(AuditLog.id)).where(AuditLog.entity_type == "school_payment_review")) == 1
    assert len(provider.initialized) == 1 and len(provider.retrieved) == 1


async def test_review_rejects_parent_wrong_actor_nonce_stale_revision_and_foreign_scope(review_client):
    client, sessions, data, _ = review_client
    values = await detail(client, data)
    assert (await post(client, data, request(values), data["user"])).status_code == 403
    assert (await post(client, data, request(values, expected_revision="0"*64))).status_code == 409
    assert (await post(client, data, request(values, debt_id=str(uuid4())))).status_code == 422
    raw_root = await post(client, data, request(values), data["root"])
    assert raw_root.status_code == 403, raw_root.text
    foreign = await client.get(f'/api/payments/iyzico/checkouts/{data["checkout_id"]}/review', headers=headers(data["other_owner"]))
    assert foreign.status_code in {403, 404}
    listing = await client.get("/api/payments/iyzico/reviews", headers=headers(data["finance"]))
    assert listing.status_code == 200 and listing.json()["data"]["total"] == 1, listing.text
    row = listing.json()["data"]["items"][0]
    assert row["review_events"] == [] and row["environment"] == "LIVE" and row["revision"] == values["revision"]
    assert "school-token-" not in listing.text and "acceptance-school-secret" not in listing.text
    async with sessions() as db:
        assert await db.scalar(select(func.count(Payment.id))) == 0


async def test_recorded_full_refund_accepts_mismatch_without_transaction_and_never_touches_ledger(review_client):
    client, sessions, data, provider = review_client
    async with sessions() as db:
        row = await db.get(PaymentCheckout, UUID(data["checkout_id"]))
        row.review_reason = "PROOF_MISMATCH"; row.provider_transaction_id = None
        row.verified_metadata = {**row.verified_metadata, "matches_checkout": False, "transaction_id": None}
        await db.commit()
    values = await detail(client, data)
    assert values["can_apply"] is False and values["can_refund"] is True
    assert (await post(client, data, request(values))).status_code == 409
    body = request(values, action="REFUND_RECORDED", refund_reference="EXTERNAL-VERIFIED-REFUND-ONLY", refund_amount="25.00", refund_currency="TRY", refunded_at=datetime.now(UTC).isoformat())
    bad = await post(client, data, {**body, "refund_amount": "24.00"})
    assert bad.status_code == 409, bad.text
    saved = await post(client, data, body)
    assert saved.status_code == 200 and saved.json()["data"]["status"] == "REFUNDED", saved.text
    again = await post(client, data, body)
    assert again.status_code == 200 and again.json()["data"] == saved.json()["data"]
    assert len(provider.retrieved) == 1
    async with sessions() as db:
        assert await db.scalar(select(func.count(Payment.id))) == 0
        assert await db.scalar(select(func.count(Receipt.id))) == 0
        assert (await db.get(Debt, data["debt"].id)).paid_amount == 0


async def test_soft_deleted_debt_can_only_record_external_refund_and_unverified_data_cannot(review_client):
    client, sessions, data, _ = review_client
    async with sessions() as db:
        debt = await db.get(Debt, data["debt"].id); debt.deleted_at = datetime.now(UTC)
        await db.commit()
    values = await detail(client, data)
    assert values["can_apply"] is False and values["can_refund"] is True
    async with sessions() as db:
        row = await db.get(PaymentCheckout, UUID(data["checkout_id"]))
        row.verified_metadata = {**row.verified_metadata, "fraud_status": "0"}
        await db.commit()
    changed = await detail(client, data)
    assert changed["can_apply"] is False and changed["can_refund"] is False
    body = request(changed, action="REFUND_RECORDED", refund_reference="NOT-VERIFIED", refund_amount="25", refund_currency="TRY", refunded_at=datetime.now(UTC).isoformat())
    assert (await post(client, data, body)).status_code == 409


async def test_branch_review_uses_whole_student_balance_and_cannot_read_other_branch(review_client):
    from app.core.database import Base
    client, sessions, data, _ = review_client
    async with sessions() as db:
        branch = Branch(name="Other historical branch", organization_id=data["org"].id)
        db.add(branch); await db.flush()
        sibling = Debt(organization_id=data["org"].id, branch_id=branch.id, student_id=data["children"][0].id,
            debt_type=DebtType.EDUCATION, amount=75, paid_amount=0, due_date=datetime.now(UTC).date())
        db.add(sibling)
        await db.execute(Base.metadata.tables["user_branches"].insert().values(user_id=data["finance"].id, branch_id=data["branch"].id))
        await db.commit()
    values = await detail(client, data)
    assert values["can_apply"] is True
    applied = await post(client, data, request(values))
    assert applied.status_code == 200, applied.text
    async with sessions() as db:
        assert (await db.execute(select(Receipt))).scalar_one().remaining_debt == 200
        assert (await db.get(Debt, sibling.id)).paid_amount == 0


def selected_root(data, organization_id=None):
    return {**headers(data["root"]), "X-SCS360-Organization-Id": str(organization_id or data["org"].id)}


async def capture_second_review(client, sessions, data, provider, debt, actor_headers):
    """Create real signed evidence through the registered fake-provider flow."""
    body = payment(data, debt_id=str(debt.id))
    initialized = await client.post("/api/payments/iyzico/initialize", headers=actor_headers, json=body)
    assert initialized.status_code == 200, initialized.text
    identifier = body["request_id"]
    provider.attempts[identifier]["result"]["paymentId"] = "review-proof-" + identifier
    async with sessions() as db:
        (await db.get(Debt, debt.id)).paid_amount = 90
        await db.commit()
    captured = await callback(client, provider, identifier)
    assert captured.status_code == 200 and captured.json()["data"]["status"] == "PAID_REVIEW", captured.text
    async with sessions() as db:
        (await db.get(Debt, debt.id)).paid_amount = 0
        await db.commit()
    return identifier


async def test_explicit_root_workspace_can_review_without_changing_original_checkout_creator(review_client):
    client, sessions, data, provider = review_client
    path = f'/api/payments/iyzico/checkouts/{data["checkout_id"]}/review'
    scoped_headers = selected_root(data)
    viewed = await client.get(path, headers=scoped_headers)
    assert viewed.status_code == 200 and viewed.json()["data"]["can_apply"] is True, viewed.text
    other_school = await client.get(path, headers=selected_root(data, data["stranger"].organization_id))
    assert other_school.status_code == 404, other_school.text
    body = request(viewed.json()["data"])
    saved = await client.post(path, headers=scoped_headers, json=body)
    assert saved.status_code == 200 and saved.json()["data"]["status"] == "COMPLETED", saved.text
    repeat = await client.post(path, headers=scoped_headers, json=body)
    assert repeat.status_code == 200 and repeat.json()["data"] == saved.json()["data"]
    async with sessions() as db:
        ledger = (await db.execute(select(Payment))).scalar_one()
        receipt = (await db.execute(select(Receipt))).scalar_one()
        row = await db.get(PaymentCheckout, UUID(data["checkout_id"]))
        assert ledger.received_by == receipt.issued_by == data["root"].id
        assert receipt.remaining_debt == 125 and row.created_by == data["user"].id
        audit = await db.get(AuditLog, UUID(body["request_id"]))
        assert audit.organization_id == data["org"].id and audit.user_id == data["root"].id
    assert len(provider.initialized) == len(provider.retrieved) == 1


async def test_postgresql_cross_organization_audit_nonce_race_rolls_back_entire_losing_ledger(review_client, monkeypatch):
    from app.application.services import school_payment_review as service
    client, sessions, data, provider = review_client
    async with sessions() as db:
        if db.bind.dialect.name != "postgresql":
            pytest.skip("Independent organization row-lock race requires PostgreSQL")
        debt = Debt(organization_id=data["stranger"].organization_id, branch_id=data["other_branch"].id,
            student_id=data["stranger"].id, debt_type=DebtType.EDUCATION, amount=100, paid_amount=0,
            due_date=datetime.now(UTC).date())
        db.add(debt); await db.commit()
    configured = await configure(client, data["other_owner"], merchant_body(api_key="second-acceptance-api", secret_key="second-acceptance-secret"))
    assert configured.status_code == 200, configured.text
    other_id = await capture_second_review(client, sessions, data, provider, debt,
        selected_root(data, data["stranger"].organization_id))
    targets = [(data["checkout_id"], selected_root(data)),
        (other_id, selected_root(data, data["stranger"].organization_id))]
    shared_nonce = str(uuid4())
    bodies = []
    for identifier, actor_headers in targets:
        viewed = await client.get(f"/api/payments/iyzico/checkouts/{identifier}/review", headers=actor_headers)
        assert viewed.status_code == 200 and viewed.json()["data"]["can_apply"] is True, viewed.text
        bodies.append(request(viewed.json()["data"], request_id=shared_nonce))
    # Both requests must observe no global audit nonce before either can insert it.
    original_apply, arrived, both_ready = service.apply_verified, 0, asyncio.Event()
    async def synchronized_apply(db, row, actor_id=None):
        nonlocal arrived
        arrived += 1
        if arrived == 2: both_ready.set()
        await asyncio.wait_for(both_ready.wait(), 10)
        return await original_apply(db, row, actor_id=actor_id)
    monkeypatch.setattr(service, "apply_verified", synchronized_apply)
    replies = await asyncio.wait_for(asyncio.gather(*[
        client.post(f"/api/payments/iyzico/checkouts/{identifier}/review", headers=actor_headers, json=body)
        for (identifier, actor_headers), body in zip(targets, bodies)
    ]), 20)
    assert sorted(reply.status_code for reply in replies) == [200, 409], [reply.text for reply in replies]
    loser = next(reply for reply in replies if reply.status_code == 409)
    assert "duplicate key" not in loser.text.lower() and "sql" not in loser.text.lower()
    assert "second-acceptance" not in loser.text and "school-token-" not in loser.text
    async with sessions() as db:
        assert await db.scalar(select(func.count(Payment.id))) == 1
        assert await db.scalar(select(func.count(Receipt.id))) == 1
        assert await db.scalar(select(func.count(NotificationJob.id)).where(NotificationJob.reference_type == "payment")) == 1
        assert await db.scalar(select(func.count(AuditLog.id)).where(AuditLog.action == AuditAction.PAYMENT)) == 1
        assert await db.scalar(select(func.count(AuditLog.id)).where(AuditLog.entity_type == "school_payment_review")) == 1
        for index, debt_id in enumerate((data["debt"].id, debt.id)):
            assert (await db.get(Debt, debt_id)).paid_amount == (25 if replies[index].status_code == 200 else 0)
            row = await db.get(PaymentCheckout, UUID(targets[index][0]))
            assert row.status == ("COMPLETED" if replies[index].status_code == 200 else "PAID_REVIEW")
            assert bool(row.payment_id) == (replies[index].status_code == 200)
    assert len(provider.initialized) == len(provider.retrieved) == 2


async def test_external_refund_reference_race_is_unique_across_restricted_branches(review_client):
    from app.core.database import Base
    client, sessions, data, provider = review_client
    async with sessions() as db:
        branch = Branch(name="Second refund branch", organization_id=data["org"].id)
        db.add(branch); await db.flush()
        student = Student(first_name="Second", last_name="Branch", organization_id=data["org"].id, branch_id=branch.id)
        reviewer = User(email="refund-second-branch@test.invalid", password_hash="unused", first_name="Second", last_name="Reviewer", organization_id=data["org"].id)
        db.add_all([student, reviewer]); await db.flush()
        role_id = await db.scalar(select(Role.id).where(Role.organization_id == data["org"].id, Role.slug == "org_admin"))
        db.add(UserRole(user_id=reviewer.id, role_id=role_id))
        await db.execute(Base.metadata.tables["user_branches"].insert(), [
            {"user_id": data["finance"].id, "branch_id": data["branch"].id},
            {"user_id": reviewer.id, "branch_id": branch.id}])
        debt = Debt(organization_id=data["org"].id, branch_id=branch.id, student_id=student.id,
            debt_type=DebtType.EDUCATION, amount=100, paid_amount=0, due_date=datetime.now(UTC).date())
        db.add(debt); await db.commit()
    second_id = await capture_second_review(client, sessions, data, provider, debt, headers(reviewer))
    targets = [(data["checkout_id"], headers(data["finance"])), (second_id, headers(reviewer))]
    bodies = []
    for index, (identifier, actor_headers) in enumerate(targets):
        viewed = await client.get(f"/api/payments/iyzico/checkouts/{identifier}/review", headers=actor_headers)
        assert viewed.status_code == 200 and viewed.json()["data"]["can_refund"] is True, viewed.text
        hidden = await client.get(f"/api/payments/iyzico/checkouts/{targets[1-index][0]}/review", headers=actor_headers)
        assert hidden.status_code == 404, hidden.text
        bodies.append(request(viewed.json()["data"], action="REFUND_RECORDED", refund_reference="SAME-EXTERNAL-MERCHANT-REFUND",
            refund_amount="25.00", refund_currency="TRY", refunded_at=datetime.now(UTC).isoformat()))
    replies = await asyncio.wait_for(asyncio.gather(*[
        client.post(f"/api/payments/iyzico/checkouts/{identifier}/review", headers=actor_headers, json=body)
        for (identifier, actor_headers), body in zip(targets, bodies)
    ]), 20)
    assert sorted(reply.status_code for reply in replies) == [200, 409], [reply.text for reply in replies]
    async with sessions() as db:
        assert await db.scalar(select(func.count(Payment.id))) == 0
        assert await db.scalar(select(func.count(Receipt.id))) == 0
        assert await db.scalar(select(func.count(AuditLog.id)).where(AuditLog.entity_type == "school_payment_review")) == 1
        for index, debt_id in enumerate((data["debt"].id, debt.id)):
            assert (await db.get(Debt, debt_id)).paid_amount == 0
            row = await db.get(PaymentCheckout, UUID(targets[index][0]))
            assert row.status == ("REFUNDED" if replies[index].status_code == 200 else "PAID_REVIEW")
    assert len(provider.initialized) == len(provider.retrieved) == 2
