from datetime import date
from sqlalchemy import select

from test_material_files import materials_client, headers  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401
from app.domain.entities.guidance import GuidanceSession, GuidanceNote
from app.infrastructure.models.models import Permission, Role, RolePermission, User, UserRole


async def test_guidance_confidential_records_are_private_and_counselor_cannot_be_forged(materials_client):
    client, sessions, data = materials_client
    async with sessions() as db:
        permissions = [Permission(code=code, name=code, module="guidance") for code in ("guidance.read", "guidance.write")]
        role = Role(name="Counselor", slug="counselor", organization_id=data["org"].id, permissions=permissions)
        counselor = User(email="counselor@privacy.invalid", password_hash="unused", first_name="Counselor", last_name="Own", organization_id=data["org"].id, roles=[role], branches=[data["branch"]])
        other = User(email="other-counselor@privacy.invalid", password_hash="unused", first_name="Counselor", last_name="Other", organization_id=data["org"].id, roles=[role], branches=[data["branch"]])
        foreign = User(email="foreign-counselor@privacy.invalid", password_hash="unused", first_name="Foreign", last_name="Counselor", organization_id=data["stranger"].organization_id)
        db.add_all([counselor, other, foreign]); await db.flush()
        for actor, level, text in ((other, "STANDARD", "Shared record"), (other, "CONFIDENTIAL", "Private other record"), (counselor, "CONFIDENTIAL", "Private own record")):
            db.add(GuidanceSession(student_id=data["children"][0].id, counselor_id=actor.id,
                session_date=date(2026, 11, 3), confidentiality_level=level, summary=text))
            db.add(GuidanceNote(student_id=data["children"][0].id, counselor_id=actor.id, content=text, confidentiality_level=level))
        await db.commit()
    for path in ("/api/guidance/sessions", "/api/guidance/notes", f'/api/guidance/students/{data["children"][0].id}/timeline'):
        response = await client.get(path, headers=headers(counselor))
        assert response.status_code == 200, response.text
        assert "Private own record" in response.text and "Shared record" in response.text
        assert "Private other record" not in response.text
    for path, payload in (("sessions", {"session_date": "2026-11-03"}), ("notes", {"content": "Own observation"})):
        own = await client.post("/api/guidance/" + path, headers=headers(counselor), json={"student_id": str(data["children"][0].id), **payload})
        assert own.status_code == 200, own.text
        forged = await client.post("/api/guidance/" + path, headers=headers(counselor), json={"student_id": str(data["children"][0].id), "counselor_id": str(foreign.id), **payload})
        assert forged.status_code in {403, 404, 422}, forged.text
    forged = await client.post("/api/guidance/incidents", headers=headers(counselor), json={"student_id": str(data["children"][0].id), "incident_date": "2026-11-03", "description": "Actual actor required", "reported_by": str(other.id)})
    assert forged.status_code in {403, 422}, forged.text
    async with sessions() as db:
        permission = Permission(code="guidance.read_confidential", name="Confidential records", module="guidance")
        db.add(permission); await db.flush()
        role_id = (await db.execute(select(UserRole.role_id).where(UserRole.user_id == counselor.id))).scalar_one()
        db.add(RolePermission(role_id=role_id, permission_id=permission.id)); await db.commit()
    for path in ("sessions", "notes"):
        response = await client.get("/api/guidance/" + path, headers=headers(counselor))
        assert response.status_code == 200 and "Private other record" in response.text, response.text


async def test_guidance_options_actual_counters_and_json_resolution_are_persistent(materials_client):
    client, sessions, data = materials_client
    async with sessions() as db:
        actor = User(email="actual-guidance@scope.invalid", password_hash="unused", first_name="Actual", last_name="Counselor",
            organization_id=data["org"].id, branches=[data["branch"]],
            roles=[Role(name="Guidance writer", slug="counselor", organization_id=data["org"].id,
                permissions=[Permission(code=code, name=code, module="guidance") for code in ("guidance.read", "guidance.write")])])
        db.add(actor); await db.commit()
    auth = headers(actor)
    student_id = str(data["children"][0].id)
    options = await client.get("/api/guidance/options", headers=auth, params={"student_id": student_id})
    assert options.status_code == 200, options.text
    choices = options.json()["data"]
    assert choices["counselors"] == [{"id": str(actor.id), "name": "Actual Counselor"}]
    assert str(data["stranger"].id) not in [row["id"] for row in choices["students"]]
    session = await client.post("/api/guidance/sessions", headers=auth, json={"student_id": student_id, "session_date": "2026-11-03", "summary": "Actual session", "confidentiality_level": "CONFIDENTIAL"})
    assert session.status_code == 200, session.text
    note = await client.post("/api/guidance/notes", headers=auth, json={"student_id": student_id, "content": "Actual observation", "confidentiality_level": "RESTRICTED"})
    assert note.status_code == 200, note.text
    incident = await client.post("/api/guidance/incidents", headers=auth, json={"student_id": student_id, "incident_date": "2026-11-03", "description": "Actual incident"})
    assert incident.status_code == 200, incident.text
    identifier = incident.json()["data"]["id"]
    stats = (await client.get("/api/guidance/summary", headers=auth)).json()["data"]
    assert stats == {"total_sessions": 1, "total_notes": 1, "total_incidents": 1, "active_cases": 1, "resolution_rate": 0}
    assert (await client.get("/api/ai/guidance-analysis", headers=auth)).json()["data"] == stats
    for text in ("Recorded solution", "Retry must preserve solution"):
        response = await client.put(f"/api/guidance/incidents/{identifier}/resolve", headers=auth, json={"resolution_notes": text})
        assert response.status_code == 200 and response.json()["data"]["resolved"] is True, response.text
    records = (await client.get("/api/guidance/incidents", headers=auth)).json()["data"]
    assert records[0]["reported_by"] == str(actor.id) and records[0]["resolution_notes"] == "Recorded solution"
    assert (await client.get("/api/guidance/summary", headers=auth)).json()["data"]["active_cases"] == 0
    for path, payload in (("notes", {"content": "x" * 5001}), ("sessions", {"session_date": "2026-11-03", "start_time": "15:00", "end_time": "14:00"})):
        invalid = await client.post("/api/guidance/" + path, headers=auth, json={"student_id": student_id, **payload})
        assert invalid.status_code == 422, invalid.text
