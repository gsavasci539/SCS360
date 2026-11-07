from test_material_files import materials_client  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401
from app.core.security import create_access_token
from app.infrastructure.models.models import User, RfidCard


def auth(user):
    return {"Authorization": "Bearer " + create_access_token(user.id)}


async def test_hardware_requires_authentication_and_role_permissions(materials_client):
    client, sessions, data = materials_client
    for path in ("/devices/register", "/devices/test/heartbeat", "/access/check", "/access/log", "/payment/process", "/wifi/card-read"):
        assert (await client.post("/api/hardware" + path, json={})).status_code == 401
    assert (await client.get("/api/hardware/wifi/card-reads")).status_code == 401
    assert (await client.post("/api/hardware/payment/process", headers=auth(data["user"]),
        json={"card_number": "RFID-TEST", "amount": "1", "branch_id": str(data["branch"].id)})).status_code == 403


async def test_registered_device_wallet_payment_and_poll_history_are_persistent(materials_client):
    client, sessions, data = materials_client
    async with sessions() as db:
        admin = User(first_name="Admin", last_name="Hardware", email="hardware@test.invalid", password_hash="unused",
            organization_id=data["org"].id, is_super_admin=True)
        db.add(admin)
        db.add(RfidCard(organization_id=str(data["org"].id), branch_id=str(data["branch"].id),
            card_number="RFID-TEST", card_type="STUDENT", holder_id=str(data["children"][0].id), holder_name="Test child"))
        await db.commit()
    registered = await client.post("/api/hardware/devices/register", headers=auth(admin), json={"device_id": "terminal-1",
        "device_type": "CANTEEN_TERMINAL", "serial_number": "ACCEPTANCE-1", "branch_id": str(data["branch"].id)})
    assert registered.status_code == 200, registered.text
    heartbeat = await client.post("/api/hardware/devices/terminal-1/heartbeat", headers=auth(admin), json={"status": "ONLINE"})
    assert heartbeat.status_code == 200 and heartbeat.json()["data"]["status"] == "ACTIVE"
    purchase = {"card_number": "RFID-TEST", "amount": "4.25", "branch_id": str(data["branch"].id)}
    assert (await client.post("/api/hardware/payment/process", headers=auth(admin), json=purchase)).status_code == 409
    topup = await client.post("/api/hardware/card/topup", headers=auth(admin),
        params={"card_number": "RFID-TEST", "amount": "10", "payment_method": "CASH"})
    assert topup.status_code == 200, topup.text
    paid = await client.post("/api/hardware/payment/process", headers=auth(admin), json=purchase)
    assert paid.status_code == 200 and paid.json()["data"]["new_balance"] == 5.75, paid.text
    balance = await client.post("/api/hardware/card/balance", headers=auth(admin), json={"card_number": "RFID-TEST"})
    assert balance.status_code == 200 and balance.json()["data"]["balance"] == 5.75
    read = await client.post("/api/hardware/wifi/card-read", headers=auth(admin), json={"device_id": "terminal-1", "card_number": "RFID-TEST"})
    assert read.status_code == 200, read.text
    history = await client.get("/api/hardware/wifi/card-reads?device_id=terminal-1", headers=auth(admin))
    assert history.status_code == 200 and len(history.json()["data"]) == 1
    assert history.json()["data"][0]["balance"] == 5.75
