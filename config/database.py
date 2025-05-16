from pymongo import MongoClient
from flask import current_app
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize MongoDB connection
client = MongoClient(os.getenv('MONGODB_URI', 'mongodb://localhost:27017/'))
db = client['internship_portal']

def init_db(app):
    app.db = db 