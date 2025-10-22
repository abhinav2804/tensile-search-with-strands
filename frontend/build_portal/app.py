from flask import Flask, jsonify, request, render_template, redirect, url_for, session
import requests
from descope import DescopeClient, AuthException
from functools import wraps
from flask_cors import CORS
import os
import tempfile
import json
import webbrowser
import threading
from werkzeug.utils import secure_filename
from enhanced_data_pipeline import EnhancedDataPipeline, EnhancedSchemaManager, FixedRemoteElasticsearchManager
from config import CONFIG, PRODUCTION_SERVER
import uuid
from datetime import datetime, timedelta
import shutil
import glob
import sys
import time
import traceback

# Import modular components
from database_module import db as user_db
from chunked_upload_module import upload_large_file
from remote_instance_manager import get_instance_manager
from remote_log_viewer import get_log_viewer

sys.stdout.reconfigure(line_buffering=True)

app = Flask(__name__)
app.secret_key = 'O26pYIWHrk9u+jk9Q3N335C75FU/mnxRbwGRfyNQ'  # Change this in production
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500 MB direct upload limit (chunks handled separately)
CORS(app)

# Configure comprehensive logging
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(name)s] - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)
logger.info("=" * 80)
logger.info("Flask Application Starting - Enhanced Logging Enabled")
logger.info("=" * 80)
logger.info(f"Maximum file upload size: 500 MB")
logger.info(f"Large files (>500MB) will be chunked automatically")

# Descope Configuration
DESCOPE_PROJECT_ID = "P32OxoFpY0ihVvncEbabQARqzw8I"
descope_client = DescopeClient(project_id=DESCOPE_PROJECT_ID)
logger.info(f"Descope client initialized: Project ID = {DESCOPE_PROJECT_ID}")

# User Database - Using modular database module
logger.info(f"User Database: Local JSON storage (easily replaceable)")
logger.info(f"Database file: data/user_database.json")

# Enhanced Pipeline Configuration
pipeline = None
processing_status = {}
ALLOWED_EXTENSIONS = {'json', 'csv', 'xml', 'txt', 'docx', 'zip'}
logger.info(f"Allowed file extensions: {ALLOWED_EXTENSIONS}")

# Cache for stats to reduce frequent Elasticsearch calls
stats_cache = {
    'data': None,
    'timestamp': None,
    'ttl_seconds': 30  # Cache for 30 seconds
}

def get_or_create_user(user_email, user_name, user_id):
    """Get existing user or create new user in the database"""
    logger.info("=" * 60)
    logger.info(f"🔍 DB CALL: get_or_create_user()")
    logger.info(f"   Email: {user_email}")
    logger.info(f"   Name: {user_name}")
    logger.info(f"   User ID: {user_id}")
    
    try:
        # Try to fetch existing user
        existing_user = user_db.get_user_by_email(user_email)
        
        if existing_user:
            logger.info(f"✅ User found: {user_email}")
            logger.info("=" * 60)
            return existing_user
        
        # User doesn't exist, create new one
        logger.info("   User not found, creating new user...")
        new_user_data = {
            "user_id": user_id,
            "email": user_email,
            "name": user_name,
            "has_elasticsearch": False,
            "has_mcp": False,
            "elasticsearch": None,
            "mcp": None
        }
        logger.info(f"   New User Data: {json.dumps(new_user_data, indent=2)}")
        
        created_user = user_db.create_user(new_user_data)
        logger.info(f"✅ New user created: {user_email}")
        logger.info("=" * 60)
        return created_user
            
    except Exception as e:
        logger.error(f"❌ Error in get_or_create_user: {e}")
        logger.info("=" * 60)
        # Return default user data on error
        return {
            "user_id": user_id,
            "email": user_email,
            "name": user_name,
            "has_elasticsearch": False,
            "has_mcp": False
        }

def update_user_status(user_id, elk_status=None, mcp_status=None):
    """Update user's Elasticsearch and MCP hosting status"""
    logger.info("=" * 60)
    logger.info(f"🔄 DB CALL: update_user_status()")
    logger.info(f"   User ID: {user_id}")
    logger.info(f"   ELK Status: {elk_status}")
    logger.info(f"   MCP Status: {mcp_status}")
    
    try:
        update_data = {}
        if elk_status is not None:
            update_data["has_elasticsearch"] = elk_status
        if mcp_status is not None:
            update_data["has_mcp"] = mcp_status
        
        logger.info(f"   Update Data: {json.dumps(update_data, indent=2)}")
        
        success = user_db.update_user(user_id, update_data)
        
        if success:
            logger.info(f"✅ User status updated for {user_id}")
            logger.info("=" * 60)
            return True
        else:
            logger.warning(f"⚠️ Failed to update user status")
            logger.info("=" * 60)
            return False
            
    except Exception as e:
        logger.error(f"❌ Error updating user status: {e}")
        logger.info("=" * 60)
        return False

def get_user_status(user_id):
    """Get current user status from database"""
    logger.info("=" * 60)
    logger.info(f"📊 DB CALL: get_user_status()")
    logger.info(f"   User ID: {user_id}")
    
    try:
        user_data = user_db.get_user(user_id)
        
        if user_data:
            logger.info(f"   User Data: {json.dumps(user_data, indent=2)}")
            
            result = {
                "login_successful": True,
                "hosted_es": user_data.get("has_elasticsearch", False),
                "hosted_mcp": user_data.get("has_mcp", False),
                "user_id": user_data.get("user_id", ""),
                "email": user_data.get("email", ""),
                "name": user_data.get("name", ""),
                "elasticsearch": user_data.get("elasticsearch"),
                "mcp": user_data.get("mcp")
            }
            logger.info(f"   Processed Result: {json.dumps(result, indent=2)}")
            logger.info(f"✅ User status retrieved successfully")
            logger.info("=" * 60)
            return result
        else:
            logger.warning(f"⚠️ User not found: {user_id}")
            logger.info("=" * 60)
            return {
                "login_successful": False,
                "hosted_es": False,
                "hosted_mcp": False
            }
            
    except Exception as e:
        logger.error(f"❌ Error getting user status: {e}")
        logger.info("=" * 60)
        return {
            "login_successful": False,
            "hosted_es": False,
            "hosted_mcp": False
        }

def initialize_pipeline():
    """Initialize the enhanced data pipeline"""
    global pipeline
    try:
        print("Initializing enhanced pipeline...")
        pipeline = EnhancedDataPipeline(
            aws_access_key=CONFIG['aws_access_key'],
            aws_secret_key=CONFIG['aws_secret_key'],
            aws_region=CONFIG['aws_region'],
            es_host=CONFIG['es_host'],
            es_auth=CONFIG['es_auth']
        )
        print("Enhanced pipeline initialized successfully")
        if hasattr(pipeline, 'mcp_enabled'):
            print(f"MCP Integration Status: {'Enabled' if pipeline.mcp_enabled else 'Disabled (fallback mode)'}")
        return True
    except Exception as e:
        print(f"Failed to initialize pipeline: {e}")
        print("Traceback:", traceback.format_exc())
        print("Note: Pipeline will be unavailable until configuration is fixed")
        return False

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def open_browser_delayed(url, delay=3):
    """Open browser after a delay"""
    def delayed_open():
        import time
        time.sleep(delay)
        try:
            webbrowser.open(url)
            logger.info(f"🌐 Browser opened to: {url}")
        except Exception as e:
            logger.error(f"❌ Failed to open browser: {e}")
    
    thread = threading.Thread(target=delayed_open)
    thread.daemon = True
    thread.start()

