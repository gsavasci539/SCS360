import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.core.security import verify_password, hash_password

# Test with current hash from DB
import sqlite3
conn = sqlite3.connect("school_management.db")
cursor = conn.execute("SELECT password_hash FROM users WHERE email = 'admin@demo.com'")
db_hash = cursor.fetchone()[0]
conn.close()

print(f"DB hash: {db_hash}")
print(f"Hash length: {len(db_hash)}")
print(f"Verify Admin123*: {verify_password('Admin123*', db_hash)}")

# Generate fresh hash
fresh = hash_password("Admin123*")
print(f"Fresh hash: {fresh}")
print(f"Verify fresh: {verify_password('Admin123*', fresh)}")
