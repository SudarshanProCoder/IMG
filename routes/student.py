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
    
    # Get all internships and activities for the student
    internships = Internship.get_by_student_id(current_app.db, current_user.id)
    activities = Activity.get_by_student_id(current_app.db, current_user.id)
    
    # Calculate total credit points and process internships
    total_credit_points = 0
    processed_internships = []
    
    # Summary statistics
    summary = {
        'internships': {
            'total': 0,
            'approved': 0,
            'pending': 0,
            'rejected': 0,
            'total_hours': 0,
            'total_credit_points': 0,
            'avg_duration': 0,
            'avg_hours_per_week': 0
        },
        'activities': {
            'total': 0,
            'approved': 0,
            'pending': 0,
            'rejected': 0,
            'total_hours': 0,
            'total_credit_points': 0,
            'avg_duration': 0,
            'avg_hours_per_week': 0,
            'total_hours_per_week': 0
        }
    }
    
    # Process internships
    for internship in internships:
        # Update summary counts
        summary['internships']['total'] += 1
        summary['internships'][internship.status] += 1
        
        if internship.status == 'approved':
            try:
                # Calculate duration in months
                start_date = datetime.strptime(str(internship.start_date).split()[0], '%Y-%m-%d')
                end_date = datetime.strptime(str(internship.end_date).split()[0], '%Y-%m-%d')
                
                # Calculate duration in months (more accurate calculation)
                months_diff = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)
                days_in_last_month = end_date.day - start_date.day
                if days_in_last_month < 0:
                    months_diff -= 1
                    days_in_last_month += 30  # Approximate days in a month
                duration_months = months_diff + (days_in_last_month / 30.44)
                duration_months = round(duration_months, 1)
                
                # Calculate total hours based on duration and hours per week
                weeks = duration_months * 4.345  # Average weeks in a month
                total_hours = round(weeks * internship.hours_per_week)
                
                # Calculate credit points (1 credit point per 40 hours)
                credit_points = round(total_hours / 40, 1)
                total_credit_points += credit_points
                
                # Update summary statistics
                summary['internships']['total_hours'] += total_hours
                summary['internships']['total_credit_points'] += credit_points
                summary['internships']['avg_duration'] += duration_months
                summary['internships']['avg_hours_per_week'] += internship.hours_per_week
                
                # Add processed data to internship
                internship.duration_months = duration_months
                internship.total_hours = total_hours
                internship.credit_points = credit_points
                
            except (ValueError, AttributeError) as e:
                current_app.logger.error(f"Error processing internship dates: {str(e)}")
                # Use default values if calculation fails
                internship.duration_months = internship.duration_months if hasattr(internship, 'duration_months') else 0
                internship.total_hours = internship.total_hours if hasattr(internship, 'total_hours') else 0
                internship.credit_points = round(internship.total_hours / 40, 1) if hasattr(internship, 'total_hours') else 0
            
            processed_internships.append(internship)
    
    # Process activities
    processed_activities = []
    for activity in activities:
        # Update summary counts
        summary['activities']['total'] += 1
        summary['activities'][activity.status] += 1
        
        if activity.status == 'approved':
            try:
                # Calculate duration in months
                start_date = datetime.strptime(str(activity.start_date).split()[0], '%Y-%m-%d')
                end_date = datetime.strptime(str(activity.end_date).split()[0], '%Y-%m-%d')
                
                # Calculate duration in months
                months_diff = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)
                days_in_last_month = end_date.day - start_date.day
                if days_in_last_month < 0:
                    months_diff -= 1
                    days_in_last_month += 30
                duration_months = months_diff + (days_in_last_month / 30.44)
                duration_months = round(duration_months, 1)
                
                # Calculate total hours
                weeks = duration_months * 4.345
                total_hours = round(weeks * activity.hours_per_week)
                
                # Calculate credit points (1 credit point per 10 hours)
                credit_points = round(total_hours / 10, 1)
                total_credit_points += credit_points
                
                # Update summary statistics
                summary['activities']['total_hours'] += total_hours
                summary['activities']['total_credit_points'] += credit_points
                summary['activities']['avg_duration'] += duration_months
                summary['activities']['avg_hours_per_week'] += activity.hours_per_week
                summary['activities']['total_hours_per_week'] += activity.hours_per_week
                
                # Add processed data to activity
                activity.duration_months = duration_months
                activity.total_hours = total_hours
                activity.credit_points = credit_points
                
            except (ValueError, AttributeError) as e:
                current_app.logger.error(f"Error processing activity dates: {str(e)}")
                # Use default values if calculation fails
                activity.duration_months = activity.duration_months if hasattr(activity, 'duration_months') else 0
                activity.total_hours = activity.total_hours if hasattr(activity, 'total_hours') else 0
                activity.credit_points = round(activity.total_hours / 10, 1) if hasattr(activity, 'total_hours') else 0
            
            processed_activities.append(activity)
    
    # Calculate averages for internships
    if summary['internships']['approved'] > 0:
        summary['internships']['avg_duration'] = round(summary['internships']['avg_duration'] / summary['internships']['approved'], 1)
        summary['internships']['avg_hours_per_week'] = round(summary['internships']['avg_hours_per_week'] / summary['internships']['approved'], 1)
    
    # Calculate averages for activities
    if summary['activities']['approved'] > 0:
        summary['activities']['avg_duration'] = round(summary['activities']['avg_duration'] / summary['activities']['approved'], 1)
        summary['activities']['avg_hours_per_week'] = round(summary['activities']['avg_hours_per_week'] / summary['activities']['approved'], 1)
    
    # Calculate overall totals
    summary['total_hours'] = summary['internships']['total_hours'] + summary['activities']['total_hours']
    summary['total_credit_points'] = round(summary['internships']['total_credit_points'] + summary['activities']['total_credit_points'], 1)
    
    # Format data for PDF tables
    pdf_data = {
        'internships': [{
            'company_name': i.company_name,
            'project_name': i.project_name,
            'start_date': i.start_date.strftime('%Y-%m-%d'),
            'end_date': i.end_date.strftime('%Y-%m-%d'),
            'duration_months': i.duration_months,
            'hours_per_week': i.hours_per_week,
            'total_hours': i.total_hours,
            'credit_points': i.credit_points
        } for i in processed_internships],
        'activities': [{
            'title': a.title,
            'activity_type': a.activity_type,
            'start_date': a.start_date.strftime('%Y-%m-%d'),
            'end_date': a.end_date.strftime('%Y-%m-%d'),
            'duration_months': a.duration_months,
            'hours_per_week': a.hours_per_week,
            'total_hours': a.total_hours,
            'credit_points': a.credit_points
        } for a in processed_activities],
        'summary': {
            'total_internship_hours': summary['internships']['total_hours'],
            'total_activity_hours_per_week': summary['activities']['total_hours_per_week'],
            'total_credit_points': summary['total_credit_points']
        }
    }
    
    return render_template('student/marksheet.html',
                         internships=processed_internships,
                         activities=processed_activities,
                         total_credit_points=total_credit_points,
                         summary=summary,
                         pdf_data=pdf_data)

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

    # Get student's internships and activities
    internships = Internship.get_by_student_id(current_app.db, current_user.id)
    activities = Activity.get_by_student_id(current_app.db, current_user.id)

    # Calculate total credit points
    total_credit_points = sum(
        (i.total_hours / 40) for i in internships if i.status == 'approved'
    ) + sum(
        (a.hours_per_week / 10) for a in activities if a.status == 'approved'
    )
    total_credit_points = round(total_credit_points, 1)

    # Generate PDF
    pdf_buffer = generate_marksheet(current_user, internships, activities, total_credit_points)

    # Create a safe filename from the student's name
    safe_name = current_user.full_name.replace(' ', '_')
    filename = f'marksheet_{safe_name}_{current_user.id}.pdf'

    # Send the PDF file
    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    ) 