# Request/Response Logging Middleware
@app.before_request
def log_request():
    """Log all incoming requests"""
    if request.path.startswith('/static'):
        return  # Skip static files
    
    logger.info("=" * 80)
    logger.info(f"📨 INCOMING REQUEST")
    logger.info(f"   Method: {request.method}")
    logger.info(f"   Path: {request.path}")
    logger.info(f"   Remote IP: {request.remote_addr}")
    
    if request.args:
        logger.info(f"   Query Params: {dict(request.args)}")
    
    if request.method in ['POST', 'PUT', 'PATCH']:
        if request.is_json:
            logger.info(f"   JSON Body: {json.dumps(request.json, indent=2)}")
        elif request.form:
            # Don't log file content, just metadata
            form_data = {k: v for k, v in request.form.items()}
            logger.info(f"   Form Data: {json.dumps(form_data, indent=2)}")
        if request.files:
            files_info = {k: f.filename for k, f in request.files.items()}
            logger.info(f"   Files: {json.dumps(files_info, indent=2)}")

@app.after_request
def log_response(response):
    """Log all outgoing responses"""
    if request.path.startswith('/static'):
        return response  # Skip static files
    
    logger.info(f"📤 OUTGOING RESPONSE")
    logger.info(f"   Status Code: {response.status_code}")
    logger.info(f"   Content Type: {response.content_type}")
    
    # Only log JSON responses
    if response.is_json and response.status_code != 200:
        try:
            logger.info(f"   Response Data: {response.get_json()}")
        except:
            pass
    
    logger.info("=" * 80)
    return response

# Login Required Decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'session_token' not in session:
            logger.info(f"🔒 Login required for: {request.path}")
            return redirect('/login')
        try:
            descope_client.validate_session(session['session_token'])
            return f(*args, **kwargs)
        except AuthException:
            session.clear()
            return redirect('/login')
    return decorated_function

@app.route('/')
def home_redirect():
    return landingpage()

@app.route('/login')
def login():
    """Fast-loading login page with immediate Descope component"""
    return f'''<!DOCTYPE html>
<html>
<head>
    <title>Login - Data Portal with MCP Integration</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="preload" href="https://unpkg.com/@descope/web-component@latest/dist/index.js" as="script">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .login-container {{
            background: white;
            padding: 40px;
            border-radius: 10px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            max-width: 400px;
            width: 100%;
        }}
        h1 {{ text-align: center; margin-bottom: 30px; color: #333; }}
        #loading {{ text-align: center; color: #666; }}
        .mcp-badge {{
            background: linear-gradient(135deg, #4f46e5, #7c3aed);
            color: white;
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 0.8rem;
            text-align: center;
            margin-top: 15px;
        }}
    </style>
</head>
<body>
    <div class="login-container">
        <h1>Welcome</h1>
        <div class="mcp-badge">Enhanced with MCP Integration</div>
        <div id="loading">Loading authentication...</div>
        <descope-wc project-id="{DESCOPE_PROJECT_ID}" flow-id="sign-up-or-in" style="display:none;"></descope-wc>
    </div>
    
    <script src="https://unpkg.com/@descope/web-component@latest/dist/index.js"></script>
    <script>
        document.addEventListener('DOMContentLoaded', function() {{
            setTimeout(() => {{
                const loading = document.getElementById('loading');
                const descope = document.querySelector('descope-wc');
                if (descope) {{
                    loading.style.display = 'none';
                    descope.style.display = 'block';
                }}
            }}, 100);
        }});
        
        const descopeWc = document.querySelector('descope-wc');
        descopeWc.addEventListener('success', (e) => {{
            fetch('/auth/callback', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ sessionToken: e.detail.sessionToken }})
            }})
            .then(r => r.json())
            .then(data => {{
                if(data.success) {{
                    window.location.href = data.redirect;
                }} else {{
                    alert('Login failed: ' + data.error);
                }}
            }});
        }});
    </script>
</body>
</html>'''

@app.route('/instances')
@login_required
def instance_manager_page():
    """Render the instance manager page"""
    return render_template('instance_manager.html')

@app.route('/logs')
@login_required
def logs_viewer_page():
    """Render the logs viewer page"""
    return render_template('logs_viewer.html')

@app.route('/')
def landingpage():
    """Render the main portal page - create a simple one if template doesn't exist"""
    try:
        return render_template('index.html')
    except:
        # Fallback to inline HTML if template doesn't exist
        mcp_status = "Enabled" if pipeline and hasattr(pipeline, 'mcp_enabled') and pipeline.mcp_enabled else "Disabled"
        return f'''<!DOCTYPE html>
<html>
<head>
    <title>Data Portal - Enhanced with MCP Integration</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 15px 35px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}
        .content {{ padding: 40px; }}
        .upload-form {{ max-width: 600px; margin: 0 auto; }}
        .form-group {{ margin-bottom: 20px; }}
        .btn {{
            background: #4f46e5;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 6px;
            cursor: pointer;
        }}
        .mcp-status {{
            background: {"#10b981" if mcp_status == "Enabled" else "#f59e0b"};
            color: white;
            padding: 8px 16px;
            border-radius: 20px;
            display: inline-block;
            margin: 10px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Data Discovery Portal</h1>
            <p>Enhanced Elasticsearch Pipeline with MCP Integration</p>
            <div class="mcp-status">MCP Integration: {mcp_status}</div>
        </div>
        <div class="content">
            <div class="upload-form">
                <h2>Upload Data Files</h2>
                <form id="uploadForm" enctype="multipart/form-data">
                    <div class="form-group">
                        <label>Files:</label>
                        <input type="file" name="files" multiple accept=".json,.csv,.xml,.txt,.docx,.zip">
                    </div>
                    <div class="form-group">
                        <label>Deployment:</label>
                        <select name="deployment">
                            <option value="local">Local</option>
                            <option value="remote">Remote (with MCP)</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>User Queries (one per line):</label>
                        <textarea name="userQueries" rows="4" placeholder="Enter search queries..."></textarea>
                    </div>
                    <div class="form-group">
                        <label>Description:</label>
                        <input type="text" name="description" placeholder="Optional description">
                    </div>
                    <button type="submit" class="btn">Upload & Deploy</button>
                </form>
            </div>
        </div>
    </div>
    
    <script>
        document.getElementById('uploadForm').addEventListener('submit', async (e) => {{
            e.preventDefault();
            const formData = new FormData(e.target);
            
            try {{
                const response = await fetch('/upload', {{
                    method: 'POST',
                    body: formData
                }});
                
                const result = await response.json();
                
                if (result.success) {{
                    alert('Upload successful! Check console for details.');
                    console.log('Upload result:', result);
                    if (result.results && result.results[0] && result.results[0].remote_deployment) {{
                        const url = result.results[0].remote_deployment.access_url;
                        if (url) {{
                            window.open(url, '_blank');
                        }}
                    }}
                }} else {{
                    alert('Upload failed: ' + (result.error || 'Unknown error'));
                }}
            }} catch (error) {{
                alert('Upload failed: ' + error.message);
            }}
        }});
    </script>
</body>
</html>'''

@app.route('/auth/callback', methods=['POST'])
def auth_callback():
    try:
        data = request.json
        session_token = data.get('sessionToken')

        if session_token:
            user = descope_client.validate_session(session_token)
            user_id = user.get('userId')
            user_email = user.get('email', 'unknown@example.com')
            user_name = user.get('name', user_email.split('@')[0])
            
            # Get or create user in database
            logger.info("📝 Creating/updating user in database...")
            db_user = get_or_create_user(user_email, user_name, user_id)
            
            # Store in session
            session['session_token'] = session_token
            session['user'] = {
                'id': user_id,
                'email': user_email,
                'name': user_name,
                'db_user_id': db_user.get('user_id'),
                'elk_hosted': db_user.get('has_elasticsearch', False),
                'mcp_hosted': db_user.get('has_mcp', False)
            }
            
            logger.info(f"✅ User logged in: {user_email}")
            logger.info(f"   ES Hosted: {db_user.get('ofELK') == '1'}")
            logger.info(f"   MCP Hosted: {db_user.get('ofMCP') == '1'}")
            logger.info(f"   Session stored: {json.dumps(session.get('user'), indent=2)}")
            logger.info("=" * 80)
            
            return jsonify({'success': True, 'redirect': '/'})

        logger.warning("⚠️ Invalid session token")
        logger.info("=" * 80)
        return jsonify({'success': False, 'error': 'Invalid token'}), 401

    except Exception as e:
        logger.error(f"❌ Auth callback error: {e}")
        traceback.print_exc()
        logger.info("=" * 80)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/logout')
