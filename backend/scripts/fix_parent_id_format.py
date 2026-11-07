"""Fix parent_id format in parents table to match student_parents"""

import sqlite3

conn = sqlite3.connect('school_management.db')
cursor = conn.cursor()

# Update parent record ID to use hyphens (to match student_parents)
cursor.execute("""
    UPDATE parents
    SET id = '604bec30-d679-44bd-b6f8-b74d525b2163'
    WHERE id = '604bec30d67944bdb6f8b74d525b2163'
""")

conn.commit()
print("Updated parent record ID to use hyphens")

# Verify
cursor.execute("SELECT id, user_id FROM parents WHERE user_id = 'e0000000-0000-4000-8000-000000000007'")
parent = cursor.fetchone()
print(f"Parent record after update: {parent}")

cursor.execute("SELECT parent_id, student_id FROM student_parents WHERE parent_id = '604bec30-d679-44bd-b6f8-b74d525b2163'")
links = cursor.fetchall()
print(f"Student-parent links ({len(links)}):")
for link in links:
    print(f"  {link}")

conn.close()
