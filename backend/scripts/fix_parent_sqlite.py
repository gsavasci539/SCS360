"""Fix parent user link directly in SQLite"""

import sqlite3

conn = sqlite3.connect('school_management.db')
cursor = conn.cursor()

# Get parent user ID
cursor.execute("SELECT id FROM users WHERE email = 'veli@demo.com'")
parent_user = cursor.fetchone()

if not parent_user:
    print("Parent user not found")
else:
    parent_user_id = parent_user[0]
    print(f"Parent user ID: {parent_user_id}")
    
    # Update parent record that's linked to student
    # Use the parent ID that's already linked to the student
    parent_id = '604bec30d67944bdb6f8b74d525b2163'
    
    cursor.execute("""
        UPDATE parents 
        SET user_id = ?, first_name = 'Ali', last_name = 'Yılmaz', email = 'veli@demo.com'
        WHERE id = ?
    """, (parent_user_id, parent_id))
    
    conn.commit()
    print(f"Updated parent record {parent_id} with user_id {parent_user_id}")
    
    # Verify the update
    cursor.execute("SELECT id, user_id, first_name, last_name FROM parents WHERE id = ?", (parent_id,))
    updated = cursor.fetchone()
    print(f"Updated parent record: {updated}")

conn.close()