def logout():
    logger.info("=" * 80)
    logger.info("🚪 ENDPOINT: /logout")
    logger.info(f"   User: {session.get('user', {}).get('email', 'unknown')}")
    logger.info("=" * 80)
    session.clear()
    logger.info("✅ Session cleared")
    return redirect('/login')

@app.route('/api/user-status', methods=['GET'])
@login_required
def api_user_status():
    """Get real-time user status from database"""
    logger.info("=" * 80)
    logger.info("🌐 ENDPOINT: /api/user-status [GET]")
    logger.info("=" * 80)
    
    try:
        user_id = session.get('user', {}).get('db_user_id') or session.get('user', {}).get('id')
        logger.info(f"   Session User ID: {user_id}")
        logger.info(f"   Session Data: {json.dumps(session.get('user', {}), indent=2)}")
        
        if not user_id:
            logger.warning("⚠️ User ID not found in session")
            return jsonify({
                'login_successful': True,  # They are logged in if they reached here
                'hosted_es': False,
                'hosted_mcp': False,
                'user_id': 'unknown',
                'error': 'User ID not found in session'
            }), 200
        
        status = get_user_status(user_id)
        
        # If we got here, user IS logged in (passed @login_required)
        status['login_successful'] = True
        
        logger.info(f"✅ Returning status: {json.dumps(status, indent=2)}")
        logger.info("=" * 80)
        return jsonify(status)
        
    except Exception as e:
        logger.error(f"❌ Error getting user status: {e}")
        traceback.print_exc()
        logger.info("=" * 80)
        # Still return success for login since they passed @login_required
        return jsonify({
            'login_successful': True,
            'hosted_es': False,
            'hosted_mcp': False,
            'user_id': session.get('user', {}).get('id', 'unknown'),
            'error': str(e)
        }), 200

