"""Check database state directly"""

import sqlite3

conn = sqlite3.connect('school_management.db')
cursor = conn.cursor()

# Check parent user
cursor.execute("SELECT id, email, first_name, last_name FROM users WHERE email = 'veli@demo.com'")
parent_user = cursor.fetchone()
print(f"Parent user: {parent_user}")

# Check parent records
cursor.execute("SELECT id, user_id, first_name, last_name FROM parents")
parents = cursor.fetchall()
print(f"\nParent records ({len(parents)}):")
for p in parents:
    print(f"  {p}")

# Check student-parent links
cursor.execute("SELECT parent_id, student_id FROM student_parents")
student_parents = cursor.fetchall()
print(f"\nStudent-parent links ({len(student_parents)}):")
for sp in student_parents:
    print(f"  {sp}")

# Check students
cursor.execute("SELECT id, first_name, last_name FROM students LIMIT 5")
students = cursor.fetchall()
print(f"\nStudents ({len(students)}):")
for s in students:
    print(f"  {s}")

conn.close()
