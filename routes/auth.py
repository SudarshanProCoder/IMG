from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_user, logout_user, login_required, current_user
from models.user import User
from config.database import db
from config.cloudinary_config import configure_cloudinary
import cloudinary.uploader
import secrets
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
import os
from datetime import datetime, timedelta
from forms.auth import LoginForm, SignupForm

auth_bp = Blueprint('auth', __name__)

configure_cloudinary()

def send_verification_email(email, token):
    sender_email = os.getenv('SMTP_EMAIL')
    sender_password = os.getenv('SMTP_PASSWORD')
    
    if not sender_email or not sender_password:
        print("SMTP credentials not configured")
        return False
    
    msg = MIMEMultipart('alternative')
    msg['From'] = sender_email
    msg['To'] = email
    msg['Subject'] = "Verify your email - Shah and Anchor College"
    
    verification_url = url_for('auth.verify_email', token=token, _external=True)
    
    with open(os.path.join(current_app.static_folder, 'images/demo.png'), 'rb') as f:
        logo = MIMEImage(f.read())
        logo.add_header('Content-ID', '<logo>')
        msg.attach(logo)
    
    html_content = render_template('email/verification.html', verification_url=verification_url)
    
    text_content = f"""
    Hello,
    
    Thank you for registering with Shah and Anchor College's Internship Portal.
    Please click the link below to verify your email address:
    
    {verification_url}
    
    If you did not create an account, please ignore this email.
    
    Best regards,
    Shah and Anchor College
    """
    
    msg.attach(MIMEText(text_content, 'plain'))
    msg.attach(MIMEText(html_content, 'html'))
    
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.get_by_email(form.email.data)
        if user and user.check_password(form.password.data):
            if not user.is_verified:
                flash('Please verify your email before logging in.', 'warning')
                return redirect(url_for('auth.login'))
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            if not next_page or not next_page.startswith('/'):
                if user.role == 'admin':
                    next_page = url_for('admin.dashboard')
                elif user.role == 'mentor':
                    next_page = url_for('mentor.dashboard')
                else:
                    next_page = url_for('student.dashboard')
            return redirect(next_page)
        flash('Invalid email or password', 'danger')
    return render_template('auth/login.html', form=form, minimal=True)

@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = SignupForm()
    if form.validate_on_submit():
        try:
            profile_image_url = None
            if form.profile_photo.data and form.profile_photo.data.filename:
                try:
                    # Upload to Cloudinary
                    result = cloudinary.uploader.upload(
                        form.profile_photo.data,
                        folder="profile_images",
                        transformation=[
                            {'width': 400, 'height': 400, 'crop': 'fill'},
                            {'radius': 'max'}
                        ]
                    )
                    profile_image_url = result['secure_url']
                except Exception as e:
                    current_app.logger.error(f"Error uploading profile photo: {str(e)}")
                    flash('Error uploading profile photo. Please try again.', 'danger')
                    return render_template('auth/signup.html', form=form, minimal=True)
            
            verification_token = secrets.token_urlsafe(32)
            
            user = User(
                full_name=form.full_name.data,
                email=form.email.data,
                password=form.password.data,
                role=form.role.data,
                profile_image=profile_image_url,
                prn=form.prn.data if form.role.data == 'student' else None,
                registration_number=form.registration_number.data if form.role.data == 'student' else None,
                branch=form.branch.data if form.role.data == 'student' else None,
                year=form.year.data if form.role.data == 'student' else None,
                mentor_email=form.mentor_email.data if form.role.data == 'student' else None
            )
            
            user.verification_token = verification_token
            user.is_verified = False
            user.save()
            
            if send_verification_email(user.email, verification_token):
                flash('Account created successfully! Please check your email to verify your account.', 'success')
                return redirect(url_for('auth.login'))
            else:
                flash('Account created, but there was an error sending the verification email. Please contact support.', 'warning')
                return render_template('auth/signup.html', form=form, minimal=True)
            
            return redirect(url_for('auth.login'))
        except Exception as e:
            current_app.logger.error(f"Error creating user: {str(e)}")
            flash('Error creating account. Please try again.', 'danger')
    
    return render_template('auth/signup.html', form=form, minimal=True)

@auth_bp.route('/verify-email/<token>')
def verify_email(token):
    user_data = db.users.find_one({'verification_token': token})
    if user_data:
        db.users.update_one(
            {'_id': user_data['_id']},
            {'$set': {'is_verified': True, 'verification_token': None}}
        )
        flash('Email verified successfully! You can now log in.', 'success')
    else:
        flash('Invalid verification token.', 'danger')
    return redirect(url_for('auth.login'))

@auth_bp.route('/resend-verification')
@login_required
def resend_verification():
    if current_user.is_verified:
        flash('Your email is already verified.', 'info')
        return redirect(url_for('index'))

    verification_token = secrets.token_urlsafe(32)
    db.users.update_one(
        {'_id': current_user.id},
        {'$set': {'verification_token': verification_token}}
    )

    if send_verification_email(current_user.email, verification_token):
        flash('Verification email has been resent. Please check your inbox.', 'success')
    else:
        flash('There was an error sending the verification email. Please try again later.', 'danger')

    return redirect(url_for('index'))

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        department = request.form.get('department')
        batch = request.form.get('batch')
        semester = request.form.get('semester')
        gender = request.form.get('gender')
        date_of_birth = request.form.get('date_of_birth')
        address = request.form.get('address')
        
        if 'profile_image' in request.files:
            file = request.files['profile_image']
            if file and file.filename:
                try:
                    result = cloudinary.uploader.upload(file, 
                        folder="profile_images",
                        transformation=[
                            {'width': 400, 'height': 400, 'crop': 'fill'},
                            {'radius': 'max'}
                        ]
                    )
                    current_user.profile_image = result['secure_url']
                except Exception as e:
                    flash('Error uploading profile image', 'error')
                    return redirect(url_for('auth.profile'))
        
        if full_name and full_name != current_user.full_name:
            current_user.full_name = full_name
        
        if email and email != current_user.email:
            existing_user = User.get_by_email(email)
            if existing_user and existing_user.id != current_user.id:
                flash('Email is already taken.', 'error')
                return redirect(url_for('auth.profile'))
            current_user.email = email
        
        current_user.phone = phone
        current_user.department = department
        current_user.batch = batch
        current_user.semester = semester
        current_user.gender = gender
        current_user.date_of_birth = datetime.strptime(date_of_birth, '%Y-%m-%d') if date_of_birth else None
        current_user.address = address
        
        current_user.save()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('auth.profile'))
    # Render role-specific profile pages
    template_map = {
        'student': 'student/profile.html',
        'mentor': 'mentor/profile.html',
        'admin': 'admin/profile.html',
    }
    template = template_map.get(current_user.role, 'auth/profile.html')
    return render_template(template)

@auth_bp.route('/change-password', methods=['POST'])
@login_required
def change_password():
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')

    if not current_user.check_password(current_password):
        flash('Current password is incorrect', 'error')
        return redirect(url_for('auth.profile'))

    if new_password != confirm_password:
        flash('New passwords do not match', 'error')
        return redirect(url_for('auth.profile'))

    current_user.set_password(new_password)
    current_user.save()

    flash('Password updated successfully', 'success')
    return redirect(url_for('auth.profile'))