@app.route('/api/update-deployment-status', methods=['POST'])
@login_required
def update_deployment_status():
    """Update user's deployment status after successful deployment"""
    logger.info("=" * 80)
    logger.info("🌐 ENDPOINT: /api/update-deployment-status [POST]")
    logger.info("=" * 80)
    
    try:
        data = request.json
        logger.info(f"   Request Data: {json.dumps(data, indent=2)}")
        
        user_id = session.get('user', {}).get('db_user_id') or session.get('user', {}).get('id')
        logger.info(f"   User ID: {user_id}")
        
        elk_status = data.get('elk_hosted')
        mcp_status = data.get('mcp_hosted')
        logger.info(f"   ELK Hosted: {elk_status}")
        logger.info(f"   MCP Hosted: {mcp_status}")
        
        success = update_user_status(user_id, elk_status, mcp_status)
        
        if success:
            # Update session
            if elk_status is not None:
                session['user']['elk_hosted'] = elk_status
            if mcp_status is not None:
                session['user']['mcp_hosted'] = mcp_status
            
            logger.info(f"✅ Deployment status updated successfully")
        else:
            logger.warning(f"⚠️ Failed to update deployment status")
        
        logger.info("=" * 80)
        return jsonify({'success': success})
        
    except Exception as e:
        print(f"Error updating deployment status: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/ask', methods=['POST'])
@login_required
def ask():
    try:
        data = request.get_json()
        chat_input = data.get('chatInput', '').strip()

        if not chat_input:
            return jsonify({"error": "No input provided"}), 400

        webhook_url = "http://54.227.251.28:5678/webhook/search"
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'insomnia/11.2.0',
            'Authorization': f'Bearer {session.get("session_token")}'
        }
        payload = {"chatInput": chat_input}

        response = requests.post(webhook_url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()

        webhook_response = response.text
        return jsonify({
            "success": True,
            "redirect": url_for('result', query=chat_input, response=webhook_response)
        })

    except requests.exceptions.RequestException as e:
        return jsonify({
            "success": True,
            "redirect": url_for('result', query=chat_input, response=f"Error: {str(e)}")
        }), 200
    except Exception as e:
        return jsonify({
            "success": True,
            "redirect": url_for('result', query=chat_input, response=f"Unexpected error: {str(e)}")
        }), 200

@app.route('/result')
def result():
    query = request.args.get('query', 'No query')
    response = request.args.get('response', 'No response')
    try:
        return render_template('result.html', query=query, response=response)
    except:
        return f'''<!DOCTYPE html>
<html><head><title>Search Results</title></head>
<body style="font-family: Arial, sans-serif; padding: 20px;">
<h1>Search Results</h1>
<p><strong>Query:</strong> {query}</p>
<p><strong>Response:</strong> {response}</p>
<a href="/">Back to Portal</a>
</body></html>'''

@app.route('/upload', methods=['POST'])
def upload_files_enhanced():
    """Enhanced file upload with MCP integration and chunked upload for large files"""
    logger.info("=" * 80)
    logger.info("🌐 ENDPOINT: /upload [POST]")
    logger.info("=" * 80)
    
    try:
        if pipeline is None:
            logger.error("❌ Pipeline not initialized")
            return jsonify({'error': 'Pipeline not initialized'}), 500
            
        files = request.files.getlist('files')
        logger.info(f"   Files received: {len(files)}")
        
        if not files:
            logger.warning("⚠️ No files provided")
            return jsonify({'error': 'No files provided'}), 400
        
        # Get form data
        description = request.form.get('description', '').strip()
        user_queries_text = request.form.get('userQueries', '').strip()
        deployment_option = request.form.get('deployment', 'local')
        
        logger.info(f"   Deployment: {deployment_option}")
        logger.info(f"   Description: {description}")
        logger.info(f"   User Queries Text: {user_queries_text[:100]}..." if len(user_queries_text) > 100 else f"   User Queries Text: {user_queries_text}")
        
        # Parse user queries
        user_queries = []
        if user_queries_text:
            user_queries = [q.strip() for q in user_queries_text.split('\n') if q.strip()]
        
        logger.info(f"   Parsed User Queries: {len(user_queries)} queries")
        
        user_id = session.get('user', {}).get('id', 'anonymous')
        logger.info(f"   User ID: {user_id}")
        
        results = []
        
        logger.info(f"📁 Processing {len(files)} files with deployment: {deployment_option}")
        logger.info(f"📝 User queries: {len(user_queries)}")
        logger.info(f"💬 Description: {description}")
        if hasattr(pipeline, 'mcp_enabled'):
            logger.info(f"🔌 MCP Integration: {'Enabled' if pipeline.mcp_enabled else 'Disabled'}")
        
        for file in files:
            if file and file.filename and allowed_file(file.filename):
                # Initialize deployment status variables
                elk_deployed = False
                mcp_deployed = False
                
                try:
                    # Save to temp file ONCE
                    filename = secure_filename(file.filename)
                    file_size = len(file.read())
                    file.seek(0)  # Reset file pointer after reading size
                    
                    logger.info(f"   📄 File: {filename}")
                    logger.info(f"   📊 Size: {file_size / (1024 * 1024):.2f} MB")
                    
                    temp_path = f"temp_{filename}"
                    logger.info(f"   💾 Saving to: {temp_path}")
                    file.save(temp_path)
                    logger.info(f"   ✅ File saved successfully")
                    
                    # ======================================
                    # CHUNKED UPLOAD FOR LARGE FILES (>500MB)
                    # ======================================
                    file_size_mb = file_size / (1024 * 1024)
                    if file_size_mb > 500:
                        logger.info(f"   🚀 LARGE FILE DETECTED: {file_size_mb:.2f} MB")
                        logger.info(f"   📦 Using chunked upload API...")
                        
                        # Use modular chunked upload
                        chunk_result = upload_large_file(
                            file_path=temp_path,
                            user_id=user_id,
                            deployment=deployment_option,
                            description=description
                        )
                        
                        if chunk_result['success']:
                            logger.info(f"   ✅ Chunked upload completed: {chunk_result['chunks_uploaded']}/{chunk_result['total_chunks']} chunks")
                            
                            # Return info about chunked upload
                            results.append({
                                'file': filename,
                                'status': 'uploaded_in_chunks',
                                'upload_id': chunk_result['upload_id'],
                                'total_chunks': chunk_result['total_chunks'],
                                'size_mb': file_size_mb,
                                'message': f'Large file uploaded in {chunk_result["total_chunks"]} chunks (500MB each)'
                            })
                            
                            # Clean up temp file
                            if os.path.exists(temp_path):
                                os.remove(temp_path)
                            
                            continue  # Skip normal processing for chunked files
                        else:
                            logger.error(f"   ❌ Chunked upload failed: {chunk_result.get('errors')}")
                            results.append({
                                'file': filename,
                                'status': 'failed',
                                'error': 'Chunked upload failed'
                            })
                            continue
                    
                    # ======================================
                    # NORMAL PROCESSING FOR FILES <= 500MB
                    # ======================================
                    # File already saved above, just process it
                    
                    # Process with enhanced pipeline
                    base_name = os.path.splitext(filename)[0]
                    base_name = base_name.replace('_', '-')
                    clean_user_id = ''.join(c for c in user_id if c.isalnum())[:10]
                    
                    # Add timestamp to ensure unique index names
                    import time
                    timestamp = int(time.time())
                    index_name = f"upload-{clean_user_id}-{base_name}-{timestamp}".lower()
                    schema_file = f"schemas/{index_name}-schema.json"
                    
                    logger.info(f"   🔄 Processing: {filename} -> {index_name}")
                    logger.info(f"   📝 Schema file: {schema_file}")
                    logger.info(f"   🔍 User queries: {len(user_queries)}")
                    logger.info(f"   🌐 Deploy to remote: {deployment_option == 'remote'}")
                    
                    # Enhanced processing with MCP integration
                    logger.info(f"   ⚙️ Starting pipeline processing...")
                    processing_result = pipeline.process_file_enhanced(
                        file_path=temp_path,
                        index_name=index_name,
                        schema_file=schema_file,
                        user_queries=user_queries,
                        deploy_remote=(deployment_option == 'remote')
                    )
                    logger.info(f"   ✅ Pipeline processing completed")
                    
                    # Build result object
                    result = {
                        'file': filename,
                        'index': index_name,
                        'status': 'completed',
                        'domain_info': processing_result['domain_info'],
                        'schema_file': schema_file,
                        'templates_generated': len(processing_result['domain_info'].get('templates', [])),
                        'domain': processing_result['domain_info'].get('domain', 'unknown'),
                        'total_documents': processing_result['total_documents'],
                        'auto_queries_generated': processing_result['auto_queries_generated'],
                        'user_queries_count': len(user_queries),
                        'attributes_extracted': processing_result['attributes_extracted'],
                        'schema_optimized': processing_result['schema_optimized'],
                        'deployment_target': deployment_option,
                        'mcp_enabled': processing_result.get('mcp_enabled', False)
                    }
                    
                    # Add deployment info based on type
                    if deployment_option == 'remote' and processing_result['deployment_result']:
                        if processing_result['deployment_result']['success']:
                            access_url = processing_result['deployment_result']['access_url']
                            result['remote_deployment'] = {
                                'success': True,
                                'access_url': access_url,
                                'instance_name': processing_result['deployment_result']['instance_name'],
                                'host': processing_result['deployment_result']['host'],
                                'port': processing_result['deployment_result']['port'],
                                'documents_deployed': processing_result['deployment_result'].get('documents_deployed', 0)
                            }
                            
                            # Add MCP integration info if available
                            if hasattr(pipeline, 'mcp_enabled') and pipeline.mcp_enabled:
                                mcp_integration = processing_result['deployment_result'].get('mcp_integration', {})
                                if mcp_integration.get('success'):
                                    result['mcp_integration'] = {
                                        'success': True,
                                        'mcp_url': mcp_integration['mcp_url'],
                                        'capabilities': mcp_integration.get('capabilities', [])
                                    }
                                    print(f"MCP server deployed: {mcp_integration['mcp_url']}")
                                    
                                    # Open both ES and MCP URLs
                                    open_browser_delayed(access_url, delay=2)
                                    open_browser_delayed(mcp_integration['mcp_url'] + '/capabilities', delay=4)
                                else:
                                    result['mcp_integration'] = {
                                        'success': False,
                                        'error': mcp_integration.get('error', 'MCP integration failed')
                                    }
                                    open_browser_delayed(access_url, delay=2)
                            else:
                                # No MCP integration, just open ES URL
                                open_browser_delayed(access_url, delay=2)
                            
                            # Invalidate stats cache
                            stats_cache['timestamp'] = None
                            
                        else:
                            result['remote_deployment'] = {
                                'success': False,
                                'error': processing_result['deployment_result'].get('error', 'Unknown deployment error')
                            }
                    elif deployment_option == 'local' and processing_result.get('local_indexing_success'):
                        # For local deployment
                        local_url = CONFIG['es_host']
                        result['local_deployment'] = {
                            'success': True,
                            'access_url': local_url,
                            'index_name': index_name
                        }
                        
                        # Check if local MCP was set up
                        if hasattr(pipeline, 'mcp_enabled') and pipeline.mcp_enabled:
                            # Add local MCP info if available
                            if hasattr(pipeline.es_manager, 'mcp_integration'):
                                mcp_status = pipeline.es_manager.mcp_integration.get_mcp_status(index_name)
                                if mcp_status and mcp_status.get('status') == 'active':
                                    result['mcp_integration'] = {
                                        'success': True,
                                        'mcp_url': mcp_status['mcp_url']
                                    }
                                    print(f"Local MCP server: {mcp_status['mcp_url']}")
                                    open_browser_delayed(local_url, delay=2)
                                    open_browser_delayed(mcp_status['mcp_url'] + '/capabilities', delay=4)
                        
                        # Invalidate stats cache
                        stats_cache['timestamp'] = None
                        
                        print(f"Local deployment successful! Elasticsearch: {local_url}")
                    
                    results.append(result)
                    
                    # ======================================
                    # UPDATE USER DATABASE WITH ES/MCP CONFIG
                    # ======================================
                    logger.info(f"   💾 Saving deployment config to database...")
                    
                    # Save Elasticsearch configuration
                    if result.get('remote_deployment', {}).get('success') or result.get('local_deployment', {}).get('success'):
                        elk_deployed = True
                        
                        if deployment_option == 'remote':
                            es_config = {
                                "host": result['remote_deployment']['host'],
                                "port": result['remote_deployment']['port'],
                                "instance_name": result['remote_deployment']['instance_name'],
                                "index_name": index_name,
                                "access_url": result['remote_deployment']['access_url'],
                                "created_at": datetime.now().isoformat()
                            }
                        else:
                            es_config = {
                                "host": CONFIG['es_host'],
                                "port": 9200,
                                "instance_name": "local",
                                "index_name": index_name,
                                "access_url": result['local_deployment']['access_url'],
                                "created_at": datetime.now().isoformat()
                            }
                        
                        user_db.update_es_node(user_id, es_config)
                        logger.info(f"      ✅ Elasticsearch config saved")
                    
                    # Save MCP configuration
                    mcp_deployed = False
                    if result.get('mcp_integration', {}).get('success'):
                        mcp_deployed = True
                        mcp_config = {
                            "host": result.get('remote_deployment', {}).get('host', CONFIG['es_host']),
                            "port": 8080,  # Default MCP port
                            "instance_name": f"mcp-{index_name}",
                            "es_instance": index_name,
                            "mcp_url": result['mcp_integration']['mcp_url'],
                            "created_at": datetime.now().isoformat()
                        }
                        user_db.update_mcp_node(user_id, mcp_config)
                        logger.info(f"      ✅ MCP config saved")
                    
                    # Update overall status
                    if elk_deployed or mcp_deployed:
                        update_user_status(user_id, elk_status=elk_deployed, mcp_status=mcp_deployed)
                        logger.info(f"      ✅ User status updated: ES={elk_deployed}, MCP={mcp_deployed}")
                    
                    # Clean up temp file
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                    
                    logger.info(f"✅ Completed processing: {filename}")
                    logger.info(f"   Domain: {processing_result['domain_info'].get('domain', 'unknown')}")
                    logger.info(f"   Templates: {len(processing_result['domain_info'].get('templates', []))}")
                    logger.info(f"   Auto-queries: {processing_result['auto_queries_generated']}")
                    logger.info(f"   Attributes: {processing_result['attributes_extracted']}")
                    
                    # Legacy print statements for backward compatibility
                    user_id = session.get('user', {}).get('db_user_id') or session.get('user', {}).get('id')
                    if user_id:
                        elk_deployed = result.get('remote_deployment', {}).get('success') or result.get('local_deployment', {}).get('success')
                        mcp_deployed = result.get('mcp_integration', {}).get('success')
                        
                        if elk_deployed or mcp_deployed:
                            update_user_status(
                                user_id,
                                elk_status=elk_deployed if elk_deployed else None,
                                mcp_status=mcp_deployed if mcp_deployed else None
                            )
                    
                except Exception as e:
                    print(f"Error processing {filename}: {e}")
                    traceback.print_exc()
                    results.append({
                        'file': filename,
                        'error': str(e),
                        'status': 'failed'
                    })
            else:
                results.append({
                    'file': file.filename if file else 'Unknown',
                    'error': 'Unsupported file type',
                    'status': 'failed'
                })
        
        return jsonify({
            'success': True,
            'results': results,
            'message': f'Processed {len(results)} files with enhanced pipeline',
            'templates_updated': any(r.get('templates_generated', 0) > 0 for r in results),
            'mcp_integrations': len([r for r in results if r.get('mcp_integration', {}).get('success')]),
            'features_enabled': {
                'intelligent_schema': True,
                'attribute_extraction': True,
                'auto_query_generation': True,
                'remote_deployment': deployment_option == 'remote',
                'mcp_integration': hasattr(pipeline, 'mcp_enabled') and pipeline.mcp_enabled,
                'browser_auto_open': True
            }
        })
        
    except Exception as e:
        print(f"Upload error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# Include all your other existing routes here...
@app.route('/domain-config', methods=['GET'])
def get_domain_config():
    try:
        schema_dir = 'schemas'
        os.makedirs(schema_dir, exist_ok=True)
        
        domain_files = []
        for file in os.listdir(schema_dir):
            if file.endswith('-domain.json'):
                domain_files.append(file)
        
        if not domain_files:
            return jsonify({
                'domain': 'general',
                'portal_name': 'Data Discovery Portal with MCP',
                'entity_name': 'record',
                'search_placeholder': 'Describe what you are looking for...',
                'upload_description': 'Upload your data files for analysis with MCP integration',
                'primary_actions': ['search', 'analyze', 'export'],
                'color_scheme': '#8b5cf6',
                'templates': [],
                'auto_queries': []
            })
        
        latest_domain_file = max(domain_files, key=lambda f: os.path.getctime(os.path.join(schema_dir, f)))
        with open(os.path.join(schema_dir, latest_domain_file), 'r') as f:
            domain_config = json.load(f)
        
        domain_config.setdefault('templates', [])
        domain_config.setdefault('auto_queries', [])
        return jsonify(domain_config)
        
    except Exception as e:
        return jsonify({
            'domain': 'general',
            'portal_name': 'Data Discovery Portal with MCP', 
            'entity_name': 'record',
            'search_placeholder': 'Describe what you are looking for...',
            'upload_description': 'Upload your data files for analysis with MCP integration',
            'primary_actions': ['search', 'analyze', 'export'],
            'color_scheme': '#8b5cf6',
            'templates': [],
            'auto_queries': []
        })

@app.route('/api/stats', methods=['GET'])
def get_dynamic_stats():
    global stats_cache
    
    try:
        now = datetime.now()
        if (stats_cache['data'] is not None and 
            stats_cache['timestamp'] is not None and
            (now - stats_cache['timestamp']).total_seconds() < stats_cache['ttl_seconds']):
            return jsonify(stats_cache['data'])
        
        if pipeline is None:
            stats_data = {
                'total_documents': '0',
                'total_indices': '0', 
                'total_fields': '0',
                'avg_query_time': 'N/A',
                'mcp_connections': '0'
            }
        else:
            # Try to get ES stats, handle both enhanced and original managers
            try:
                if hasattr(pipeline.es_manager, 'es') and pipeline.es_manager.es:
                    indices_info = pipeline.es_manager.es.cat.indices(format='json')
                    our_indices = [idx for idx in indices_info if idx['index'].startswith('upload-')]
                    total_docs = sum(int(idx.get('docs.count', 0)) for idx in our_indices)
                    total_indices = len(our_indices)
                else:
                    total_docs = 0
                    total_indices = 0
            except:
                total_docs = 0
                total_indices = 0
            
            # Get field count from schemas
            schema_files = glob.glob('schemas/*-schema.json')
            total_fields = 0
            for schema_file in schema_files:
                try:
                    with open(schema_file, 'r') as f:
                        schema_data = json.load(f)
                        properties = schema_data.get('schema', {}).get('mappings', {}).get('properties', {})
                        total_fields += len(properties)
                except:
                    pass
            
            # Get MCP connection count
            mcp_connections = 0
            if hasattr(pipeline, 'mcp_enabled') and pipeline.mcp_enabled:
                try:
                    mcp_status = pipeline.get_mcp_connections()
                    mcp_connections = mcp_status.get('healthy_count', 0)
                except:
                    pass
            
            stats_data = {
                'total_documents': f"{total_docs:,}" if total_docs > 0 else "0",
                'total_indices': f"{total_indices:,}" if total_indices > 0 else "0",
                'total_fields': f"{total_fields:,}" if total_fields > 0 else "0", 
                'avg_query_time': '< 150ms',
                'mcp_connections': f"{mcp_connections:,}"
            }
        
        stats_cache['data'] = stats_data
        stats_cache['timestamp'] = now
        return jsonify(stats_data)
        
    except Exception as e:
        if stats_cache['data'] is not None:
            return jsonify(stats_cache['data'])
        
        return jsonify({
            'total_documents': '0',
            'total_indices': '0',
            'total_fields': '0',
            'avg_query_time': 'N/A',
            'mcp_connections': '0'
        })

@app.route('/api/query-templates', methods=['GET'])
def get_query_templates():
    """Get generalized query templates for the UI"""
    logger.info("=" * 80)
    logger.info("🌐 ENDPOINT: /api/query-templates [GET]")
    logger.info("=" * 80)
    
    try:
        from config import DEFAULT_QUERY_TEMPLATES
        logger.info(f"   ✅ Returning {len(DEFAULT_QUERY_TEMPLATES)} query templates")
        return jsonify({
            'success': True,
            'templates': DEFAULT_QUERY_TEMPLATES
        })
    except Exception as e:
        logger.error(f"   ❌ Error loading templates: {e}")
        # Return basic fallback templates
        fallback_templates = [
            {
                "name": "Search All",
                "query": {"match_all": {}},
                "description": "Retrieve all documents"
            },
            {
                "name": "Full Text Search",
                "query": {"match": {"_all": "{{search_term}}"}},
                "description": "Search across all fields"
            }
        ]
        return jsonify({
            'success': True,
            'templates': fallback_templates
        })

@app.route('/api/server-config', methods=['GET'])
def get_server_config():
    """Get production server configuration"""
    logger.info("=" * 80)
    logger.info("🌐 ENDPOINT: /api/server-config [GET]")
    logger.info("=" * 80)
    
    try:
        from config import PRODUCTION_SERVER
        logger.info(f"   ✅ Production Server: {PRODUCTION_SERVER['host']}")
        return jsonify({
            'success': True,
            'server': {
                'host': PRODUCTION_SERVER['host'],
                'es_base_port': PRODUCTION_SERVER['es_base_port'],
                'mcp_base_port': PRODUCTION_SERVER['mcp_base_port'],
                'webhook_url': PRODUCTION_SERVER['webhook_url']
            }
        })
    except Exception as e:
        logger.error(f"   ❌ Error loading config: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/health', methods=['GET'])
def health_check():
    mcp_status = {}
    if pipeline and hasattr(pipeline, 'mcp_enabled') and pipeline.mcp_enabled:
        try:
            mcp_connections = pipeline.get_mcp_connections()
            mcp_status = {
                'enabled': True,
                'total_connections': mcp_connections.get('total_count', 0),
                'healthy_connections': mcp_connections.get('healthy_count', 0)
            }
        except:
            mcp_status = {'enabled': True, 'status': 'error'}
    else:
        mcp_status = {'enabled': False}
    
    return jsonify({
        'status': 'healthy',
        'pipeline_ready': pipeline is not None,
        'mcp_integration': mcp_status,
        'features': {
            'intelligent_schema': True,
            'attribute_extraction': True,
            'auto_query_generation': True,
            'remote_deployment': True,
            'domain_detection': True,
            'browser_auto_open': True,
            'mcp_server_integration': hasattr(pipeline, 'mcp_enabled') and pipeline.mcp_enabled if pipeline else False
        },
        'timestamp': datetime.now().isoformat()
    })

# ============================================
# REMOTE INSTANCE MANAGEMENT ENDPOINTS
# ============================================

@app.route('/api/instances/create', methods=['POST'])
@login_required
def create_user_instances():
    """
    Create Elasticsearch and MCP instances for a user
    
    Request body:
    {
        "user_id": "U123456",
        "ssh_password": "optional",
        "open_browser": true
    }
    """
    logger.info("=" * 80)
    logger.info("🚀 API CALL: /api/instances/create")
    logger.info("=" * 80)
    
    try:
        data = request.get_json()
        user_id = data.get('user_id') or session.get('user_id')
        ssh_password = data.get('ssh_password')
        open_browser = data.get('open_browser', True)
        
        if not user_id:
            logger.error("❌ No user_id provided")
            return jsonify({
                'success': False,
                'error': 'user_id is required'
            }), 400
        
        logger.info(f"   User ID: {user_id}")
        logger.info(f"   Open Browser: {open_browser}")
        
        # Get instance manager
        instance_manager = get_instance_manager(ssh_password=ssh_password)
        
        # Create instances
        logger.info("🔄 Creating instances...")
        result = instance_manager.create_user_instances(user_id, open_browser)
        
        if result.get('success'):
            # Store in database
            logger.info("💾 Storing instance info in database...")
            
            es_info = result.get('elasticsearch', {})
            mcp_info = result.get('mcp', {})
            
            # Update ES config
            user_db.update_es_node(user_id, {
                'host': es_info.get('host'),
                'port': es_info.get('port'),
                'url': es_info.get('url'),
                'cluster_name': es_info.get('cluster_name'),
                'node_name': es_info.get('node_name'),
                'status': es_info.get('status'),
                'created_at': es_info.get('created_at')
            })
            
            # Update MCP config
            user_db.update_mcp_node(user_id, {
                'host': mcp_info.get('host'),
                'port': mcp_info.get('port'),
                'url': mcp_info.get('url'),
                'connected_es': mcp_info.get('connected_es'),
                'status': mcp_info.get('status'),
                'created_at': mcp_info.get('created_at')
            })
            
            logger.info("✅ Instance info stored in database")
            logger.info("=" * 80)
            logger.info("✅ Instances created successfully!")
            logger.info("=" * 80)
            
            return jsonify(result), 200
        else:
            logger.error(f"❌ Failed to create instances: {result.get('error')}")
            return jsonify(result), 500
            
    except Exception as e:
        logger.error(f"❌ Error creating instances: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/api/instances/status/<user_id>', methods=['GET'])
@login_required
def get_instance_status(user_id):
    """Get status of user's instances"""
    logger.info(f"📊 API CALL: /api/instances/status/{user_id}")
    
    try:
        # Get from database first
        user = user_db.get_user(user_id)
        
        if not user:
            logger.error(f"❌ User not found: {user_id}")
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404
        
        # Get live status from remote server
        instance_manager = get_instance_manager()
        live_status = instance_manager.get_instance_status(user_id)
        
        # Combine database info with live status
        result = {
            'success': True,
            'user_id': user_id,
            'elasticsearch': {
                'database_info': user.get('elasticsearch'),
                'live_status': live_status.get('elasticsearch', {})
            },
            'mcp': {
                'database_info': user.get('mcp'),
                'live_status': live_status.get('mcp', {})
            }
        }
        
        logger.info(f"✅ Status retrieved for user: {user_id}")
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"❌ Error getting instance status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/instances/stop/<user_id>', methods=['POST'])
@login_required
def stop_user_instances(user_id):
    """Stop user's instances"""
    logger.info(f"🛑 API CALL: /api/instances/stop/{user_id}")
    
    try:
        instance_manager = get_instance_manager()
        result = instance_manager.stop_instances(user_id)
        
        if result.get('success'):
            # Update database
            user_db.update_user(user_id, {
                'elasticsearch': {
                    **(user_db.get_user(user_id).get('elasticsearch', {})),
                    'status': 'stopped'
                },
                'mcp': {
                    **(user_db.get_user(user_id).get('mcp', {})),
                    'status': 'stopped'
                }
            })
            
            logger.info(f"✅ Instances stopped for user: {user_id}")
            return jsonify(result), 200
        else:
            logger.error(f"❌ Failed to stop instances: {result.get('error')}")
            return jsonify(result), 500
            
    except Exception as e:
        logger.error(f"❌ Error stopping instances: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/instances/list', methods=['GET'])
@login_required
def list_all_instances():
    """List all user instances from database"""
    logger.info("📊 API CALL: /api/instances/list")
    
    try:
        # Read all users from database
        db_data = user_db._read_local_db()
        users = db_data.get('users', {})
        
        instances = []
        for user_id, user_data in users.items():
            if user_data.get('has_elasticsearch') or user_data.get('has_mcp'):
                instances.append({
                    'user_id': user_id,
                    'email': user_data.get('email'),
                    'name': user_data.get('name'),
                    'elasticsearch': user_data.get('elasticsearch'),
                    'mcp': user_data.get('mcp'),
                    'has_elasticsearch': user_data.get('has_elasticsearch'),
                    'has_mcp': user_data.get('has_mcp')
                })
        
        logger.info(f"✅ Found {len(instances)} users with instances")
        return jsonify({
            'success': True,
            'instances': instances,
            'total_count': len(instances)
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Error listing instances: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ============================================
# REMOTE LOG VIEWING ENDPOINTS
# ============================================

@app.route('/api/logs/es/<user_id>', methods=['GET'])
@login_required
def get_es_logs(user_id):
    """Get Elasticsearch logs for a user"""
    logger.info(f"📋 API CALL: /api/logs/es/{user_id}")
    
    try:
        lines = int(request.args.get('lines', 100))
        log_viewer = get_log_viewer(ssh_key_path=PRODUCTION_SERVER.get('ssh_key_path'))
        result = log_viewer.get_es_logs(user_id, lines)
        
        if result.get('success'):
            logger.info(f"✅ Retrieved {result.get('total_lines')} ES log lines")
            return jsonify(result), 200
        else:
            logger.error(f"❌ Failed to get ES logs: {result.get('error')}")
            return jsonify(result), 500
            
    except Exception as e:
        logger.error(f"❌ Error getting ES logs: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/logs/mcp/<user_id>', methods=['GET'])
@login_required
def get_mcp_logs(user_id):
    """Get MCP logs for a user"""
    logger.info(f"📋 API CALL: /api/logs/mcp/{user_id}")
    
    try:
        lines = int(request.args.get('lines', 100))
        log_viewer = get_log_viewer(ssh_key_path=PRODUCTION_SERVER.get('ssh_key_path'))
        result = log_viewer.get_mcp_logs(user_id, lines)
        
        if result.get('success'):
            logger.info(f"✅ Retrieved {result.get('total_lines')} MCP log lines")
            return jsonify(result), 200
        else:
            logger.error(f"❌ Failed to get MCP logs: {result.get('error')}")
            return jsonify(result), 500
            
    except Exception as e:
        logger.error(f"❌ Error getting MCP logs: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/logs/system', methods=['GET'])
@login_required
def get_system_logs():
    """Get system logs from remote server"""
    logger.info(f"📋 API CALL: /api/logs/system")
    
    try:
        lines = int(request.args.get('lines', 50))
        log_viewer = get_log_viewer(ssh_key_path=PRODUCTION_SERVER.get('ssh_key_path'))
        result = log_viewer.get_system_logs(lines)
        
        if result.get('success'):
            logger.info(f"✅ Retrieved {result.get('total_lines')} system log lines")
            return jsonify(result), 200
        else:
            logger.error(f"❌ Failed to get system logs: {result.get('error')}")
            return jsonify(result), 500
            
    except Exception as e:
        logger.error(f"❌ Error getting system logs: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/logs/list/<user_id>', methods=['GET'])
@login_required
def list_log_files(user_id):
    """List all log files for a user"""
    logger.info(f"📁 API CALL: /api/logs/list/{user_id}")
    
    try:
        log_viewer = get_log_viewer(ssh_key_path=PRODUCTION_SERVER.get('ssh_key_path'))
        result = log_viewer.list_log_files(user_id)
        
        if result.get('success'):
            logger.info(f"✅ Found {result.get('total_count')} log files")
            return jsonify(result), 200
        else:
            logger.error(f"❌ Failed to list log files: {result.get('error')}")
            return jsonify(result), 500
            
    except Exception as e:
        logger.error(f"❌ Error listing log files: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/logs/search/<user_id>', methods=['GET'])
@login_required
def search_logs(user_id):
    """Search logs for a user"""
    logger.info(f"🔍 API CALL: /api/logs/search/{user_id}")
    
    try:
        search_term = request.args.get('term', '')
        log_type = request.args.get('type', 'es')  # 'es' or 'mcp'
        
        if not search_term:
            return jsonify({
                'success': False,
                'error': 'Search term is required'
            }), 400
        
        log_viewer = get_log_viewer(ssh_key_path=PRODUCTION_SERVER.get('ssh_key_path'))
        result = log_viewer.search_logs(user_id, search_term, log_type)
        
        if result.get('success'):
            logger.info(f"✅ Found {result.get('total_matches')} matches")
            return jsonify(result), 200
        else:
            logger.error(f"❌ Search failed: {result.get('error')}")
            return jsonify(result), 500
            
    except Exception as e:
        logger.error(f"❌ Error searching logs: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/logs/health/<user_id>', methods=['GET'])
@login_required
def get_instance_health(user_id):
    """Get instance health from logs"""
    logger.info(f"🏥 API CALL: /api/logs/health/{user_id}")
    
    try:
        log_viewer = get_log_viewer(ssh_key_path=PRODUCTION_SERVER.get('ssh_key_path'))
        health = log_viewer.get_instance_health(user_id)
        
        logger.info(f"✅ Health check complete for {user_id}")
        return jsonify(health), 200
            
    except Exception as e:
        logger.error(f"❌ Error getting instance health: {e}")
        return jsonify({
            'error': str(e)
        }), 500

# Add remaining essential routes
@app.route('/remote-instances', methods=['GET'])
@login_required
def list_remote_instances():
    try:
        if pipeline is None:
            return jsonify({'error': 'Pipeline not initialized'}), 500
        
        instances = pipeline.get_remote_instances()
        return jsonify({
            'instances': instances,
            'total_count': len(instances)
        })
        
    except Exception as e:
        print(f"Error listing remote instances: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/remote-instances/<instance_name>/stop', methods=['POST'])
@login_required  
def stop_remote_instance(instance_name):
    try:
        if pipeline is None:
            return jsonify({'error': 'Pipeline not initialized'}), 500
        
        success = pipeline.stop_remote_instance(instance_name)
        return jsonify({
            'success': success,
            'message': f'Instance {instance_name} {"stopped" if success else "failed to stop"}'
        })
        
    except Exception as e:
        print(f"Error stopping remote instance: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/remote-instances/<instance_name>/delete', methods=['DELETE'])
@login_required
def delete_remote_instance(instance_name):
    try:
        if pipeline is None:
            return jsonify({'error': 'Pipeline not initialized'}), 500
        
        success = pipeline.delete_remote_instance(instance_name)
        return jsonify({
            'success': success,
            'message': f'Instance {instance_name} {"deleted" if success else "failed to delete"}'
        })
        
    except Exception as e:
        print(f"Error deleting remote instance: {e}")
        return jsonify({'error': str(e)}), 500

# MCP-specific routes
@app.route('/mcp/connections', methods=['GET'])
@login_required
def get_mcp_connections():
    try:
        if pipeline is None:
            return jsonify({'error': 'Pipeline not initialized'}), 500
        
        if hasattr(pipeline, 'get_mcp_connections'):
            connections = pipeline.get_mcp_connections()
            return jsonify(connections)
        else:
            return jsonify({'active_connections': {}, 'total_count': 0, 'healthy_count': 0})
        
    except Exception as e:
        print(f"Error getting MCP connections: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/mcp/test/<instance_name>', methods=['POST'])
@login_required
def test_mcp_connection(instance_name):
    try:
        if pipeline is None:
            return jsonify({'error': 'Pipeline not initialized'}), 500
        
        if hasattr(pipeline, 'test_mcp_connection'):
            result = pipeline.test_mcp_connection(instance_name)
            return jsonify(result)
        else:
            return jsonify({'success': False, 'error': 'MCP integration not available'})
        
    except Exception as e:
        print(f"Error testing MCP connection: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/mcp/status', methods=['GET'])
@login_required
def get_mcp_status():
    try:
        if pipeline is None:
            return jsonify({'error': 'Pipeline not initialized'}), 500
        
        mcp_enabled = hasattr(pipeline, 'mcp_enabled') and pipeline.mcp_enabled
        connections = {}
        
        if mcp_enabled and hasattr(pipeline, 'get_mcp_connections'):
            connections = pipeline.get_mcp_connections()
        
        return jsonify({
            'mcp_enabled': mcp_enabled,
            'active_connections': connections.get('total_count', 0),
            'healthy_connections': connections.get('healthy_count', 0),
            'connection_details': connections.get('active_connections', {}),
            'features': {
                'elasticsearch_integration': True,
                'docker_compose_generation': mcp_enabled,
                'automatic_connection': mcp_enabled,
                'health_monitoring': mcp_enabled
            }
        })
        
    except Exception as e:
        print(f"Error getting MCP status: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/trigger-indexing-live', methods=['GET'])
def trigger_indexing_live():
    """
    Trigger live indexing with real-time progress updates via Server-Sent Events (SSE)
    Integrates with Harshit's indexing API
    
    Query Parameters:
        - user_id: User identifier
        - data_path: Path to data file (optional if using uploaded file)
        - user_query_path: Path to user queries (optional)
        - deployment_id: ID of deployment to get ES details from DB
    """
    from flask import Response, stream_with_context
    
    user_id = request.args.get('user_id', session.get('user', {}).get('id', 'anonymous'))
    data_path = request.args.get('data_path')
    user_query_path = request.args.get('user_query_path')
    deployment_id = request.args.get('deployment_id')
    
    logger.info(f"🚀 Triggering live indexing for user: {user_id}")
    logger.info(f"   Data path: {data_path}")
    logger.info(f"   Query path: {user_query_path}")
    logger.info(f"   Deployment ID: {deployment_id}")
    
    def generate_progress_stream():
        """Generate Server-Sent Events stream with progress updates"""
        try:
            # Step 1: Get ES connection details from DB
            yield f"data: {json.dumps({'step': 'Fetching deployment details', 'status': 'in_progress', 'progress': 5, 'details': 'Connecting to database...'})}\n\n"
            
            es_host = None
            es_port = None
            index_name = None
            
            if deployment_id:
                # Fetch from database using the deployment_id
                try:
                    # Query database API
                    db_api_url = "http://82.112.235.26:4000"
                    response = requests.get(f"{db_api_url}/deployments/{deployment_id}", timeout=10)
                    
                    if response.status_code == 200:
                        dynamo_data = response.json()
                        es_host = dynamo_data.get("es_host")
                        es_port = dynamo_data.get("es_port")
                        index_name = dynamo_data.get("index_name")
                        
                        yield f"data: {json.dumps({'step': 'Fetching deployment details', 'status': 'completed', 'progress': 10, 'details': f'Found ES instance: {es_host}:{es_port}'})}\n\n"
                    else:
                        yield f"data: {json.dumps({'step': 'Fetching deployment details', 'status': 'error', 'progress': 10, 'details': 'Failed to fetch from database'})}\n\n"
                        return
                except Exception as e:
                    logger.error(f"Error fetching from DB: {e}")
                    yield f"data: {json.dumps({'step': 'Fetching deployment details', 'status': 'error', 'progress': 10, 'details': str(e)})}\n\n"
                    return
            else:
                # Use default production server
                es_host = PRODUCTION_SERVER.get('host', '82.112.235.26')
                es_port = 9205  # Default port
                yield f"data: {json.dumps({'step': 'Fetching deployment details', 'status': 'completed', 'progress': 10, 'details': f'Using production ES: {es_host}:{es_port}'})}\n\n"
            
            # Step 2: Forward request to Harshit's indexing API
            indexing_api_url = "http://localhost:8000/triggerIndexingLive"
            params = {
                'user_id': user_id,
                'es_host': es_host,
                'es_port': es_port
            }
            
            if data_path:
                params['data_path'] = data_path
            if user_query_path:
                params['user_query_path'] = user_query_path
            if index_name:
                params['index_name'] = index_name
            
            logger.info(f"   Forwarding to indexing API: {indexing_api_url}")
            logger.info(f"   Parameters: {params}")
            
            yield f"data: {json.dumps({'step': 'Starting indexing process', 'status': 'in_progress', 'progress': 15, 'details': 'Connecting to indexing service...'})}\n\n"
            
            # Stream responses from Harshit's API
            try:
                with requests.get(indexing_api_url, params=params, stream=True, timeout=300) as r:
                    r.raise_for_status()
                    
                    # Stream each line from the indexing API
                    for line in r.iter_lines():
                        if line:
                            decoded_line = line.decode('utf-8')
                            
                            # Forward the SSE event
                            if decoded_line.startswith('data:'):
                                yield f"{decoded_line}\n\n"
                            else:
                                # Wrap non-SSE formatted data
                                try:
                                    data = json.loads(decoded_line)
                                    yield f"data: {json.dumps(data)}\n\n"
                                except json.JSONDecodeError:
                                    # Forward as-is if not JSON
                                    yield f"data: {json.dumps({'step': 'Processing', 'status': 'in_progress', 'details': decoded_line})}\n\n"
                
                logger.info("✅ Indexing stream completed")
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Error connecting to indexing API: {e}")
                yield f"data: {json.dumps({'step': 'Indexing', 'status': 'error', 'progress': 50, 'details': f'Indexing API error: {str(e)}'})}\n\n"
                
        except Exception as e:
            logger.error(f"Error in progress stream: {e}")
            logger.error(traceback.format_exc())
            yield f"data: {json.dumps({'step': 'Error', 'status': 'error', 'progress': 0, 'details': str(e)})}\n\n"
    
    return Response(
        stream_with_context(generate_progress_stream()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive'
        }
    )

@app.route('/api/indexing-status/<deployment_id>', methods=['GET'])
@login_required
def get_indexing_status(deployment_id):
    """
    Get the current status of an indexing operation
    """
    try:
        # Query database for deployment status
        db_api_url = "http://82.112.235.26:4000"
        response = requests.get(f"{db_api_url}/deployments/{deployment_id}/status", timeout=10)
        
        if response.status_code == 200:
            status_data = response.json()
            return jsonify(status_data)
        else:
            return jsonify({'error': 'Failed to fetch status'}), response.status_code
            
    except Exception as e:
        logger.error(f"Error fetching indexing status: {e}")
        return jsonify({'error': str(e)}), 500

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return jsonify({'error': 'Page not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    print(f"Internal server error: {error}")
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    print("="*60)
    print("ENHANCED ELASTICSEARCH PIPELINE WITH MCP INTEGRATION")
    print("="*60)
    
    # Create necessary directories
    os.makedirs('schemas', exist_ok=True)
    os.makedirs('uploads', exist_ok=True)
    os.makedirs('mcp_configs', exist_ok=True)
    print("Created necessary directories")
    
    # Initialize enhanced pipeline
    print("\nInitializing pipeline...")
    pipeline_success = initialize_pipeline()
    
    if pipeline_success:
        print("Pipeline initialization successful")
        if hasattr(pipeline, 'mcp_enabled'):
            print(f"MCP Integration: {'Enabled' if pipeline.mcp_enabled else 'Disabled (fallback mode)'}")
    else:
        print("Pipeline initialization failed - some features may be unavailable")
    
    print("\nStarting Flask server...")
    print("Server will be available at: http://localhost:7000")
    print("Main portal: http://localhost:7000/")
    
    print("\nAvailable features:")
    print("  - Intelligent Schema Generation")
    print("  - Attribute Extraction")  
    print("  - Auto-Query Generation")
    print("  - Remote Elasticsearch Deployment")
    print("  - MCP Server Integration (if enabled)")
    print("  - Automatic Browser Opening")
    print("  - Enhanced SSH Authentication")
    
    print("\nKey endpoints:")
    print("  POST /upload - Enhanced upload with MCP")
    print("  GET /remote-instances - List remote ES instances")
    print("  GET /mcp/connections - List MCP connections")
    print("  GET /mcp/status - MCP integration status")
    print("  GET /health - System health check")
    
    try:
        app.run(host='0.0.0.0', port=7000, debug=True)
    except Exception as e:
        print(f"\nFailed to start Flask server: {e}")
        print("Make sure port 7000 is not already in use")
        print("Try: lsof -i :7000")
        sys.exit(1)
