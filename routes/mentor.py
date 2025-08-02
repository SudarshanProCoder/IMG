from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from models.user import User
from models.internship import Internship
from models.activity import Activity
from bson.objectid import ObjectId
from config.database import db

mentor_bp = Blueprint('mentor', __name__)

@mentor_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.role != 'mentor':
        flash('Access denied.', 'error')
        return redirect(url_for('auth.login'))
    
    try:
        # Get filter parameters
        year = request.args.get('year')
        internship_status = request.args.get('internship_status')
        activity_status = request.args.get('activity_status')
        
        # Build query for students
        query = {'mentor_email': current_user.email}
        if year:
            query['year'] = year
        
        # Get students
        students = []
        total_internship_hours = 0
        total_activity_hours = 0
        total_credit_points = 0
        
        for student_data in db.users.find(query):
            student = User(student_data)
            
            # Get internships and activities
            internship_query = {'student_id': student.id}
            activity_query = {'student_id': student.id}
            
            if internship_status:
                internship_query['status'] = internship_status
            if activity_status:
                activity_query['status'] = activity_status
            
            student.internships = list(db.internships.find(internship_query))
            student.activities = list(db.activities.find(activity_query))
            
            # Calculate student statistics
            student.total_internship_hours = sum(i.get('total_hours', 0) for i in student.internships if i.get('status') == 'approved')
            student.total_activity_hours = sum(a.get('hours_per_week', 0) for a in student.activities if a.get('status') == 'approved')
            student.internship_credit_points = round(student.total_internship_hours / 40, 2) if student.total_internship_hours else 0
            student.activity_credit_points = round(student.total_activity_hours / 10, 2) if student.total_activity_hours else 0
            student.total_credit_points = round(student.internship_credit_points + student.activity_credit_points, 2)
            
            # Update overall totals
            total_internship_hours += student.total_internship_hours
            total_activity_hours += student.total_activity_hours
            total_credit_points += student.total_credit_points
            
            # Only add students that match the filters
            if (not internship_status or student.internships) and (not activity_status or student.activities):
                students.append(student)
        
        # Get unique years for filter
        years = list(db.users.distinct('year', {'mentor_email': current_user.email}))
        
        return render_template('mentor/dashboard.html',
                            students=students,
                            years=years,
                            selected_year=year,
                            internship_status=internship_status,
                            activity_status=activity_status,
                            total_internship_hours=total_internship_hours,
                            total_activity_hours=total_activity_hours,
                            total_credit_points=total_credit_points)
    except Exception as e:
        flash(f'Error loading dashboard: {str(e)}', 'error')
        return redirect(url_for('auth.login'))

@mentor_bp.route('/student/<student_id>')
@login_required
def view_student(student_id):
    if current_user.role != 'mentor':
        flash('Access denied.', 'error')
        return redirect(url_for('auth.login'))
    
    student = User.get_by_id(current_app.db, student_id)
    if not student or student.mentor_email != current_user.email:
        flash('Student not found.', 'error')
        return redirect(url_for('mentor.dashboard'))
    
    # Get filter parameters
    internship_status = request.args.get('internship_status')
    activity_status = request.args.get('activity_status')
    
    # Build queries
    internship_query = {'student_id': student_id}
    activity_query = {'student_id': student_id}
    
    if internship_status:
        internship_query['status'] = internship_status
    if activity_status:
        activity_query['status'] = activity_status
    
    # Get filtered internships and activities
    internships = list(db.internships.find(internship_query))
    activities = list(db.activities.find(activity_query))
    
    # Calculate statistics
    total_internship_hours = sum(i.get('total_hours', 0) for i in internships if i.get('status') == 'approved')
    total_activity_hours = sum(a.get('hours_per_week', 0) for a in activities if a.get('status') == 'approved')
    internship_credit_points = round(total_internship_hours / 40, 2) if total_internship_hours else 0
    activity_credit_points = round(total_activity_hours / 10, 2) if total_activity_hours else 0
    total_credit_points = round(internship_credit_points + activity_credit_points, 2)
    
    return render_template('mentor/student_profile.html',
                         student=student,
                         internships=internships,
                         activities=activities,
                         internship_status=internship_status,
                         activity_status=activity_status,
                         total_internship_hours=total_internship_hours,
                         total_activity_hours=total_activity_hours,
                         total_credit_points=total_credit_points)

@mentor_bp.route('/internship/<internship_id>/approve')
@login_required
def approve_internship(internship_id):
    if current_user.role != 'mentor':
        flash('Access denied.', 'error')
        return redirect(url_for('auth.login'))
    
    internship = Internship.get_by_id(current_app.db, internship_id)
    if not internship:
        flash('Internship not found.', 'error')
        return redirect(url_for('mentor.dashboard'))
    
    student = User.get_by_id(current_app.db, internship.student_id)
    if not student or student.mentor_email != current_user.email:
        flash('Access denied.', 'error')
        return redirect(url_for('mentor.dashboard'))
    
    internship.status = 'approved'
    internship.save(current_app.db)
    flash('Internship approved successfully!', 'success')
    return redirect(url_for('mentor.view_student', student_id=internship.student_id))

@mentor_bp.route('/internship/<internship_id>/reject')
@login_required
def reject_internship(internship_id):
    if current_user.role != 'mentor':
        flash('Access denied.', 'error')
        return redirect(url_for('auth.login'))
    
    internship = Internship.get_by_id(current_app.db, internship_id)
    if not internship:
        flash('Internship not found.', 'error')
        return redirect(url_for('mentor.dashboard'))
    
    student = User.get_by_id(current_app.db, internship.student_id)
    if not student or student.mentor_email != current_user.email:
        flash('Access denied.', 'error')
        return redirect(url_for('mentor.dashboard'))
    
    internship.status = 'rejected'
    internship.save(current_app.db)
    flash('Internship rejected.', 'success')
    return redirect(url_for('mentor.view_student', student_id=internship.student_id))

@mentor_bp.route('/activity/<activity_id>/approve')
@login_required
def approve_activity(activity_id):
    if current_user.role != 'mentor':
        flash('Access denied.', 'error')
        return redirect(url_for('auth.login'))
    
    activity = Activity.get_by_id(current_app.db, activity_id)
    if not activity:
        flash('Activity not found.', 'error')
        return redirect(url_for('mentor.dashboard'))
    
    student = User.get_by_id(current_app.db, activity.student_id)
    if not student or student.mentor_email != current_user.email:
        flash('Access denied.', 'error')
        return redirect(url_for('mentor.dashboard'))
    
    activity.status = 'approved'
    activity.save(current_app.db)
    flash('Activity approved successfully!', 'success')
    return redirect(url_for('mentor.view_student', student_id=activity.student_id))

@mentor_bp.route('/activity/<activity_id>/reject')
@login_required
def reject_activity(activity_id):
    if current_user.role != 'mentor':
        flash('Access denied.', 'error')
        return redirect(url_for('auth.login'))
    
    activity = Activity.get_by_id(current_app.db, activity_id)
    if not activity:
        flash('Activity not found.', 'error')
        return redirect(url_for('mentor.dashboard'))
    
    student = User.get_by_id(current_app.db, activity.student_id)
    if not student or student.mentor_email != current_user.email:
        flash('Access denied.', 'error')
        return redirect(url_for('mentor.dashboard'))
    
    activity.status = 'rejected'
    activity.save(current_app.db)
    flash('Activity rejected.', 'success')
    return redirect(url_for('mentor.view_student', student_id=activity.student_id))