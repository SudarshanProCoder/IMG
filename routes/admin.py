from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, send_from_directory, jsonify, Response
from flask_login import login_required, current_user
from models.user import User
from models.internship import Internship
from models.activity import Activity
from bson.objectid import ObjectId
from config.database import db
import os
from datetime import datetime
import csv
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from utils.certificate_generator import generate_internship_certificate

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/students/<student_id>/send_certificate', methods=['POST'])
@login_required
def send_certificate(student_id):
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('main.index'))
    
    try:
        # Validate student_id format
        if not ObjectId.is_valid(student_id):
            flash('Invalid student ID format.', 'danger')
            return redirect(url_for('admin.students'))
        
        # Get student details
        student_data = db.users.find_one({'_id': ObjectId(student_id), 'role': 'student'})
        if not student_data:
            flash('Student not found.', 'danger')
            return redirect(url_for('admin.students'))
        
        # Create a User object from the data
        student = User(student_data)
        
        # Get approved internships
        internships = list(db.internships.find({'student_id': str(student_id), 'status': 'approved'}))
        
        # Calculate total credit points
        total_hours = sum(i.get('total_hours', 0) for i in internships)
        total_credit_points = round(total_hours / 40, 2) if total_hours > 0 else 0
        
        # Generate certificate
        certificate_pdf = generate_internship_certificate(student, total_credit_points)
        
        # Send email with certificate
        sender_email = os.getenv('SMTP_EMAIL')
        sender_password = os.getenv('SMTP_PASSWORD')
        
        if not sender_email or not sender_password:
            flash('SMTP credentials not configured. Cannot send email.', 'danger')
            return redirect(url_for('admin.view_student', student_id=student_id))
        
        # Create email
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = student.email
        msg['Subject'] = "Internship Completion Certificate - Shah and Anchor College"
        
        # Email body
        body = f"""Dear {student.full_name},

Congratulations on successfully completing your internship requirements!

We are pleased to present you with the attached Internship Completion Certificate. This certificate recognizes your dedication and hard work in earning {total_credit_points} credit points through your internship activities.

Your commitment to professional development is commendable, and we wish you continued success in your future endeavors.

Best regards,
Shah and Anchor Kutchhi Engineering College
Internship Program"""
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Attach certificate
        pdf_attachment = MIMEApplication(certificate_pdf.read())
        pdf_attachment.add_header('Content-Disposition', 'attachment', filename='internship_certificate.pdf')
        msg.attach(pdf_attachment)
        
        # Send email
        try:
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
            server.quit()
            flash('Certificate sent successfully to student email.', 'success')
        except Exception as e:
            current_app.logger.error(f"Error sending email: {str(e)}")
            flash(f'Error sending email: {str(e)}', 'danger')
        
        return redirect(url_for('admin.view_student', student_id=student_id))
    
    except Exception as e:
        current_app.logger.error(f"Error generating certificate: {str(e)}")
        flash(f'Error generating certificate: {str(e)}', 'danger')
        return redirect(url_for('admin.view_student', student_id=student_id))

@admin_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.role != 'admin':
        flash('Access denied.', 'error')
        return redirect(url_for('auth.login'))
    
    try:
        # Get statistics
        total_students = db.users.count_documents({'role': 'student'})
        total_mentors = db.users.count_documents({'role': 'mentor'})
        total_internships = db.internships.count_documents({})
        total_activities = db.activities.count_documents({})
        
        # Get pending approvals
        pending_internships = db.internships.count_documents({'status': 'pending'})
        pending_activities = db.activities.count_documents({'status': 'pending'})
        
        # Get recent activities
        recent_internships = list(db.internships.find().sort('created_at', -1).limit(5))
        recent_activities = list(db.activities.find().sort('created_at', -1).limit(5))
        
        # Convert ObjectId to string for JSON serialization
        for internship in recent_internships:
            internship['_id'] = str(internship['_id'])
            if 'created_at' in internship:
                internship['created_at'] = internship['created_at'].strftime('%Y-%m-%d %H:%M:%S')
        
        for activity in recent_activities:
            activity['_id'] = str(activity['_id'])
            if 'created_at' in activity:
                activity['created_at'] = activity['created_at'].strftime('%Y-%m-%d %H:%M:%S')
        
        return render_template('admin/dashboard.html',
                            total_students=total_students,
                            total_mentors=total_mentors,
                            total_internships=total_internships,
                            total_activities=total_activities,
                            pending_internships=pending_internships,
                            pending_activities=pending_activities,
                            recent_internships=recent_internships,
                            recent_activities=recent_activities)
    except Exception as e:
        flash(f'Error loading dashboard: {str(e)}', 'error')
        return redirect(url_for('auth.login'))

