"""
Configuration file for the File Storage API
"""
import os

# Base directory for file storage
BASE_DIR = os.getenv('BASE_DIR', '/var/www/es')

# Allowed file extensions
ALLOWED_EXTENSIONS = {
    'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 
    'json', 'csv', 'xml', 'doc', 'docx'
}

# API Authentication Keys
# You can set these via environment variables or modify directly
API_KEYS = {
    os.getenv('API_USER_1', 'admin'): os.getenv('API_KEY_1', 'admin123'),
    os.getenv('API_USER_2', 'user1'): os.getenv('API_KEY_2', 'user1pass'),
    os.getenv('API_USER_3', 'user2'): os.getenv('API_KEY_3', 'user2pass')
}

# Flask configuration
FLASK_CONFIG = {
    'DEBUG': os.getenv('FLASK_DEBUG', 'False').lower() == 'true',
    'HOST': os.getenv('FLASK_HOST', '0.0.0.0'),
    'PORT': int(os.getenv('FLASK_PORT', '5000'))
}
