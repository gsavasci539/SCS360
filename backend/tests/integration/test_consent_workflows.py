import asyncio
from datetime import timedelta
from hashlib import sha256

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from test_material_files import materials_client, headers  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401
from app.core.dates import school_today
from app.domain.entities.consents import ConsentDocument, StudentConsent
from app.infrastructure.models.models import AuditLog, Branch, Parent, Permission, Role, RolePermission, Student, User


async def setup(client, sessions, data, *, grant_parent=True):
    async with sessions() as db:
        role = Role(name="Consent manager", slug="org_admin", organization_id=data["org"].id,
            permissions=[Permission(code=code, name=code, module="consents") for code in ("consents.read", "consents.write")])
        manager = User(organization_id=data["org"].id, first_name="Manager", last_name="Consent",
            email="manager@consent.invalid", password_hash="unused", roles=[role])
        db.add(manager)
        if grant_parent:
            permission = Permission(code="parent.give_consent", name="Guardian decision", module="parent")
            db.add(permission); await db.flush()
            parent_role = (await db.execute(select(Role).where(Role.slug == "parent"))).scalar_one()
            db.add(RolePermission(role_id=parent_role.id, permission_id=permission.id))
        await db.commit()
    payload = {"title": "Gezi izni", "document_type": "TRIP_CONSENT", "content": "Gezinin tam kapsamı.", "effective_date": str(school_today()), "version": "1.0"}
    response = await client.post("/api/consents/documents", headers=headers(manager), json=payload)
    assert response.status_code == 200, response.text
    return manager, response.json()["data"], payload


def decision(document, **overrides):
    return {"consent_status": "APPROVED", "acknowledged": True, "document_version": document["version"],
        "content_sha256": document["content_sha256"], "signed_name": "Parent Test", **overrides}


async def test_guardian_decision_version_freeze_retry_and_audit(materials_client):
    client, sessions, data = materials_client
    manager, doc, payload = await setup(client, sessions, data)
    path = f'/api/parent/child/{data["children"][0].id}/consents'
    listing = await client.get(path, headers=headers(data["user"]))
    assert listing.status_code == 200 and listing.json()["data"][0]["content"] == payload["content"]
    responses = await asyncio.gather(*[client.post(path + "/" + doc["id"], headers=headers(data["user"]), json=decision(doc)) for _ in range(2)])
    assert all(response.status_code == 200 for response in responses), [response.text for response in responses]
    assert responses[0].json()["data"] == responses[1].json()["data"]
    frozen = await client.put("/api/consents/documents/" + doc["id"], headers=headers(manager), json={**payload, "content": "Changed terms"})
    assert frozen.status_code == 409, frozen.text
    async with sessions() as db:
        assert (await db.execute(select(func.count(StudentConsent.id)))).scalar() == 1
        logs = (await db.execute(select(AuditLog).where(AuditLog.entity_type == "student_consent"))).scalars().all()
        assert len(logs) == 1 and logs[0].user_id == data["user"].id
        assert logs[0].new_values["content_sha256"] == sha256(payload["content"].encode()).hexdigest()
        assert "Parent Test" not in str(logs[0].new_values)
    rejected = await client.post(path + "/" + doc["id"], headers=headers(data["user"]), json=decision(doc, consent_status="REJECTED"))
    assert rejected.status_code == 200 and rejected.json()["data"]["consent_status"] == "REJECTED"
    records = (await client.get("/api/consents/student-consents", headers=headers(manager))).json()["data"]
    assert records[0]["document_version"] == "1.0" and "signature_data" not in records[0] and "ip_address" not in records[0]
    assert records[0]["consent_method"] == "PARENT_PORTAL"


async def test_guardian_permission_child_ownership_and_forged_parent_denied(materials_client):
    client, sessions, data = materials_client
    manager, doc, _ = await setup(client, sessions, data, grant_parent=False)
    path = f'/api/parent/child/{data["children"][0].id}/consents/{doc["id"]}'
    assert (await client.post(path, headers=headers(data["user"]), json=decision(doc))).status_code == 403
    assert (await client.get("/api/consents/documents", headers=headers(data["user"]))).status_code == 403
    assert (await client.get(f'/api/parent/child/{data["stranger"].id}/consents', headers=headers(data["user"]))).status_code == 403
    async with sessions() as db:
        foreign = Parent(organization_id=data["stranger"].organization_id, first_name="Foreign", last_name="Guardian")
        db.add(foreign); await db.commit()
    manual = {"student_id": str(data["children"][0].id), "parent_id": str(foreign.id), "consent_document_id": doc["id"]}
    response = await client.post("/api/consents/student-consents", headers=headers(manager), json=manual)
    assert response.status_code in {403, 422}, response.text
    assert (await client.post("/api/consents/student-consents", headers=headers(manager), json={**manual, "consent_method": "PARENT_PORTAL"})).status_code == 422


