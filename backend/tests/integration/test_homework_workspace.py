from uuid import uuid4

from app.infrastructure.models.models import Branch, User
from test_material_files import materials_client, headers  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401


async def test_homework_scope_and_request_identity_are_preserved_through_grading(materials_client):
    client, sessions, data = materials_client
    async with sessions() as db:
        other = Branch(organization_id=data["org"].id, name="Alternate homework branch")
        actor = User(organization_id=data["org"].id, email="isolated-homework-root@test.invalid", first_name="Test",
            last_name="Operator", password_hash="unused", is_super_admin=True)
        db.add_all([other, actor])
        await db.commit()
    auth = {**headers(actor), "X-SCS360-Organization-Id": str(data["org"].id)}
    branch = {"branch_id": str(data["branch"].id)}
    wrong = {"branch_id": str(other.id)}
    child = str(data["children"][0].id)
    request_id = str(uuid4())
    form = {"title": "İzole ödev", "status": "ACTIVE", "class_id": str(data["classroom"].id), "request_id": request_id}
    denied = await client.post("/api/homework", headers=auth, params=wrong, json=form)
    assert denied.status_code == 403
    for _ in range(2):
        created = await client.post("/api/homework", headers=auth, params=branch, json=form)
        assert created.status_code == 200 and created.json()["data"]["id"] == request_id, created.text
    listed = await client.get("/api/homework", headers=auth, params=branch)
    assert [row["id"] for row in listed.json()["data"]["items"]] == [request_id]
    filtered = await client.get("/api/homework", headers=auth, params=wrong)
    assert filtered.json()["data"]["items"] == []
    students = await client.get(f"/api/homework/{request_id}/students", headers=auth, params=branch)
    assert students.status_code == 200 and child in {row["id"] for row in students.json()["data"]["students"]}
    body = {"student_id": child, "homework_id": request_id, "submission_text": "İzole teslim"}
    submitted = await client.post(f"/api/homework/{request_id}/submit", headers=auth, params=branch, json=body)
    assert submitted.status_code == 200, submitted.text
    identifier = submitted.json()["data"]["id"]
    attachment = b"%PDF-1.4\nisolated homework"
    uploaded = await client.post(f"/api/homework/{request_id}/submit-file", headers=auth, params=branch,
        data={"student_id": child, "submission_text": "İzole teslim"},
        files={"file": ("izole.pdf", attachment, "application/pdf")})
    assert uploaded.status_code == 200 and uploaded.json()["data"]["id"] == identifier, uploaded.text
    download_path = f"/api/homework/submissions/{identifier}/attachment"
    assert (await client.get(download_path, headers=auth, params=wrong)).status_code == 404
    downloaded = await client.get(download_path, headers=auth, params=branch)
    assert downloaded.status_code == 200 and downloaded.content == attachment
    grade_path = f"/api/homework/submissions/{identifier}/grade"
    grade = {"score": 87.25, "teacher_feedback": "İzole değerlendirme"}
    assert (await client.put(grade_path, headers=auth, params=wrong, json=grade)).status_code == 404
    confirmed = await client.put(grade_path, headers=auth, params=branch, json=grade)
    assert confirmed.status_code == 200, confirmed.text
    selected = await client.get("/api/homework/submissions", headers=auth,
        params={**branch, "homework_id": request_id, "record_id": identifier, "limit": 1})
    rows = selected.json()["data"]
    assert len(rows) == 1 and rows[0]["student_id"] == child and rows[0]["score"] == 87.25
    assert rows[0]["status"] == "GRADED" and rows[0]["teacher_feedback"] == grade["teacher_feedback"]


async def test_parent_homework_uses_only_the_selected_child_submission(materials_client):
    client, _, data = materials_client
    teacher = headers(data["teacher"])
    parent = headers(data["user"])
    created = await client.post("/api/homework", headers=teacher,
        json={"title": "Veli kapsamı", "class_id": str(data["classroom"].id)})
    assert created.status_code == 200, created.text
    homework_id = created.json()["data"]["id"]
    by_child = {}
    for child in data["children"]:
        child_id = str(child.id)
        listing = await client.get(f"/api/parent/child/{child_id}/homework", headers=parent)
        assert [row["id"] for row in listing.json()["data"]] == [homework_id]
        saved = await client.post(f"/api/homework/{homework_id}/submit", headers=parent,
            json={"student_id": child_id, "homework_id": homework_id, "submission_text": child.first_name})
        assert saved.status_code == 200, saved.text
        by_child[child_id] = saved.json()["data"]["id"]
    child_a, child_b = by_child
    path = "/api/homework/submissions"
    response = await client.get(path, headers=parent, params={"homework_id": homework_id, "student_id": child_b})
    assert [row["id"] for row in response.json()["data"]] == [by_child[child_b]]
    mismatched = await client.get(path, headers=parent,
        params={"homework_id": homework_id, "student_id": child_b, "record_id": by_child[child_a]})
    assert mismatched.json()["data"] == []
    outsider = await client.get(path, headers=parent,
        params={"homework_id": homework_id, "student_id": str(data["stranger"].id)})
    assert outsider.json()["data"] == []
