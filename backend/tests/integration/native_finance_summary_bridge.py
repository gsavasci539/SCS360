"""Opt-in real Kotlin/FastAPI ledger acceptance; no Main DB or provider calls."""
import asyncio
import json
import os
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from sqlalchemy import func, select
from test_finance_compatibility import finance_client  # noqa: F401
from test_material_files import materials_client  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401

from app.core.dates import school_today
from app.core.security import create_access_token
from app.infrastructure.models.models import (
    Branch,
    Debt,
    DebtType,
    NotificationJob,
    Payment,
    PaymentMethod,
    Student,
)


async def test_native_finance_summary_real_api(finance_client):  # noqa: F811
    client, sessions, data = finance_client
    async with sessions() as db:
        second = Branch(organization_id=data["org"].id, name="Synthetic finance second branch")
        db.add(second); await db.flush()
        student = Student(organization_id=data["org"].id, branch_id=second.id, first_name="Synthetic", last_name="Finance")
        db.add(student); await db.flush()
        debts = [Debt(organization_id=data["org"].id, branch_id=data["branch"].id,
            student_id=data["children"][0].id, debt_type=DebtType.EDUCATION,
            amount=Decimal("100.01") if i == 0 else Decimal("100"), paid_amount=Decimal("100") if i == 0 else 0,
            due_date=school_today()) for i in range(101)]
        db.add_all(debts); await db.flush()
        db.add(Debt(organization_id=data["org"].id, branch_id=second.id, student_id=student.id,
            debt_type=DebtType.EDUCATION, amount=Decimal("300.03"), paid_amount=0, due_date=school_today()))
        for status, cancelled in (("completed", False), ("pending", False), ("completed", True)):
            db.add(Payment(organization_id=data["org"].id, branch_id=data["branch"].id,
                student_id=data["children"][0].id, debt_id=debts[0].id, amount=100,
                payment_method=PaymentMethod.CASH, payment_date=datetime.now(UTC), status=status,
                cancelled_at=datetime.now(UTC) if cancelled else None, received_by=data["accountant"].id))
        await db.commit()
        before = [(await db.execute(select(func.count()).select_from(model))).scalar_one() for model in (Debt, Payment, NotificationJob)]
    loop = asyncio.get_running_loop()
    events = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_GET(self):
            headers = {k: v for k, v in self.headers.items() if k.lower() not in ("host", "connection", "content-length")}
            future = asyncio.run_coroutine_threadsafe(client.get(self.path, headers=headers), loop)
            response = future.result(timeout=60)
            events.append({"path": self.path, "status": response.status_code})
            self.send_response(response.status_code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(response.content)))
            self.send_header("Connection", "close"); self.end_headers()
            self.wfile.write(response.content)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True); thread.start()
    root = Path(__file__).resolve().parents[3]
    mobile = root / "mobile-android"
    gradle = os.environ["NATIVE_GRADLE_EXECUTABLE"]
    command = (["cmd.exe", "/d", "/c", gradle] if os.name == "nt" else [gradle]) + [
        "--no-daemon", "--no-configuration-cache", "--offline", "--max-workers", "1", "--no-parallel",
        "-PnativeBackendAcceptance=true", ":app:testDebugUnitTest", "--tests", "com.example.NativeFinanceSummaryBackendAcceptance",
        "-g", os.environ["NATIVE_GRADLE_HOME"], "--project-cache-dir", os.environ["NATIVE_GRADLE_PROJECT_CACHE"]]
    env = os.environ.copy()
    expires = int((datetime.now(UTC) + timedelta(hours=2)).timestamp())
    env.update({"NATIVE_TEST_API_URL": f"http://127.0.0.1:{server.server_port}/api/",
        "NATIVE_TEST_FINANCE_TOKEN": create_access_token(data["accountant"].id, {"exp": expires}),
        "NATIVE_TEST_PARENT_TOKEN": create_access_token(data["user"].id, {"exp": expires}),
        "NATIVE_TEST_BRANCH": str(data["branch"].id), "NATIVE_TEST_FOREIGN_BRANCH": str(data["other_branch"].id)})
    log = Path(os.environ["NATIVE_ACCEPTANCE_LOG"])
    try:
        with log.open("wb") as stream:
            process = await asyncio.create_subprocess_exec(*command, cwd=mobile, env=env, stdout=stream, stderr=stream)
            code = await asyncio.wait_for(process.wait(), timeout=1500)
        assert code == 0, log.read_text(encoding="utf-8", errors="replace")[-5000:]
        assert len(events) == 4 and [e["status"] for e in events] == [200, 200, 404, 403], events
        async with sessions() as db:
            after = [(await db.execute(select(func.count()).select_from(model))).scalar_one() for model in (Debt, Payment, NotificationJob)]
        assert before == after and after == [102, 3, 0]
        Path(os.environ["NATIVE_ACCEPTANCE_REPORT"]).write_text(json.dumps({"real_api": True,
            "temporary_database": "sqlite", "requests": events, "debt_rows": 102, "payment_rows": 3,
            "notification_jobs": 0, "new_writes": 0}, indent=2), encoding="utf-8")
    finally:
        await asyncio.to_thread(server.shutdown); server.server_close(); thread.join(timeout=5)