@admin_bp.route('/dashboard/data/trends')
@login_required
def dashboard_trends_data():
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    from datetime import datetime, timedelta
    now = datetime.now()
    # Get the first day of each of the last 12 months
    months = [(now.replace(day=1) - timedelta(days=30*i)) for i in reversed(range(12))]
    month_labels = [d.strftime('%b %Y') for d in months]
    # MongoDB aggregation for internships
    internship_pipeline = [
        {"$match": {"created_at": {"$gte": months[0]}}},
        {"$group": {
            "_id": {"year": {"$year": "$created_at"}, "month": {"$month": "$created_at"}},
            "count": {"$sum": 1}
        }}
    ]
    activity_pipeline = [
        {"$match": {"created_at": {"$gte": months[0]}}},
        {"$group": {
            "_id": {"year": {"$year": "$created_at"}, "month": {"$month": "$created_at"}},
            "count": {"$sum": 1}
        }}
    ]
    internship_results = list(db.internships.aggregate(internship_pipeline))
    activity_results = list(db.activities.aggregate(activity_pipeline))
    # Build a map {(year, month): count}
    internship_map = { (r['_id']['year'], r['_id']['month']): r['count'] for r in internship_results }
    activity_map = { (r['_id']['year'], r['_id']['month']): r['count'] for r in activity_results }
    internship_counts = []
    activity_counts = []
    for d in months:
        y, m = d.year, d.month
        internship_counts.append(internship_map.get((y, m), 0))
        activity_counts.append(activity_map.get((y, m), 0))
    return jsonify({'labels': month_labels, 'internships': internship_counts, 'activities': activity_counts})

@admin_bp.route('/dashboard/data/activity-types')
@login_required
def dashboard_activity_types_data():
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    pipeline = [
        {'$group': {'_id': '$activity_type', 'count': {'$sum': 1}}}
    ]
    results = list(db.activities.aggregate(pipeline))
    labels = [r['_id'] or 'Other' for r in results]
    data = [r['count'] for r in results]
    return jsonify({'labels': labels, 'data': data})

@admin_bp.route('/dashboard/data/internship-status')
@login_required
def dashboard_internship_status_data():
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    statuses = ['approved', 'pending', 'rejected']
    data = [db.internships.count_documents({'status': s}) for s in statuses]
    return jsonify({'labels': [s.title() for s in statuses], 'data': data})

@admin_bp.route('/dashboard/data/activity-status')
@login_required
def dashboard_activity_status_data():
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    statuses = ['approved', 'pending', 'rejected']
    data = [db.activities.count_documents({'status': s}) for s in statuses]
    return jsonify({'labels': [s.title() for s in statuses], 'data': data})

@admin_bp.route('/students')
@login_required
def students():
    if current_user.role != 'admin':
        flash('Access denied.', 'error')
        return redirect(url_for('auth.login'))
    
    try:
        department = request.args.get('department')
        year = request.args.get('year')
        academic_year = request.args.get('academic_year')
        semester = request.args.get('semester')
        search_query = request.args.get('search', '').strip()
        
        # Base query for students
        query = {'role': 'student'}
        if department:
            query['department'] = department
        if year:
            query['year'] = year
        if semester:
            query['semester'] = semester
        
        students = []
        for student_data in db.users.find(query):
            student = User(student_data)
            
            # Get internships and activities for each student
            if academic_year:
                # Filter internships and activities by academic year
                student.internships = list(db.internships.find({
                    'student_id': str(student.id),
                    'academic_year': academic_year
                }))
                student.activities = list(db.activities.find({
                    'student_id': str(student.id),
                    'academic_year': academic_year
                }))
                
                # Only add student if they have matching internships or activities
                if not student.internships and not student.activities:
                    continue
            else:
                # Get all internships and activities
                student.internships = list(db.internships.find({'student_id': str(student.id)}))
                student.activities = list(db.activities.find({'student_id': str(student.id)}))
            
            # Apply search filter if search query exists
            if search_query:
                search_query = search_query.lower()
                if (search_query in student.full_name.lower() or
                    search_query in student.email.lower() or
                    search_query in student.registration_number.lower()):
                    students.append(student)
            else:
                students.append(student)
        
        # Get unique values for filters
        departments = list(db.users.distinct('department', {'role': 'student', 'department': {'$exists': True, '$ne': None, '$ne': 'None'}}))
        years = list(db.users.distinct('year', {'role': 'student', 'year': {'$exists': True, '$ne': None, '$ne': 'None'}}))
        
        # Get academic years from both internships and activities
        internship_academic_years = list(db.internships.distinct('academic_year', {'academic_year': {'$exists': True, '$ne': None, '$ne': 'None'}}))
        activity_academic_years = list(db.activities.distinct('academic_year', {'academic_year': {'$exists': True, '$ne': None, '$ne': 'None'}}))
        academic_years = sorted(list(set(internship_academic_years + activity_academic_years)))
        
        semesters = list(db.users.distinct('semester', {'role': 'student', 'semester': {'$exists': True, '$ne': None, '$ne': 'None'}}))
        
        # Ensure we're passing the correct filter values (not None if they're empty strings)
        selected_department = department if department else None
        selected_year = year if year else None
        selected_academic_year = academic_year if academic_year else None
        selected_semester = semester if semester else None
        
        return render_template('admin/students.html',
                            students=students,
                            departments=departments,
                            years=years,
                            academic_years=academic_years,
                            semesters=semesters,
                            selected_department=selected_department,
                            selected_year=selected_year,
                            selected_academic_year=selected_academic_year,
                            selected_semester=selected_semester,
                            search_query=search_query)
    except Exception as e:
        flash(f'Error loading students: {str(e)}', 'error')
        return redirect(url_for('admin.dashboard'))

