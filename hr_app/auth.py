from flask import Blueprint, render_template, request, redirect, session, flash, jsonify
import pandas as pd
import bcrypt
from functools import wraps
from database import get_db_connection
from datetime import datetime

auth_bp = Blueprint('auth', __name__)

def login_required(roles=["ANY"]):
    def wrapper(fn):
        @wraps(fn)
        def decorated_view(*args, **kwargs):
            if not session.get('role'):
                # Intelligent redirect based on path
                path = request.path
                if '/hr' in path: return redirect('/login/hr')
                if '/teamleader' in path or '/add_task' in path: return redirect('/login/tl')
                if '/dashboard' in path: return redirect('/login/management')
                if '/manager' in path or '/approve_evaluation' in path: return redirect('/login/manager')
                return redirect('/login/employee')
            
            if "ANY" not in roles and session.get('role') not in roles:
                flash("You don't have permission to access this page.", "danger")
                return redirect('/')
            return fn(*args, **kwargs)
        return decorated_view
    return wrapper

@auth_bp.route('/heartbeat', methods=['POST'])
def heartbeat():
    if session.get('role'):
        conn = get_db_connection()
        cursor = conn.cursor()
        username = session['username']
        now = datetime.now().strftime('%H:%M:%S')
        
        # Only employees have an attendance record to update
        if session.get('role') == 'EMPLOYEE':
            cursor.execute("""
                UPDATE attendance
                SET Last_Seen = ?
                WHERE rowid = (
                    SELECT rowid
                    FROM attendance
                    WHERE Employee_ID = ? AND Logout_Time IS NULL
                    ORDER BY Date DESC, Login_Time DESC
                    LIMIT 1
                )
            """, (now, username))
            conn.commit()
        
        conn.close()
    return jsonify({"status": "ok"})

@auth_bp.route('/login/<role>', methods=['GET', 'POST'])
def login(role):
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password'].encode('utf-8')
        conn = get_db_connection()

        if role == 'employee':
            emp = pd.read_sql("SELECT * FROM employees WHERE Employee_ID=?", conn, params=(username,))
            if len(emp) > 0 and bcrypt.checkpw(password, emp.iloc[0]["Password"]):
                session['role'] = 'EMPLOYEE'
                session['username'] = username
                
                # Record attendance with Last_Seen
                cursor = conn.cursor()
                now = datetime.now()
                cursor.execute("INSERT INTO attendance (Employee_ID, Date, Login_Time, Last_Seen) VALUES (?, ?, ?, ?)",
                               (username, now.strftime('%Y-%m-%d'), now.strftime('%H:%M:%S'), now.strftime('%H:%M:%S')))
                conn.commit()
                conn.close()
                return redirect('/employee')
            else:
                conn.close()
                flash('Invalid credentials', 'danger')
                return redirect(f'/login/{role}')

        user = pd.read_sql("SELECT * FROM users WHERE username=?", conn, params=(username,))
        conn.close()
        if len(user) > 0 and bcrypt.checkpw(password, user.iloc[0]["password"]):
            session['role'] = user.iloc[0]["role"]
            session['username'] = username
            
            if session['role'] == 'HR':
                return redirect('/hr')
            elif session['role'] == 'TEAMLEADER':
                return redirect('/teamleader')
            elif session['role'] == 'MANAGEMENT':
                return redirect('/dashboard')
            elif session['role'] == 'MANAGER':
                return redirect('/manager')
        else:
            flash('Invalid credentials', 'danger')
            return redirect(f'/login/{role}')

    return render_template('login.html', role=role)

@auth_bp.route('/logout', methods=['GET', 'POST'])
def logout():
    if session.get('role') == 'EMPLOYEE':
        conn = get_db_connection()
        cursor = conn.cursor()
        employee_id = session['username']
        now = datetime.now()
        logout_time_str = now.strftime('%H:%M:%S')
        
        # Get the login record
        cursor.execute("SELECT Login_Time, Date FROM attendance WHERE Employee_ID = ? AND Logout_Time IS NULL ORDER BY Date DESC, Login_Time DESC LIMIT 1", (employee_id,))
        login_record = cursor.fetchone()

        overtime = 0
        if login_record:
            login_time = datetime.strptime(f"{login_record['Date']} {login_record['Login_Time']}", '%Y-%m-%d %H:%M:%S')
            duration = now - login_time
            hours_worked = duration.total_seconds() / 3600
            if hours_worked > 8:
                overtime = round(hours_worked - 8, 2)

        cursor.execute("""
            UPDATE attendance
            SET Logout_Time = ?, Overtime_Hours = ?
            WHERE rowid = (
                SELECT rowid
                FROM attendance
                WHERE Employee_ID = ? AND Logout_Time IS NULL
                ORDER BY Date DESC, Login_Time DESC
                LIMIT 1
            )
        """, (logout_time_str, overtime, employee_id))
        conn.commit()
        conn.close()

    session.clear()
    if request.method == 'GET':
        flash('You have been logged out.', 'success')
        return redirect('/')
    return jsonify({"status": "logged_out"})
