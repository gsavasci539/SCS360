from datetime import date
from uuid import UUID, uuid4

from sqlalchemy import func, select

from app.infrastructure.models.models import Debt, DebtType, Payment, Permission, Role, User
from test_school_checkout_durability import school_checkout_client, payment, start, callback  # noqa: F401
from test_school_payment_merchants import merchant_client, body as merchant_body, configure  # noqa: F401
from test_material_files import materials_client, headers  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401


async def test_provider_reference_is_unique_per_stable_merchant_not_across_schools(school_checkout_client):
    client, sessions, data, provider = school_checkout_client
    one = payment(data)
    assert (await start(client, data, one)).status_code == 200
    assert (await callback(client, provider, one["request_id"])).status_code == 200
    async with sessions() as db:
        permission = (await db.execute(select(Permission).where(Permission.code == "finance.write"))).scalar_one()
        owner = await db.get(User, data["other_owner"].id)
        role = Role(name="Other school finance", slug="other_school_finance", organization_id=owner.organization_id, permissions=[permission])
        from app.infrastructure.models.models import UserRole
        db.add(role); await db.flush(); db.add(UserRole(user_id=owner.id, role_id=role.id))
        debt = Debt(organization_id=owner.organization_id, branch_id=data["other_branch"].id, student_id=data["stranger"].id,
            debt_type=DebtType.EDUCATION, amount=100, paid_amount=0, due_date=date(2026, 11, 5))
        db.add(debt); await db.commit()
    configured = await configure(client, data["other_owner"], merchant_body(api_key="other-account-api", secret_key="other-account-secret"))
    assert configured.status_code == 200, configured.text
    two = payment(data, request_id=str(uuid4()), debt_id=str(debt.id))
    started = await client.post("/api/payments/iyzico/initialize", headers=headers(data["other_owner"]), json=two)
    assert started.status_code == 200, started.text
    confirmed = await callback(client, provider, two["request_id"])
    assert confirmed.status_code == 200, confirmed.text
    async with sessions() as db:
        sibling = (await db.execute(select(Debt).where(Debt.organization_id == data["org"].id, Debt.id != data["debt"].id))).scalar_one()
    duplicate = payment(data, debt_id=str(sibling.id))
    assert (await start(client, data, duplicate)).status_code == 200
    blocked = await callback(client, provider, duplicate["request_id"])
    assert blocked.status_code == 409, blocked.text
    async with sessions() as db:
        assert await db.scalar(select(func.count(Payment.id))) == 2
        assert (await db.get(Debt, sibling.id)).paid_amount == 0
        assert (await db.get(Debt, debt.id)).paid_amount == 25
