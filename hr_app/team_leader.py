from flask import Blueprint, render_template, request, flash, redirect, session
from database import get_db_connection
from auth import login_required
import pandas as pd
from ai_analysis import analyze_evaluation_feedback
from datetime import datetime
from mailer import send_email
from config import MANAGEMENT_EMAIL

team_leader_bp = Blueprint('team_leader', __name__)

@team_leader_bp.route('/teamleader', methods=['GET', 'POST'])
@login_required(roles=['TEAMLEADER'])
def teamleader():
    conn = get_db_connection()
    
    # Fetch team data for overview
    team_query = """
    SELECT 
        e.Employee_ID, e.Name, 
        IFNULL(AVG(ev.Productivity), 0) as avg_prod,
        IFNULL(AVG(ev.Task_Completion), 0) as avg_task,
        (SELECT COUNT(*) FROM tasks t WHERE t.Employee_ID = e.Employee_ID AND t.Status = 'Completed') as completed_tasks,
        (SELECT COUNT(*) FROM tasks t WHERE t.Employee_ID = e.Employee_ID AND t.Status != 'Completed') as pending_tasks
    FROM employees e
    LEFT JOIN evaluation ev ON e.Employee_ID = ev.Employee_ID
    GROUP BY e.Employee_ID
    """
    team_data = pd.read_sql(team_query, conn).to_dict('records')

    # Fetch recent evaluations submitted by this TL
    recent_evals = pd.read_sql("""
        SELECT e.Name, ev.* 
        FROM evaluation ev 
        JOIN employees e ON ev.Employee_ID = e.Employee_ID 
        ORDER BY ev.Evaluation_ID DESC LIMIT 5
    """, conn).to_dict('records')

    if request.method == 'POST':
        cursor = conn.cursor()
        try:
            # --- Objective Data Fetching ---
            cursor.execute("SELECT COUNT(*) FROM tasks WHERE Employee_ID = ?", (request.form['id'],))
            total_tasks_db = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM tasks WHERE Employee_ID = ? AND Status = 'Completed'", (request.form['id'],))
            completed_tasks_db = cursor.fetchone()[0]
            actual_completion_rate = (completed_tasks_db / total_tasks_db * 100) if total_tasks_db > 0 else 100

            # AI Analysis
            scores = {'prod': float(request.form['prod']), 'task': float(request.form['task']), 'train': float(request.form['train'])}
            feedback_text = request.form['qualitative_feedback']
            is_red_flag, reason = analyze_evaluation_feedback(scores, feedback_text, actual_completion_rate)

            if is_red_flag:
                cursor.execute("""
                INSERT INTO red_flags (Evaluator_Username, Employee_ID, Reason, Evaluation_Text, Timestamp)
                VALUES (?, ?, ?, ?, ?)
                """, (session['username'], request.form['id'], reason, feedback_text, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
                conn.commit()
                flash(f"AI Red Flag Detected: {reason}.", "danger")
                
                # Email to management
                send_email(MANAGEMENT_EMAIL, f"AI Red Flag: {session['username']}", f"Reason: {reason}\nText: {feedback_text}")

            cursor.execute("""
            INSERT INTO evaluation (Employee_ID, Productivity, Task_Completion, Training_Score, Manager_Rating, Qualitative_Feedback)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (request.form['id'], request.form['prod'], request.form['task'], request.form['train'], request.form['rating'], feedback_text))
            conn.commit()
            flash('Evaluation submitted!', 'success')
        except Exception as e:
            flash(f'Error: {e}', 'danger')
        
        conn.close()
        return redirect('/teamleader')

    # Fetch pending leave requests for the TL's team
    pending_leaves = pd.read_sql("""
        SELECT l.*, e.Name 
        FROM leaves l 
        JOIN employees e ON l.Employee_ID = e.Employee_ID 
        WHERE l.Status = 'Pending' 
        ORDER BY l.Start_Date ASC
    """, conn).to_dict('records')

    conn.close()
    return render_template('teamleader_panel.html', team_data=team_data, recent_evals=recent_evals, pending_leaves=pending_leaves)

@team_leader_bp.route('/tl_approve_leave/<int:leave_id>/<string:status>', methods=['POST'])
@login_required(roles=['TEAMLEADER'])
def tl_approve_leave(leave_id, status):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE leaves SET Status = ? WHERE Leave_ID = ?", (status, leave_id))
    
    # Also log this as a system action for audit
    from datetime import datetime
    cursor.execute("INSERT INTO logs (username, action, timestamp) VALUES (?, ?, ?)", 
                   (session['username'], f"TL {status} leave for Leave_ID {leave_id}", datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    
    conn.commit()
    conn.close()
    flash(f"Leave application has been {status}.", "success")
    return redirect('/teamleader')

@team_leader_bp.route('/get_employee_tasks/<int:emp_id>')
@login_required(roles=['TEAMLEADER', 'MANAGEMENT'])
def get_employee_tasks(emp_id):
    conn = get_db_connection()
    tasks = pd.read_sql("SELECT Task_Description, Due_Date, Status FROM tasks WHERE Employee_ID = ?", conn, params=(emp_id,)).to_dict('records')
    conn.close()
    return jsonify(tasks)

@team_leader_bp.route('/add_task', methods=['GET', 'POST'])
@login_required(roles=['TEAMLEADER', 'MANAGEMENT'])
def add_task():
    conn = get_db_connection()
    employees = pd.read_sql("SELECT Employee_ID, Name, Email FROM employees", conn).to_dict('records')

    if request.method == 'POST':
        cursor = conn.cursor()
        try:
            # Insert the task
            cursor.execute("""
            INSERT INTO tasks (Employee_ID, Task_Description, Due_Date, Status)
            VALUES (?, ?, ?, ?)
            """, (
                request.form['employee_id'],
                request.form['task_description'],
                request.form['due_date'],
                request.form['status']
            ))
            conn.commit()
            flash('Task added successfully!', 'success')

            # Send email to the employee
            employee_id = request.form['employee_id']
            employee_info = next((emp for emp in employees if str(emp['Employee_ID']) == employee_id), None)
            
            if employee_info:
                subject = "New Task Assigned to You"
                message_body = f"""
                Hello {employee_info['Name']},

                A new task has been assigned to you by {session['username']}.

                Task: {request.form['task_description']}
                Due Date: {request.form['due_date']}

                Please log in to the employee dashboard to view your tasks.
                """
                send_email(employee_info['Email'], subject, message_body)
                flash(f"An email notification has been sent to {employee_info['Name']}.", "info")

        except Exception as e:
            flash(f'Error adding task: {e}', 'danger')
        
        conn.close()
        return redirect('/add_task')

    conn.close()
    return render_template('add_task.html', employees=employees)
