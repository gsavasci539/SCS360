"""Clean up and add single correct student-parent link"""

import sqlite3

conn = sqlite3.connect('school_management.db')
cursor = conn.cursor()

# Delete all links for this parent
cursor.execute("DELETE FROM student_parents WHERE parent_id = '604bec30d67944bdb6f8b74d525b2163'")
conn.commit()
print("Deleted all student-parent links for this parent")

# Add single correct link
cursor.execute("""
    INSERT INTO student_parents (parent_id, student_id, is_primary, is_emergency)
    VALUES ('604bec30d67944bdb6f8b74d525b2163', '4b07e20d77e84bc3add086845190f4ea', 1, 0)
""")
conn.commit()
print("Added single correct student-parent link")

# Verify
cursor.execute("SELECT parent_id, student_id FROM student_parents WHERE parent_id = '604bec30d67944bdb6f8b74d525b2163'")
links = cursor.fetchall()
print(f"\nStudent-parent links after fix ({len(links)}):")
for link in links:
    print(f"  {link}")

conn.close()
