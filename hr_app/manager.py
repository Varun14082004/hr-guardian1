from flask import Blueprint, render_template, session, request, redirect, flash
from auth import login_required
from database import get_db_connection
import pandas as pd
from datetime import datetime

manager_bp = Blueprint('manager', __name__)

@manager_bp.route('/manager')
@login_required(roles=['MANAGER'])
def manager_dashboard():
    conn = get_db_connection()
    
    # Fetch evaluations for Audit (Wait for approval/review)
    eval_query = """
        SELECT e.Name, ev.* 
        FROM evaluation ev 
        JOIN employees e ON ev.Employee_ID = e.Employee_ID 
        ORDER BY ev.Evaluation_ID DESC
    """
    evaluations = pd.read_sql(eval_query, conn).to_dict('records')

    # Overall Team Status
    team_query = """
        SELECT e.Name, e.Employee_ID, 
               (SELECT COUNT(*) FROM tasks t WHERE t.Employee_ID = e.Employee_ID AND t.Status = 'Completed') as tasks_done,
               (SELECT COUNT(*) FROM tasks t WHERE t.Employee_ID = e.Employee_ID) as total_tasks
        FROM employees e
    """
    team_status = pd.read_sql(team_query, conn).to_dict('records')

    conn.close()
    return render_template('manager_dashboard.html', evaluations=evaluations, team_status=team_status)

@manager_bp.route('/update_evaluation_status/<int:eval_id>/<string:status>', methods=['POST'])
@login_required(roles=['MANAGER'])
def update_evaluation_status(eval_id, status):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Fetch the evaluation data to audit it
    cursor.execute("SELECT * FROM evaluation WHERE Evaluation_ID = ?", (eval_id,))
    ev = cursor.fetchone()
    
    if ev:
        if status == 'Approved':
            # Run AI Multi-Stage Audit for Bias on Approval
            cursor.execute("SELECT COUNT(*) FROM tasks WHERE Employee_ID = ?", (ev['Employee_ID'],))
            total_tasks = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM tasks WHERE Employee_ID = ? AND Status = 'Completed'", (ev['Employee_ID'],))
            completed_tasks = cursor.fetchone()[0]
            actual_completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 100

            from ai_analysis import analyze_evaluation_feedback
            scores = {'prod': ev['Productivity'], 'task': ev['Task_Completion'], 'train': ev['Training_Score']}
            is_red_flag, reason = analyze_evaluation_feedback(scores, ev['Qualitative_Feedback'], actual_completion_rate)

            if is_red_flag:
                cursor.execute("""
                INSERT INTO red_flags (Evaluator_Username, Employee_ID, Reason, Evaluation_Text, Timestamp)
                VALUES (?, ?, ?, ?, ?)
                """, (session['username'], ev['Employee_ID'], f"MANAGER BIAS: Approved despite AI Warning ({reason})", ev['Qualitative_Feedback'], datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
                from mailer import send_email
                from config import MANAGEMENT_EMAIL
                send_email(MANAGEMENT_EMAIL, "URGENT: Manager Bias Detected", f"Manager {session['username']} has approved a flagged evaluation.")
                flash("Warning: The AI has flagged this approval as suspicious. Reported to Management.", "danger")
            else:
                flash(f"Evaluation #{eval_id} finalized and approved.", "success")
        
        elif status == 'Rejected':
            # Log the rejection for TL visibility
            cursor.execute("INSERT INTO logs (username, action, timestamp) VALUES (?, ?, ?)",
                           (session['username'], f"REJECTED Evaluation ID {eval_id} - Requested Re-evaluation", datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            flash(f"Evaluation #{eval_id} has been declined. Team Leader will be notified to re-evaluate.", "warning")

    conn.commit()
    conn.close()
    return redirect('/manager')
