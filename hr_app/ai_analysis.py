import re

def analyze_evaluation_feedback(scores, feedback, actual_task_completion_rate=None):
    """
    Advanced AI Analysis to detect False Allegations.
    """
    feedback_lower = feedback.lower()
    avg_score = (scores['prod'] + scores['task'] + scores['train']) / 3
    
    # 1. Objective Fact Check
    if actual_task_completion_rate is not None:
        if scores['task'] < 40 and actual_task_completion_rate > 80:
            return True, f"Possible False Allegation: Manager score ({scores['task']}) contradicts database ({actual_task_completion_rate:.1f}%)."

    # 2. Professionalism
    unprofessional_terms = ['lazy', 'useless', 'stupid', 'incompetent', 'terrible', 'toxic', 'disaster', 'failure']
    found_unprofessional = [word for word in unprofessional_terms if word in feedback_lower]
    if found_unprofessional:
        return True, f"Possible False Allegation: Unprofessional language ({', '.join(found_unprofessional)})."

    # 3. Contradiction Detection
    positive_keywords = ['excellent', 'great', 'amazing', 'wonderful', 'fantastic', 'superb']
    if any(word in feedback_lower for word in positive_keywords) and avg_score < 40:
        return True, "Contradiction: Positive sentiment with suspiciously low scores."

    return False, "No red flags detected."

def calculate_employee_risk(attendance_days, task_completion_rate, avg_rating):
    """
    AI Predictor: High Risk = Low Attendance + Low Task Completion + Negative Feedback.
    """
    risk_score = 0
    reasons = []

    if task_completion_rate < 50:
        risk_score += 40
        reasons.append("Critically low task completion")
    
    if attendance_days < 15: # Assuming a monthly view
        risk_score += 30
        reasons.append("Irregular attendance patterns")

    if avg_rating < 40:
        risk_score += 30
        reasons.append("Consistently negative management feedback")

    risk_level = "Low"
    if risk_score >= 70: risk_level = "Critical"
    elif risk_score >= 40: risk_level = "Medium"

    return risk_level, reasons
