"""Normalize legacy 32-character UUID values in the local SQLite database.

Older demo imports wrote some UUIDs without hyphens.  SQLAlchemy's UUID type
correctly binds the standard (hyphenated) form, so mixed storage prevents
foreign-key lookups after login.  This migration is idempotent.
"""

from __future__ import annotations

import re
import sqlite3
import sys
import uuid
from pathlib import Path


UUID32 = re.compile(r"^[0-9a-fA-F]{32}$")


def normalize(value: object) -> object:
    if isinstance(value, str) and UUID32.fullmatch(value):
        return str(uuid.UUID(value))
    return value


def main() -> int:
    database = Path(__file__).resolve().parents[1] / "school_management.db"
    if not database.exists():
        print(f"Database not found: {database}")
        return 1

    connection = sqlite3.connect(database)
    try:
        connection.execute("PRAGMA foreign_keys = OFF")
        # A previous demo seed could create the same class-teacher relation in
        # both UUID spellings.  Keep one relation before normalizing its
        # composite primary key.
        duplicate_rows = connection.execute(
            "SELECT rowid, class_id, user_id FROM class_teachers"
        ).fetchall()
        seen_relations: set[tuple[object, object]] = set()
        for rowid, class_id, user_id in duplicate_rows:
            relation = (normalize(class_id), normalize(user_id))
            if relation in seen_relations:
                connection.execute("DELETE FROM class_teachers WHERE rowid = ?", (rowid,))
            else:
                seen_relations.add(relation)
        updates = 0
        # Normalize user identifiers first: authentication resolves users by
        # their primary key immediately after decoding the access token.
        raw_users = connection.execute("SELECT rowid, id FROM users").fetchall()
        for rowid, user_id in raw_users:
            normalized = normalize(user_id)
            if normalized != user_id:
                connection.execute("UPDATE users SET id = ? WHERE rowid = ?", (normalized, rowid))
                connection.execute("UPDATE class_teachers SET user_id = ? WHERE user_id = ?", (normalized, user_id))
                updates += 1

        # The demo database has one duplicated relation in the old spelling.
        # It was removed above, then the surviving relation can be normalized.
        relations = connection.execute("SELECT rowid, class_id, user_id FROM class_teachers").fetchall()
        for rowid, class_id, user_id in relations:
            normalized_class = normalize(class_id)
            normalized_user = normalize(user_id)
            if normalized_class != class_id or normalized_user != user_id:
                connection.execute(
                    "UPDATE class_teachers SET class_id = ?, user_id = ? WHERE rowid = ?",
                    (normalized_class, normalized_user, rowid),
                )
                updates += 1
        connection.commit()
        print(f"Normalized {updates} legacy UUID values.")
        return 0
    finally:
        connection.close()


if __name__ == "__main__":
    raise SystemExit(main())
