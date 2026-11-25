from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.testclient import TestClient

from app.core.database import get_db
from app.core.dependencies import get_tenant_context
from app.core.exceptions import AppException, ValidationException
from app.core.middleware import app_exception_handler
from app.core.tenant import TenantContext
from app.infrastructure.storage import file_service as file_service_module
from app.infrastructure.storage import uploads as uploads_module
from app.infrastructure.storage.file_service import FileService
from app.routers.files import _resolve_scoped_file
from app.routers.files import router as files_router


@pytest.mark.asyncio
async def test_upload_stores_random_filename_inside_tenant_namespace(tmp_path, monkeypatch):
    monkeypatch.setattr(file_service_module, "get_settings", lambda: SimpleNamespace(
        UPLOAD_DIR=str(tmp_path), MAX_UPLOAD_SIZE_MB=1, allowed_file_types_list=["pdf"],
        max_upload_size_bytes=1024 * 1024,
    ))
    service = FileService()
    organization_id, branch_id = uuid4(), uuid4()
    upload = UploadFile(file=BytesIO(b"%PDF-test"), filename="report.pdf")

    path, url = await service.upload_file(upload, f"{organization_id}/{branch_id}/general")

    assert Path(path).is_relative_to(tmp_path.resolve())
    assert Path(path).parent == tmp_path.resolve() / str(organization_id) / str(branch_id) / "general"
    assert Path(path).name != "report.pdf"
    assert url.startswith(f"/api/files/{organization_id}/{branch_id}/general/")


@pytest.mark.asyncio
@pytest.mark.parametrize("subfolder", ["../private", "branch/../../private", "C:\\private"])
async def test_upload_rejects_traversal_folder(tmp_path, monkeypatch, subfolder):
    monkeypatch.setattr(file_service_module, "get_settings", lambda: SimpleNamespace(
        UPLOAD_DIR=str(tmp_path), MAX_UPLOAD_SIZE_MB=1, allowed_file_types_list=["pdf"],
        max_upload_size_bytes=1024 * 1024,
    ))
    service = FileService()
    upload = UploadFile(file=BytesIO(b"%PDF-test"), filename="report.pdf")

    with pytest.raises(HTTPException) as error:
        await service.upload_file(upload, subfolder)

    assert error.value.status_code == 400


@pytest.mark.parametrize("filename", ["../report.pdf", "folder\\report.pdf"])
@pytest.mark.asyncio
async def test_upload_sanitizes_path_like_filename(tmp_path, monkeypatch, filename):
    monkeypatch.setattr(file_service_module, "get_settings", lambda: SimpleNamespace(
        UPLOAD_DIR=str(tmp_path), MAX_UPLOAD_SIZE_MB=1, allowed_file_types_list=["pdf"],
        max_upload_size_bytes=1024 * 1024,
    ))
    service = FileService()
    upload = UploadFile(file=BytesIO(b"%PDF-test"), filename=filename)

    path, _ = await service.upload_file(upload, "org/branch/general")

    assert Path(path).is_relative_to(tmp_path.resolve())
    assert Path(path).name != filename


@pytest.mark.asyncio
async def test_upload_rejects_control_characters_in_filename(tmp_path, monkeypatch):
    monkeypatch.setattr(file_service_module, "get_settings", lambda: SimpleNamespace(
        UPLOAD_DIR=str(tmp_path), MAX_UPLOAD_SIZE_MB=1, allowed_file_types_list=["pdf"],
        max_upload_size_bytes=1024 * 1024,
    ))
    service = FileService()
    upload = UploadFile(file=BytesIO(b"%PDF-test"), filename="bad\x00name.pdf")

    with pytest.raises(ValidationException):
        await service.upload_file(upload, "org/branch/general")


