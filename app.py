from flask import Flask, render_template, redirect, url_for
from flask_login import LoginManager, current_user
import os
from dotenv import load_dotenv
from config.database import init_db, db
from models.user import User

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key')

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

init_db(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'

@login_manager.user_loader
def load_user(user_id):
    return User.get_by_id(db, user_id)

from routes.auth import auth_bp
from routes.student import student_bp
from routes.mentor import mentor_bp
from routes.admin import admin_bp

app.register_blueprint(auth_bp)
app.register_blueprint(student_bp, url_prefix='/student')
app.register_blueprint(mentor_bp, url_prefix='/mentor')
app.register_blueprint(admin_bp, url_prefix='/admin')

@app.route('/')
def index():
    # If logged in, redirect to role dashboard; else show landing page
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin.dashboard'))
        if current_user.role == 'mentor':
            return redirect(url_for('mentor.dashboard'))
        return redirect(url_for('student.dashboard'))

    # Get real counts from database for landing page
    student_count = db.users.count_documents({'role': 'student'})
    internship_count = db.internships.count_documents({})
    mentor_count = db.users.count_documents({'role': 'mentor'})
    activity_count = db.activities.count_documents({})

    return render_template('index.html',
                           student_count=student_count,
                           internship_count=internship_count,
                           mentor_count=mentor_count,
                           activity_count=activity_count)

if __name__ == '__main__':
    app.run(debug=True)