@admin_bp.route('/students/<student_id>')
@login_required
def view_student(student_id):
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('main.index'))

    try:
        # Check database connection
        if db is None:
            current_app.logger.error("Database connection not available")
            flash('Database connection error. Please try again.', 'danger')
            return redirect(url_for('admin.students'))

        # Validate student_id format
        if not ObjectId.is_valid(student_id):
            current_app.logger.error(f"Invalid student_id format: {student_id}")
            flash('Invalid student ID format.', 'danger')
            return redirect(url_for('admin.students'))

        # Get student details directly from database
        try:
            student_data = db.users.find_one({'_id': ObjectId(student_id), 'role': 'student'})
            if not student_data:
                current_app.logger.error(f"Student not found with ID: {student_id}")
                flash('Student not found.', 'danger')
                return redirect(url_for('admin.students'))
        except Exception as db_error:
            current_app.logger.error(f"Database error while fetching student: {str(db_error)}")
            flash('Error accessing student data. Please try again.', 'danger')
            return redirect(url_for('admin.students'))

        # Convert ObjectId to string
        student_data['_id'] = str(student_data['_id'])
        
        # Ensure all required student fields exist with defaults
        student_data.setdefault('name', 'N/A')
        student_data.setdefault('email', 'N/A')
        student_data.setdefault('branch', 'N/A')
        student_data.setdefault('year', 'N/A')
        student_data.setdefault('roll_number', 'N/A')
        student_data.setdefault('phone', 'N/A')
        student_data.setdefault('address', 'N/A')
        student_data.setdefault('gender', 'N/A')
        student_data.setdefault('date_of_birth', 'N/A')
        student_data.setdefault('profile_image', url_for('static', filename='images/default_avatar.png'))
        
        # Format dates if they exist
        for date_field in ['created_at', 'updated_at', 'date_of_birth']:
            if date_field in student_data and student_data[date_field]:
                if isinstance(student_data[date_field], datetime):
                    student_data[date_field] = student_data[date_field].strftime('%Y-%m-%d')
                else:
                    student_data[date_field] = 'N/A'

        # Get internships and activities
        try:
            internships = list(db.internships.find({'student_id': str(student_id)}).sort('created_at', -1))
            activities = list(db.activities.find({'student_id': str(student_id)}).sort('created_at', -1))
        except Exception as e:
            current_app.logger.error(f"Error fetching internships/activities: {str(e)}")
            internships = []
            activities = []

        # Calculate statistics
        internship_count = len(internships)
        activity_count = len(activities)
        approved_internships = sum(1 for i in internships if i.get('status') == 'approved')
        approved_activities = sum(1 for a in activities if a.get('status') == 'approved')
        
        # Calculate total credit points (1 credit point per 40 hours)
        total_hours = sum(i.get('total_hours', 0) for i in internships if i.get('status') == 'approved')
        total_credit_points = round(total_hours / 40, 2) if total_hours > 0 else 0

        # Format dates and convert ObjectIds to strings for internships
        for internship in internships:
            try:
                internship['_id'] = str(internship['_id'])
                # Format dates
                for date_field in ['created_at', 'start_date', 'end_date', 'joining_date']:
                    if date_field in internship and internship[date_field]:
                        if isinstance(internship[date_field], datetime):
                            internship[date_field] = internship[date_field].strftime('%Y-%m-%d')
                        else:
                            internship[date_field] = 'N/A'
                
                # Ensure all fields exist with proper defaults
                internship.setdefault('company_name', 'N/A')
                internship.setdefault('project_name', 'N/A')
                internship.setdefault('role', 'N/A')
                internship.setdefault('total_hours', 0)
                internship.setdefault('hours_per_week', 0)
                internship.setdefault('skills', [])
                internship.setdefault('offer_letter_url', '')
                internship.setdefault('completion_letter_url', '')
                internship.setdefault('status', 'pending')
                internship.setdefault('semester', 'N/A')
                internship.setdefault('description', 'No description provided')
            except Exception as e:
                current_app.logger.error(f"Error processing internship: {str(e)}")
                continue

        # Format dates and convert ObjectIds to strings for activities
        for activity in activities:
            try:
                activity['_id'] = str(activity['_id'])
                # Format dates
                for date_field in ['created_at', 'date']:
                    if date_field in activity and activity[date_field]:
                        if isinstance(activity[date_field], datetime):
                            activity[date_field] = activity[date_field].strftime('%Y-%m-%d')
                        else:
                            activity[date_field] = 'N/A'
                
                # Ensure all fields exist with proper defaults
                activity.setdefault('title', 'N/A')
                activity.setdefault('activity_type', 'N/A')
                activity.setdefault('description', 'No description provided')
                activity.setdefault('hours_spent', 0)
                activity.setdefault('venue', 'N/A')
                activity.setdefault('organizer', 'N/A')
                activity.setdefault('certificate_url', '')
                activity.setdefault('status', 'pending')
                activity.setdefault('semester', 'N/A')
            except Exception as e:
                current_app.logger.error(f"Error processing activity: {str(e)}")
                continue

        # Debug output for diagnosis
        current_app.logger.info(f"Prepared data for student {student_id}")
        current_app.logger.debug(f"Student data: {student_data}")
        current_app.logger.debug(f"Internships: {internships}")
        current_app.logger.debug(f"Activities: {activities}")
        print('Student:', student_data)
        print('Internships:', internships)
        print('Activities:', activities)

        return render_template('admin/student_profile.html',
                            student=student_data,
                            internships=internships,
                            activities=activities,
                            internship_count=internship_count,
                            activity_count=activity_count,
                            approved_internships=approved_internships,
                            approved_activities=approved_activities,
                            total_credit_points=total_credit_points)
    except Exception as e:
        import traceback
        current_app.logger.error(f"Error loading student profile: {str(e)}")
        current_app.logger.error(f"Traceback: {traceback.format_exc()}")
        print('Error loading student profile:', str(e))
        print(traceback.format_exc())
        # Fallback: render a minimal template for debugging
        try:
            return render_template('admin/student_profile.html', student={}, internships=[], activities=[], internship_count=0, activity_count=0, approved_internships=0, approved_activities=0, error=str(e))
        except Exception as te:
            return f"Critical template error: {str(te)}\nOriginal error: {str(e)}"

