"""Check UUID format consistency"""

import sqlite3

conn = sqlite3.connect('school_management.db')
cursor = conn.cursor()

# Check parent record
cursor.execute("SELECT id, user_id FROM parents WHERE id = '604bec30d67944bdb6f8b74d525b2163'")
parent = cursor.fetchone()
print(f"Parent record: {parent}")

# Check student-parent links for this parent
cursor.execute("SELECT parent_id, student_id FROM student_parents WHERE parent_id = '604bec30d67944bdb6f8b74d525b2163'")
links = cursor.fetchall()
print(f"\nStudent-parent links for this parent ({len(links)}):")
for link in links:
    print(f"  {link}")

# Also check with hyphens
cursor.execute("SELECT parent_id, student_id FROM student_parents WHERE parent_id = '604bec30-d679-44bd-b6f8-b74d525b2163'")
links_hyphen = cursor.fetchall()
print(f"\nStudent-parent links with hyphens ({len(links_hyphen)}):")
for link in links_hyphen:
    print(f"  {link}")

conn.close()
