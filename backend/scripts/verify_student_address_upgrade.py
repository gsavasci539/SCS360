"""Review 033->034 on a clone; --apply requires a stopped local API and backup.

Reports contain hashes/counts, never account data or row contents.
"""
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
from urllib.parse import urlparse

BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent
SOURCE = BACKEND / "school_management.db"
REPORTS = ROOT / ".codex-build/local"


def quoted(name):
    return '"' + name.replace('"', '""') + '"'


def snapshot(path, previous=None):
    with sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True) as db:
        tables = [row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        result = {"revision": db.execute("SELECT version_num FROM alembic_version").fetchone()[0], "tables": {}}
        for table in tables:
            columns = [row[1] for row in db.execute("PRAGMA table_info(" + quoted(table) + ")")]
            old_columns = previous["tables"][table]["columns"] if previous else columns
            if not set(old_columns).issubset(columns):
                raise RuntimeError("An existing column disappeared: " + table)
            selection = ','.join(quoted(column) for column in old_columns)
            rows = db.execute("SELECT " + selection + " FROM " + quoted(table) + " ORDER BY " + selection).fetchall()
            digest = hashlib.sha256(json.dumps(rows, ensure_ascii=False, default=str).encode()).hexdigest()
            result["tables"][table] = {"columns": columns, "count": len(rows), "old_columns_sha256": digest}
        return result


def copy_database(destination):
    with sqlite3.connect(f"file:{SOURCE.as_posix()}?mode=ro", uri=True) as source, sqlite3.connect(destination) as target:
        source.backup(target)


def upgrade(path, before):
    if before["revision"] != "033" or "address" in before["tables"]["students"]["columns"]:
        raise RuntimeError("Only a reviewed 033 database without student address can be upgraded")
    env = {**os.environ, "DATABASE_URL": "sqlite+aiosqlite:///" + path.as_posix(), "NOTIFICATION_DELIVERY_ENABLED": "false", "SEED_DEMO_DATA": "false"}
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "034"], cwd=BACKEND, env=env, check=True)
    after = snapshot(path, before)
    assert after["revision"] == "034" and set(before["tables"]) == set(after["tables"])
    for name, original in before["tables"].items():
        changed = after["tables"][name]
        assert changed["count"] == original["count"], name
        if name != "alembic_version":
            assert changed["old_columns_sha256"] == original["old_columns_sha256"], name
        assert changed["columns"] == original["columns"] + (["address"] if name == "students" else []), name
    with sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True) as db:
        assert db.execute("SELECT count(*) FROM students WHERE address IS NOT NULL").fetchone()[0] == 0
    return after


def main():
    REPORTS.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    if "--apply" in sys.argv:
        state = json.loads((REPORTS / "processes.json").read_text(encoding="utf-8-sig"))
        address = urlparse(state["backend"])
        if address.hostname not in {"127.0.0.1", "localhost"}:
            raise RuntimeError("Only the local API may be checked")
        with socket.socket() as probe:
            probe.settimeout(1)
            if probe.connect_ex((address.hostname, address.port)) == 0:
                raise RuntimeError("Stop the local API before applying this migration")
        before = snapshot(SOURCE)
        backup = BACKEND / ("school_management.before-student-address-" + stamp + ".db")
        copy_database(backup)
        assert snapshot(backup) == before
        after = upgrade(SOURCE, before)
        report = {"backup": str(backup), "before": before, "after": after}
        destination = REPORTS / "migration034-verification.json"
    else:
        clone = ROOT / "output" / ("migration034-clone-" + stamp + ".db")
        copy_database(clone)
        before = snapshot(clone)
        after = upgrade(clone, before)
        report = {"clone": str(clone), "before": before, "after": after}
        destination = REPORTS / "migration034-clone-verification.json"
    destination.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"revision": after["revision"], "tables_verified": len(before["tables"]), "existing_rows_unchanged": True, "report": str(destination)}))


if __name__ == "__main__":
    main()