@admin_bp.route('/internships/<internship_id>/approve')
@login_required
def approve_internship(internship_id):
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('main.index'))

    try:
        internship = db.internships.find_one({'_id': ObjectId(internship_id)})
        if not internship:
            flash('Internship not found.', 'danger')
            return redirect(url_for('admin.students'))

        # Update internship status
        db.internships.update_one(
            {'_id': ObjectId(internship_id)},
            {
                '$set': {
                    'status': 'approved',
                    'updated_at': datetime.now()
                }
            }
        )

        flash('Internship approved successfully!', 'success')
        return redirect(url_for('admin.view_student', student_id=internship['student_id']))

    except Exception as e:
        current_app.logger.error(f"Error approving internship: {str(e)}")
        flash('Error approving internship.', 'danger')
        return redirect(url_for('admin.students'))

@admin_bp.route('/internships/<internship_id>/reject')
@login_required
def reject_internship(internship_id):
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('main.index'))

    try:
        internship = db.internships.find_one({'_id': ObjectId(internship_id)})
        if not internship:
            flash('Internship not found.', 'danger')
            return redirect(url_for('admin.students'))

        # Update internship status
        db.internships.update_one(
            {'_id': ObjectId(internship_id)},
            {
                '$set': {
                    'status': 'rejected',
                    'updated_at': datetime.now()
                }
            }
        )

        flash('Internship rejected successfully!', 'success')
        return redirect(url_for('admin.view_student', student_id=internship['student_id']))

    except Exception as e:
        current_app.logger.error(f"Error rejecting internship: {str(e)}")
        flash('Error rejecting internship.', 'danger')
        return redirect(url_for('admin.students'))

@admin_bp.route('/activity/<activity_id>/approve')
@login_required
def approve_activity(activity_id):
    if current_user.role != 'admin':
        flash('Access denied.', 'error')
        return redirect(url_for('auth.login'))
    
    try:
        activity = db.activities.find_one({'_id': ObjectId(activity_id)})
        if not activity:
            flash('Activity not found.', 'error')
            return redirect(url_for('admin.dashboard'))
        
        db.activities.update_one(
            {'_id': ObjectId(activity_id)},
            {'$set': {'status': 'approved'}}
        )
        flash('Activity approved successfully!', 'success')
        return redirect(url_for('admin.view_student', student_id=activity['student_id']))
    except Exception as e:
        flash(f'Error approving activity: {str(e)}', 'error')
        return redirect(url_for('admin.dashboard'))

@admin_bp.route('/activity/<activity_id>/reject')
@login_required
def reject_activity(activity_id):
    if current_user.role != 'admin':
        flash('Access denied.', 'error')
        return redirect(url_for('auth.login'))
    
    try:
        activity = db.activities.find_one({'_id': ObjectId(activity_id)})
        if not activity:
            flash('Activity not found.', 'error')
            return redirect(url_for('admin.dashboard'))
        
        db.activities.update_one(
            {'_id': ObjectId(activity_id)},
            {'$set': {'status': 'rejected'}}
        )
        flash('Activity rejected.', 'success')
        return redirect(url_for('admin.view_student', student_id=activity['student_id']))
    except Exception as e:
        flash(f'Error rejecting activity: {str(e)}', 'error')
        return redirect(url_for('admin.dashboard'))

