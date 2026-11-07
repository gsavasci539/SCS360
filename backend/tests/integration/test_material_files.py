from datetime import date, timedelta
from io import BytesIO
from uuid import UUID

import pytest
from fastapi import UploadFile
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from test_parent_homework_outbox import portal_db  # noqa: F401
from app.core.config import get_settings
from app.core.database import get_db
from app.core.exceptions import ValidationException
from app.core.security import create_access_token
from app.domain.entities.materials import CourseMaterial
from app.infrastructure.models.models import User
from app.infrastructure.storage.local_storage import LocalFileStorage
from app.infrastructure.storage.uploads import read_upload
from app.main import app
from app.core.rate_limit import limiter


@pytest.fixture
async def materials_client(portal_db, tmp_path, monkeypatch):
    sessions, data = portal_db
    # Every fixture is a separate application/database acceptance scenario.
    # Keep login throttling active inside it without carrying another test's IP quota.
    limiter.reset()
    monkeypatch.setattr(get_settings(), "PRIVATE_UPLOAD_DIR", str(tmp_path / "private"))
    monkeypatch.setattr(get_settings(), "UPLOAD_DIR", str(tmp_path / "uploads"))
    async def override_db():
        async with sessions() as db:
            try:
                yield db
                await db.commit()
            except Exception:
                await db.rollback()
                raise
    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = override_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield client, sessions, data
    finally:
        app.dependency_overrides = previous


def headers(user):
    return {"Authorization": "Bearer " + create_access_token(user.id)}


async def upload(client, data, **params):
    return await client.post("/api/materials/upload", headers=headers(data["teacher"]),
        params={"title": "Çalışma kâğıdı", "material_type": "PDF", "visibility": "CLASS_ONLY",
            "class_id": str(data["classroom"].id), **params},
        files={"file": ("../../çalışma.pdf", b"%PDF-1.4\nacceptance", "application/pdf")})


async def test_material_upload_download_and_parent_visibility(materials_client):
    client, sessions, data = materials_client
    response = await upload(client, data)
    assert response.status_code == 200, response.text
    material = response.json()["data"]
    assert material["file_name"] == "çalışma.pdf"
    path = material["file_url"]
    assert path.startswith("/api/materials/") and path.endswith("/file")
    assert (await client.get(path)).status_code == 401
    downloaded = await client.get(path, headers=headers(data["teacher"]))
    assert downloaded.status_code == 200 and downloaded.content.startswith(b"%PDF-")
    assert downloaded.headers["cache-control"] == "private, no-store"
    child = data["children"][0]
    parent_path = f"/api/parent/child/{child.id}/materials"
    listing = await client.get(parent_path, headers=headers(data["user"]))
    assert [item["id"] for item in listing.json()["data"]] == [material["id"]]
    assert (await client.get(parent_path + f'/{material["id"]}/download', headers=headers(data["user"]))).status_code == 200
    assert (await client.get(path, headers=headers(data["user"]))).status_code == 403
    # A corrupt cross-institution parent link must never authorize the download.
    forbidden = f'/api/parent/child/{data["stranger"].id}/materials/{material["id"]}/download'
    assert (await client.get(forbidden, headers=headers(data["user"]))).status_code == 403
    for params in ({"visibility": "TEACHER_ONLY"}, {"visible_from": (date.today() + timedelta(days=1)).isoformat()},
        {"visible_until": (date.today() - timedelta(days=1)).isoformat()}):
        hidden = await upload(client, data, **params)
        assert hidden.status_code == 200
        hidden_id = hidden.json()["data"]["id"]
        assert (await client.get(parent_path + f'/{hidden_id}/download', headers=headers(data["user"]))).status_code == 404
    listing = await client.get(parent_path, headers=headers(data["user"]))
    assert len(listing.json()["data"]) == 1
    async with sessions() as db:
        row = await db.get(CourseMaterial, UUID(material["id"]))
        assert row.download_count == 2
        assert row.created_by == data["teacher"].id and row.teacher_id == data["teacher"].id
    assert (await client.delete("/api/materials/" + material["id"], headers=headers(data["teacher"]))).status_code == 200
    assert (await client.get(path, headers=headers(data["teacher"]))).status_code == 404


