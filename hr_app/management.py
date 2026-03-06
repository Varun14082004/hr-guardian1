from flask import Blueprint, render_template, flash, redirect
from database import get_db_connection
from auth import login_required
import pandas as pd

management_bp = Blueprint('management', __name__)

@management_bp.route('/dashboard')
@login_required(roles=['MANAGEMENT'])
def dashboard():
    conn = get_db_connection()
    
    # Existing logs and red flags
    logs = pd.read_sql("SELECT * FROM logs ORDER BY timestamp DESC LIMIT 10", conn)
    red_flags = pd.read_sql("SELECT * FROM red_flags ORDER BY Timestamp DESC", conn)
    
    # Summary Statistics
    total_employees = conn.execute("SELECT COUNT(*) FROM employees").fetchone()[0]
    total_tasks = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
    avg_rating = conn.execute("SELECT AVG(Manager_Rating) FROM evaluation").fetchone()[0] or 0
    
    # Performance Overview (Top Performers)
    performance_query = """
    SELECT e.Name, ev.Productivity, ev.Task_Completion, ev.Manager_Rating 
    FROM employees e 
    JOIN evaluation ev ON e.Employee_ID = ev.Employee_ID 
    ORDER BY ev.Manager_Rating DESC LIMIT 5
    """
    top_performers = pd.read_sql(performance_query, conn)
    
    # Task Status Distribution
    task_status = pd.read_sql("SELECT Status, COUNT(*) as count FROM tasks GROUP BY Status", conn)
    
    # Recent Evaluations
    recent_evals_query = """
    SELECT e.Name, ev.Manager_Rating, ev.Qualitative_Feedback 
    FROM employees e 
    JOIN evaluation ev ON e.Employee_ID = ev.Employee_ID 
    ORDER BY ev.Evaluation_ID DESC LIMIT 5
    """
    recent_evaluations = pd.read_sql(recent_evals_query, conn)

    # Grievances
    grievances = pd.read_sql("SELECT * FROM grievances ORDER BY Date DESC", conn)

    # Comparison Data for Graphs
    comparison_query = """
    SELECT 
        e.Name, 
        e.Salary,
        IFNULL(AVG(ev.Productivity), 0) as avg_prod,
        IFNULL(AVG(ev.Task_Completion), 0) as avg_task,
        IFNULL(AVG(ev.Manager_Rating), 0) as avg_rating,
        (SELECT COUNT(*) FROM tasks t WHERE t.Employee_ID = e.Employee_ID AND t.Status = 'Completed') as completed_tasks,
        (SELECT COUNT(DISTINCT Date) FROM attendance a WHERE a.Employee_ID = e.Employee_ID) as total_days
    FROM employees e
    LEFT JOIN evaluation ev ON e.Employee_ID = ev.Employee_ID
    GROUP BY e.Employee_ID
    """
    comparison_data = pd.read_sql(comparison_query, conn).to_dict('records')

    # Enhanced Analytics: ROI & Risk
    from ai_analysis import calculate_employee_risk
    for emp in comparison_data:
        # AI Risk
        risk_level, risk_reasons = calculate_employee_risk(emp['total_days'], emp['avg_task'], emp['avg_rating'])
        emp['risk_level'] = risk_level
        emp['risk_reasons'] = ", ".join(risk_reasons) if risk_reasons else "Healthy"
        
        # Salary ROI (Efficiency Score)
        salary_factor = emp['Salary'] / 1000  # k value
        performance_factor = (emp['avg_prod'] + emp['avg_task'] + emp['avg_rating']) / 3
        emp['roi_score'] = round(performance_factor / (salary_factor / 10), 2) if salary_factor > 0 else 0

    conn.close()
    
    return render_template('management_dashboard.html', 
                           logs=logs, 
                           red_flags=red_flags,
                           total_employees=total_employees,
                           total_tasks=total_tasks,
                           avg_rating=round(avg_rating, 2),
                           top_performers=top_performers,
                           task_status=task_status,
                           recent_evaluations=recent_evaluations,
                           grievances=grievances,
                           comparison_data=comparison_data)

@management_bp.route('/resolve_grievance/<int:grievance_id>', methods=['POST'])
@login_required(roles=['MANAGEMENT'])
def resolve_grievance(grievance_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE grievances SET Status = 'Noted by Management' WHERE Grievance_ID = ?", (grievance_id,))
    conn.commit()
    conn.close()
    flash("Grievance marked as noted. The employee will see this acknowledgment.", "success")
    return redirect('/dashboard')
