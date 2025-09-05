from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from bson import ObjectId
from config.database import db
from datetime import datetime

class User(UserMixin):
    def __init__(self, user_data=None, **kwargs):
        if user_data:
            self.id = str(user_data.get('_id'))
            self.email = user_data.get('email')
            self.password_hash = user_data.get('password_hash')
            self.role = user_data.get('role')
            self.full_name = user_data.get('full_name')
            self.is_verified = user_data.get('is_verified', False)
            self.verification_token = user_data.get('verification_token')
            self.profile_image = user_data.get('profile_image')
            self.created_at = user_data.get('created_at')
            self.updated_at = user_data.get('updated_at')
            
            self.phone = user_data.get('phone')
            self.department = user_data.get('department')
            self.batch = user_data.get('batch')
            self.semester = user_data.get('semester')
            self.gender = user_data.get('gender')
            self.date_of_birth = user_data.get('date_of_birth')
            self.address = user_data.get('address')
            self.skills = user_data.get('skills', [])
            self.soft_skills = user_data.get('soft_skills', [])
            
            if self.role == 'student':
                self.prn = user_data.get('prn')
                self.registration_number = user_data.get('registration_number')
                self.branch = user_data.get('branch')
                self.year = user_data.get('year')
                self.mentor_email = user_data.get('mentor_email')
        else:
            self.email = kwargs.get('email')
            self.role = kwargs.get('role')
            self.full_name = kwargs.get('full_name')
            self.is_verified = False
            self.verification_token = None
            self.profile_image = kwargs.get('profile_image')
            self.created_at = datetime.utcnow()
            self.updated_at = datetime.utcnow()
            
            self.phone = kwargs.get('phone')
            self.department = kwargs.get('department')
            self.batch = kwargs.get('batch')
            self.semester = kwargs.get('semester')
            self.gender = kwargs.get('gender')
            self.date_of_birth = kwargs.get('date_of_birth')
            self.address = kwargs.get('address')
            self.skills = kwargs.get('skills', [])
            self.soft_skills = kwargs.get('soft_skills', [])
            
            if 'password' in kwargs:
                self.set_password(kwargs['password'])
            
            if self.role == 'student':
                self.prn = kwargs.get('prn')
                self.registration_number = kwargs.get('registration_number')
                self.branch = kwargs.get('branch')
                self.year = kwargs.get('year')
                self.mentor_email = kwargs.get('mentor_email')

    @staticmethod
    def get_by_email(email):
        user_data = db.users.find_one({'email': email})
        if user_data:
            return User(user_data)
        return None

    @staticmethod
    def get_by_prn(prn):
        user_data = db.users.find_one({'prn': prn})
        if user_data:
            return User(user_data)
        return None

    @staticmethod
    def get_by_registration_number(registration_number):
        user_data = db.users.find_one({'registration_number': registration_number})
        if user_data:
            return User(user_data)
        return None

    @staticmethod
    def get_by_slug(slug):
        user_data = db.users.find_one({
            'role': 'student',
            '$expr': {
                '$eq': [
                    { '$toLower': { '$replaceAll': { 'input': '$full_name', 'find': ' ', 'replacement': '-' } } },
                    slug.lower()
                ]
            }
        })
        if user_data:
            return User(user_data)
        return None

    @staticmethod
    def get_by_id(db, user_id):
        try:
            if not user_id:
                return None
            user_data = db.users.find_one({'_id': ObjectId(user_id)})
            if user_data:
                return User(user_data)
        except (TypeError, ValueError):
            return None
        return None

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def save(self):
        user_data = {
            'email': self.email,
            'password_hash': self.password_hash,
            'role': self.role,
            'full_name': self.full_name,
            'is_verified': self.is_verified,
            'verification_token': self.verification_token,
            'profile_image': self.profile_image,
            'phone': self.phone,
            'department': self.department,
            'batch': self.batch,
            'semester': self.semester,
            'gender': self.gender,
            'date_of_birth': self.date_of_birth,
            'address': self.address,
            'skills': self.skills,
            'soft_skills': self.soft_skills,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

        if self.role == 'student':
            user_data.update({
                'prn': self.prn,
                'registration_number': self.registration_number,
                'branch': self.branch,
                'year': self.year,
                'mentor_email': self.mentor_email
            })

        if hasattr(self, 'id') and self.id:
            try:
                db.users.update_one(
                    {'_id': ObjectId(self.id)},
                    {'$set': user_data}
                )
            except:
                pass
        else:
            result = db.users.insert_one(user_data)
            self.id = str(result.inserted_id)

    def delete(self):
        if hasattr(self, 'id') and self.id:
            try:
                db.users.delete_one({'_id': ObjectId(self.id)})
                return True
            except:
                pass
        return False

    def update(self, **kwargs):
        update_data = {k: v for k, v in kwargs.items() if v is not None}
        if 'password' in update_data:
            update_data['password_hash'] = generate_password_hash(update_data.pop('password'))
        update_data['updated_at'] = datetime.utcnow()
        db.users.update_one({'_id': ObjectId(self.id)}, {'$set': update_data})
        for key, value in update_data.items():
            setattr(self, key, value)

    @staticmethod
    def get_all():
        users = []
        for user_data in db.users.find():
            user = User(user_data)
            user.id = str(user_data['_id'])
            users.append(user)
        return users

    @staticmethod
    def get_by_role(role):
        users = []
        for user_data in db.users.find({'role': role}):
            user = User(user_data)
            user.id = str(user_data['_id'])
            users.append(user)
        return users

    @staticmethod
    def get_students_by_mentor(mentor_email):
        users = []
        for user_data in db.users.find({'role': 'student', 'mentor_email': mentor_email}):
            user = User(user_data)
            user.id = str(user_data['_id'])
            users.append(user)
        return users

    def to_dict(self):
        return {
            'full_name': self.full_name,
            'email': self.email,
            'password_hash': self.password_hash,
            'role': self.role,
            'profile_image': self.profile_image,
            'phone': self.phone,
            'department': self.department,
            'batch': self.batch,
            'semester': self.semester,
            'gender': self.gender,
            'date_of_birth': self.date_of_birth,
            'address': self.address,
            'is_verified': self.is_verified,
            'verification_token': self.verification_token,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        } 