from uuid import UUID

from test_saas_platform import platform_client  # noqa: F401
from test_material_files import materials_client, headers  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401
from app.infrastructure.models.models import Student


async def test_student_and_parent_bad_writes_are_validation_errors_and_keep_existing_data(platform_client):
    client, sessions, data = platform_client
    auth = {**headers(data["root"]), "X-SCS360-Organization-Id": str(data["org"].id)}
    body = {"organization_id": str(data["org"].id), "branch_id": str(data["branch"].id), "first_name": "Deneme", "last_name": "Ogrenci", "student_number": "VALIDATION-001", "birth_date": "2020-01-01"}
    invalid = [{"branch_id": "invalid"}, {"organization_id": "invalid"}, {"class_id": "invalid"}, {"birth_date": "2020-02-31"}, {"enrollment_date": "yesterday"}, {"gender": "unknown"}, {"status": "unknown"}, {"first_name": " "}, {"last_name": "A" * 101}, {"student_number": "A" * 51}, {"date_of_birth": "2021-01-01"}]
    for fields in invalid:
        response = await client.post("/api/students", headers=auth, json={**body, **fields})
        assert response.status_code == 422, (fields, response.text)
    first = await client.post("/api/students", headers=auth, json={**body, "status": "active", "gender": "female"})
    assert first.status_code == 200, first.text
    identifier = first.json()["data"]["id"]
    assert (await client.post("/api/students", headers=auth, json=body)).status_code == 409
    for fields in [{"first_name": None}, {"last_name": None}, {"status": None}, {"branch_id": None}, {"branch_id": "invalid"}, {"birth_date": "2020-02-31"}, {"status": "unknown"}]:
        response = await client.put(f"/api/students/{identifier}", headers=auth, json=fields)
        assert response.status_code == 422, (fields, response.text)
    response = await client.put(f"/api/students/{identifier}", headers=auth, json={"date_of_birth": None})
    assert response.status_code == 200, response.text
    async with sessions() as db:
        row = await db.get(Student, UUID(identifier))
        assert row.first_name == "Deneme" and row.birth_date is None and row.student_number == "VALIDATION-001"
    parent = await client.post("/api/parents", headers=auth, json={"organization_id": str(data["org"].id), "first_name": "Deneme", "last_name": "Veli"})
    assert parent.status_code == 200, parent.text
    for field in ["first_name", "last_name", "relation_type", "receive_notifications"]:
        response = await client.put(f'/api/parents/{parent.json()["data"]["id"]}', headers=auth, json={field: None})
        assert response.status_code == 422, response.text
