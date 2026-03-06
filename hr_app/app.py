from flask import Flask, render_template, session
import os
from database import create_tables
from auth import auth_bp
from hr import hr_bp
from team_leader import team_leader_bp
from management import management_bp
from employee import employee_bp
from manager import manager_bp

# --- Database Check ---
DB_FILE = 'hr_system.db'
if not os.path.exists(DB_FILE):
    print("Database not found. Creating it now...")
    create_tables()
# --- End Database Check ---

app = Flask(__name__)
app.secret_key = "a_much_more_secure_secret_key"
app.config['SESSION_PERMANENT'] = False  # Ensure session expires on browser close

# Register Blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(hr_bp)
app.register_blueprint(team_leader_bp)
app.register_blueprint(management_bp)
app.register_blueprint(employee_bp)
app.register_blueprint(manager_bp)

@app.route('/')
def home():
    return render_template('home.html')

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
