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

admin_bp = Blueprint('admin', __name__)

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
        branch = request.args.get('branch')
        year = request.args.get('year')
        academic_year = request.args.get('academic_year')
        semester = request.args.get('semester')
        search_query = request.args.get('search', '').strip()
        
        query = {'role': 'student'}
        if branch:
            query['branch'] = branch
        if year:
            query['year'] = year
        if academic_year:
            query['academic_year'] = academic_year
        if semester:
            query['semester'] = semester
        
        students = []
        for student_data in db.users.find(query):
            student = User(student_data)
            # Get internships and activities for each student
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
        
        # Get unique branches, years, academic_years, and semesters for filters
        branches = list(db.users.distinct('branch', {'role': 'student'}))
        years = list(db.users.distinct('year', {'role': 'student'}))
        academic_years = list(db.users.distinct('academic_year', {'role': 'student'}))
        semesters = list(db.users.distinct('semester', {'role': 'student'}))
        
        return render_template('admin/students.html',
                            students=students,
                            branches=branches,
                            years=years,
                            academic_years=academic_years,
                            semesters=semesters,
                            selected_branch=branch,
                            selected_year=year,
                            selected_academic_year=academic_year,
                            selected_semester=semester,
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
                            approved_activities=approved_activities)
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