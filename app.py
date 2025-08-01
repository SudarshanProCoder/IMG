from flask import Flask, render_template
from flask_login import LoginManager
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
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True) 