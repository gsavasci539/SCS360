"""Fix user_id format in parent record to match"""

import sqlite3

conn = sqlite3.connect('school_management.db')
cursor = conn.cursor()

# Update parent record to use user_id without hyphens
cursor.execute("""
    UPDATE parents
    SET user_id = 'e0000000000004000800000000000007'
    WHERE user_id = 'e0000000-0000-4000-8000-000000000007'
""")

conn.commit()
print("Updated parent record user_id to remove hyphens")

# Verify
cursor.execute("SELECT id, user_id FROM parents WHERE user_id = 'e0000000000004000800000000000007'")
parent = cursor.fetchone()
print(f"Parent record after update: {parent}")

conn.close()
