import sqlite3
from pathlib import Path

db_path = Path(__file__).resolve().parent / "school_management.db"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get a sample debt and check its student
cursor.execute("SELECT id, student_id FROM debts LIMIT 1")
debt = cursor.fetchone()

if debt:
    debt_id, student_id = debt
    print(f"Debt ID: {debt_id}")
    print(f"Student ID: {student_id}")
    
    # Check student
    cursor.execute("SELECT id, first_name, last_name, deleted_at FROM students WHERE id = ?", (student_id,))
    student = cursor.fetchone()
    
    if student:
        print(f"Student: {student[1]} {student[2]} (deleted_at: {student[3]})")
    else:
        print("Student NOT FOUND in students table")
    
    # Check if student has class关联
    if student:
        cursor.execute("SELECT id, name FROM classes WHERE id = (SELECT class_id FROM students WHERE id = ?)", (student_id,))
        class_room = cursor.fetchone()
        if class_room:
            print(f"Class: {class_room[1]}")
        else:
            print("No class found or class_id is NULL")
    
    # Check parent
    cursor.execute("""
        SELECT p.id, p.first_name, p.last_name, p.phone
        FROM parents p
        JOIN student_parents sp ON p.id = sp.parent_id
        WHERE sp.student_id = ?
        ORDER BY sp.is_primary DESC
        LIMIT 1
    """, (student_id,))
    parent = cursor.fetchone()
    
    if parent:
        print(f"Parent: {parent[1]} {parent[2]} (phone: {parent[3]})")
    else:
        print("No parent found")

conn.close()
