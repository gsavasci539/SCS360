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

from app.core.security import create_access_token
from app.infrastructure.models.models import (
    Debt,
    NotificationJob,
    Payment,
)


async def test_native_debt_create_real_api(finance_client):  # noqa: F811
    client, sessions, data = finance_client
    from app.infrastructure.models.models import Student
    async with sessions() as db:
        db.add_all([Student(organization_id=data["org"].id, branch_id=data["branch"].id,
            first_name=f"Synthetic{i}", last_name="DebtOptions") for i in range(100)])
        await db.commit()
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
        "-PnativeBackendAcceptance=true", ":app:testDebugUnitTest", "--tests", "com.example.NativeDebtCreateBackendAcceptance",
        "-g", os.environ["NATIVE_GRADLE_HOME"], "--project-cache-dir", os.environ["NATIVE_GRADLE_PROJECT_CACHE"]]
    env = os.environ.copy()
    expires = int((datetime.now(UTC) + timedelta(hours=2)).timestamp())
    env.update({"NATIVE_TEST_API_URL": f"http://127.0.0.1:{server.server_port}/api/",
        "NATIVE_TEST_FINANCE_TOKEN": create_access_token(data["accountant"].id, {"exp": expires}),
        "NATIVE_TEST_PARENT_TOKEN": create_access_token(data["user"].id, {"exp": expires}),
        "NATIVE_TEST_OTHER_BRANCH": str(data["other_branch"].id), "NATIVE_TEST_FINANCE_ACTOR": str(data["accountant"].id), "NATIVE_TEST_PARENT_ACTOR": str(data["user"].id),
        "NATIVE_TEST_BRANCH": str(data["branch"].id), "NATIVE_TEST_FOREIGN_BRANCH": str(data["other_branch"].id), "NATIVE_TEST_STUDENT": str(data["children"][0].id)})
    log = Path(os.environ["NATIVE_ACCEPTANCE_LOG"])
    try:
        with log.open("wb") as stream:
            process = await asyncio.create_subprocess_exec(*command, cwd=mobile, env=env, stdout=stream, stderr=stream)
            code = await asyncio.wait_for(process.wait(), timeout=1500)
        assert code == 0, log.read_text(encoding="utf-8", errors="replace")[-5000:]
        posts = [row for row in events if row["method"] == "POST"]
        assert len(posts) == 2 and all(row["status"] == 200 for row in posts), events
        assert posts[0]["request_id"] == posts[1]["request_id"]
        assert [row["status"] for row in events][-2:] == [404, 403]
        async with sessions() as db:
            debts = (await db.execute(select(Debt))).scalars().all()
            assert len(debts) == 1 and debts[0].amount == Decimal("100.01") and debts[0].paid_amount == 0
            assert (await db.execute(select(func.count()).select_from(Payment))).scalar_one() == 0
            assert (await db.execute(select(func.count()).select_from(NotificationJob))).scalar_one() == 0
        Path(os.environ["NATIVE_ACCEPTANCE_REPORT"]).write_text(json.dumps({"real_api": True,
            "temporary_database": "sqlite", "requests": events, "debt_rows": 1, "amount": "100.01",
            "payment_rows": 0, "notification_jobs": 0, "options_count": 102,
            "lost_ack_replayed_once": True, "room_ledger_unchanged": True}, indent=2), encoding="utf-8")

    finally:
        await asyncio.to_thread(server.shutdown); server.server_close(); thread.join(timeout=5)
