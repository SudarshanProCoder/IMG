from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError
from models.user import User

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[
        DataRequired(),
        Email()
    ])
    password = PasswordField('Password', validators=[
        DataRequired()
    ])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class SignupForm(FlaskForm):
    full_name = StringField('Full Name', validators=[
        DataRequired(),
        Length(min=2, max=100)
    ])
    email = StringField('Email', validators=[
        DataRequired(),
        Email()
    ])
    password = PasswordField('Password', validators=[
        DataRequired(),
        Length(min=6)
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(),
        EqualTo('password')
    ])
    role = SelectField('Role', choices=[
        ('student', 'Student'),
        ('mentor', 'Mentor'),
        ('admin', 'Admin')
    ])
    prn = StringField('PRN (Permanent Registration Number)', validators=[
        Length(max=20)
    ])
    registration_number = StringField('Registration Number', validators=[
        Length(max=20)
    ])
    branch = SelectField('Branch', choices=[
        ('', 'Select Branch'),
        ('computer_science', 'Computer Science'),
        ('information_technology', 'Information Technology'),
        ('electronics', 'Electronics'),
        ('electrical', 'Electrical'),
        ('mechanical', 'Mechanical'),
        ('civil', 'Civil')
    ])
    year = SelectField('Year', choices=[
        ('', 'Select Year'),
        ('1', 'First Year'),
        ('2', 'Second Year'),
        ('3', 'Third Year'),
        ('4', 'Fourth Year')
    ])
    mentor_email = StringField('Mentor Email', validators=[
        Email()
    ])
    submit = SubmitField('Sign Up')

    def validate_email(self, email):
        user = User.get_by_email(email.data)
        if user:
            raise ValidationError('Email already registered. Please use a different email.')

    def validate_prn(self, prn):
        if self.role.data == 'student':
            if not prn.data:
                raise ValidationError('PRN is required for students.')
            user = User.get_by_prn(prn.data)
            if user:
                raise ValidationError('PRN already registered. Please use a different PRN.')

    def validate_registration_number(self, registration_number):
        if self.role.data == 'student':
            if not registration_number.data:
                raise ValidationError('Registration number is required for students.')
            user = User.get_by_registration_number(registration_number.data)
            if user:
                raise ValidationError('Registration number already registered.')

    def validate_mentor_email(self, mentor_email):
        if self.role.data == 'student' and mentor_email.data:
            mentor = User.get_by_email(mentor_email.data)
            if not mentor or mentor.role != 'mentor':
                raise ValidationError('Invalid mentor email. Please enter a valid mentor email address.') 