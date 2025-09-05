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
        department = request.args.get('department')
        academic_year = request.args.get('academic_year')
        semester = request.args.get('semester')
        year = request.args.get('year')
        internship_status = request.args.get('internship_status')
        activity_status = request.args.get('activity_status')
        
        # Build query for students
        query = {'mentor_email': current_user.email}
        if department:
            query['department'] = department
        if year:
            query['year'] = year
        if semester:
            query['semester'] = semester
        
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
            
            if academic_year:
                internship_query['academic_year'] = academic_year
                activity_query['academic_year'] = academic_year
            
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
        
        # Get unique values for filters from mentor's students
        mentor_students_query = {'mentor_email': current_user.email}
        
        # If department is selected, filter other options based on that department
        if department:
            mentor_students_query['department'] = department
        
        # Get departments, years, and semesters from mentor's students
        departments = list(db.users.distinct('department', {'mentor_email': current_user.email, 'department': {'$exists': True, '$ne': None, '$ne': 'None'}}))
        years = list(db.users.distinct('year', {**mentor_students_query, 'year': {'$exists': True, '$ne': None, '$ne': 'None'}}))
        semesters = list(db.users.distinct('semester', {**mentor_students_query, 'semester': {'$exists': True, '$ne': None, '$ne': 'None'}}))
        
        # Get academic years from both internships and activities of mentor's students
        mentor_student_ids = [str(student['_id']) for student in db.users.find(mentor_students_query, {'_id': 1})]
        
        internship_academic_years = list(db.internships.distinct('academic_year', {'student_id': {'$in': mentor_student_ids}, 'academic_year': {'$exists': True, '$ne': None, '$ne': 'None'}}))
        activity_academic_years = list(db.activities.distinct('academic_year', {'student_id': {'$in': mentor_student_ids}, 'academic_year': {'$exists': True, '$ne': None, '$ne': 'None'}}))
        academic_years = sorted(list(set(internship_academic_years + activity_academic_years)))
        
        
        # Ensure we're passing the correct filter values (not None if they're empty strings)
        selected_department = department if department else None
        selected_year = year if year else None
        selected_semester = semester if semester else None
        selected_academic_year = academic_year if academic_year else None
        
        return render_template('mentor/dashboard.html',
                            students=students,
                            departments=departments,
                            years=years,
                            semesters=semesters,
                            academic_years=academic_years,
                            selected_department=selected_department,
                            selected_year=selected_year,
                            selected_semester=selected_semester,
                            selected_academic_year=selected_academic_year,
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
    
    student = User.get_by_id(db, student_id)
    if not student:
        flash('Student not found.', 'error')
        return redirect(url_for('mentor.dashboard'))
    
    if student.mentor_email != current_user.email:
        flash('Access denied.', 'error')
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
    
    internship = Internship.get_by_id(db, internship_id)
    if not internship:
        flash('Internship not found.', 'error')
        return redirect(url_for('mentor.dashboard'))
    
    student = User.get_by_id(db, internship.student_id)
    if not student or student.mentor_email != current_user.email:
        flash('Access denied.', 'error')
        return redirect(url_for('mentor.dashboard'))
    
    internship.status = 'approved'
    internship.save(db)
    flash('Internship approved successfully!', 'success')
    return redirect(url_for('mentor.view_student', student_id=internship.student_id))

@mentor_bp.route('/internship/<internship_id>/reject')
@login_required
def reject_internship(internship_id):
    if current_user.role != 'mentor':
        flash('Access denied.', 'error')
        return redirect(url_for('auth.login'))
    
    internship = Internship.get_by_id(db, internship_id)
    if not internship:
        flash('Internship not found.', 'error')
        return redirect(url_for('mentor.dashboard'))
    
    student = User.get_by_id(db, internship.student_id)
    if not student or student.mentor_email != current_user.email:
        flash('Access denied.', 'error')
        return redirect(url_for('mentor.dashboard'))
    
    internship.status = 'rejected'
    internship.save(db)
    flash('Internship rejected.', 'success')
    return redirect(url_for('mentor.view_student', student_id=internship.student_id))

@mentor_bp.route('/activity/<activity_id>/approve')
@login_required
def approve_activity(activity_id):
    if current_user.role != 'mentor':
        flash('Access denied.', 'error')
        return redirect(url_for('auth.login'))
    
    activity = Activity.get_by_id(db, activity_id)
    if not activity:
        flash('Activity not found.', 'error')
        return redirect(url_for('mentor.dashboard'))
    
    student = User.get_by_id(db, activity.student_id)
    if not student or student.mentor_email != current_user.email:
        flash('Access denied.', 'error')
        return redirect(url_for('mentor.dashboard'))
    
    activity.status = 'approved'
    activity.save(db)
    flash('Activity approved successfully!', 'success')
    return redirect(url_for('mentor.view_student', student_id=activity.student_id))

@mentor_bp.route('/activity/<activity_id>/reject')
@login_required
def reject_activity(activity_id):
    if current_user.role != 'mentor':
        flash('Access denied.', 'error')
        return redirect(url_for('auth.login'))
    
    activity = Activity.get_by_id(db, activity_id)
    if not activity:
        flash('Activity not found.', 'error')
        return redirect(url_for('mentor.dashboard'))
    
    student = User.get_by_id(db, activity.student_id)
    if not student or student.mentor_email != current_user.email:
        flash('Access denied.', 'error')
        return redirect(url_for('mentor.dashboard'))
    
    activity.status = 'rejected'
    activity.save(db)
    flash('Activity rejected.', 'success')
    return redirect(url_for('mentor.view_student', student_id=activity.student_id))

@mentor_bp.route('/internship/<internship_id>')
@login_required
def view_internship(internship_id):
    if current_user.role != 'mentor':
        flash('Access denied.', 'error')
        return redirect(url_for('auth.login'))
    
    internship = Internship.get_by_id(db, internship_id)
    if not internship:
        flash('Internship not found.', 'error')
        return redirect(url_for('mentor.dashboard'))
    
    student = User.get_by_id(db, internship.student_id)
    if not student or student.mentor_email != current_user.email:
        flash('Access denied.', 'error')
        return redirect(url_for('mentor.dashboard'))
    
    return render_template('mentor/internship_detail.html', 
                         internship=internship, 
                         student=student)

@mentor_bp.route('/activity/<activity_id>')
@login_required
def view_activity(activity_id):
    if current_user.role != 'mentor':
        flash('Access denied.', 'error')
        return redirect(url_for('auth.login'))
    
    activity = Activity.get_by_id(db, activity_id)
    if not activity:
        flash('Activity not found.', 'error')
        return redirect(url_for('mentor.dashboard'))
    
    student = User.get_by_id(db, activity.student_id)
    if not student or student.mentor_email != current_user.email:
        flash('Access denied.', 'error')
        return redirect(url_for('mentor.dashboard'))
    
    return render_template('mentor/activity_detail.html', 
                         activity=activity, 
                         student=student)
