from datetime import datetime
from bson import ObjectId

class Internship:
    def __init__(self, data):
        self.id = str(data.get('_id')) if '_id' in data else None
        self.student_id = data.get('student_id')
        self.company_name = data.get('company_name')
        self.project_name = data.get('project_name')
        self.start_date = data.get('start_date')
        self.end_date = data.get('end_date')
        self.duration_months = data.get('duration_months')
        self.semester = data.get('semester')
        self.hours_per_week = data.get('hours_per_week')
        self.total_hours = data.get('total_hours')
        self.academic_year = data.get('academic_year')
        self.offer_letter_url = data.get('offer_letter_url')
        self.completion_letter_url = data.get('completion_letter_url')
        self.skills = data.get('skills', [])
        self.status = data.get('status', 'pending')
        self.created_at = data.get('created_at', datetime.now())
        self.updated_at = data.get('updated_at', datetime.now())

    def to_dict(self):
        return {
            'student_id': self.student_id,
            'company_name': self.company_name,
            'project_name': self.project_name,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'duration_months': self.duration_months,
            'semester': self.semester,
            'hours_per_week': self.hours_per_week,
            'total_hours': self.total_hours,
            'academic_year': self.academic_year,
            'offer_letter_url': self.offer_letter_url,
            'completion_letter_url': self.completion_letter_url,
            'skills': self.skills,
            'status': self.status,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

    def save(self, db):
        if self.id:
            # Update existing internship
            db.internships.update_one(
                {'_id': ObjectId(self.id)},
                {'$set': self.to_dict()}
            )
        else:
            # Create new internship
            result = db.internships.insert_one(self.to_dict())
            self.id = str(result.inserted_id)

    @staticmethod
    def get_by_id(db, internship_id):
        data = db.internships.find_one({'_id': ObjectId(internship_id)})
        return Internship(data) if data else None

    @staticmethod
    def get_by_student_id(db, student_id):
        cursor = db.internships.find({'student_id': str(student_id)})
        return [Internship(data) for data in cursor]

    def delete(self, db):
        if self.id:
            db.internships.delete_one({'_id': ObjectId(self.id)})

    def update(self, db, internship_data):
        # Update instance attributes
        for key, value in internship_data.items():
            setattr(self, key, value)
        self.updated_at = datetime.now()
        
        # Save to database
        self.save(db)

    @staticmethod
    def get_all(db):
        cursor = db.internships.find()
        return [Internship(data) for data in cursor] 