"""Fix UUID format consistency in student_parents table"""

import sqlite3

conn = sqlite3.connect('school_management.db')
cursor = conn.cursor()

# Get parent record ID (without hyphens)
cursor.execute("SELECT id FROM parents WHERE user_id = 'e0000000-0000-4000-8000-000000000007'")
parent = cursor.fetchone()

if not parent:
    print("Parent record not found")
else:
    parent_id = parent[0]
    print(f"Parent ID: {parent_id}")
    
    # Update student-parent link to use the same format
    # The link currently has hyphens, parent doesn't
    cursor.execute("""
        UPDATE student_parents
        SET parent_id = ?
        WHERE parent_id = '604bec30-d679-44bd-b6f8-b74d525b2163'
    """, (parent_id,))
    
    conn.commit()
    print(f"Updated student-parent link to use parent_id: {parent_id}")
    
    # Verify
    cursor.execute("SELECT parent_id, student_id FROM student_parents WHERE parent_id = ?", (parent_id,))
    links = cursor.fetchall()
    print(f"\nStudent-parent links after update ({len(links)}):")
    for link in links:
        print(f"  {link}")

conn.close()
