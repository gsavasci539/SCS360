"""Remove duplicate student-parent link"""

import sqlite3

conn = sqlite3.connect('school_management.db')
cursor = conn.cursor()

# Remove the duplicate link with hyphens
cursor.execute("""
    DELETE FROM student_parents
    WHERE parent_id = '604bec30-d679-44bd-b6f8-b74d525b2163'
    AND student_id = '4b07e20d-77e8-4bc3-add0-86845190f4ea'
""")

conn.commit()
print("Removed duplicate student-parent link")

# Verify
cursor.execute("SELECT parent_id, student_id FROM student_parents WHERE parent_id = '604bec30d67944bdb6f8b74d525b2163'")
links = cursor.fetchall()
print(f"\nStudent-parent links after cleanup ({len(links)}):")
for link in links:
    print(f"  {link}")

conn.close()
