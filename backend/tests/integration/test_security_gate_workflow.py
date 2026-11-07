import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select

from test_material_files import materials_client, headers  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401
from app.core.dates import school_today, school_day_bounds
from app.domain.entities.security import DigitalIdToken, GateLog
from app.infrastructure.models.models import Permission, Role, User


@pytest.fixture
async def security_client(materials_client):
    client, sessions, data = materials_client
    async with sessions() as db:
        read = Permission(code="security.read", name="Security read", module="security")
        write = Permission(code="security.write", name="Security write", module="security")
        students_read = (await db.execute(select(Permission).where(Permission.code == "students.read"))).scalar_one()
        writer = User(email="gate-writer@test.invalid", password_hash="unused", first_name="Gate", last_name="Officer",
            organization_id=data["org"].id, branches=[data["branch"]], roles=[Role(name="Gate desk", slug="security", organization_id=data["org"].id,
                permissions=[read, write, students_read])])
        reader = User(email="gate-reader@test.invalid", password_hash="unused", first_name="Gate", last_name="Reader",
            organization_id=data["org"].id, branches=[data["branch"]], roles=[Role(name="Gate read only", slug="security_reader", organization_id=data["org"].id, permissions=[read])])
        db.add_all([writer, reader]); await db.commit()
    return client, sessions, {**data, "writer": writer, "reader": reader}


async def test_student_read_permission_cannot_issue_gate_credentials_and_read_is_side_effect_free(security_client):
    client, sessions, data = security_client
    child = str(data["children"][0].id)
    denied = await client.get("/api/security/digital-id/" + child, headers=headers(data["teacher"]))
    assert denied.status_code == 403, denied.text
    response = await client.get("/api/security/digital-id/" + child, headers=headers(data["reader"]))
    assert response.status_code == 200 and response.json()["data"]["id"] is None, response.text
    async with sessions() as db:
        assert (await db.execute(select(func.count(DigitalIdToken.id)))).scalar() == 0
    assert (await client.post("/api/security/digital-id/generate", headers=headers(data["reader"]), json={"student_id": child})).status_code == 403


async def test_security_legacy_multiple_active_ids_read_latest_and_qr_download_is_private(security_client):
    client, sessions, data = security_client
    async with sessions() as db:
        rows = [DigitalIdToken(student_id=data["children"][0].id, token=str(uuid4()), barcode_number="SCS" + uuid4().hex,
            issued_at=datetime.now(UTC) - timedelta(hours=index), expires_at=datetime.now(UTC) + timedelta(days=1)) for index in (0, 1)]
        db.add_all(rows); await db.commit()
    auth = headers(data["writer"])
    response = await client.get(f'/api/security/digital-id/{data["children"][0].id}', headers=auth)
    assert response.status_code == 200 and response.json()["data"]["id"] == str(rows[0].id), response.text
    downloaded = await client.get(response.json()["data"]["qr_code_url"], headers=auth)
    assert downloaded.status_code == 200 and b"<svg" in downloaded.content, downloaded.text[:100]
    assert downloaded.headers["cache-control"] == "private, no-store"
    assert (await client.get(response.json()["data"]["qr_code_url"])).status_code == 401
    async with sessions() as db:
        assert (await db.execute(select(func.count(DigitalIdToken.id)))).scalar() == 2


async def test_gate_verification_has_real_actor_branch_and_retry_without_invented_pickup_permissions(security_client):
    client, sessions, data = security_client
    auth = headers(data["writer"]); child = str(data["children"][0].id)
    issue = {"student_id": child, "request_id": str(uuid4())}
    issued = await asyncio.gather(*[client.post("/api/security/digital-id/generate", headers=auth, json=issue) for _ in range(2)])
    assert all(row.status_code == 200 for row in issued), [row.text for row in issued]
    assert issued[0].json()["data"]["id"] == issued[1].json()["data"]["id"]
    token = issued[0].json()["data"]
    changed = await client.post("/api/security/digital-id/generate", headers=auth, json={**issue, "expires_hours": 12})
    assert changed.status_code == 409, changed.text
    body = {"token": token["token"], "direction": "IN", "gate_location": "Acceptance gate", "request_id": str(uuid4())}
    replies = await asyncio.gather(*[client.post("/api/security/gate-logs/verify-qr", headers=auth, json=body) for _ in range(2)])
    assert all(row.status_code == 200 for row in replies), [row.text for row in replies]
    result = replies[0].json()["data"]
    assert result["authorized"] is True and result["gate_log_id"] == replies[1].json()["data"]["gate_log_id"]
    assert result["timestamp"] == replies[1].json()["data"]["timestamp"]
    assert result["parent_pickup_permission"] is False and result["service_permission"] is False
    async with sessions() as db:
        logs = (await db.execute(select(GateLog))).scalars().all()
        assert len(logs) == 1 and logs[0].verified_by == data["writer"].id and logs[0].branch_id == data["branch"].id
    conflict = await client.post("/api/security/gate-logs/verify-qr", headers=auth, json={**body, "direction": "OUT"})
    assert conflict.status_code == 409
    barcode = await client.post("/api/security/gate-logs/verify-qr", headers=auth, json={**body, "token": token["barcode_number"], "verification_method": "BARCODE", "request_id": str(uuid4())})
    assert barcode.status_code == 200 and barcode.json()["data"]["authorized"] is True
    rotated = await client.post("/api/security/digital-id/generate", headers=auth, json={"student_id": child, "request_id": str(uuid4())})
    assert rotated.status_code == 200
    old = await client.post("/api/security/gate-logs/verify-qr", headers=auth, json={**body, "request_id": str(uuid4())})
    assert old.status_code == 200 and old.json()["data"]["authorized"] is False


