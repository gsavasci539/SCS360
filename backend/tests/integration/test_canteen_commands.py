import asyncio
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import func, select

from app.domain.entities.canteen import CanteenOrder, CanteenProduct, CanteenWalletTransaction
from app.infrastructure.models.models import AuditLog, Branch, Permission, Role, StudentWallet, User
from test_material_files import materials_client, headers  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401


async def test_canteen_read_is_side_effect_free_and_two_retries_change_wallet_once(materials_client):
    client, sessions, data = materials_client
    async with sessions() as db:
        sibling = Branch(organization_id=data["org"].id, name="Other canteen")
        codes = ("canteen.read", "canteen.write")
        existing = {item.code: item for item in (await db.execute(select(Permission).where(Permission.code.in_(codes)))).scalars()}
        permissions = [existing.get(code) or Permission(code=code, name=code, module="canteen") for code in codes]
        operator = User(organization_id=data["org"].id, email="canteen-desk@test.invalid", first_name="Test",
            last_name="Canteen", password_hash="unused", branches=[data["branch"], sibling],
            roles=[Role(name="Canteen test cashier", slug="canteen_desk", organization_id=data["org"].id,
                permissions=permissions)])
        product = CanteenProduct(branch_id=data["branch"].id, name="Isolated product", price=Decimal("8.25"))
        db.add_all([operator, product])
        await db.commit()
    actor = headers(operator)
    child = str(data["children"][0].id)
    branch = str(data["branch"].id)
    scope = {"branch_id": branch}
    wrong = {"branch_id": str(sibling.id)}
    wallet_path = f"/api/canteen/student/{child}/wallet"
    wallet = await client.get(wallet_path, headers=actor, params=scope)
    assert wallet.status_code == 200 and wallet.json()["data"]["balance"] == 0, wallet.text
    options = await client.get("/api/canteen/options", headers=actor, params=scope)
    assert options.status_code == 200 and child in {row["id"] for row in options.json()["data"]["students"]}
    async with sessions() as db:
        assert await db.get(StudentWallet, data["children"][0].id) is None
    top_up = {"student_id": child, "amount": "20.00", "payment_method": "CASH", "request_id": str(uuid4())}
    mismatch = await client.post(wallet_path + "/top-up", headers=actor, params=scope,
        json={**top_up, "student_id": str(data["children"][1].id)})
    assert mismatch.status_code == 422
    rejected = await client.post(wallet_path + "/top-up", headers=actor, params=wrong, json=top_up)
    assert rejected.status_code == 404
    reloaded = await asyncio.gather(*(client.post(wallet_path + "/top-up", headers=actor, params=scope, json=top_up) for _ in range(2)))
    assert all(reply.status_code == 200 for reply in reloaded), [reply.text for reply in reloaded]
    receipts = [reply.json()["data"] for reply in reloaded]
    assert receipts[0]["transaction_id"] == receipts[1]["transaction_id"]
    assert {receipt["repeated_request"] for receipt in receipts} == {True, False}
    assert all(receipt["balance"] == 20 for receipt in receipts)
    sale = {"student_id": child, "branch_id": branch, "product_id": str(product.id), "quantity": 1,
        "payment_method": "WALLET", "expected_unit_price": "8.25", "request_id": str(uuid4())}
    stale = await client.post("/api/canteen/pos/checkout", headers=actor, json={**sale, "expected_unit_price": "8.00"})
    assert stale.status_code == 409
    sold = await asyncio.gather(*(client.post("/api/canteen/pos/checkout", headers=actor, json=sale) for _ in range(2)))
    assert all(reply.status_code == 200 for reply in sold), [reply.text for reply in sold]
    sales = [reply.json()["data"] for reply in sold]
    assert sales[0]["order_id"] == sales[1]["order_id"]
    assert sales[0]["operation_id"] == sale["request_id"] and sales[1]["student_balance"] == 11.75
    conflict = await client.post("/api/canteen/pos/checkout", headers=actor, json={**sale, "quantity": 2})
    assert conflict.status_code == 409
    stored = await client.get(wallet_path + "/transactions", headers=actor,
        params={**scope, "record_id": sales[0]["transaction_id"], "limit": 1})
    assert stored.status_code == 200, stored.text
    assert len(stored.json()["data"]) == 1 and stored.json()["data"][0]["transaction_type"] == "DEBIT"
    assert stored.json()["data"][0]["amount"] == 8.25
    order = await client.get("/api/canteen/orders", headers=actor,
        params={**scope, "student_id": child, "record_id": sales[0]["order_id"], "limit": 1})
    assert order.status_code == 200 and [row["id"] for row in order.json()["data"]] == [sales[0]["order_id"]]
    async with sessions() as db:
        assert await db.scalar(select(func.count()).select_from(CanteenWalletTransaction)) == 2
        assert await db.scalar(select(func.count()).select_from(CanteenOrder)) == 1
        events = (await db.execute(select(AuditLog).where(AuditLog.entity_type.in_(
            ["CANTEEN_TOPUP_RECORDED", "CANTEEN_POS_RECORDED"])))).scalars().all()
        assert len(events) == 2 and all("dietary_restrictions" not in event.new_values["response"] for event in events)