async def test_invalid_uploads_are_validation_errors_not_server_errors(materials_client, monkeypatch):
    client, sessions, data = materials_client
    for params in ({"material_type": "EXECUTABLE"}, {"class_id": str(data["other_class"].id)},
        {"class_id": ""}, {"visibility": "SPECIFIC_STUDENTS"},
        {"visible_from": "2026-11-03", "visible_until": "2026-11-02"}):
        response = await upload(client, data, **params)
        assert response.status_code == 422, response.text
    monkeypatch.setattr(get_settings(), "MAX_UPLOAD_SIZE_MB", 0)
    response = await upload(client, data)
    assert response.status_code == 422
    async with sessions() as db:
        assert (await db.execute(select(CourseMaterial))).scalars().all() == []
        teacher = await db.get(User, data["teacher"].id)
        teacher.is_super_admin = True
        await db.commit()
    response = await client.post(f'/api/students/{data["children"][0].id}/files',
        headers=headers(data["teacher"]), data={"category": "NOT_A_CATEGORY"},
        files={"file": ("file.pdf", b"%PDF-1.4 test", "application/pdf")})
    assert response.status_code == 422, response.text


async def test_unowned_and_foreign_materials_do_not_leak(materials_client):
    client, sessions, data = materials_client
    async with sessions() as db:
        other = User(email="foreign@test.invalid", password_hash="unused", first_name="Other", last_name="User",
            organization_id=data["other_branch"].organization_id)
        db.add(other)
        await db.flush()
        for owner in (None, other.id):
            db.add(CourseMaterial(title="Private", material_type="PDF", file_url="/uploads/materials/private.pdf",
                teacher_id=owner, created_by=owner, visibility="PUBLIC"))
        await db.commit()
    response = await client.get("/api/materials", headers=headers(data["teacher"]))
    assert response.status_code == 200 and response.json()["data"] == []
    assert (await client.get(f'/api/parent/child/{data["children"][0].id}/materials',
        headers=headers(data["user"]))).json()["data"] == []


async def test_public_material_is_available_to_other_classes_and_legacy_files_stay_private(materials_client):
    from pathlib import Path
    client, sessions, data = materials_client
    root = Path(get_settings().UPLOAD_DIR) / "materials"
    root.mkdir(parents=True)
    (root / "legacy.pdf").write_bytes(b"%PDF-1.4 legacy")
    async with sessions() as db:
        material = CourseMaterial(title="Kurum kaynağı", class_id=data["other_class"].id,
            teacher_id=data["teacher"].id, created_by=data["teacher"].id, material_type="PDF",
            visibility="PUBLIC", file_name="legacy.pdf", file_url="/uploads/materials/legacy.pdf")
        db.add(material)
        await db.commit()
        material_id = material.id
    child_path = f'/api/parent/child/{data["children"][0].id}/materials'
    response = await client.get(child_path, headers=headers(data["user"]))
    assert [item["id"] for item in response.json()["data"]] == [str(material_id)]
    downloaded = await client.get(child_path + f"/{material_id}/download", headers=headers(data["user"]))
    assert downloaded.status_code == 200 and downloaded.content == b"%PDF-1.4 legacy"
    assert (await client.get("/uploads/materials/legacy.pdf")).status_code == 404


async def test_storage_rejects_sibling_prefix_and_absolute_escape(tmp_path):
    storage = LocalFileStorage(str(tmp_path / "uploads"))
    for path in ("../uploads-other/secret.pdf", str(tmp_path / "secret.pdf")):
        with pytest.raises(ValidationException):
            storage.get_full_path(path)
    for name, content in (("wrong.pdf", b"not pdf"), ("empty.pdf", b""), ("bad.docx", b"not zip")):
        with pytest.raises(ValidationException):
            await read_upload(UploadFile(filename=name, file=BytesIO(content)))


async def test_material_submission_persists_and_grading_works(materials_client):
    client, sessions, data = materials_client
    material = (await upload(client, data)).json()["data"]
    path = f'/api/materials/{material["id"]}/submissions'
    payload = {"material_id": material["id"], "student_id": str(data["children"][0].id),
        "submission_text": "Öğrenci çalışmayı tamamladı."}
    response = await client.post(path, headers=headers(data["teacher"]), json=payload)
    assert response.status_code == 200, response.text
    submission_id = response.json()["data"]["id"]
    assert (await client.post(path, headers=headers(data["teacher"]), json=payload)).status_code == 409
    response = await client.put(f'/api/materials/submissions/{submission_id}/grade',
        headers=headers(data["teacher"]), json={"grade": 92, "feedback": "Başarılı"})
    assert response.status_code == 200, response.text
    listing = (await client.get(path, headers=headers(data["teacher"]))).json()["data"]
    assert len(listing) == 1 and float(listing[0]["grade"]) == 92 and listing[0]["status"] == "GRADED"
    assert (await client.post(path, headers=headers(data["teacher"]),
        json={**payload, "material_id": str(data["classroom"].id)})).status_code == 422
    assert (await client.delete('/api/materials/' + material["id"], headers=headers(data["teacher"]))).status_code == 200
    # Deletion preserves the historical submission instead of failing its FK.
    from app.domain.entities.materials import MaterialSubmission
    async with sessions() as db:
        assert (await db.get(MaterialSubmission, UUID(submission_id))).feedback == "Başarılı"