@admin_bp.route('/mentors')
@login_required
def mentors():
    if current_user.role != 'admin':
        flash('Access denied.', 'error')
        return redirect(url_for('auth.login'))
    
    try:
        # Get filter parameters
        department = request.args.get('department')
        search_query = request.args.get('search', '').strip()
        
        # Build query
        query = {'role': 'mentor'}
        if department:
            query['department'] = department
        
        # Get all mentors from the database
        mentors_data = list(db.users.find(query))
        
        # Apply search filter if search query exists
        if search_query:
            search_query = search_query.lower()
            mentors_data = [
                mentor for mentor in mentors_data
                if search_query in mentor.get('full_name', '').lower() or
                   search_query in mentor.get('email', '').lower()
            ]
        
        mentors = [User(mentor_data) for mentor_data in mentors_data]
        
        # Get unique departments for filter
        departments = list(db.users.distinct('department', {'role': 'mentor'}))
        
        return render_template('admin/mentors.html',
                            mentors=mentors,
                            departments=departments,
                            selected_department=department,
                            search_query=search_query)
    except Exception as e:
        flash(f'Error loading mentors: {str(e)}', 'error')
        return redirect(url_for('admin.dashboard'))

@admin_bp.route('/mentor/<mentor_id>/approve', methods=['POST'])
@login_required
def approve_mentor(mentor_id):
    if current_user.role != 'admin':
        flash('Access denied.', 'error')
        return redirect(url_for('auth.login'))
    
    mentor = User.get_by_id(current_app.db, mentor_id)
    if mentor and mentor.role == 'mentor':
        mentor.update(current_app.db, {'is_approved': True})
        flash('Mentor approved successfully!', 'success')
    else:
        flash('Mentor not found.', 'error')
    
    return redirect(url_for('admin.mentors'))

@admin_bp.route('/mentor/<mentor_id>/delete', methods=['POST'])
@login_required
def delete_mentor(mentor_id):
    if current_user.role != 'admin':
        flash('Access denied.', 'error')
        return redirect(url_for('admin.mentors'))
    try:
        mentor = db.users.find_one({'_id': ObjectId(mentor_id), 'role': 'mentor'})
        if not mentor:
            flash('Mentor not found.', 'error')
            return redirect(url_for('admin.mentors'))
        db.users.delete_one({'_id': ObjectId(mentor_id)})
        flash('Mentor deleted successfully.', 'success')
    except Exception as e:
        flash(f'Error deleting mentor: {str(e)}', 'error')
    return redirect(url_for('admin.mentors'))

@admin_bp.route('/uploads/<path:filename>')
@login_required
def serve_pdf(filename):
    """Serve PDF files from the uploads directory."""
    if current_user.role != 'admin':
        flash('Access denied.', 'error')
        return redirect(url_for('auth.login'))
    
    try:
        return send_from_directory(
            os.path.join(current_app.static_folder, 'uploads'),
            filename,
            mimetype='application/pdf'
        )
    except Exception as e:
        flash(f'Error serving PDF: {str(e)}', 'error')
        return redirect(url_for('admin.dashboard')) 

@admin_bp.route('/export-csv')
@login_required
def export_csv():
    if current_user.role != 'admin':
        flash('Access denied.', 'error')
        return redirect(url_for('auth.login'))
    # Get all students and mentors
    users = list(db.users.find({'role': {'$in': ['student', 'mentor']}}))
    if not users:
        flash('No data to export.', 'warning')
        return redirect(url_for('admin.dashboard'))
    # Get all unique keys for CSV header
    all_keys = set()
    for user in users:
        all_keys.update(user.keys())
    all_keys = sorted(all_keys)
    # Write CSV to memory
    def generate():
        yield ','.join(all_keys) + '\n'
        for user in users:
            row = []
            for key in all_keys:
                val = user.get(key, '')
                # Convert lists/dicts to string
                if isinstance(val, (list, dict)):
                    val = str(val)
                # Convert ObjectId to string
                if hasattr(val, 'hex') or hasattr(val, 'binary'):
                    val = str(val)
                # Escape commas and newlines
                if isinstance(val, str):
                    val = val.replace(',', ';').replace('\n', ' ')
                row.append(f'"{val}"')
            yield ','.join(row) + '\n'
    return Response(generate(), mimetype='text/csv', headers={
        'Content-Disposition': 'attachment; filename=students_mentors_export.csv'
    }) 

