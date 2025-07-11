from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, send_file
from flask_login import login_required, current_user
from models.internship import Internship
from models.activity import Activity
import os
from werkzeug.utils import secure_filename
from datetime import datetime
import logging
from utils.pdf_generator import generate_marksheet
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
            joining_date = datetime.strptime(request.form.get('joining_date'), '%Y-%m-%d')
            semester = request.form.get('semester')
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
                'joining_date': joining_date,
                'duration_months': round(duration_days / 30, 1),
                'semester': semester,
                'hours_per_week': hours_per_week,
                'total_hours': round(total_hours),
                'offer_letter_url': offer_letter_url,
                'completion_letter_url': completion_letter_url,
                'skills': skills,
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
    total_credit_points = 0
    for internship in internships:
        if hasattr(internship, 'total_hours') and internship.total_hours:
            total_credit_points += round(internship.total_hours / 40, 1)
    for activity in activities:
        if hasattr(activity, 'hours_per_week') and activity.hours_per_week:
            total_credit_points += round(activity.hours_per_week / 10, 1)
    return render_template('student/marksheet.html', internships=internships, activities=activities, total_credit_points=total_credit_points)

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
        
        # Update internship data
        internship_data = {
            'company_name': request.form.get('company_name'),
            'project_name': request.form.get('project_name'),
            'start_date': start_date,
            'end_date': end_date,
            'duration_months': duration_months,
            'semester': request.form.get('semester'),
            'hours_per_week': hours_per_week,
            'total_hours': total_hours,
            'joining_date': datetime.strptime(request.form.get('joining_date'), '%Y-%m-%d'),
            'offer_letter_url': offer_letter_url,
            'completion_letter_url': completion_letter_url,
            'skills': request.form.getlist('skills'),
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
    # Ensure profile image path is correct (absolute or URL)
    student = current_user
    if student.profile_image and not student.profile_image.startswith('http') and not os.path.exists(student.profile_image):
        # If the image is not a URL and not a local file, use default
        student.profile_image = os.path.join('static', 'images', 'default_avatar.png')
    pdf_buffer = generate_internship_pdf(student, internships)
    safe_name = student.full_name.replace(' ', '_')
    filename = f'marksheet_{safe_name}_{student.id}.pdf'
    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    ) 