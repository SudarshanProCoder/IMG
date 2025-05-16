import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.user import User
from config.database import db
from dotenv import load_dotenv

def create_admin_user():
    # Check if admin already exists
    admin = User.get_by_email('admin@shahandanchor.edu')
    if admin:
        print("Admin user already exists!")
        return

    # Create admin user
    admin = User()
    admin.email = 'admin@shahandanchor.edu'
    admin.set_password('admin123')  # You should change this password
    admin.role = 'admin'
    admin.full_name = 'System Administrator'
    admin.is_verified = True  # Admin is automatically verified

    # Save admin user
    admin.save()
    print("Admin user created successfully!")
    print("Email: admin@shahandanchor.edu")
    print("Password: admin123")
    print("\nPlease change the password after first login!")

if __name__ == '__main__':
    create_admin_user() 