@admin_bp.route('/export-students-csv')
@login_required
def export_students_csv():
    if current_user.role != 'admin':
        flash('Access denied.', 'error')
        return redirect(url_for('auth.login'))
    users = list(db.users.find({'role': 'student'}))
    if not users:
        flash('No student data to export.', 'warning')
        return redirect(url_for('admin.dashboard'))
    all_keys = set()
    for user in users:
        all_keys.update(user.keys())
    all_keys = sorted(all_keys)
    def generate():
        yield ','.join(all_keys) + '\n'
        for user in users:
            row = []
            for key in all_keys:
                val = user.get(key, '')
                if isinstance(val, (list, dict)):
                    val = str(val)
                if hasattr(val, 'hex') or hasattr(val, 'binary'):
                    val = str(val)
                if isinstance(val, str):
                    val = val.replace(',', ';').replace('\n', ' ')
                row.append(f'"{val}"')
            yield ','.join(row) + '\n'
    return Response(generate(), mimetype='text/csv', headers={
        'Content-Disposition': 'attachment; filename=students_export.csv'
    })

@admin_bp.route('/export-mentors-csv')
@login_required
def export_mentors_csv():
    if current_user.role != 'admin':
        flash('Access denied.', 'error')
        return redirect(url_for('auth.login'))
    users = list(db.users.find({'role': 'mentor'}))
    if not users:
        flash('No mentor data to export.', 'warning')
        return redirect(url_for('admin.dashboard'))
    all_keys = set()
    for user in users:
        all_keys.update(user.keys())
    all_keys = sorted(all_keys)
    def generate():
        yield ','.join(all_keys) + '\n'
        for user in users:
            row = []
            for key in all_keys:
                val = user.get(key, '')
                if isinstance(val, (list, dict)):
                    val = str(val)
                if hasattr(val, 'hex') or hasattr(val, 'binary'):
                    val = str(val)
                if isinstance(val, str):
                    val = val.replace(',', ';').replace('\n', ' ')
                row.append(f'"{val}"')
            yield ','.join(row) + '\n'
    return Response(generate(), mimetype='text/csv', headers={
        'Content-Disposition': 'attachment; filename=mentors_export.csv'
    })

@admin_bp.route('/certificate-management')
@login_required
def certificate_management():
    if current_user.role != 'admin':
        flash('Access denied.', 'error')
        return redirect(url_for('admin.dashboard'))
    
    try:
        # Check database connection
        if db is None:
            flash('Database connection not available. Please try again.', 'danger')
            return redirect(url_for('admin.dashboard'))
        
        current_app.logger.info("Starting certificate management route")
        
        # Get unique departments and academic years for filtering
        try:
            departments = list(db.users.distinct('department', {'role': 'student', 'department': {'$exists': True, '$ne': None}}))
            current_app.logger.info(f"Found {len(departments)} departments")
        except Exception as e:
            current_app.logger.error(f"Error getting departments: {str(e)}")
            departments = []
        
        try:
            # Get academic years from internships table (this is more reliable)
            academic_years = list(db.internships.distinct('academic_year', {'academic_year': {'$exists': True, '$ne': None}}))
            current_app.logger.info(f"Found {len(academic_years)} academic years from internships")
        except Exception as e:
            current_app.logger.error(f"Error getting academic years from internships: {str(e)}")
            academic_years = []
        
        # Remove the user_years fallback - only use academic_year from internships
        all_academic_years = sorted(academic_years)
        current_app.logger.info(f"Academic years from internships: {all_academic_years}")
        
        # Get filter parameters
        selected_department = request.args.get('department', '')
        selected_year = request.args.get('academic_year', '')
        current_app.logger.info(f"Filters: department={selected_department}, academic_year={selected_year}")
        
        # Build filter query for students
        filter_query = {'role': 'student'}
        if selected_department:
            filter_query['department'] = selected_department
        
        # Get students based on filters
        try:
            students = list(db.users.find(filter_query))
            current_app.logger.info(f"Found {len(students)} students")
        except Exception as e:
            current_app.logger.error(f"Error getting students: {str(e)}")
            students = []
        
        # Count eligible students (with approved internships)
        eligible_count = 0
        total_credit_points = 0.0
        eligible_students = {}
        
        for i, student_data in enumerate(students):
            try:
                current_app.logger.debug(f"Processing student {i+1}/{len(students)}: {student_data.get('_id', 'Unknown')}")
                
                # Convert ObjectId to string for consistent key handling
                student_id = str(student_data['_id'])
                current_app.logger.debug(f"Student ID converted to string: {student_id}")
                
                # Get approved internships for the student
                internship_query = {'student_id': student_id, 'status': 'approved'}
                
                # If academic year is selected, filter internships by that year
                if selected_year:
                    internship_query['academic_year'] = selected_year
                
                try:
                    internships = list(db.internships.find(internship_query))
                    current_app.logger.debug(f"Found {len(internships)} approved internships for student {student_id}")
                except Exception as e:
                    current_app.logger.error(f"Error getting internships for student {student_id}: {str(e)}")
                    internships = []
                
                if internships:
                    eligible_count += 1
                    # Calculate total hours from approved internships
                    total_hours = sum(i.get('total_hours', 0) for i in internships)
                    credit_points = round(total_hours / 40, 2) if total_hours > 0 else 0.0
                    total_credit_points += credit_points
                    eligible_students[student_id] = credit_points
                    current_app.logger.debug(f"Student {student_id} eligible with {credit_points} credit points")
                else:
                    # Student has no approved internships
                    eligible_students[student_id] = 0.0
                    current_app.logger.debug(f"Student {student_id} not eligible")
                    
            except Exception as e:
                current_app.logger.error(f"Error processing student {i+1}: {str(e)}")
                # Set default values for this student
                try:
                    student_id = str(student_data.get('_id', 'unknown'))
                except:
                    student_id = f'unknown_{i}'
                eligible_students[student_id] = 0.0
                continue
        
        # Round total credit points to 2 decimal places
        total_credit_points = round(total_credit_points, 2)
        
        # Convert student ObjectIds to strings for template compatibility and ensure profile_image
        for i, student in enumerate(students):
            try:
                student['_id'] = str(student['_id'])
                # Ensure profile_image field exists
                if 'profile_image' not in student or not student['profile_image']:
                    student['profile_image'] = None  # Will use default image in template
                current_app.logger.debug(f"Converted student {i+1} ID to string: {student['_id']}")
            except Exception as e:
                current_app.logger.error(f"Error converting student {i+1} ID: {str(e)}")
                student['_id'] = f'unknown_{i}'
                student['profile_image'] = None
        
        # Debug logging
        current_app.logger.info(f"Certificate management loaded: {len(students)} students, {eligible_count} eligible")
        current_app.logger.debug(f"Eligible students keys: {list(eligible_students.keys())[:5]}...")
        current_app.logger.debug(f"Sample student IDs: {[str(s.get('_id', 'unknown'))[:10] for s in students[:3]]}")
        
        return render_template('admin/certificate_management.html',
                             departments=departments,
                             academic_years=all_academic_years,
                             selected_department=selected_department,
                             selected_year=selected_year,
                             students=students,
                             eligible_count=eligible_count,
                             total_credit_points=total_credit_points,
                             eligible_students=eligible_students)
                             
    except Exception as e:
        current_app.logger.error(f"Error in certificate_management: {str(e)}")
        import traceback
        current_app.logger.error(f"Traceback: {traceback.format_exc()}")
        flash(f'Error loading certificate management: {str(e)}', 'danger')
        return redirect(url_for('admin.dashboard'))

