"""Add canteen role and permissions to the database using direct SQL."""

import sqlite3
import uuid
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "scs360.db"


def add_canteen_role():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Add canteen permissions
    canteen_permissions = [
        {
            "id": "f0000000-0000-4000-8000-000000000019",
            "code": "canteen.read",
            "name": "Kantin Görüntüle",
            "module": "canteen",
        },
        {
            "id": "f0000000-0000-4000-8000-00000000001a",
            "code": "canteen.write",
            "name": "Kantin Yönet",
            "module": "canteen",
        },
    ]

    for perm_data in canteen_permissions:
        cursor.execute(
            "SELECT id FROM permissions WHERE code = ?", (perm_data["code"],)
        )
        if not cursor.fetchone():
            cursor.execute(
                "INSERT INTO permissions (id, code, name, module) VALUES (?, ?, ?, ?)",
                (perm_data["id"], perm_data["code"], perm_data["name"], perm_data["module"]),
            )
            print(f"Added permission: {perm_data['code']}")

    # Add canteen role
    canteen_role_id = "a0000000-0000-4000-8000-000000000007"
    cursor.execute("SELECT id FROM roles WHERE slug = ?", ("canteen_staff",))
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO roles (id, name, slug, description, is_system, organization_id) VALUES (?, ?, ?, ?, ?, ?)",
            (canteen_role_id, "Kantin Personeli", "canteen_staff", "Kantin yöneticisi", 1, None),
        )
        print("Added role: Kantin Personeli")

    conn.commit()

    # Assign permissions to canteen role
    for perm_data in canteen_permissions:
        cursor.execute(
            "SELECT id FROM role_permissions WHERE role_id = ? AND permission_id = ?",
            (canteen_role_id, perm_data["id"]),
        )
        if not cursor.fetchone():
            cursor.execute(
                "INSERT INTO role_permissions (role_id, permission_id) VALUES (?, ?)",
                (canteen_role_id, perm_data["id"]),
            )
            print(f"Assigned permission {perm_data['code']} to canteen role")

    conn.commit()
    conn.close()
    print("Canteen role and permissions added successfully!")


if __name__ == "__main__":
    add_canteen_role()