async def test_gate_day_validation_latest_presence_and_unattributable_legacy_scope(security_client):
    client, sessions, data = security_client
    auth = headers(data["writer"])
    created = await client.post("/api/security/digital-id/generate", headers=auth, json={"student_id": str(data["children"][0].id)})
    assert created.status_code == 200, created.text
    for direction in ("IN", "IN", "OUT"):
        reply = await client.post("/api/security/gate-logs/verify-qr", headers=auth, json={"token": created.json()["data"]["token"], "direction": direction, "request_id": str(uuid4())})
        assert reply.status_code == 200 and reply.json()["data"]["authorized"] is True, reply.text
    stats = await client.get("/api/security/gate-logs/stats", headers=auth, params={"date": str(school_today())})
    assert stats.status_code == 200 and stats.json()["data"]["currently_in_school"] == 0, stats.text
    assert stats.json()["data"]["total_entries"] == 2 and stats.json()["data"]["total_exits"] == 1
    assert (await client.get("/api/security/gate-logs", headers=auth, params={"start_date": "bad-date"})).status_code == 422
    async with sessions() as db:
        orphan = GateLog(direction="IN", status="AUTHORIZED")
        db.add(orphan); await db.commit()
    rows = await client.get("/api/security/gate-logs", headers=auth)
    assert rows.status_code == 200 and str(orphan.id) not in {row["id"] for row in rows.json()["data"]}, rows.text
    denied = await client.post("/api/security/digital-id/generate", headers=auth, json={"student_id": str(data["stranger"].id)})
    assert denied.status_code in {403, 404}, denied.text


async def test_security_request_uuid_collision_between_students_never_returns_500(security_client):
    client, _, data = security_client
    auth = headers(data["writer"])
    shared = str(uuid4())
    issued = await asyncio.gather(*[client.post("/api/security/digital-id/generate", headers=auth,
        json={"student_id": str(child.id), "request_id": shared}) for child in data["children"]])
    assert sorted(row.status_code for row in issued) == [200, 409], [row.text for row in issued]
    tokens = []
    for child in data["children"]:
        reply = await client.post("/api/security/digital-id/generate", headers=auth, json={"student_id": str(child.id)})
        assert reply.status_code == 200, reply.text
        tokens.append(reply.json()["data"]["token"])
    shared = str(uuid4())
    replies = await asyncio.gather(*[client.post("/api/security/gate-logs/verify-qr", headers=auth,
        json={"token": token, "direction": "IN", "request_id": shared}) for token in tokens])
    assert sorted(row.status_code for row in replies) == [200, 409], [row.text for row in replies]


async def test_gate_presence_inherits_scope_and_legacy_equal_timestamps_require_review(security_client):
    client, sessions, data = security_client
    auth = headers(data["writer"]); day = school_today(); start, _ = school_day_bounds(day)
    async with sessions() as db:
        db.add(GateLog(student_id=data["children"][0].id, branch_id=data["branch"].id, direction="IN", status="AUTHORIZED", created_at=start - timedelta(minutes=1)))
        db.add(GateLog(student_id=data["stranger"].id, branch_id=data["other_branch"].id, direction="IN", status="AUTHORIZED", created_at=start + timedelta(hours=1)))
        await db.commit()
    first = await client.get("/api/security/gate-logs/stats", headers=auth, params={"date": str(day)})
    assert first.status_code == 200 and first.json()["data"]["currently_in_school"] == 1, first.text
    assert first.json()["data"]["total_entries"] == 0
    async with sessions() as db:
        db.add(GateLog(student_id=data["children"][0].id, branch_id=data["branch"].id, direction="OUT", status="AUTHORIZED", created_at=start + timedelta(hours=1)))
        for direction in ("IN", "OUT"):
            db.add(GateLog(student_id=data["children"][1].id, branch_id=data["branch"].id, direction=direction,
                status="AUTHORIZED", created_at=start + timedelta(hours=2)))
        await db.commit()
    result = await client.get("/api/security/gate-logs/stats", headers=auth, params={"date": str(day)})
    assert result.status_code == 200 and result.json()["data"]["currently_in_school"] == 0, result.text
    assert result.json()["data"]["presence_review_required"] == 1
    filtered = await client.get("/api/security/gate-logs", headers=auth, params={"start_date": str(day), "end_date": str(day)})
    assert filtered.status_code == 200 and len(filtered.json()["data"]) == 3, filtered.text