@admin_bp.route('/send-certificates', methods=['POST'])
@login_required
def send_certificates():
    if current_user.role != 'admin':
        flash('Access denied.', 'error')
        return redirect(url_for('admin.certificate_management'))
    
    try:
        # Get filter parameters
        department = request.form.get('department', '')
        academic_year = request.form.get('academic_year', '')
        
        current_app.logger.info(f"Sending certificates for department: {department}, academic_year: {academic_year}")
        
        # Build filter query
        filter_query = {'role': 'student'}
        if department:
            filter_query['department'] = department
        
        # Get students based on filters
        students = list(db.users.find(filter_query))
        
        if not students:
            flash('No students found with the selected filters.', 'warning')
            return redirect(url_for('admin.certificate_management'))
        
        # Send certificates to each student
        sent_count = 0
        failed_count = 0
        
        for student_data in students:
            try:
                student = User(student_data)
                student_id = str(student_data['_id'])
                
                # Get approved internships for the student
                internship_query = {'student_id': student_id, 'status': 'approved'}
                
                # If academic year is selected, filter internships by that year
                if academic_year:
                    internship_query['academic_year'] = academic_year
                
                internships = list(db.internships.find(internship_query))
                
                if not internships:
                    current_app.logger.info(f"Student {student.full_name} has no approved internships, skipping")
                    continue  # Skip students with no approved internships
                
                # Calculate total credit points and round to 2 decimal places
                total_hours = sum(i.get('total_hours', 0) for i in internships)
                total_credit_points = round(total_hours / 40, 2) if total_hours > 0 else 0.0
                
                current_app.logger.info(f"Generating certificate for {student.full_name} with {total_credit_points} credit points")
                
                # Generate certificate using SVG format
                certificate_pdf = generate_internship_certificate(student, total_credit_points)
                
                # Send email with certificate
                sender_email = os.getenv('SMTP_EMAIL')
                sender_password = os.getenv('SMTP_PASSWORD')
                
                if not sender_email or not sender_password:
                    flash('SMTP credentials not configured. Cannot send emails.', 'danger')
                    return redirect(url_for('admin.certificate_management'))
                
                # Create email
                msg = MIMEMultipart()
                msg['From'] = sender_email
                msg['To'] = student.email
                msg['Subject'] = f"Internship Completion Certificate - {student.full_name} ({academic_year or 'N/A'})"
                
                # Email body
                body = f"""Dear {student.full_name},

Congratulations on successfully completing your internship requirements!

We are pleased to present you with the attached Internship Completion Certificate. This certificate recognizes your dedication and hard work in earning {total_credit_points} credit points through your internship activities.

Your commitment to professional development is commendable, and we wish you continued success in your future endeavors.

Best regards,
Shah and Anchor Kutchhi Engineering College
Internship Program"""
                
                msg.attach(MIMEText(body, 'plain'))
                
                # Attach certificate
                pdf_attachment = MIMEApplication(certificate_pdf.read())
                pdf_attachment.add_header('Content-Disposition', 'attachment', 
                                       filename=f'{student.full_name.replace(" ", "_")}_{academic_year or "N/A"}_certificate.pdf')
                msg.attach(pdf_attachment)
                
                # Send email
                server = smtplib.SMTP('smtp.gmail.com', 587)
                server.starttls()
                server.login(sender_email, sender_password)
                server.send_message(msg)
                server.quit()
                
                sent_count += 1
                current_app.logger.info(f"Successfully sent certificate to {student.full_name}")
                
            except Exception as e:
                current_app.logger.error(f"Error sending certificate to {student_data.get('email', 'Unknown')}: {str(e)}")
                failed_count += 1
        
        if sent_count > 0:
            flash(f'Successfully sent {sent_count} certificates. {failed_count} failed.', 'success')
        else:
            flash('No certificates were sent successfully.', 'warning')
            
    except Exception as e:
        current_app.logger.error(f"Error in send_certificates: {str(e)}")
        flash(f'Error sending certificates: {str(e)}', 'danger')
    
    return redirect(url_for('admin.certificate_management'))

