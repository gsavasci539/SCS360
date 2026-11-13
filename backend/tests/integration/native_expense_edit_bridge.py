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
from datetime import datetime
from uuid import UUID, uuid4
from test_finance_compatibility import finance_client  # noqa: F401
from test_material_files import materials_client  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401

from app.core.security import create_access_token
from app.infrastructure.models.models import (
    Expense,
    NotificationJob,
    Payment,
)


async def test_native_expense_edit_real_api(finance_client):  # noqa: F811
    client, sessions, data = finance_client
    rows = [Expense(id=uuid4(), organization_id=data["org"].id, branch_id=data["branch"].id,
        description="Synthetic seeded expense", category="Synthetic seed", amount=Decimal("1.00"),
        expense_date=datetime(2027, 1, 15, tzinfo=UTC)) for _ in range(100)]
    async with sessions() as db:
        db.add_all(rows); await db.commit()
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
                "body_fields": sorted(json.loads(content)) if content else []})
            if self.command == "POST" and len([row for row in events if row["method"] == "POST"]) == 1:
                self.close_connection = True
                return  # Commit succeeded; only the client acknowledgement is deliberately lost.
            if self.command == "PUT" and content and sorted(json.loads(content)) == ["amount", "notes"] and len([r for r in events if r["method"] == "PUT" and r["body_fields"] == ["amount", "notes"]]) == 1:
                self.close_connection = True
                return  # The native delta committed; lose only its first ACK.
            self.send_response(response.status_code); self.send_header("Content-Type", response.headers.get("content-type", "application/json"))
            self.send_header("Content-Length", str(len(response.content))); self.send_header("Connection", "close")
            self.end_headers(); self.wfile.write(response.content)
        do_GET = forward
        do_POST = forward
        do_PUT = forward
        do_DELETE = forward

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True); thread.start()
    root = Path(__file__).resolve().parents[3]
    mobile = root / "mobile-android"
    gradle = os.environ["NATIVE_GRADLE_EXECUTABLE"]
    command = (["cmd.exe", "/d", "/c", gradle] if os.name == "nt" else [gradle]) + [
        "--no-daemon", "--no-configuration-cache", "--offline", "--max-workers", "1", "--no-parallel",
        "-PnativeBackendAcceptance=true", ":app:testDebugUnitTest", "--tests", "com.example.NativeExpenseEditBackendAcceptance",
        "-g", os.environ["NATIVE_GRADLE_HOME"], "--project-cache-dir", os.environ["NATIVE_GRADLE_PROJECT_CACHE"]]
    env = os.environ.copy()
    expires = int((datetime.now(UTC) + timedelta(hours=2)).timestamp())
    env.update({"NATIVE_TEST_API_URL": f"http://127.0.0.1:{server.server_port}/api/",
        "NATIVE_TEST_FINANCE_TOKEN": create_access_token(data["accountant"].id, {"exp": expires}),
        "NATIVE_TEST_PARENT_TOKEN": create_access_token(data["user"].id, {"exp": expires}),
        "NATIVE_TEST_OTHER_BRANCH": str(data["other_branch"].id), "NATIVE_TEST_FINANCE_ACTOR": str(data["accountant"].id), "NATIVE_TEST_PARENT_ACTOR": str(data["user"].id),
        "NATIVE_TEST_SEEDED_EXPENSE": str(rows[0].id),
        "NATIVE_TEST_BRANCH": str(data["branch"].id), "NATIVE_TEST_FOREIGN_BRANCH": str(data["other_branch"].id), "NATIVE_TEST_STUDENT": str(data["children"][0].id)})
    log = Path(os.environ["NATIVE_ACCEPTANCE_LOG"])
    try:
        with log.open("wb") as stream:
            process = await asyncio.create_subprocess_exec(*command, cwd=mobile, env=env, stdout=stream, stderr=stream)
            code = await asyncio.wait_for(process.wait(), timeout=1500)
        assert code == 0, log.read_text(encoding="utf-8", errors="replace")[-5000:]
        posts = [row for row in events if row["method"] == "POST"]
        assert len(posts) == 2 and all(row["status"] == 200 for row in posts)
        assert all(row["body_fields"] == ["amount", "branch_id", "category", "date", "request_id", "title"] for row in posts)
        assert [row["status"] for row in events if row["method"] == "PUT"] == [200, 200, 200]
        assert len([row for row in events if row["method"] == "DELETE" and row["status"] == 200]) == 101
        assert any("page=2&" in row["path"] and "/api/expenses?" in row["path"] for row in events)
        assert [row["status"] for row in events][-2:] == [404, 403]
        async with sessions() as db:
            ledger = (await db.execute(select(Expense))).scalars().all()
            assert len(ledger) == 101 and all(row.deleted_at is not None for row in ledger)
            changed = [row for row in ledger if row.description == "Updated from web"]
            assert len(changed) == 1 and changed[0].amount == Decimal("120.03") and changed[0].notes == "Native ref" and changed[0].category == "Web category"
            assert (await db.execute(select(func.count()).select_from(Payment))).scalar_one() == 0
            assert (await db.execute(select(func.count()).select_from(NotificationJob))).scalar_one() == 0
        Path(os.environ["NATIVE_ACCEPTANCE_REPORT"]).write_text(json.dumps({"real_api": True,
            "temporary_database": "sqlite", "requests": events, "seeded_expenses": 100, "created_expenses": 1,
            "lost_committed_ack_recovered_once": True, "ledger_rows_after_create": 101, "visible_after_deletes": 0,
            "updated_amount": "120.03", "native_delta_visible_to_web": True, "native_edit_lost_ack_replay": True, "web_edit_visible_natively": True, "canonical_native_and_web_delete": True,
            "payment_rows": 0, "notification_jobs": 0, "room_ledger_unchanged": True}, indent=2), encoding="utf-8")

    finally:
        await asyncio.to_thread(server.shutdown); server.server_close(); thread.join(timeout=5)
