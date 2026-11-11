from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

import pytest
from sqlalchemy import select

from test_material_files import materials_client  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401
from app.core.exceptions import ConflictException
from app.core.security import create_access_token
from app.core.tenant import TenantContext
from app.application.services import canteen_wallet_service as wallets
from app.infrastructure.models.models import (AuditLog, Branch, ClassRoom, Device, Permission, RfidCard,
    Role, Student, User, UserBranch)
from app.domain.entities.canteen import CanteenWalletTransaction


def auth(user):
    return {"Authorization": "Bearer " + create_access_token(user.id)}


@pytest.fixture
async def hardware_client(materials_client):
    client, sessions, data = materials_client
    async with sessions() as db:
        permissions = []
        for code in ("settings.write", "security.read", "security.write", "canteen.read", "canteen.write"):
            permission = (await db.execute(select(Permission).where(Permission.code == code))).scalar_one_or_none()
            permissions.append(permission or Permission(code=code, name=code, module=code.split('.')[0]))
        role = Role(name="Manager", slug="org_admin", organization_id=data["org"].id, permissions=permissions)
        other_branch = Branch(organization_id=data["org"].id, name="Second campus")
        db.add(other_branch)
        await db.flush()
        manager = User(organization_id=data["org"].id, first_name="Manager", last_name="Test", password_hash="unused",
            email="hardware-manager@test.invalid", roles=[role], branches=[data["branch"], other_branch])
        root = User(organization_id=data["org"].id, first_name="Root", last_name="Test", password_hash="unused",
            email="hardware-root@test.invalid", is_super_admin=True)
        classroom = ClassRoom(organization_id=data["org"].id, branch_id=other_branch.id, name="Other campus")
        db.add_all([manager, root, classroom])
        await db.flush()
        other_student = Student(organization_id=data["org"].id, branch_id=other_branch.id, class_id=classroom.id,
            first_name="Other campus", last_name="Student")
        db.add(other_student)
        await db.flush()
        db.add(UserBranch(user_id=data["user"].id, branch_id=data["branch"].id))
        for suffix, branch in (("a", data["branch"]), ("b", other_branch)):
            db.add(Device(id="gate-" + suffix, organization_id=str(data["org"].id), branch_id=str(branch.id),
                name="Gate " + suffix, serial_number="SERIAL-" + suffix, device_type="TURNSTILE", status="ACTIVE"))
        for number, student, organization, branch in (("OWN", data["children"][0], data["org"].id, data["branch"].id),
            ("CORRUPT", other_student, data["org"].id, data["branch"].id),
            ("OWN", data["stranger"], data["other_branch"].organization_id, data["other_branch"].id)):
            db.add(RfidCard(card_number=number, holder_id=str(student.id), holder_name="Fixture", card_type="STUDENT",
                organization_id=str(organization), branch_id=str(branch), status="ACTIVE"))
        await db.commit()
    yield client, sessions, {**data, "manager": manager, "root": root, "second_branch": other_branch, "second_student": other_student}


async def test_entry_requires_correct_campus_and_staff_relationship(hardware_client):
    client, sessions, data = hardware_client
    for holder, card_type, device, allowed in ((data["children"][0], "STUDENT", "gate-a", True),
        (data["children"][0], "STUDENT", "gate-b", False), (data["second_student"], "STUDENT", "gate-a", False),
        (data["teacher"], "STAFF", "gate-a", True), (data["teacher"], "STAFF", "gate-b", False),
        (data["user"], "STAFF", "gate-a", False), (data["stranger"], "STUDENT", "gate-a", False)):
        response = await client.post("/api/hardware/access/check", headers=auth(data["manager"]),
            json={"holder_id": str(holder.id), "card_type": card_type, "device_id": device})
        assert response.status_code == 200, response.text
        assert response.json()["data"]["access_granted"] is allowed, response.text


async def test_entry_logs_cannot_forge_a_grant_or_another_holder(hardware_client):
    client, sessions, data = hardware_client
    body = {"card_number": "OWN", "holder_id": str(data["children"][0].id), "device_id": "gate-a",
        "branch_id": str(data["branch"].id), "access_status": "GRANTED"}
    for changes in ({"holder_id": str(data["second_student"].id)}, {"branch_id": str(data["second_branch"].id)},
        {"card_number": "UNKNOWN"}, {"access_status": "INVALID"}):
        response = await client.post("/api/hardware/access/log", headers=auth(data["manager"]), json={**body, **changes})
        assert response.status_code == 422, response.text
    assert (await client.post("/api/hardware/access/log", headers=auth(data["manager"]), json=body)).status_code == 200
    denied = {**body, "card_number": "UNKNOWN", "access_status": "DENIED", "holder_id": None}
    assert (await client.post("/api/hardware/access/log", headers=auth(data["manager"]), json=denied)).status_code == 200
    async with sessions() as db:
        rows = (await db.execute(select(AuditLog).where(AuditLog.entity_type == "ACCESS_LOG"))).scalars().all()
        assert len(rows) == 2 and all(row.organization_id == data["org"].id for row in rows)
        unknown = next(row for row in rows if row.new_values["card_number"] == "UNKNOWN")
        assert unknown.entity_id is None and unknown.new_values["holder_id"] is None


async def test_root_card_lookup_disambiguates_organization_and_rejects_corrupt_holder(hardware_client):
    client, sessions, data = hardware_client
    root_scope = {**auth(data["root"]), "X-SCS360-Organization-Id": str(data["org"].id)}
    response = await client.post("/api/hardware/card/balance", headers=root_scope, json={"card_number": "OWN"})
    assert response.status_code == 200, response.text
    assert response.json()["data"]["holder_id"] == str(data["children"][0].id)
    response = await client.post("/api/hardware/card/topup", headers=root_scope,
        params={"card_number": "CORRUPT", "amount": "10", "payment_method": "CASH"})
    assert response.status_code == 422, response.text
    async with sessions() as db:
        assert (await db.execute(select(CanteenWalletTransaction))).scalars().all() == []


async def test_wallet_daily_spend_uses_school_day_even_before_utc_midnight(portal_db, monkeypatch):
    sessions, data = portal_db
    monkeypatch.setattr(wallets, "school_today", lambda: date(2026, 11, 3))
    tenant = TenantContext(user_id=data["teacher"].id, organization_id=data["org"].id, role_slugs={"org_admin"})
    student = data["children"][0]
    async with sessions() as db:
        db.add_all([CanteenWalletTransaction(student_id=student.id, amount=100, transaction_type="CREDIT", payment_method="CASH",
            status="COMPLETED", created_at=datetime(2026, 11, 2, 20, 0, tzinfo=UTC)),
            CanteenWalletTransaction(student_id=student.id, amount=10, transaction_type="DEBIT", payment_method="WALLET",
                status="COMPLETED", created_at=datetime(2026, 11, 2, 22, 0, tzinfo=UTC))])
        await db.commit()
    async with sessions() as db:
        owner, wallet = await wallets.wallet(db, tenant, student.id)
        assert wallet.balance == Decimal("90") and wallet.today_spent == Decimal("10")
        wallet.daily_limit = Decimal("12")
        await db.commit()
    async with sessions() as db:
        with pytest.raises(ConflictException):
            await wallets.purchase(db, tenant, student.id, price="3", name="Test")
    async with sessions() as db:
        result = await wallets.purchase(db, tenant, student.id, price="2", name="Test")
        assert result["new_balance"] == 88 and result["daily_spent"] == 12