@admin_bp.route('/download-certificates', methods=['POST'])
@login_required
def download_certificates():
    if current_user.role != 'admin':
        flash('Access denied.', 'error')
        return redirect(url_for('admin.certificate_management'))
    
    try:
        # Get filter parameters
        department = request.form.get('department', '')
        academic_year = request.form.get('academic_year', '')
        
        current_app.logger.info(f"Downloading certificates for department: {department}, academic_year: {academic_year}")
        
        # Build filter query
        filter_query = {'role': 'student'}
        if department:
            filter_query['department'] = department
        
        # Get students based on filters
        students = list(db.users.find(filter_query))
        
        if not students:
            flash('No students found with the selected filters.', 'warning')
            return redirect(url_for('admin.certificate_management'))
        
        # Create zip file in memory
        import zipfile
        import io
        
        zip_buffer = io.BytesIO()
        certificates_added = 0
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for student_data in students:
                try:
                    student = User(student_data)
                    student_id = str(student_data['_id'])
                    
                    # Get approved internships for the student
                    internship_query = {'student_id': student_id, 'status': 'approved'}
                    
                    # If academic year is selected, filter internships by that year
                    if academic_year:
                        internship_query['academic_year'] = academic_year
                    
                    internships = list(db.internships.find(internship_query))
                    
                    if not internships:
                        current_app.logger.info(f"Student {student.full_name} has no approved internships, skipping")
                        continue  # Skip students with no approved internships
                    
                    # Calculate total credit points and round to 2 decimal places
                    total_hours = sum(i.get('total_hours', 0) for i in internships)
                    total_credit_points = round(total_hours / 40, 2) if total_hours > 0 else 0.0
                    
                    current_app.logger.info(f"Generating certificate for {student.full_name} with {total_credit_points} credit points")
                    
                    # Generate certificate using SVG format
                    certificate_pdf = generate_internship_certificate(student, total_credit_points)
                    
                    # Add to zip file with proper naming: student_name_academic_year
                    filename = f"{student.full_name.replace(' ', '_')}_{academic_year or 'N/A'}_certificate.pdf"
                    zip_file.writestr(filename, certificate_pdf.getvalue())
                    certificates_added += 1
                    
                except Exception as e:
                    current_app.logger.error(f"Error generating certificate for {student_data.get('email', 'Unknown')}: {str(e)}")
                    continue
        
        if certificates_added == 0:
            flash('No certificates were generated. Please check if students have approved internships.', 'warning')
            return redirect(url_for('admin.certificate_management'))
        
        # Reset buffer position
        zip_buffer.seek(0)
        
        # Generate filename based on filters
        filename_parts = ['certificates']
        if department:
            filename_parts.append(department.replace(' ', '_'))
        if academic_year:
            filename_parts.append(academic_year.replace(' ', '_'))
        filename = '_'.join(filename_parts) + '.zip'
        
        current_app.logger.info(f"Successfully created zip file with {certificates_added} certificates")
        
        return Response(
            zip_buffer.getvalue(),
            mimetype='application/zip',
            headers={'Content-Disposition': f'attachment; filename={filename}'}
        )
        
    except Exception as e:
        current_app.logger.error(f"Error in download_certificates: {str(e)}")
        flash(f'Error downloading certificates: {str(e)}', 'danger')
        return redirect(url_for('admin.certificate_management'))