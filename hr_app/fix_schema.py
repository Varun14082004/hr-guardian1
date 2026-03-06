import sqlite3

def fix():
    conn = sqlite3.connect('hr_system.db')
    cursor = conn.cursor()
    
    # Check if Overtime_Hours exists
    cursor.execute("PRAGMA table_info(attendance)")
    columns = [row[1] for row in cursor.fetchall()]
    
    if 'Overtime_Hours' not in columns:
        print("Adding Overtime_Hours column...")
        cursor.execute("ALTER TABLE attendance ADD COLUMN Overtime_Hours REAL DEFAULT 0")
    else:
        print("Overtime_Hours column already exists.")
        
    if 'Last_Seen' not in columns:
        print("Adding Last_Seen column...")
        cursor.execute("ALTER TABLE attendance ADD COLUMN Last_Seen TEXT")
    else:
        print("Last_Seen column already exists.")

    conn.commit()
    conn.close()
    print("Schema fix complete.")

if __name__ == "__main__":
    fix()