async def test_document_dates_stale_content_archival_and_tenant_ownership(materials_client):
    client, sessions, data = materials_client
    manager, doc, payload = await setup(client, sessions, data)
    path = f'/api/parent/child/{data["children"][0].id}/consents/{doc["id"]}'
    updated = await client.put("/api/consents/documents/" + doc["id"], headers=headers(manager), json={**payload, "content": "New detailed terms"})
    assert updated.status_code == 200, updated.text
    assert (await client.post(path, headers=headers(data["user"]), json=decision(doc))).status_code == 409
    current = updated.json()["data"]
    assert (await client.post(path, headers=headers(data["user"]), json=decision(current, acknowledged=False))).status_code == 422
    assert (await client.post(path, headers=headers(data["user"]), json={**decision(current), "parent_id": str(data["user"].id)})).status_code == 422
    assert (await client.post(path, headers=headers(data["user"]), json=decision(current))).status_code == 200
    archive = await client.patch("/api/consents/documents/" + doc["id"] + "/status", headers=headers(manager), json={"is_active": False})
    assert archive.status_code == 200, archive.text
    listing = (await client.get(path.rsplit("/", 1)[0], headers=headers(data["user"]))).json()["data"]
    assert listing[0]["consent_status"] == "APPROVED" and listing[0]["can_decide"] is False
    assert (await client.post(path, headers=headers(data["user"]), json=decision(current, consent_status="REJECTED"))).status_code == 409
    future = await client.post("/api/consents/documents", headers=headers(manager), json={**payload, "effective_date": str(school_today() + timedelta(days=2))})
    assert future.status_code == 200
    assert (await client.post(path.rsplit("/", 1)[0] + "/" + future.json()["data"]["id"], headers=headers(data["user"]), json=decision(future.json()["data"]))).status_code == 409
    assert (await client.post("/api/consents/documents", headers=headers(manager), json={**payload, "organization_id": str(data["stranger"].organization_id)})).status_code == 403


async def test_manual_decision_valid_guardian_options_and_summary(materials_client):
    client, sessions, data = materials_client
    manager, doc, _ = await setup(client, sessions, data)
    async with sessions() as db:
        parent = (await db.execute(select(Parent).where(Parent.user_id == data["user"].id))).scalar_one()
    options = await client.get("/api/consents/options", headers=headers(manager), params={"student_id": str(data["children"][0].id)})
    assert options.status_code == 200 and options.json()["data"]["parents"][0]["id"] == str(parent.id)
    assert len(options.json()["data"]["students"]) == 2
    payload = {"student_id": str(data["children"][0].id), "consent_document_id": doc["id"], "parent_id": str(parent.id), "consent_status": "REJECTED", "consent_method": "PAPER", "notes": "Written decision recorded"}
    result = await client.post("/api/consents/student-consents", headers=headers(manager), json=payload)
    assert result.status_code == 200, result.text
    summary = (await client.get("/api/consents/consent-summary", headers=headers(manager))).json()["data"]
    assert summary["rejected"] == 1 and summary["total"] == 1 and summary["approval_rate"] == 0


async def test_document_freeze_includes_hidden_branch_decisions_and_root_authors(materials_client):
    client, sessions, data = materials_client
    manager, doc, payload = await setup(client, sessions, data)
    async with sessions() as db:
        actor = (await db.execute(select(User).options(selectinload(User.branches)).where(User.id == manager.id))).scalar_one()
        actor.branches = [data["branch"]]
        root = User(email="root@consent.invalid", password_hash="unchanged", first_name="Root", last_name="Owner", is_super_admin=True)
        branch = Branch(organization_id=data["org"].id, name="Hidden branch")
        db.add_all([root, branch]); await db.flush()
        student = Student(organization_id=data["org"].id, branch_id=branch.id, first_name="Hidden", last_name="Child")
        db.add(student); await db.flush()
        from uuid import UUID
        record = StudentConsent(student_id=student.id, consent_document_id=UUID(doc["id"]), consent_status="APPROVED")
        db.add(record); await db.commit()
    assert (await client.get("/api/consents/student-consents", headers=headers(manager))).json()["data"] == []
    assert (await client.put("/api/consents/documents/" + doc["id"], headers=headers(manager), json={**payload, "content": "Must remain frozen"})).status_code == 409
    response = await client.post("/api/consents/documents", headers=headers(root), json={**payload, "title": "Root authored", "organization_id": str(data["org"].id)})
    assert response.status_code == 200, response.text
    identifier = response.json()["data"]["id"]
    archived = await client.patch(f"/api/consents/documents/{identifier}/status", headers=headers(manager), json={"is_active": False})
    assert archived.status_code == 200, archived.text
