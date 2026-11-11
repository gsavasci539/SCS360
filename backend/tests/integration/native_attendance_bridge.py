"""Explicit cross-client acceptance: pytest native_attendance_bridge.py.

Not included by normal test_*.py discovery. Run the actual Kotlin client through
localhost HTTP into the real FastAPI application and the fixture's temporary DB.
No lifespan workers, live delivery, provider calls or working database are used.
"""
import asyncio
import json
import os
import socket
from datetime import UTC, date, datetime, timedelta
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
from app.infrastructure.models.models import (
    AttendanceRecord,
    AuditLog,
    NotificationJob,
    Permission,
    Role,
    Student,
)


async def test_native_android_attendance_against_temporary_real_backend(platform_client, tmp_path, monkeypatch):  # noqa: F811
    client, sessions, data = platform_client
    settings = get_settings()
    monkeypatch.setattr(settings, "JWT_SECRET_KEY", "native-acceptance-only-not-a-production-key-20261111")
    day = date(2026, 11, 10)
    async with sessions() as db:
        extra = [Student(organization_id=data["org"].id, branch_id=data["branch"].id,
            class_id=data["classroom"].id, first_name=f"Native{i:03}", last_name="Synthetic") for i in range(100)]
        db.add_all(extra)
        await db.flush()
        children = [*data["children"], *extra]
        for i, student in enumerate(children[:101]):
            db.add(AttendanceRecord(organization_id=data["org"].id, branch_id=data["branch"].id,
                class_id=data["classroom"].id, student_id=student.id, attendance_date=day,
                status="HALF_DAY" if i == 1 else "ABSENT", notes="Original note",
                recorded_by=data["teacher"].id))
        db.add(AttendanceRecord(organization_id=data["org"].id, branch_id=data["branch"].id,
            class_id=data["classroom"].id, student_id=children[0].id, attendance_date=day - timedelta(days=1),
            status="PRESENT", notes="Different day", recorded_by=data["teacher"].id))
        role = (await db.execute(select(Role).where(Role.slug == "teacher").options(selectinload(Role.permissions)))).scalar_one()
        role.permissions.extend([Permission(code=code, name=code, module=code.split(".")[0]) for code in ("class.read", "attendance.read")])
        await db.commit()
        first, new = children[0].id, children[-1].id
        initial_jobs = (await db.execute(select(func.count(NotificationJob.id)))).scalar_one()

    loop = asyncio.get_running_loop()
    writes, reads = [], []
    events = []
    dropped = False

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def forward(self):
            nonlocal dropped
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
            if self.command == "PUT":
                writes.append((body, response.status_code))
                if not dropped and response.status_code == 200:
                    dropped = True
                    # The database committed; deliberately lose the reply.
                    self.connection.shutdown(socket.SHUT_RDWR)
                    self.connection.close()
                    return
            elif self.path.startswith("/api/attendance?"):
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

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    repo = Path(__file__).resolve().parents[3]
    mobile = Path(os.environ.get("SCS360_MOBILE_ROOT", repo)) / "mobile-android"
    gradle = os.environ.get("NATIVE_GRADLE_EXECUTABLE", str(mobile / ("gradlew.bat" if os.name == "nt" else "gradlew")))
    command = (["cmd.exe", "/d", "/c", gradle] if os.name == "nt" else [gradle]) + [
        "--no-daemon", "--no-configuration-cache", "--offline", "--max-workers", "1", "--no-parallel",
        "-PnativeBackendAcceptance=true", ":app:testDebugUnitTest", "--tests", "com.example.NativeAttendanceBackendAcceptance",
    ]
    if os.environ.get("NATIVE_GRADLE_HOME"):
        command += ["-g", os.environ["NATIVE_GRADLE_HOME"]]
    if os.environ.get("NATIVE_GRADLE_PROJECT_CACHE"):
        command += ["--project-cache-dir", os.environ["NATIVE_GRADLE_PROJECT_CACHE"]]
    env = os.environ.copy()
    expires = int((datetime.now(UTC) + timedelta(hours=2)).timestamp())
    env.update({
        "NATIVE_TEST_API_URL": f"http://127.0.0.1:{server.server_port}/api/",
        "NATIVE_TEST_ROOT_ID": str(data["root"].id),
        "NATIVE_TEST_ROOT_TOKEN": create_access_token(data["root"].id, {"exp": expires}),
        "NATIVE_TEST_TEACHER_ID": str(data["teacher"].id),
        "NATIVE_TEST_TEACHER_TOKEN": create_access_token(data["teacher"].id, {"exp": expires}),
        "NATIVE_TEST_ORG": str(data["org"].id), "NATIVE_TEST_OTHER_ORG": str(data["stranger"].organization_id),
        "NATIVE_TEST_CLASS": str(data["classroom"].id), "NATIVE_TEST_DAY": day.isoformat(),
        "NATIVE_TEST_FIRST": str(first), "NATIVE_TEST_NEW": str(new),
    })
    log = Path(os.environ.get("NATIVE_ACCEPTANCE_LOG", str(tmp_path / "native-gradle.log")))
    try:
        with log.open("wb") as stream:
            process = await asyncio.create_subprocess_exec(*command, cwd=mobile, env=env,
                stdout=stream, stderr=asyncio.subprocess.STDOUT)
            await process.wait()
        assert process.returncode == 0, f"Kotlin acceptance failed; inspect {log}"
        assert dropped and len(writes) == 4
        assert writes[0][1] == writes[1][1] == 200 and writes[0][0] == writes[1][0]
        assert writes[2][1] == 409 and writes[3][1] == 403
        assert any("page=2" in path for path in reads)
        assert all("attendance_date=" + day.isoformat() in path and "&date=" not in path for path in reads)
        async with sessions() as db:
            records = (await db.execute(select(AttendanceRecord).where(AttendanceRecord.attendance_date == day))).scalars().all()
            assert len(records) == 102
            edited = next(r for r in records if r.student_id == first)
            assert edited.status.value == "LATE" and edited.notes == "Native düzenleme Ω"
            assert edited.recorded_by == data["teacher"].id
            created = next(r for r in records if r.student_id == new)
            assert created.status.value == "EXCUSED" and created.notes == "Native yeni not" and created.recorded_by == data["root"].id
            assert (await db.execute(select(func.count(AuditLog.id)).where(AuditLog.entity_type == "attendance_batch"))).scalar_one() == 1
            assert (await db.execute(select(func.count(NotificationJob.id)))).scalar_one() == initial_jobs
        report = {"real_backend": True, "temporary_db": True, "native_tests": 1,
            "paged_rows_before": 101, "rows_after": 102, "identical_retry_bytes": True,
            "stale_version_status": 409, "read_only_write_status": 403, "foreign_class_status": 404,
            "durable_audit_receipts": 1, "notification_jobs_created": 0}
        if os.environ.get("NATIVE_ACCEPTANCE_REPORT"):
            Path(os.environ["NATIVE_ACCEPTANCE_REPORT"]).write_text(json.dumps(report, indent=2), encoding="utf-8")
    finally:
        log.with_suffix(".http.json").write_text(json.dumps(events, indent=2), encoding="utf-8")
        await asyncio.to_thread(server.shutdown)
        server.server_close()
        thread.join(timeout=5)
