from flask import Blueprint, render_template, request, flash, redirect
from database import get_db_connection
from auth import login_required
import bcrypt
import pandas as pd

hr_bp = Blueprint('hr', __name__)

@hr_bp.route('/hr', methods=['GET', 'POST'])
@login_required(roles=['HR'])
def hr_panel():
    conn = get_db_connection()
    
    if request.method == 'POST':
        cursor = conn.cursor()
        password = request.form['password'].encode('utf-8')
        hashed_password = bcrypt.hashpw(password, bcrypt.gensalt())

        try:
            cursor.execute("""
            INSERT INTO employees (Employee_ID, Name, Salary, Joining_Date, Email, Password)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (
                request.form['id'],
                request.form['name'],
                request.form['salary'],
                request.form['joining'],
                request.form['email'],
                hashed_password
            ))
            conn.commit()
            flash('Employee added successfully!', 'success')
        except Exception as e:
            flash(f'Error adding employee: {e}', 'danger')
        
        return redirect('/hr')

    # Fetch Pending Leaves
    pending_leaves = pd.read_sql("""
        SELECT l.*, e.Name FROM leaves l 
        JOIN employees e ON l.Employee_ID = e.Employee_ID 
        WHERE l.Status = 'Pending' ORDER BY Start_Date ASC
    """, conn).to_dict('records')

    # Overtime Compliance (Employees with > 10 hours overtime this month)
    overtime_alerts = pd.read_sql("""
        SELECT e.Name, SUM(a.Overtime_Hours) as total_ot
        FROM attendance a
        JOIN employees e ON a.Employee_ID = e.Employee_ID
        GROUP BY e.Employee_ID
        HAVING total_ot > 0
        ORDER BY total_ot DESC
    """, conn).to_dict('records')

    conn.close()
    return render_template('hr_panel.html', pending_leaves=pending_leaves, overtime_alerts=overtime_alerts)

@hr_bp.route('/update_leave_status/<int:leave_id>/<string:status>', methods=['POST'])
@login_required(roles=['HR'])
def update_leave_status(leave_id, status):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE leaves SET Status = ? WHERE Leave_ID = ?", (status, leave_id))
    conn.commit()
    conn.close()
    flash(f"Leave application has been {status}.", "success")
    return redirect('/hr')
