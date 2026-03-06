import os
from flask import Blueprint, render_template, session, request, redirect, flash, jsonify
from auth import login_required
from database import get_db_connection
import pandas as pd
from datetime import datetime
import bcrypt

employee_bp = Blueprint('employee', __name__)

RECORDINGS_DIR = "recordings"
if not os.path.exists(RECORDINGS_DIR):
    os.makedirs(RECORDINGS_DIR)

@employee_bp.route('/upload_recording', methods=['POST'])
@login_required(roles=['EMPLOYEE'])
def upload_recording():
    if 'video' not in request.files:
        return jsonify({"error": "No video data"}), 400
    
    video = request.files['video']
    employee_id = session['username']
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    filename = f"emp_{employee_id}_{timestamp}.webm"
    video.save(os.path.join(RECORDINGS_DIR, filename))
    
    return jsonify({"status": "saved", "filename": filename})

@employee_bp.route('/employee')
@login_required(roles=['EMPLOYEE'])
def employee_dashboard():
    conn = get_db_connection()
    employee_id = session['username']
    attendance_df = pd.read_sql("SELECT * FROM attendance WHERE Employee_ID = ? ORDER BY Date DESC, Login_Time DESC", conn, params=(employee_id,))
    tasks_df = pd.read_sql("SELECT * FROM tasks WHERE Employee_ID = ?", conn, params=(employee_id,))
    
    total_days_present = len(attendance_df['Date'].unique())
    total_tasks = tasks_df.shape[0]
    tasks_completed = tasks_df[tasks_df['Status'] == 'Completed'].shape[0]
    tasks_in_progress = tasks_df[tasks_df['Status'] == 'In Progress'].shape[0]
    tasks_not_started = tasks_df[tasks_df['Status'] == 'Not Started'].shape[0]
    
    task_completion_rate = (tasks_completed / total_tasks * 100) if total_tasks > 0 else 100

    # Peer Review Data
    peer_reviews = pd.read_sql("SELECT AVG(Teamwork_Score) as avg_score FROM peer_reviews WHERE Reviewee_ID = ?", conn, params=(employee_id,))
    avg_peer_score = peer_reviews.iloc[0]['avg_score'] if not pd.isna(peer_reviews.iloc[0]['avg_score']) else 100

    # Objective Promotion Score
    promotion_score = round((task_completion_rate * 0.6) + (avg_peer_score * 0.4), 1)

    # Colleagues for Peer Review
    colleagues = pd.read_sql("SELECT Employee_ID, Name FROM employees WHERE Employee_ID != ?", conn, params=(employee_id,)).to_dict('records')

    # Leave Requests
    leaves = pd.read_sql("SELECT * FROM leaves WHERE Employee_ID = ? ORDER BY Start_Date DESC", conn, params=(employee_id,)).to_dict('records')

    # Personal Grievances (Directly submitted, not anonymous)
    personal_grievances = pd.read_sql("SELECT * FROM grievances WHERE Employee_ID = ? ORDER BY Date DESC", conn, params=(employee_id,)).to_dict('records')

    insights = {
        'total_days_present': total_days_present,
        'tasks_completed': tasks_completed,
        'tasks_in_progress': tasks_in_progress,
        'tasks_not_started': tasks_not_started,
        'task_completion_rate': round(task_completion_rate, 1),
        'avg_peer_score': round(avg_peer_score, 1),
        'promotion_score': promotion_score
    }
    conn.close()
    return render_template('employee_dashboard.html', 
                           attendance=attendance_df, 
                           tasks=tasks_df, 
                           insights=insights, 
                           colleagues=colleagues, 
                           leaves=leaves, 
                           grievances=personal_grievances)

@employee_bp.route('/apply_leave', methods=['POST'])
@login_required(roles=['EMPLOYEE'])
def apply_leave():
    leave_type = request.form['leave_type']
    start_date = request.form['start_date']
    end_date = request.form['end_date']
    reason = request.form['reason']
    employee_id = session['username']
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO leaves (Employee_ID, Leave_Type, Start_Date, End_Date, Reason)
        VALUES (?, ?, ?, ?, ?)
    """, (employee_id, leave_type, start_date, end_date, reason))
    conn.commit()
    conn.close()
    
    flash("Leave application submitted successfully!", "success")
    return redirect('/employee')

@employee_bp.route('/submit_grievance', methods=['POST'])
@login_required(roles=['EMPLOYEE'])
def submit_grievance():
    is_anonymous = request.form.get('anonymous') == 'on'
    subject = request.form['subject']
    description = request.form['description']
    employee_id = None if is_anonymous else session['username']
    date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO grievances (Is_Anonymous, Employee_ID, Subject, Description, Date, Status)
        VALUES (?, ?, ?, ?, ?, 'Open')
    """, (is_anonymous, employee_id, subject, description, date))
    conn.commit()
    conn.close()

    flash("Grievance submitted successfully. It will be reviewed directly by upper management.", "success")
    return redirect('/employee')

@employee_bp.route('/submit_peer_review', methods=['POST'])
@login_required(roles=['EMPLOYEE'])
def submit_peer_review():
    reviewee_id = request.form['reviewee_id']
    score = float(request.form['score'])
    comments = request.form['comments']
    reviewer_id = session['username']
    date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO peer_reviews (Reviewer_ID, Reviewee_ID, Teamwork_Score, Comments, Date)
        VALUES (?, ?, ?, ?, ?)
    """, (reviewer_id, reviewee_id, score, comments, date))
    conn.commit()
    conn.close()

    flash("Peer review submitted successfully! Your input helps combat bias.", "success")
    return redirect('/employee')

@employee_bp.route('/change_password', methods=['POST'])
@login_required(roles=['EMPLOYEE'])
def change_password():
    new_password = request.form['new_password'].encode('utf-8')
    confirm_password = request.form['confirm_password'].encode('utf-8')
    employee_id = session['username']
    
    if new_password != confirm_password:
        flash("Passwords do not match!", "danger")
        return redirect('/employee')
    
    hashed_password = bcrypt.hashpw(new_password, bcrypt.gensalt())
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE employees SET Password = ? WHERE Employee_ID = ?", (hashed_password, employee_id))
    conn.commit()
    conn.close()
    
    flash("Password updated successfully! It is now more secure.", "success")
    return redirect('/employee')

@employee_bp.route('/update_task_status', methods=['POST'])
@login_required(roles=['EMPLOYEE'])
def update_task_status():
    task_id = request.form['task_id']
    new_status = request.form['status']
    employee_id = session['username']
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET Status = ? WHERE Task_ID = ? AND Employee_ID = ?", (new_status, task_id, employee_id))
    conn.commit()
    conn.close()
    
    flash(f"Task status updated to {new_status}.", "success")
    return redirect('/employee')
