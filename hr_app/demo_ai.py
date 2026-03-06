from ai_analysis import analyze_evaluation_feedback

def run_demo():
    scenarios = [
        {
            "name": "Scenario 1: Unprofessional Language (Personal Attack)",
            "scores": {"prod": 20, "task": 15, "train": 25},
            "feedback": "This employee is just lazy and a total disaster for the team."
        },
        {
            "name": "Scenario 2: Vague Malice (Low scores, no explanation)",
            "scores": {"prod": 5, "task": 10, "train": 5},
            "feedback": "Bad worker."
        },
        {
            "name": "Scenario 3: Positive Contradiction (Low scores, but positive words)",
            "scores": {"prod": 30, "task": 25, "train": 35},
            "feedback": "She is a great employee and very fantastic at her job."
        },
        {
            "name": "Scenario 4: Valid Evaluation (High scores, professional feedback)",
            "scores": {"prod": 90, "task": 85, "train": 88},
            "feedback": "Consistently meets targets and shows great initiative in team projects."
        }
    ]

    print("="*80)
    print("AI FALSE ALLEGATION DETECTION - DEMO RESULTS")
    print("="*80)

    for i, s in enumerate(scenarios, 1):
        is_red_flag, reason = analyze_evaluation_feedback(s['scores'], s['feedback'])
        status = "❌ FLAGGED (False Allegation / Bias)" if is_red_flag else "✅ VALID EVALUATION"
        
        print(f"\n[CASE {i}] {s['name']}")
        print(f"Feedback: \"{s['feedback']}\"")
        print(f"Avg Score: {sum(s['scores'].values())/3:.1f}%")
        print(f"Result: {status}")
        if is_red_flag:
            print(f"AI Reason: {reason}")
    
    print("\n" + "="*80)

if __name__ == "__main__":
    run_demo()
