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
    Debt,
    DebtType,
    NotificationJob,
    Payment,
)


async def test_native_cash_collection_real_api(finance_client):  # noqa: F811
    client, sessions, data = finance_client
    async with sessions() as db:
        debt = Debt(organization_id=data["org"].id, branch_id=data["branch"].id, student_id=data["children"][0].id,
            debt_type=DebtType.EDUCATION, amount=Decimal("100.01"), paid_amount=0, due_date=school_today())
        foreign = Debt(organization_id=data["stranger"].organization_id, branch_id=data["other_branch"].id,
            student_id=data["stranger"].id, debt_type=DebtType.EDUCATION, amount=1000, paid_amount=0, due_date=school_today())
        db.add_all([debt, foreign]); await db.commit()
    loop = asyncio.get_running_loop()
    events = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def forward(self):
            content = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            headers = {k: v for k, v in self.headers.items() if k.lower() not in ("host", "connection", "content-length")}
            response = asyncio.run_coroutine_threadsafe(client.request(self.command, self.path, headers=headers, content=content), loop).result(timeout=60)
            events.append({"method": self.command, "path": self.path, "status": response.status_code,
                "request_id": json.loads(content)["request_id"] if content else None})
            if self.command == "POST" and len([row for row in events if row["method"] == "POST"]) == 1:
                self.close_connection = True
                return  # The DB committed; only the client ACK is deliberately lost.
            self.send_response(response.status_code); self.send_header("Content-Type", response.headers.get("content-type", "application/json"))
            self.send_header("Content-Length", str(len(response.content))); self.send_header("Connection", "close")
            self.end_headers(); self.wfile.write(response.content)
        do_GET = forward
        do_POST = forward

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True); thread.start()
    root = Path(__file__).resolve().parents[3]
    mobile = root / "mobile-android"
    gradle = os.environ["NATIVE_GRADLE_EXECUTABLE"]
    command = (["cmd.exe", "/d", "/c", gradle] if os.name == "nt" else [gradle]) + [
        "--no-daemon", "--no-configuration-cache", "--offline", "--max-workers", "1", "--no-parallel",
        "-PnativeBackendAcceptance=true", ":app:testDebugUnitTest", "--tests", "com.example.NativeCashCollectionBackendAcceptance",
        "-g", os.environ["NATIVE_GRADLE_HOME"], "--project-cache-dir", os.environ["NATIVE_GRADLE_PROJECT_CACHE"]]
    env = os.environ.copy()
    expires = int((datetime.now(UTC) + timedelta(hours=2)).timestamp())
    env.update({"NATIVE_TEST_API_URL": f"http://127.0.0.1:{server.server_port}/api/",
        "NATIVE_TEST_FINANCE_TOKEN": create_access_token(data["accountant"].id, {"exp": expires}),
        "NATIVE_TEST_PARENT_TOKEN": create_access_token(data["user"].id, {"exp": expires}),
        "NATIVE_TEST_OTHER_BRANCH": str(data["other_branch"].id), "NATIVE_TEST_FINANCE_ACTOR": str(data["accountant"].id), "NATIVE_TEST_PARENT_ACTOR": str(data["user"].id),
        "NATIVE_TEST_DEBT": str(debt.id), "NATIVE_TEST_FOREIGN_DEBT": str(foreign.id)})
    log = Path(os.environ["NATIVE_ACCEPTANCE_LOG"])
    try:
        with log.open("wb") as stream:
            process = await asyncio.create_subprocess_exec(*command, cwd=mobile, env=env, stdout=stream, stderr=stream)
            code = await asyncio.wait_for(process.wait(), timeout=1500)
        assert code == 0, log.read_text(encoding="utf-8", errors="replace")[-5000:]
        posts = [row for row in events if row["method"] == "POST"]
        assert len(posts) == 3 and all(row["status"] == 200 for row in posts), events
        assert posts[0]["request_id"] == posts[1]["request_id"] != posts[2]["request_id"]
        assert [row["status"] for row in events][-2:] == [404, 403]
        from app.infrastructure.models.models import AuditAction, AuditLog, Receipt
        async with sessions() as db:
            saved = await db.get(Debt, debt.id)
            assert saved.paid_amount == Decimal("40.01") and saved.amount - saved.paid_amount == Decimal("60.00")
            assert (await db.execute(select(func.count()).select_from(Payment))).scalar_one() == 2
            assert (await db.execute(select(func.count()).select_from(Receipt))).scalar_one() == 2
            assert (await db.execute(select(func.count()).select_from(NotificationJob))).scalar_one() == 2
            assert (await db.execute(select(func.count()).select_from(AuditLog).where(AuditLog.action == AuditAction.PAYMENT))).scalar_one() == 2
        Path(os.environ["NATIVE_ACCEPTANCE_REPORT"]).write_text(json.dumps({"real_api": True,
            "temporary_database": "sqlite", "requests": events, "payment_rows": 2, "receipt_rows": 2,
            "payment_audits": 2, "notification_jobs": 2, "actual_deliveries": 0,
            "paid_amount": "40.01", "remaining": "60.00", "lost_ack_replayed_once": True, "native_receipts": 2, "server_pdf_verified": True}, indent=2), encoding="utf-8")

    finally:
        await asyncio.to_thread(server.shutdown); server.server_close(); thread.join(timeout=5)
