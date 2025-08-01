from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, send_file
from flask_login import login_required, current_user
from models.internship import Internship
from models.activity import Activity
import os
from werkzeug.utils import secure_filename
from datetime import datetime
import logging
from utils.pdf_generator import generate_marksheet, generate_internship_pdf, generate_custom_marksheet
from io import BytesIO
import cloudinary
import cloudinary.uploader
import cloudinary.api
import time
from PIL import Image
import io
import fitz  # PyMuPDF
import base64
from utils.pdf_generator import generate_internship_pdf
from models.user import User
from dateutil.relativedelta import relativedelta
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

student_bp = Blueprint('student', __name__)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'jpg', 'jpeg', 'png', 'gif'}

def convert_pdf_to_image(pdf_file):
    """Convert first page of PDF to image"""
    try:
        # Read the PDF file
        pdf_document = fitz.open(stream=pdf_file.read(), filetype="pdf")
        # Get the first page
        first_page = pdf_document[0]
        # Convert to image with higher quality
        pix = first_page.get_pixmap(matrix=fitz.Matrix(3, 3))  # Increased zoom for better quality
        # Convert to PIL Image
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        # Convert to bytes with better quality
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG', quality=95)
        img_byte_arr.seek(0)
        return img_byte_arr
    except Exception as e:
        logging.error(f"Error converting PDF to image: {str(e)}")
        return None

def upload_to_cloudinary(file, folder):
    """Upload an image to Cloudinary and return the URL"""
    try:
        result = cloudinary.uploader.upload(
            file,
            resource_type="image",
            folder=folder,
            public_id=f"{current_user.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            overwrite=True,
            format="jpg"  # Convert all images to JPG for consistency
        )
        return result['secure_url']
    except Exception as e:
        logging.error(f"Error uploading to Cloudinary: {str(e)}")
        raise

@student_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.role != 'student':
        flash('Access denied.', 'error')
        return redirect(url_for('auth.login'))
    
    internships = Internship.get_by_student_id(current_app.db, current_user.id)
    activities = Activity.get_by_student_id(current_app.db, current_user.id)
    
    return render_template('student/dashboard.html',
                         internships=internships,
                         activities=activities)

@student_bp.route('/internships')
@login_required
def internships():
    if current_user.role != 'student':
        flash('Access denied.', 'error')
        return redirect(url_for('auth.login'))
    
    internships = Internship.get_by_student_id(current_app.db, current_user.id)
    return render_template('student/internships.html', internships=internships)

@student_bp.route('/activities')
@login_required
def activities():
    if current_user.role != 'student':
        flash('Access denied.', 'error')
        return redirect(url_for('auth.login'))
    
    activities = Activity.get_by_student_id(current_app.db, current_user.id)
    return render_template('student/activities.html', activities=activities)

