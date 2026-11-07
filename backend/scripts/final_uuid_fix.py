"""Final fix - ensure consistent UUID format with hyphens"""

import sqlite3

conn = sqlite3.connect('school_management.db')
cursor = conn.cursor()

# Step 1: Update parent record to use user_id WITH hyphens (to match users table)
cursor.execute("""
    UPDATE parents
    SET user_id = 'e0000000-0000-4000-8000-000000000007'
    WHERE id = '604bec30d67944bdb6f8b74d525b2163'
""")
conn.commit()
print("Step 1: Updated parent record user_id with hyphens")

# Step 2: Update student-parent link to use parent_id WITH hyphens
cursor.execute("""
    UPDATE student_parents
    SET parent_id = '604bec30-d679-44bd-b6f8-b74d525b2163'
    WHERE parent_id = '604bec30d67944bdb6f8b74d525b2163'
""")
conn.commit()
print("Step 2: Updated student-parent link parent_id with hyphens")

# Step 3: Update student_id in student_parents to use hyphens (to match students table)
cursor.execute("""
    UPDATE student_parents
    SET student_id = '4b07e20d-77e8-4bc3-add0-86845190f4ea'
    WHERE student_id = '4b07e20d77e84bc3add086845190f4ea'
""")
conn.commit()
print("Step 3: Updated student-parent link student_id with hyphens")

# Verify everything
cursor.execute("SELECT id, user_id FROM parents WHERE user_id = 'e0000000-0000-4000-8000-000000000007'")
parent = cursor.fetchone()
print(f"\nParent record: {parent}")

cursor.execute("SELECT parent_id, student_id FROM student_parents WHERE parent_id = '604bec30-d679-44bd-b6f8-b74d525b2163'")
links = cursor.fetchall()
print(f"Student-parent links ({len(links)}):")
for link in links:
    print(f"  {link}")

conn.close()