def test_scoped_download_rejects_other_organization_and_branch(tmp_path):
    organization_id, branch_id, foreign_branch_id = uuid4(), uuid4(), uuid4()
    tenant = TenantContext(user_id=uuid4(), organization_id=organization_id,
        branch_ids=[branch_id], permissions={"files.upload"})

    with pytest.raises(HTTPException) as foreign_org:
        _resolve_scoped_file(f"{uuid4()}/{branch_id}/general/file.pdf", tenant, tmp_path)
    with pytest.raises(HTTPException) as foreign_branch:
        _resolve_scoped_file(f"{organization_id}/{foreign_branch_id}/general/file.pdf", tenant, tmp_path)
    with pytest.raises(HTTPException) as traversal:
        _resolve_scoped_file(f"{organization_id}/{branch_id}/../../secret.pdf", tenant, tmp_path)

    assert foreign_org.value.status_code == 404
    assert foreign_branch.value.status_code == 404
    assert traversal.value.status_code == 404


def test_scoped_download_allows_owned_branch_and_blocks_all_branch_namespace(tmp_path):
    organization_id, branch_id = uuid4(), uuid4()
    tenant = TenantContext(user_id=uuid4(), organization_id=organization_id,
        branch_ids=[branch_id], permissions={"files.upload"})

    target = _resolve_scoped_file(f"{organization_id}/{branch_id}/general/file.pdf", tenant, tmp_path)
    assert target == tmp_path.resolve() / str(organization_id) / str(branch_id) / "general" / "file.pdf"
    with pytest.raises(HTTPException) as error:
        _resolve_scoped_file(f"{organization_id}/all/general/file.pdf", tenant, tmp_path)
    assert error.value.status_code == 404


def _file_test_client(tenant):
    app = FastAPI()
    app.add_exception_handler(AppException, app_exception_handler)
    app.include_router(files_router)

    async def provide_tenant():
        return tenant

    async def provide_db():
        yield None

    app.dependency_overrides[get_tenant_context] = provide_tenant
    app.dependency_overrides[get_db] = provide_db
    return TestClient(app)


def test_file_api_requires_upload_permission_for_read(tmp_path):
    organization_id, branch_id = uuid4(), uuid4()
    tenant = TenantContext(user_id=uuid4(), organization_id=organization_id,
        branch_ids=[branch_id], permissions={"files.delete"})

    response = _file_test_client(tenant).get(
        f"/api/files/{organization_id}/{branch_id}/general/document.pdf")

    assert response.status_code == 403


def test_file_api_upload_readback_and_cross_tenant_denial_use_only_temp_storage(tmp_path, monkeypatch):
    organization_id, branch_id = uuid4(), uuid4()
    settings = SimpleNamespace(
        UPLOAD_DIR=str(tmp_path), MAX_UPLOAD_SIZE_MB=1, allowed_file_types_list=["pdf"],
        max_upload_size_bytes=1024 * 1024,
    )
    monkeypatch.setattr(file_service_module, "get_settings", lambda: settings)
    monkeypatch.setattr(uploads_module, "get_settings", lambda: settings)
    tenant = TenantContext(user_id=uuid4(), organization_id=organization_id,
        branch_ids=[branch_id], permissions={"files.upload"})
    client = _file_test_client(tenant)

    uploaded = client.post("/api/files/upload", files={"file": ("report.pdf", b"%PDF-test", "application/pdf")})
    assert uploaded.status_code == 200
    file_url = uploaded.json()["data"]["file_url"]
    assert file_url.startswith(f"/api/files/{organization_id}/{branch_id}/general/")

    downloaded = client.get(file_url)
    assert downloaded.status_code == 200
    assert downloaded.content == b"%PDF-test"
    assert downloaded.headers["cache-control"] == "private, no-store"
    assert downloaded.headers["content-disposition"].startswith("attachment;")

    foreign_tenant = TenantContext(user_id=uuid4(), organization_id=uuid4(),
        branch_ids=[branch_id], permissions={"files.upload"})
    denied = _file_test_client(foreign_tenant).get(file_url)
    assert denied.status_code == 404
