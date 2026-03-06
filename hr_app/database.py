import sqlite3
import bcrypt

DATABASE_NAME = "hr_system.db"

def get_db_connection():
    conn = sqlite3.connect(DATABASE_NAME, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def create_tables():
    conn = get_db_connection()
    cursor = conn.cursor()

    # --- TABLE CREATION ---
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        password TEXT,
        role TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS employees (
        Employee_ID INTEGER PRIMARY KEY,
        Name TEXT,
        Salary REAL,
        Joining_Date TEXT,
        Email TEXT,
        Password TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS evaluation (
        Evaluation_ID INTEGER PRIMARY KEY AUTOINCREMENT,
        Employee_ID INTEGER,
        Productivity REAL,
        Task_Completion REAL,
        Training_Score REAL,
        Manager_Rating REAL,
        Qualitative_Feedback TEXT,
        FOREIGN KEY(Employee_ID) REFERENCES employees(Employee_ID)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS logs (
        username TEXT,
        action TEXT,
        timestamp TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS red_flags (
        Flag_ID INTEGER PRIMARY KEY AUTOINCREMENT,
        Evaluator_Username TEXT,
        Employee_ID INTEGER,
        Reason TEXT,
        Evaluation_Text TEXT,
        Timestamp TEXT,
        FOREIGN KEY(Employee_ID) REFERENCES employees(Employee_ID)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS attendance (
        Attendance_ID INTEGER PRIMARY KEY AUTOINCREMENT,
        Employee_ID INTEGER,
        Date TEXT,
        Login_Time TEXT,
        Logout_Time TEXT,
        Last_Seen TEXT,
        Overtime_Hours REAL DEFAULT 0,
        FOREIGN KEY(Employee_ID) REFERENCES employees(Employee_ID)
    )
    """)

    # --- LEAVE MANAGEMENT TABLE ---
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS leaves (
        Leave_ID INTEGER PRIMARY KEY AUTOINCREMENT,
        Employee_ID INTEGER,
        Leave_Type TEXT,
        Start_Date TEXT,
        End_Date TEXT,
        Reason TEXT,
        Status TEXT DEFAULT 'Pending',
        FOREIGN KEY(Employee_ID) REFERENCES employees(Employee_ID)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        Task_ID INTEGER PRIMARY KEY AUTOINCREMENT,
        Employee_ID INTEGER,
        Task_Description TEXT,
        Due_Date TEXT,
        Status TEXT,
        FOREIGN KEY(Employee_ID) REFERENCES employees(Employee_ID)
    )
    """)

    # --- NEW TABLES FOR ANTI-POLITICS ---
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS grievances (
        Grievance_ID INTEGER PRIMARY KEY AUTOINCREMENT,
        Is_Anonymous BOOLEAN,
        Employee_ID INTEGER NULL,
        Subject TEXT,
        Description TEXT,
        Date TEXT,
        Status TEXT,
        FOREIGN KEY(Employee_ID) REFERENCES employees(Employee_ID)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS peer_reviews (
        Review_ID INTEGER PRIMARY KEY AUTOINCREMENT,
        Reviewer_ID INTEGER,
        Reviewee_ID INTEGER,
        Teamwork_Score REAL,
        Comments TEXT,
        Date TEXT,
        FOREIGN KEY(Reviewer_ID) REFERENCES employees(Employee_ID),
        FOREIGN KEY(Reviewee_ID) REFERENCES employees(Employee_ID)
    )
    """)

    # ---------------- DEFAULT USERS ----------------
    hr_password = bcrypt.hashpw(b'hr123', bcrypt.gensalt())
    boss_password = bcrypt.hashpw(b'boss123', bcrypt.gensalt())
    tl_password = bcrypt.hashpw(b'tl123', bcrypt.gensalt())
    manager_password = bcrypt.hashpw(b'manager123', bcrypt.gensalt())

    cursor.execute("INSERT OR IGNORE INTO users VALUES ('hr', ?, 'HR')", (hr_password,))
    cursor.execute("INSERT OR IGNORE INTO users VALUES ('boss', ?, 'MANAGEMENT')", (boss_password,))
    cursor.execute("INSERT OR IGNORE INTO users VALUES ('tl', ?, 'TEAMLEADER')", (tl_password,))
    cursor.execute("INSERT OR IGNORE INTO users VALUES ('manager', ?, 'MANAGER')", (manager_password,))

    # ---------------- DUMMY DATA ----------------
    # Add dummy employees if not exists
    cursor.execute("SELECT * FROM employees")
    if len(cursor.fetchall()) <= 1:
        dummy_password = bcrypt.hashpw(b'emp123', bcrypt.gensalt())
        employees = [
            (1, 'John Doe', 50000, '2024-01-15', 'john.doe@example.com', dummy_password),
            (2, 'Jane Smith', 60000, '2024-02-10', 'jane.smith@example.com', dummy_password),
            (3, 'Robert Brown', 55000, '2024-03-05', 'robert.brown@example.com', dummy_password),
            (4, 'Emily Davis', 62000, '2024-04-12', 'emily.davis@example.com', dummy_password)
        ]
        cursor.executemany("INSERT OR IGNORE INTO employees (Employee_ID, Name, Salary, Joining_Date, Email, Password) VALUES (?, ?, ?, ?, ?, ?)", employees)

        # Add dummy tasks
        tasks = [
            (1, 'Complete project proposal', '2024-08-15', 'In Progress'),
            (1, 'Prepare presentation', '2024-08-20', 'Not Started'),
            (1, 'Review software module', '2024-08-25', 'Completed'),
            (2, 'Update client database', '2024-08-18', 'Completed'),
            (2, 'Draft budget report', '2024-08-22', 'In Progress'),
            (3, 'Security audit', '2024-08-30', 'Not Started'),
            (4, 'Team training session', '2024-08-15', 'Completed')
        ]
        cursor.executemany("INSERT OR IGNORE INTO tasks (Employee_ID, Task_Description, Due_Date, Status) VALUES (?, ?, ?, ?)", tasks)

        # Add dummy evaluations
        evaluations = [
            (1, 85.5, 90.0, 88.0, 4.5, 'Excellent performance this quarter.'),
            (2, 92.0, 95.0, 90.0, 4.8, 'Very proactive and consistent.'),
            (3, 70.0, 65.0, 75.0, 3.2, 'Needs improvement in task completion speed.'),
            (4, 88.0, 85.0, 92.0, 4.3, 'Strong technical skills and good team player.')
        ]
        cursor.executemany("INSERT OR IGNORE INTO evaluation (Employee_ID, Productivity, Task_Completion, Training_Score, Manager_Rating, Qualitative_Feedback) VALUES (?, ?, ?, ?, ?, ?)", evaluations)

    conn.commit()
    conn.close()

if __name__ == '__main__':
    create_tables()
    print("Database and tables created successfully.")
