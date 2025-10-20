from flask import Flask, request, jsonify
import os
import uuid
import base64
from functools import wraps
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Configuration
BASE_DIR = "/var/www/es"
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'json', 'csv', 'xml', 'doc', 'docx'}

# Authentication configuration
API_KEYS = {
    'admin': 'admin123',
    'user1': 'user1pass',
    'user2': 'user2pass'
}

# You can also set these via environment variables
# API_KEYS = {
#     os.getenv('API_USER_1', 'admin'): os.getenv('API_KEY_1', 'admin123'),
#     os.getenv('API_USER_2', 'user1'): os.getenv('API_KEY_2', 'user1pass'),
#     os.getenv('API_USER_3', 'user2'): os.getenv('API_KEY_3', 'user2pass')
# }

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def require_auth(f):
    """Decorator to require authentication for endpoints"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        if not auth_header:
            return jsonify({'error': 'Authorization header is required'}), 401
        
        try:
            # Check for Basic Auth format
            if auth_header.startswith('Basic '):
                # Decode Basic Auth
                encoded_credentials = auth_header.split(' ')[1]
                decoded_credentials = base64.b64decode(encoded_credentials).decode('utf-8')
                username, password = decoded_credentials.split(':', 1)
                
                if username not in API_KEYS or API_KEYS[username] != password:
                    return jsonify({'error': 'Invalid credentials'}), 401
                    
            # Check for API Key format (X-API-Key header)
            elif request.headers.get('X-API-Key'):
                api_key = request.headers.get('X-API-Key')
                if api_key not in API_KEYS.values():
                    return jsonify({'error': 'Invalid API key'}), 401
                    
            # Check for Bearer token format
            elif auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
                if token not in API_KEYS.values():
                    return jsonify({'error': 'Invalid token'}), 401
                    
            else:
                return jsonify({'error': 'Unsupported authentication method'}), 401
                
        except Exception as e:
            return jsonify({'error': f'Authentication failed: {str(e)}'}), 401
        
        return f(*args, **kwargs)
    return decorated_function

def create_directory_structure(userid):
    """Create directory structure for user"""
    user_dir = os.path.join(BASE_DIR, str(userid))
    data_dir = os.path.join(user_dir, "data")
    query_dir = os.path.join(user_dir, "query")
    
    # Create directories if they don't exist
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(query_dir, exist_ok=True)
    
    return user_dir, data_dir, query_dir

@app.route('/upload', methods=['POST'])
@require_auth
def upload_file():
    """Upload file endpoint"""
    try:
        # Validate required parameters
        if 'userid' not in request.form:
            return jsonify({'error': 'userid is required'}), 400
        
        if 'filetype' not in request.form:
            return jsonify({'error': 'filetype is required'}), 400
        
        if 'file' not in request.files:
            return jsonify({'error': 'file is required'}), 400
        
        userid = request.form['userid']
        filetype = request.form['filetype'].lower()
        file = request.files['file']
        
        # Validate filetype
        if filetype not in ['data', 'query']:
            return jsonify({'error': 'filetype must be either "data" or "query"'}), 400
        
        # Validate file
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'File type not allowed'}), 400
        
        # Create base directory if it doesn't exist
        os.makedirs(BASE_DIR, exist_ok=True)
        
        # Create user directory structure
        _, data_dir, query_dir = create_directory_structure(userid)
        
        # Choose target directory based on filetype
        if filetype == 'data':
            target_dir = data_dir
        else:  # filetype == 'query'
            target_dir = query_dir
        
        # Secure the filename and save file
        filename = secure_filename(file.filename)
        # Add timestamp to avoid filename conflicts
        name, ext = os.path.splitext(filename)
        unique_filename = f"{name}_{uuid.uuid4().hex[:8]}{ext}"
        file_path = os.path.join(target_dir, unique_filename)
        
        file.save(file_path)
        
        return jsonify({
            'message': 'File uploaded successfully',
            'userid': userid,
            'filetype': filetype,
            'filename': unique_filename,
            'file_path': file_path,
            'file_size': os.path.getsize(file_path)
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'message': 'API is running'}), 200

@app.route('/list/<userid>', methods=['GET'])
@require_auth
def list_user_files(userid):
    """List files for a specific user"""
    try:
        user_dir = os.path.join(BASE_DIR, str(userid))
        
        if not os.path.exists(user_dir):
            return jsonify({'message': f'No files found for user {userid}', 'files': []}), 200
        
        files = []
        for filetype in ['data', 'query']:
            type_dir = os.path.join(user_dir, filetype)
            if os.path.exists(type_dir):
                for filename in os.listdir(type_dir):
                    file_path = os.path.join(type_dir, filename)
                    if os.path.isfile(file_path):
                        files.append({
                            'filename': filename,
                            'filetype': filetype,
                            'file_path': file_path,
                            'file_size': os.path.getsize(file_path),
                            'created_at': os.path.getctime(file_path)
                        })
        
        return jsonify({
            'userid': userid,
            'files': files,
            'total_files': len(files)
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to list files: {str(e)}'}), 500

if __name__ == '__main__':
    # Create base directory if it doesn't exist
    os.makedirs(BASE_DIR, exist_ok=True)
    app.run(debug=True, host='0.0.0.0', port=5000)