@student_bp.route('/internships/new', methods=['GET', 'POST'])
@login_required
def new_internship():
    if current_user.role != 'student':
        flash('Access denied.', 'danger')
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        try:
            # Get form data
            company_name = request.form.get('company_name')
            project_name = request.form.get('project_name')
            start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d')
            end_date = datetime.strptime(request.form.get('end_date'), '%Y-%m-%d')
            # Get academic year from form (calculated by JavaScript)
            academic_year = request.form.get('academic_year')
            # If academic_year is not provided in the form, calculate it
            if not academic_year:
                month = start_date.month
                year = start_date.year
                if 1 <= month <= 5:
                    academic_year = f"{year-1}-{str(year)[-2:]}"
                else:
                    academic_year = f"{year}-{str(year+1)[-2:]}"
            hours_per_week = int(request.form.get('hours_per_week'))
            skills = [skill.strip() for skill in request.form.get('skills').split(',')]

            # Handle file uploads
            offer_letter_url = None
            completion_letter_url = None

            if 'offer_letter' in request.files:
                offer_letter = request.files['offer_letter']
                if offer_letter and offer_letter.filename:
                    if not allowed_file(offer_letter.filename):
                        flash('Offer letter must be an image file (JPG, PNG, GIF).', 'danger')
                        return redirect(url_for('student.new_internship'))
                    
                    # Upload to Cloudinary
                    offer_letter_url = upload_to_cloudinary(offer_letter, 'internships/offer_letters')

            if 'completion_letter' in request.files:
                completion_letter = request.files['completion_letter']
                if completion_letter and completion_letter.filename:
                    if not allowed_file(completion_letter.filename):
                        flash('Completion letter must be an image file (JPG, PNG, GIF).', 'danger')
                        return redirect(url_for('student.new_internship'))
                    
                    # Upload to Cloudinary
                    completion_letter_url = upload_to_cloudinary(completion_letter, 'internships/completion_letters')

            # Calculate total hours
            duration_days = (end_date - start_date).days
            total_hours = (duration_days / 7) * hours_per_week

            # Create internship data
            internship_data = {
                'student_id': str(current_user.id),
                'company_name': company_name,
                'project_name': project_name,
                'start_date': start_date,
                'end_date': end_date,
                'duration_months': round(duration_days / 30, 1),
                'semester': request.form.get('semester'), # Assuming semester is selected in the form
                'hours_per_week': hours_per_week,
                'total_hours': round(total_hours),
                'offer_letter_url': offer_letter_url,
                'completion_letter_url': completion_letter_url,
                'skills': skills,
                'academic_year': academic_year,
                'status': 'pending',
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }

            # Save to database
            result = current_app.db.internships.insert_one(internship_data)
            if result.inserted_id:
                flash('Internship details submitted successfully!', 'success')
                return redirect(url_for('student.internships'))
            else:
                flash('Error submitting internship details.', 'danger')

        except Exception as e:
            current_app.logger.error(f"Error in new_internship: {str(e)}")
            flash('Error submitting internship details. Please try again.', 'danger')

    return render_template('student/internship_form.html')

