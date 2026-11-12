"""Explicit native registry acceptance; never touches the working database."""
import asyncio
import json
import os
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from test_material_files import materials_client  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401
from test_saas_platform import platform_client  # noqa: F401

from app.core.config import get_settings
from app.core.security import create_access_token
from app.infrastructure.models.models import Branch, ClassRoom, Permission, Role, Student, User


async def test_native_registry_against_temporary_backend(platform_client, tmp_path, monkeypatch):  # noqa: F811
    client, sessions, data = platform_client
    monkeypatch.setattr(get_settings(), "JWT_SECRET_KEY", "native-registry-acceptance-only-not-production-20261112")
    async with sessions() as db:
        db.add_all([Student(organization_id=data["org"].id, branch_id=data["branch"].id,
            class_id=data["classroom"].id, first_name=f"Native{i:03}", last_name="Synthetic") for i in range(100)])
        second_branch = Branch(organization_id=data["org"].id, name="Native Same Organization Branch")
        db.add(second_branch)
        codes = ("students.read", "students.write", "branches.read", "classes.read")
        permissions = {row.code: row for row in (await db.execute(select(Permission).where(Permission.code.in_(codes)))).scalars()}
        for code in codes:
            if code not in permissions:
                permissions[code] = Permission(code=code, name=code, module=code.split(".")[0]); db.add(permissions[code])
        clerk_role = Role(name="Registry Clerk", slug="registry-clerk", organization_id=data["org"].id,
            permissions=[permissions[code] for code in ("students.read", "students.write")])
        clerk = User(email="native-registry-clerk@example.com", password_hash="token-only-synthetic-fixture",
            first_name="Registry", last_name="Clerk", organization_id=data["org"].id, roles=[clerk_role], branches=[data["branch"]])
        db.add(clerk)
        teacher_role = (await db.execute(select(Role).where(Role.slug == "teacher").options(selectinload(Role.permissions)))).scalar_one()
        for code in ("branches.read", "classes.read"):
            if code not in {p.code for p in teacher_role.permissions}: teacher_role.permissions.append(permissions[code])
        await db.commit()
        before = (await db.execute(select(func.count(Student.id)))).scalar_one()
    loop = asyncio.get_running_loop()
    writes, reads = [], []
    events = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def forward(self):
            body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            headers = {k: v for k, v in self.headers.items() if k.lower() not in ("host", "connection", "content-length")}
            future = asyncio.run_coroutine_threadsafe(client.request(self.command, self.path, headers=headers, content=body), loop)
            try:
                response = future.result(timeout=60)
            except Exception as failure:
                events.append({"method": self.command, "path": self.path,
                    "error": type(failure).__name__, "detail": str(failure)[:500]})
                self.send_error(500, "Temporary backend request failed")
                return
            events.append({"method": self.command, "path": self.path, "status": response.status_code})
            if self.command in ("POST", "PUT", "DELETE"):
                writes.append((self.command, self.path, body, response.status_code))
            else:
                reads.append(self.path)
            content = response.content
            self.send_response(response.status_code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(content)))
            # HTTP/1.0 handler closes each socket; make that explicit to clients
            # that disable transparent retries for idempotency verification.
            self.send_header("Connection", "close")
            self.close_connection = True
            self.end_headers()
            self.wfile.write(content)

        do_GET = forward
        do_PUT = forward
        do_POST = forward
        do_DELETE = forward

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    repo = Path(__file__).resolve().parents[3]
    mobile = Path(os.environ.get("SCS360_MOBILE_ROOT", repo)) / "mobile-android"
    gradle = os.environ.get("NATIVE_GRADLE_EXECUTABLE", str(mobile / ("gradlew.bat" if os.name == "nt" else "gradlew")))
    command = (["cmd.exe", "/d", "/c", gradle] if os.name == "nt" else [gradle]) + [
        "--no-daemon", "--no-configuration-cache", "--offline", "--max-workers", "1", "--no-parallel",
        "-PnativeBackendAcceptance=true", ":app:testDebugUnitTest", "--tests", "com.example.NativeRegistryBackendAcceptance",
    ]
    if os.environ.get("NATIVE_GRADLE_HOME"):
        command += ["-g", os.environ["NATIVE_GRADLE_HOME"]]
    if os.environ.get("NATIVE_GRADLE_PROJECT_CACHE"):
        command += ["--project-cache-dir", os.environ["NATIVE_GRADLE_PROJECT_CACHE"]]
    env = os.environ.copy()
    expires = int((datetime.now(UTC) + timedelta(hours=2)).timestamp())
    env.update({
        "NATIVE_TEST_API_URL": f"http://127.0.0.1:{server.server_port}/api/",
        "NATIVE_TEST_ROOT_TOKEN": create_access_token(data["root"].id, {"exp": expires}),
        "NATIVE_TEST_CLERK_TOKEN": create_access_token(clerk.id, {"exp": expires}),
        "NATIVE_TEST_TEACHER_TOKEN": create_access_token(data["teacher"].id, {"exp": expires}),
        "NATIVE_TEST_TEACHER_ID": str(data["teacher"].id),
        "NATIVE_TEST_ORG": str(data["org"].id), "NATIVE_TEST_OTHER_ORG": str(data["stranger"].organization_id),
        "NATIVE_TEST_BRANCH": str(data["branch"].id), "NATIVE_TEST_SAME_ORG_BRANCH": str(second_branch.id),
        "NATIVE_TEST_EXISTING": str(data["children"][0].id), "NATIVE_TEST_FOREIGN_STUDENT": str(data["stranger"].id),
    })
    log = Path(os.environ.get("NATIVE_ACCEPTANCE_LOG", str(tmp_path / "native-registry-gradle.log")))
    try:
        with log.open("wb") as stream:
            process = await asyncio.create_subprocess_exec(*command, cwd=mobile, env=env,
                stdout=stream, stderr=asyncio.subprocess.STDOUT)
            await process.wait()
        assert process.returncode == 0, f"Kotlin acceptance failed; inspect {log}"
        assert any("page=2" in path and path.startswith("/api/students?") for path in reads)
        assert {403, 404, 409, 422} <= {status for _, _, _, status in writes} | {e["status"] for e in events if "status" in e}
        for method, path, body, status in writes:
            if method == "POST" and path == "/api/students":
                payload = json.loads(body)
                assert "id" not in payload and "parent_name" not in payload and "blood_type" not in payload and "today_attendance_status" not in payload
                assert payload["organization_id"] == str(data["org"].id)
                assert payload.get("birth_date") is None and payload.get("gender") is None
        edits = [json.loads(body) for method, path, body, status in writes if method == "PUT" and path.startswith("/api/students/") and status == 200]
        assert any(patch == {"last_name": "Edited", "class_id": None} for patch in edits)
        async with sessions() as db:
            assert (await db.execute(select(func.count(Student.id)))).scalar_one() == before + 2
            student = (await db.execute(select(Student).where(Student.first_name == "NativeRegistry"))).scalar_one()
            assert student.deleted_at is not None and student.last_name == "Edited" and student.class_id is None
            assert student.health_notes == "Private synthetic note" and student.birth_date is None and student.gender is None
            classroom = (await db.execute(select(ClassRoom).where(ClassRoom.name == "Native Registry Class"))).scalar_one()
            assert classroom.deleted_at is not None and classroom.code is None and classroom.teacher_id is None and classroom.description is None
            assert classroom.organization_id == data["org"].id
        report = {"real_backend": True, "temporary_db": True, "native_tests": 1, "initial_paged_students": 102,
            "nullable_unknown_fields": True, "canonical_class_crud": True, "canonical_student_crud": True,
            "privacy_preserved_by_changed_fields_only": True, "server_rejections": [403, 404, 409, 422],
            "original_room_rows_unchanged": True, "application_source_acceptance": "registry operations only; not full native parity"}
        if os.environ.get("NATIVE_ACCEPTANCE_REPORT"):
            Path(os.environ["NATIVE_ACCEPTANCE_REPORT"]).write_text(json.dumps(report, indent=2), encoding="utf-8")
    finally:
        log.with_suffix(".http.json").write_text(json.dumps(events, indent=2), encoding="utf-8")
        await asyncio.to_thread(server.shutdown); server.server_close(); thread.join(timeout=5)
