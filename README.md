# Shah and Anchor College Internship Portal

A comprehensive web application for managing student internships and activities at Shah and Anchor College.

## Features

- **Student Dashboard**
  - Profile management
  - Internship tracking
  - Activity logging
  - Document uploads
  - Progress monitoring

- **Mentor Dashboard**
  - Student oversight
  - Internship approval
  - Activity verification
  - Performance tracking
  - Document review

- **Admin Dashboard**
  - User management
  - System configuration
  - Analytics and reporting
  - Document verification
  - Bulk operations

## Screenshots

### Student Interface
<div class="grid-container">
  <div class="grid-item">
    <img src="docs/images/student-dashboard.png" alt="Student Dashboard">
    <p>Student Dashboard</p>
  </div>
  <div class="grid-item">
    <img src="docs/images/student-profile.png" alt="Student Profile">
    <p>Student Profile</p>
  </div>
  <div class="grid-item">
    <img src="docs/images/internship-form.png" alt="Internship Form">
    <p>Internship Form</p>
  </div>
</div>

### Mentor Interface
<div class="grid-container">
  <div class="grid-item">
    <img src="docs/images/mentor-dashboard.png" alt="Mentor Dashboard">
    <p>Mentor Dashboard</p>
  </div>
  <div class="grid-item">
    <img src="docs/images/student-list.png" alt="Student List">
    <p>Student List</p>
  </div>
  <div class="grid-item">
    <img src="docs/images/approval-interface.png" alt="Approval Interface">
    <p>Approval Interface</p>
  </div>
</div>

### Admin Interface
<div class="grid-container">
  <div class="grid-item">
    <img src="docs/images/admin-dashboard.png" alt="Admin Dashboard">
    <p>Admin Dashboard</p>
  </div>
  <div class="grid-item">
    <img src="docs/images/user-management.png" alt="User Management">
    <p>User Management</p>
  </div>
  <div class="grid-item">
    <img src="docs/images/analytics.png" alt="Analytics">
    <p>Analytics</p>
  </div>
</div>

## Technology Stack

- **Backend**: Python, Flask
- **Database**: MongoDB
- **Frontend**: HTML5, CSS3, JavaScript, Bootstrap 5
- **File Storage**: Cloudinary
- **Email**: SMTP (Gmail)
- **Authentication**: Flask-Login

## Prerequisites

- Python 3.8+
- MongoDB
- Cloudinary Account
- Gmail Account (for SMTP)

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/internship-portal.git
   cd internship-portal
   ```

2. Create and activate virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. Initialize the database:
   ```bash
   flask db upgrade
   ```

6. Run the application:
   ```bash
   flask run
   ```

## Environment Variables

Create a `.env` file with the following variables:

```env
FLASK_APP=app.py
FLASK_ENV=development
SECRET_KEY=your-secret-key
MONGODB_URI=your-mongodb-uri
CLOUDINARY_CLOUD_NAME=your-cloud-name
CLOUDINARY_API_KEY=your-api-key
CLOUDINARY_API_SECRET=your-api-secret
SMTP_EMAIL=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

## Project Structure

```
internship-portal/
├── app/
│   ├── __init__.py
│   ├── models/
│   ├── routes/
│   ├── static/
│   └── templates/
├── config/
├── docs/
│   └── images/
├── tests/
├── .env
├── .gitignore
├── requirements.txt
└── README.md
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contact

Shah and Anchor College - [contact@example.com](mailto:contact@example.com)

Project Link: [https://github.com/yourusername/internship-portal](https://github.com/yourusername/internship-portal)

## Acknowledgments

- [Bootstrap](https://getbootstrap.com/)
- [Font Awesome](https://fontawesome.com/)
- [Flask](https://flask.palletsprojects.com/)
- [MongoDB](https://www.mongodb.com/)
- [Cloudinary](https://cloudinary.com/)