@student_bp.route('/activity/new', methods=['GET', 'POST'])
@login_required
def new_activity():
    if current_user.role != 'student':
        flash('Access denied.', 'error')
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        try:
            # Handle certificate upload
            certificate_url = None
            if 'certificate' in request.files:
                certificate = request.files['certificate']
                if certificate and certificate.filename:
                    if not allowed_file(certificate.filename):
                        flash('Certificate must be an image file (JPG, PNG, GIF).', 'danger')
                        return redirect(url_for('student.new_activity'))
                    
                    # Upload to Cloudinary
                    try:
                        certificate_url = upload_to_cloudinary(certificate, 'activities/certificates')
                        logging.info(f"Uploaded certificate to Cloudinary: {certificate_url}")
                    except Exception as e:
                        current_app.logger.error(f"Error uploading certificate to Cloudinary: {str(e)}")
                        flash('Error uploading certificate. Please try again.', 'danger')
                        return redirect(url_for('student.new_activity'))
            
            # Calculate total hours
            start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d')
            end_date = datetime.strptime(request.form.get('end_date'), '%Y-%m-%d')
            
            # Calculate duration in months (more accurate calculation)
            months_diff = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)
            days_in_last_month = end_date.day - start_date.day
            if days_in_last_month < 0:
                months_diff -= 1
                days_in_last_month += 30
            duration_months = months_diff + (days_in_last_month / 30.44)
            duration_months = round(duration_months, 1)
            
            hours_per_week = int(request.form.get('hours_per_week', 0))
            weeks = duration_months * 4.345  # Average weeks in a month
            total_hours = round(weeks * hours_per_week)
            
            # Get academic year from form (calculated by JavaScript)
            academic_year = request.form.get('academic_year')
            # If academic_year is not provided in the form, calculate it as fallback
            if not academic_year:
                month = start_date.month
                year = start_date.year
                if 1 <= month <= 5:
                    academic_year = f"{year-1}-{str(year)[-2:]}"
                else:
                    academic_year = f"{year}-{str(year+1)[-2:]}"
            current_app.logger.info(f"Using academic year: {academic_year}")

            # Create activity data
            activity_data = {
                'student_id': str(current_user.id),
                'activity_type': request.form.get('activity_type'),
                'title': request.form.get('title'),
                'description': request.form.get('description'),
                'start_date': start_date,
                'end_date': end_date,
                'duration_months': duration_months,
                'semester': request.form.get('semester'),
                'hours_per_week': hours_per_week,
                'total_hours': total_hours,
                'certificate_url': certificate_url,
                'skills': request.form.getlist('skills'),
                'academic_year': academic_year,
                'status': 'pending',
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
            
            # Save to database
            result = current_app.db.activities.insert_one(activity_data)
            if result.inserted_id:
                flash('Activity details submitted successfully!', 'success')
                return redirect(url_for('student.activities'))
            else:
                flash('Error submitting activity details.', 'danger')
                
        except Exception as e:
            current_app.logger.error(f"Error in new_activity: {str(e)}")
            flash('Error submitting activity details. Please try again.', 'danger')
    
    return render_template('student/activity_form.html')

@student_bp.route('/marksheet')
@login_required
def marksheet():
    if current_user.role != 'student':
        flash('Access denied.', 'error')
        return redirect(url_for('auth.login'))

    internships = Internship.get_by_student_id(current_app.db, current_user.id)
    activities = Activity.get_by_student_id(current_app.db, current_user.id)
    # Calculate total months for approved internships
    total_internship_months = 0
    for internship in internships:
        if getattr(internship, 'status', None) == 'approved' and internship.start_date and internship.end_date:
            try:
                start = internship.start_date
                end = internship.end_date
                start_dt = start if isinstance(start, datetime) else datetime.strptime(str(start).split()[0], '%Y-%m-%d')
                end_dt = end if isinstance(end, datetime) else datetime.strptime(str(end).split()[0], '%Y-%m-%d')
                rdelta = relativedelta(end_dt, start_dt)
                months = rdelta.years * 12 + rdelta.months
                if rdelta.days > 0:
                    months += 1
                if months < 0:
                    months = 0
                total_internship_months += months
            except Exception:
                pass
    # Calculate total months for approved activities
    total_activity_months = 0
    for activity in activities:
        if getattr(activity, 'status', None) == 'approved' and activity.start_date and activity.end_date:
            try:
                start = activity.start_date
                end = activity.end_date
                start_dt = start if isinstance(start, datetime) else datetime.strptime(str(start).split()[0], '%Y-%m-%d')
                end_dt = end if isinstance(end, datetime) else datetime.strptime(str(end).split()[0], '%Y-%m-%d')
                rdelta = relativedelta(end_dt, start_dt)
                months = rdelta.years * 12 + rdelta.months
                if rdelta.days > 0:
                    months += 1
                if months < 0:
                    months = 0
                total_activity_months += months
            except Exception:
                pass
    total_credit_points = 0
    for internship in internships:
        if hasattr(internship, 'total_hours') and internship.total_hours:
            total_credit_points += round(internship.total_hours / 40, 1)
    for activity in activities:
        if hasattr(activity, 'hours_per_week') and activity.hours_per_week:
            total_credit_points += round(activity.hours_per_week / 10, 1)
    return render_template('student/marksheet.html', internships=internships, activities=activities, total_credit_points=total_credit_points, total_internship_months=total_internship_months, total_activity_months=total_activity_months)

@student_bp.route('/internship/<internship_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_internship(internship_id):
    if current_user.role != 'student':
        flash('Access denied.', 'error')
        return redirect(url_for('auth.login'))
    
    internship = Internship.get_by_id(current_app.db, internship_id)
    
    # Check if internship exists and belongs to the current user
    if not internship or internship.student_id != str(current_user.id):
        flash('Internship not found.', 'error')
        return redirect(url_for('student.internships'))
    
    if request.method == 'POST':
        # Handle file uploads
        offer_letter = request.files.get('offer_letter')
        completion_letter = request.files.get('completion_letter')
        
        # Keep existing URLs if no new files are uploaded
        offer_letter_url = internship.offer_letter_url
        completion_letter_url = internship.completion_letter_url
        
        if offer_letter and allowed_file(offer_letter.filename):
            offer_letter_url = upload_to_cloudinary(offer_letter, 'internships/offer_letters')
            logging.info(f"Uploaded new offer letter to Cloudinary: {offer_letter_url}")
        
        if completion_letter and allowed_file(completion_letter.filename):
            completion_letter_url = upload_to_cloudinary(completion_letter, 'internships/completion_letters')
            logging.info(f"Uploaded new completion letter to Cloudinary: {completion_letter_url}")
        
        # Calculate total hours
        start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d')
        end_date = datetime.strptime(request.form.get('end_date'), '%Y-%m-%d')
        duration_months = (end_date.year - start_date.year) * 12 + end_date.month - start_date.month
        hours_per_week = int(request.form.get('hours_per_week', 0))
        total_hours = duration_months * 4 * hours_per_week
        
        # Update internship data (edit_internship)
        start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d')
        end_date = datetime.strptime(request.form.get('end_date'), '%Y-%m-%d')
        month = start_date.month
        year = start_date.year
        if 1 <= month <= 5:
            academic_year = f"{year-1}-{str(year)[-2:]}"
        else:
            academic_year = f"{year}-{str(year+1)[-2:]}"
        internship_data = {
            'company_name': request.form.get('company_name'),
            'project_name': request.form.get('project_name'),
            'start_date': start_date,
            'end_date': end_date,
            'duration_months': duration_months,
            'semester': request.form.get('semester'),
            'hours_per_week': hours_per_week,
            'total_hours': total_hours,
            'offer_letter_url': offer_letter_url,
            'completion_letter_url': completion_letter_url,
            'skills': request.form.getlist('skills'),
            'academic_year': academic_year,
            'status': 'pending'  # Reset status to pending when edited
        }
        
        internship.update(current_app.db, internship_data)
        flash('Internship updated successfully!', 'success')
        return redirect(url_for('student.internships'))
    
    return render_template('student/internship_form.html', internship=internship)

@student_bp.route('/internship/<internship_id>/delete', methods=['POST'])
@login_required
def delete_internship(internship_id):
    if current_user.role != 'student':
        flash('Access denied.', 'error')
        return redirect(url_for('auth.login'))
    
    internship = Internship.get_by_id(current_app.db, internship_id)
    
    # Check if internship exists and belongs to the current user
    if not internship or internship.student_id != str(current_user.id):
        flash('Internship not found.', 'error')
        return redirect(url_for('student.internships'))
    
    # Delete the internship record
    internship.delete(current_app.db)
    flash('Internship deleted successfully!', 'success')
    return redirect(url_for('student.internships'))

@student_bp.route('/activity/<activity_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_activity(activity_id):
    if current_user.role != 'student':
        flash('Access denied.', 'error')
        return redirect(url_for('auth.login'))
    
    activity = Activity.get_by_id(current_app.db, activity_id)
    
    # Check if activity exists and belongs to the current user
    if not activity or activity.student_id != str(current_user.id):
        flash('Activity not found.', 'error')
        return redirect(url_for('student.activities'))
    
    if request.method == 'POST':
        # Handle certificate upload
        certificate = request.files.get('certificate')
        
        # Keep existing URL if no new file is uploaded
        certificate_url = activity.certificate_url
        
        if certificate and allowed_file(certificate.filename):
            certificate_url = upload_to_cloudinary(certificate, 'activities/certificates')
            logging.info(f"Uploaded new certificate to Cloudinary: {certificate_url}")
        
        # Calculate total hours
        start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d')
        end_date = datetime.strptime(request.form.get('end_date'), '%Y-%m-%d')
        duration_months = (end_date.year - start_date.year) * 12 + end_date.month - start_date.month
        hours_per_week = int(request.form.get('hours_per_week', 0))
        total_hours = duration_months * 4 * hours_per_week
        
        # Calculate academic year
        month = start_date.month
        year = start_date.year
        if 1 <= month <= 5:
            academic_year = f"{year-1}-{str(year)[-2:]}"
        else:
            academic_year = f"{year}-{str(year+1)[-2:]}"

        # Update activity data
        activity_data = {
            'activity_type': request.form.get('activity_type'),
            'title': request.form.get('title'),
            'description': request.form.get('description'),
            'start_date': start_date,
            'end_date': end_date,
            'duration_months': duration_months,
            'semester': request.form.get('semester'),
            'hours_per_week': hours_per_week,
            'total_hours': total_hours,
            'certificate_url': certificate_url,
            'skills': request.form.getlist('skills'),
            'academic_year': academic_year,
            'status': 'pending'  # Reset status to pending when edited
        }
        
        activity.update(current_app.db, activity_data)
        flash('Activity updated successfully!', 'success')
        return redirect(url_for('student.activities'))
    
    return render_template('student/activity_form.html', activity=activity)

@student_bp.route('/activity/<activity_id>/delete', methods=['POST'])
@login_required
def delete_activity(activity_id):
    if current_user.role != 'student':
        flash('Access denied.', 'error')
        return redirect(url_for('auth.login'))
    
    activity = Activity.get_by_id(current_app.db, activity_id)
    
    # Check if activity exists and belongs to the current user
    if not activity or activity.student_id != str(current_user.id):
        flash('Activity not found.', 'error')
        return redirect(url_for('student.activities'))
    
    # Delete the activity record
    activity.delete(current_app.db)
    flash('Activity deleted successfully!', 'success')
    return redirect(url_for('student.activities'))

@student_bp.route('/marksheet/download')
@login_required
def download_marksheet():
    if current_user.role != 'student':
        flash('Access denied.', 'error')
        return redirect(url_for('index'))

    internships = Internship.get_by_student_id(current_app.db, current_user.id)
    activities = Activity.get_by_student_id(current_app.db, current_user.id)
    student = current_user
    if student.profile_image and not student.profile_image.startswith('http') and not os.path.exists(student.profile_image):
        student.profile_image = os.path.join('static', 'images', 'default_avatar.png')
    # Generate a student-specific URL for the QR code
    safe_name = student.full_name.strip().replace(' ', '-').lower()
    marksheet_url = f"{request.url_root.rstrip('/')}/student/{safe_name}"
    pdf_buffer = generate_custom_marksheet(student, internships, activities, marksheet_url)
    filename = f'marksheet_{safe_name}_{student.id}.pdf'
    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    )

# Certificate download route disabled for students - only available for admins
# @student_bp.route('/certificate/download')
# @login_required
# def download_certificate():
#     if current_user.role != 'student':
#         flash('Access denied.', 'error')
#         return redirect(url_for('index'))
#     
#     # Calculate total credit points
#     internships = Internship.get_by_student_id(current_app.db, current_user.id)
#     activities = Activity.get_by_student_id(current_app.db, current_user.id)
#     
#     total_credit_points = 0
#     for internship in internships:
#         if hasattr(internship, 'status') and internship.status == 'approved' and hasattr(internship, 'total_hours') and internship.total_hours:
#             total_credit_points += round(internship.total_hours / 40, 1)
#     
#     for activity in activities:
#         if hasattr(activity, 'status') and activity.status == 'approved' and hasattr(activity, 'hours_per_week') and activity.hours_per_week:
#             total_credit_points += round(activity.hours_per_week / 10, 1)
#     
#     # Generate the certificate
#     from utils.certificate_generator import generate_svg_certificate
#     pdf_buffer = generate_svg_certificate(current_user, total_credit_points)
#     
#     # Create filename
#     safe_name = current_user.full_name.strip().replace(' ', '-').lower()
#     filename = f'certificate_{safe_name}_{current_user.id}.pdf'
#     
#     return send_file(
#         pdf_buffer,
#         mimetype='application/pdf',
#         as_attachment=True,
#         download_name=filename
#     )

# Certificate email route disabled for students - only available for admins
# @student_bp.route('/certificate/send-email')
# @login_required
# def send_certificate_email():
#     if current_user.role != 'student':
#         flash('Access denied.', 'error')
#         return redirect(url_for('index'))
#     
#     try:
#         # Calculate total credit points
#         internships = Internship.get_by_student_id(current_app.db, current_user.id)
#         activities = Activity.get_by_student_id(current_app.db, current_user.id)
#         
#         total_credit_points = 0
#         for internship in internships:
#             if hasattr(internship, 'status') and internship.status == 'approved' and hasattr(internship, 'total_hours') and internship.total_hours:
#                 total_credit_points += round(internship.total_hours / 40, 1)
#         
#         for activity in activities:
#             if hasattr(activity, 'status') and activity.status == 'approved' and hasattr(activity, 'hours_per_week') and activity.hours_per_week:
#                 total_credit_points += round(activity.hours_per_week / 10, 1)
#         
#         # Generate certificate
#         from utils.certificate_generator import generate_svg_certificate
#         certificate_pdf = generate_svg_certificate(current_user, total_credit_points)
#         
#         # Send email with certificate
#         sender_email = os.getenv('SMTP_EMAIL')
#         sender_password = os.getenv('SMTP_PASSWORD')
#         
#         if not sender_email or not sender_password:
#             flash('SMTP credentials not configured. Cannot send email.', 'danger')
#             return redirect(url_for('student.marksheet'))
#         
#         # Create email
#         msg = MIMEMultipart()
#         msg['From'] = sender_email
#         msg['To'] = current_user.email
#         msg['Subject'] = "Internship Completion Certificate - Shah and Anchor College"
#         
#         # Email body
#         body = f"""Dear {current_user.full_name},

# Congratulations on successfully completing your internship requirements!

# We are pleased to present you with the attached Internship Completion Certificate. This certificate recognizes your dedication and hard work in earning {total_credit_points} credit points through your internship activities.

# Your commitment to professional development is commendable, and we wish you continued success in your future endeavors.

# Best regards,
# Shah and Anchor Kutchhi Engineering College
# Internship Program"""
#         
#         msg.attach(MIMEText(body, 'plain'))
#         
#         # Attach certificate
#         pdf_attachment = MIMEApplication(certificate_pdf.read())
#         safe_name = current_user.full_name.strip().replace(' ', '-').lower()
#         pdf_attachment.add_header('Content-Disposition', 'attachment', 
#                                  filename=f'certificate_{safe_name}.pdf')
#         msg.attach(pdf_attachment)
#         
#         # Send email
#         try:
#             server = smtplib.SMTP('smtp.gmail.com', 587)
#             server.starttls()
#             server.login(sender_email, sender_password)
#             server.send_message(msg)
#             server.quit()
#             flash('Certificate sent successfully to your email.', 'success')
#         except Exception as e:
#             current_app.logger.error(f"Error sending email: {str(e)}")
#             flash(f'Error sending email: {str(e)}', 'danger')
#         
#         return redirect(url_for('student.marksheet'))
#     
#     except Exception as e:
#         current_app.logger.error(f"Error generating certificate: {str(e)}")
#         flash(f'Error generating certificate: {str(e)}', 'danger')
#         return redirect(url_for('student.marksheet'))

@student_bp.route('/<student_slug>')
def public_marksheet(student_slug):
    student = User.get_by_slug(student_slug)
    if not student or student.role != 'student':
        return render_template('404.html'), 404
    from models.internship import Internship
    from models.activity import Activity
    from flask import current_app
    internships = Internship.get_by_student_id(current_app.db, student.id)
    activities = Activity.get_by_student_id(current_app.db, student.id)
    total_credit_points = 0
    for internship in internships:
        if hasattr(internship, 'total_hours') and internship.total_hours:
            total_credit_points += round(internship.total_hours / 40, 1)
    for activity in activities:
        if hasattr(activity, 'hours_per_week') and activity.hours_per_week:
            total_credit_points += round(activity.hours_per_week / 10, 1)
    return render_template('student/marksheet.html', internships=internships, activities=activities, total_credit_points=total_credit_points, current_user=student, minimal=True)