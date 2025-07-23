from datetime import datetime
from bson import ObjectId

class Activity:
    def __init__(self, activity_data=None):
        if activity_data is None:
            activity_data = {}
        self.id = activity_data.get('_id')
        self.student_id = activity_data.get('student_id')
        self.activity_type = activity_data.get('activity_type')
        self.title = activity_data.get('title')
        self.description = activity_data.get('description')
        self.start_date = activity_data.get('start_date')
        self.end_date = activity_data.get('end_date')
        self.duration_months = activity_data.get('duration_months')
        self.semester = activity_data.get('semester')
        self.hours_per_week = activity_data.get('hours_per_week')
        self.total_hours = activity_data.get('total_hours')
        self.certificate_path = activity_data.get('certificate_path')
        self.academic_year = activity_data.get('academic_year')
        self.skills = activity_data.get('skills', [])
        self.status = activity_data.get('status', 'pending')
        self.created_at = activity_data.get('created_at', datetime.now())
        self.updated_at = activity_data.get('updated_at', datetime.now())

    def save(self, db):
        activity_data = {
            'student_id': self.student_id,
            'activity_type': self.activity_type,
            'title': self.title,
            'description': self.description,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'duration_months': self.duration_months,
            'semester': self.semester,
            'hours_per_week': self.hours_per_week,
            'total_hours': self.total_hours,
            'certificate_path': self.certificate_path,
            'academic_year': self.academic_year,
            'skills': self.skills,
            'status': self.status,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

        if self.id:
            # Update existing activity
            db.activities.update_one(
                {'_id': ObjectId(self.id)},
                {'$set': activity_data}
            )
        else:
            # Insert new activity
            result = db.activities.insert_one(activity_data)
            self.id = str(result.inserted_id)

    def update(self, db, activity_data):
        # Update instance attributes
        for key, value in activity_data.items():
            setattr(self, key, value)
        self.updated_at = datetime.now()
        
        # Save to database
        self.save(db)

    def delete(self, db):
        """Delete the activity from the database"""
        if self.id:
            db.activities.delete_one({'_id': ObjectId(self.id)})
            return True
        return False

    @staticmethod
    def get_by_id(db, activity_id):
        """Get activity by ID"""
        if not activity_id:
            return None
        try:
            activity_data = db.activities.find_one({'_id': ObjectId(activity_id)})
            if activity_data:
                activity_data['_id'] = str(activity_data['_id'])
                return Activity(activity_data)
        except:
            return None
        return None

    @staticmethod
    def get_by_student_id(db, student_id):
        """Get all activities for a student"""
        activities = []
        cursor = db.activities.find({'student_id': str(student_id)})
        for activity_data in cursor:
            activity_data['_id'] = str(activity_data['_id'])
            activities.append(Activity(activity_data))
        return activities

    @staticmethod
    def get_all(db):
        """Get all activities"""
        activities = []
        cursor = db.activities.find()
        for activity_data in cursor:
            activity_data['_id'] = str(activity_data['_id'])
            activities.append(Activity(activity_data))
        return activities 