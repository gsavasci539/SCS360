"""Opt-in actual native login/parent parity acceptance against disposable SQLite only."""
import asyncio
import json
import os
from decimal import Decimal
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from sqlalchemy import func, select
from test_material_files import materials_client  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401
from app.core.security import hash_password
from app.infrastructure.models.models import Branch, ChatMessage, Debt, DebtType, NotificationJob, OperationalRecord, Parent, Payment, Permission, Role, StudentParent, User
from app.domain.entities.health import MedicationSchedule


async def test_native_parent_parity_real_api(materials_client):  # noqa: F811
    client, sessions, data = materials_client
    async with sessions() as db:
        existing = {p.code: p for p in (await db.execute(select(Permission))).scalars()}
        codes = ["parents.read", "parents.write", "users.write", "student.read", "student.write", "students.read", "students.write"]
        permissions = [existing.get(code) or Permission(code=code, name=code, module=code.split(".")[0]) for code in codes]
        role = Role(name="Native contact manager", slug="native_contact_manager", organization_id=data["org"].id, permissions=permissions)
        branch = await db.get(Branch, data["branch"].id)
        manager = User(email="native-manager@example.com", password_hash=hash_password("Synthetic-pass-2026!"), first_name="Native", last_name="Manager", organization_id=data["org"].id, roles=[role], branches=[])
        parent_role = (await db.execute(select(Role).where(Role.slug == "parent"))).scalar_one()
        new_permissions = [existing.get(code) or Permission(code=code, name=code, module="parent") for code in ["parent.view_finances", "parent.view_daily_report", "parent.medicine_request"]]
        # Load the relation before changing it (avoid async lazy IO).
        from sqlalchemy.orm import selectinload
        parent_role = (await db.execute(select(Role).options(selectinload(Role.permissions)).where(Role.id == parent_role.id))).scalar_one()
        parent_role.permissions.extend(new_permissions)
        parent_user = User(email="native-parent@example.com", password_hash=hash_password("Synthetic-pass-2026!"), first_name="Native", last_name="Parent", organization_id=data["org"].id, roles=[parent_role])
        db.add_all([manager, parent_user])
        db.add_all([Parent(organization_id=data["org"].id, first_name=f"NativeSeed{n:03}", last_name="Contact") for n in range(101)])
        debt = Debt(organization_id=data["org"].id, branch_id=data["branch"].id, student_id=data["children"][0].id, amount=Decimal("100.10"), paid_amount=Decimal("0.00"), description="Native parent debt", debt_type=DebtType.EDUCATION, due_date=date(2027, 1, 15))
        db.add(debt); await db.commit()
    loop = asyncio.get_running_loop(); events = []
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass
        def forward(self):
            content = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            headers = {k: v for k, v in self.headers.items() if k.lower() not in ("host", "connection", "content-length")}
            response = asyncio.run_coroutine_threadsafe(client.request(self.command, self.path, headers=headers, content=content), loop).result(timeout=60)
            events.append({"method": self.command, "path": self.path, "status": response.status_code})
            if response.status_code >= 400:
                print("Native bridge rejected", self.command, self.path, response.status_code, response.text[:500], flush=True)
            self.send_response(response.status_code); self.send_header("Content-Type", response.headers.get("content-type", "application/json")); self.send_header("Content-Length", str(len(response.content))); self.send_header("Connection", "close"); self.end_headers(); self.wfile.write(response.content)
        do_GET = forward
        do_POST = forward
        do_PUT = forward
        do_DELETE = forward
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler); thread = Thread(target=server.serve_forever, daemon=True); thread.start()
    root = Path(__file__).resolve().parents[3]
    env = os.environ.copy(); env.update({"NATIVE_TEST_API_URL": f"http://127.0.0.1:{server.server_port}/api/", "NATIVE_TEST_ORGANIZATION": str(data["org"].id), "NATIVE_TEST_ACCOUNT": str(parent_user.id), "NATIVE_TEST_STUDENT": str(data["children"][0].id), "NATIVE_TEST_DEBT": str(debt.id), "NATIVE_TEST_TEACHER": str(data["teacher"].id)})
    command = ["cmd.exe", "/d", "/c", env["NATIVE_GRADLE_EXECUTABLE"], "--no-daemon", "--no-configuration-cache", "--offline", "--max-workers", "1", "--no-parallel", "-PnativeBackendAcceptance=true", ":app:testDebugUnitTest", "--tests", "com.example.NativeParentParityBackendAcceptance", "-g", env["NATIVE_GRADLE_HOME"], "--project-cache-dir", env["NATIVE_GRADLE_PROJECT_CACHE"]]
    try:
        with Path(env["NATIVE_ACCEPTANCE_LOG"]).open("wb") as stream:
            process = await asyncio.create_subprocess_exec(*command, cwd=root/"mobile-android", env=env, stdout=stream, stderr=stream)
            assert await asyncio.wait_for(process.wait(), timeout=1500) == 0, Path(env["NATIVE_ACCEPTANCE_LOG"]).read_text(errors="replace")[-5000:]
        assert any("skip=100" in row["path"] for row in events)
        assert sum(row["path"] == "/api/auth/login" and row["status"] == 200 for row in events) == 2
        assert any(row["path"].startswith("/api/parents?") and row["status"] == 403 for row in events)
        async with sessions() as db:
            assert (await db.execute(select(func.count()).select_from(Parent).where(Parent.first_name == "NativeCreated"))).scalar_one() == 0
            assert (await db.execute(select(func.count()).select_from(MedicationSchedule).where(MedicationSchedule.medication_name == "Synthetic acceptance request", MedicationSchedule.request_status == "PENDING"))).scalar_one() == 1
            assert (await db.execute(select(func.count()).select_from(OperationalRecord).where(OperationalRecord.kind == "STUDENT_EXCUSE", OperationalRecord.data["description"].as_string() == "Synthetic acceptance excuse"))).scalar_one() == 1
            assert (await db.execute(select(func.count()).select_from(ChatMessage).where(ChatMessage.content == "Native acceptance message"))).scalar_one() == 1
            assert (await db.execute(select(func.count()).select_from(Payment))).scalar_one() == 0
            assert (await db.execute(select(func.count()).select_from(NotificationJob))).scalar_one() == 0
        Path(env["NATIVE_ACCEPTANCE_REPORT"]).write_text(json.dumps({"real_api": True, "temporary_database": "sqlite", "actual_native_login": True, "custom_role_preserved": True, "parent_contacts_paged": 101, "contact_create_update_delete": True, "account_student_link_roundtrip": True, "parent_children_finance_visible": True, "parent_directory_rejected": True, "no_synthetic_daily_report": True, "pending_medicine_excuse_persisted": True, "isolated_stored_message_roundtrip": True, "real_message_delivery": 0, "payment_rows": 0, "notification_jobs": 0, "requests": events}, indent=2), encoding="utf-8")
    finally:
        await asyncio.to_thread(server.shutdown); server.server_close(); thread.join(timeout=5)
