from flask import Flask, request, jsonify, render_template, redirect, url_for, session
import requests
import os
import uuid
import math
from werkzeug.utils import secure_filename
import tempfile
import base64
import time

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Change this in production

# Remote API endpoints (defaults to api.lehana.in, override with env vars)
DB_API_URL = os.getenv("DB_API_URL", "http://82.112.235.26:4000/users")
UPLOAD_API_URL = os.getenv("UPLOAD_API_URL", "https://api.lehana.in/build_search/upload")
SEARCH_API_URL = os.getenv("SEARCH_API_URL", "https://api.lehana.in/build_search/query")

# API credentials
API_USER = os.getenv("API_USER", "admin")
API_PASS = os.getenv("API_PASS", "admin123")
API_AUTH = base64.b64encode(f'{API_USER}:{API_PASS}'.encode()).decode('ascii')
HEADERS = {'Authorization': f'Basic {API_AUTH}'}

# Configuration
MAX_CHUNK_SIZE = 500 * 1024 * 1024  # 500MB
UPLOAD_FOLDER = tempfile.gettempdir()

@app.route('/')
def index():
    """Serve the main portal directly at root ('/')."""
    # Prefer environment variable; fall back to provided project id for convenience in dev
    project_id = os.getenv('DESCOPE_PROJECT_ID', 'P32OxoFpY0ihVvncEbabQARqzw8I')
    flow_id = os.getenv('DESCOPE_FLOW_ID', 'passwords-with-explicit-sign-up')
    return render_template('esportal.html', 
                         descope_project_id=project_id,
                         descope_flow_id=flow_id)


@app.route('/api/user-status')
def user_status():
    """Return lightweight user status for the widget after login.

    This keeps it simple for now: if the user is in session, login is successful.
    Flags for hosted services can later be wired to a real backend.
    """
    email = session.get('user_email')
    unique_key = session.get('unique_key')
    has_es = False
    has_mcp = False
    # TODO: Integrate a real check against your infra/DB if available
    return jsonify({
        'login': bool(email),
        'has_es': has_es,
        'has_mcp': has_mcp,
        'email': email or '',
        'unique_key': (unique_key or '')
    })


@app.route('/api/logout', methods=['POST'])
def api_logout():
    """Clear server session for logout and return success."""
    session.clear()
    return jsonify({'success': True})

@app.route('/esportal')
def esportal_page():
    """Main portal page"""
    # Prefer environment variable; fall back to provided project id for convenience in dev
    project_id = os.getenv('DESCOPE_PROJECT_ID', 'P32OxoFpY0ihVvncEbabQARqzw8I')
    flow_id = os.getenv('DESCOPE_FLOW_ID', 'passwords-with-explicit-sign-up')
    return render_template('esportal.html', 
                         descope_project_id=project_id,
                         descope_flow_id=flow_id)

@app.route('/auth/info')
def auth_info():
    """Expose current Descope configuration for debugging in dev"""
    return jsonify({
        'projectId': os.getenv('DESCOPE_PROJECT_ID', 'P32OxoFpY0ihVvncEbabQARqzw8I'),
        'flowId': os.getenv('DESCOPE_FLOW_ID', 'passwords-with-explicit-sign-up')
    })

@app.route('/domain-config')
def domain_config():
    """Return sample templates for the frontend"""
    return jsonify({
        "templates": [
            {
                "title": "Cement Raw Materials Overview",
                "prompt": "Summarize cement raw materials across all indices: list top material types, counts, and typical suppliers.",
                "category": "materials"
            },
            {
                "title": "Building Materials Availability",
                "prompt": "Find building materials with available stock and lead time under 14 days. Return name, SKU/code, unit, stock, and lead time.",
                "category": "b2b"
            },
            {
                "title": "Industrial Products Aggregation",
                "prompt": "Aggregate B2B industrial products by category and show counts and average unit price per category.",
                "category": "analytics"
            },
            {
                "title": "Recent Additions (7 days)",
                "prompt": "Show items added or updated in the last 7 days across all available indices with timestamp and source index.",
                "category": "recent"
            },
            {
                "title": "Supplier Directory",
                "prompt": "List suppliers found across indices with the materials/products they provide and contact fields when available.",
                "category": "suppliers"
            },
            {
                "title": "Cross-index Search (Generic)",
                "prompt": "Search across all indices for 'telecommunications' or 'mobile devices'. If none found, clearly state that no such data exists and list the indices that are available instead.",
                "category": "discovery"
            }
        ]
    })

@app.route('/api/user/upsert', methods=['POST'])
def upsert_user():
    """
    API 1: Database API - Store or update user information
    Creates unique ID for new users, stores in remote DB
    """
    try:
        data = request.get_json()
        email = data.get('email')
        name = data.get('name', '')
        user_id = data.get('userId')
        
        if not email:
            return jsonify({'error': 'Email is required'}), 400
        
        # Generate unique ID if not provided (deterministic based on email for consistency)
        if not user_id:
            user_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, email))
        
        print(f"[USER UPSERT] email={email} name={name} userId={user_id}")
        
        # First, check if user already exists
        check_url = f"{DB_API_URL}/{user_id}"
        print(f"[USER CHECK] Checking if user exists: GET {check_url}")
        
        try:
            check_response = requests.get(
                check_url,
                headers={'Authorization': f'Basic {API_AUTH}'},
                timeout=10
            )
            user_exists = check_response.status_code == 200
            print(f"[USER CHECK] User exists: {user_exists} (status={check_response.status_code})")
        except Exception as e:
            print(f"[USER CHECK] Error checking user: {e}")
            user_exists = False
        
        # Prepare JSON payload for remote DB API (expects JSON with capitalized fields)
        db_payload = {
            'UserId': user_id,  # Capitalized as per API spec
            'ofELK': user_id,   # Using user_id for ofELK field
            'name': name,
            'email': email
        }
        
        # Call remote database API with Basic Auth and JSON format
        start = time.time()
        response = requests.post(
            DB_API_URL, 
            headers={
                'Authorization': f'Basic {API_AUTH}',
                'Content-Type': 'application/json'
            },
            json=db_payload,  # JSON format (not form-data)
            timeout=30
        )
        duration = round((time.time() - start)*1000)
        print(f"[UPSTREAM] POST {DB_API_URL} status={response.status_code} timeMs={duration}")
        
        if response.status_code == 200 or response.status_code == 201:
            try:
                response_data = response.json() if response.content else {}
                print(f"[UPSTREAM] Response data: {response_data}")
            except:
                print(f"[UPSTREAM] Response text: {response.text}")
            
            # Store user info in session for later use
            session['user_email'] = email
            session['unique_key'] = user_id
            session['user_name'] = name
            
            # Parse DB response to check for ES and MCP status
            db_response = {}
            try:
                db_response = response.json() if response.content else {}
            except:
                db_response = {}
            
            # Check if user has Elasticsearch and MCP from DB response
            has_es = db_response.get('hasElasticsearch', False) or db_response.get('has_es', False)
            has_mcp = db_response.get('hasMCP', False) or db_response.get('has_mcp', False)
            
            return jsonify({
                'success': True,
                'uniqueKey': user_id,
                'email': email,
                'message': 'User created/updated successfully',
                'hasElasticsearch': has_es,
                'hasMCP': has_mcp,
                'has_es': has_es,
                'has_mcp': has_mcp,
                'meta': {'upstream': DB_API_URL, 'status': response.status_code, 'timeMs': duration}
            })
        else:
            # Even if DB fails, store locally in session
            session['user_email'] = email
            session['unique_key'] = user_id
            session['user_name'] = name
            
            return jsonify({
                'success': True,
                'uniqueKey': user_id,
                'email': email,
                'message': 'User stored locally (DB unavailable)',
                'hasElasticsearch': False,
                'hasMCP': False,
                'has_es': False,
                'has_mcp': False,
                'warning': f'Remote DB returned {response.status_code}',
                'meta': {'upstream': DB_API_URL, 'status': response.status_code, 'timeMs': duration}
            })
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"[ERROR] /api/user/upsert failed: {str(e)}")
        
        # Fallback: store in session even on error
        if email:
            user_id = user_id or str(uuid.uuid5(uuid.NAMESPACE_DNS, email))
            session['user_email'] = email
            session['unique_key'] = user_id
            session['user_name'] = name
            
            return jsonify({
                'success': True,
                'uniqueKey': user_id,
                'email': email,
                'message': 'User stored locally (error connecting to DB)',
                'error_details': str(e)
            })
        
        return jsonify({'error': str(e)}), 500

@app.route('/api/upload/proxy', methods=['POST'])
def upload_proxy():
    """
    API 2: Upload API - Handle file uploads with chunking
    Processes large files in 500MB chunks and sends queries on last chunk
    """
    try:
        # Get form data
        userid = request.form.get('userid')
        uniquekey = request.form.get('uniquekey', '')
        chunk_index = request.form.get('chunk_index', '0')
        total_chunks = request.form.get('total_chunks', '1')
        is_last = request.form.get('is_last', 'false').lower() == 'true'
        temperature = request.form.get('temperature', '0.3')
        queries = request.form.get('queries', '')  # Only on last chunk
        
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not userid:
            return jsonify({'error': 'User ID is required'}), 400
        
        print(f"[UPLOAD] chunk={int(chunk_index)+1}/{total_chunks} file={file.filename} is_last={is_last} userid={userid} uniquekey={uniquekey[:10]}...")
        
        # FIRST: Upload the file chunk with filetype=data
        files = {'file': (file.filename, file.stream, file.content_type or 'application/octet-stream')}
        data = {
            'userid': userid,
            'uniquekey': uniquekey,
            'filetype': 'data',  # Always 'data' for file uploads
            'temperature': str(temperature)
        }
        
        # Call remote upload API with Basic Auth
        start = time.time()
        response = requests.post(
            UPLOAD_API_URL,
            headers={'Authorization': f'Basic {API_AUTH}'},
            files=files,
            data=data,  # form-data format
            timeout=600  # 10 minutes for large files
        )
        duration = round((time.time() - start)*1000)
        print(f"[UPSTREAM] POST {UPLOAD_API_URL} file={file.filename} filetype=data status={response.status_code} timeMs={duration}")
        
        if response.status_code != 200:
            error_text = response.text
            print(f"[UPLOAD ERROR] Response body: {error_text}")
            return jsonify({
                'error': 'Upload failed',
                'details': error_text,
                'status_code': response.status_code,
                'meta': {'upstream': UPLOAD_API_URL, 'status': response.status_code, 'timeMs': duration}
            }), response.status_code
        
        # Log successful response
        try:
            response_data = response.json() if response.content else {}
            print(f"[UPLOAD] File upload response: {response_data}")
        except:
            print(f"[UPLOAD] File upload response (text): {response.text[:200]}")
        
        # Build initial result
        result = {
            'success': True,
            'chunk_index': chunk_index,
            'total_chunks': total_chunks,
            'is_last': is_last,
            'filename': file.filename,
            'meta': {'upstream': UPLOAD_API_URL, 'status': response.status_code, 'timeMs': duration}
        }
        
        # SECOND: If this is the last chunk AND queries provided, make a separate API call with filetype=query
        if is_last and queries:
            print(f"[UPLOAD] Sending queries as separate request with filetype=query: {queries[:100]}...")
            
            # Create a text file with the queries content
            query_filename = f"{userid}_queries.txt"
            query_file_data = queries.encode('utf-8')
            
            query_files = {'file': (query_filename, query_file_data, 'text/plain')}
            query_data = {
                'userid': userid,
                'uniquekey': uniquekey,
                'filetype': 'query',  # Different filetype for queries
                'temperature': str(temperature)
            }
            
            # Make second API call for queries
            query_start = time.time()
            query_response = requests.post(
                UPLOAD_API_URL,
                headers={'Authorization': f'Basic {API_AUTH}'},
                files=query_files,
                data=query_data,
                timeout=600
            )
            query_duration = round((time.time() - query_start)*1000)
            print(f"[UPSTREAM] POST {UPLOAD_API_URL} file={query_filename} filetype=query status={query_response.status_code} timeMs={query_duration}")
            
            if query_response.status_code == 200:
                try:
                    query_response_data = query_response.json() if query_response.content else {}
                    print(f"[UPLOAD] Queries upload response: {query_response_data}")
                except:
                    print(f"[UPLOAD] Queries upload response (text): {query_response.text[:200]}")
                
                result['queries_uploaded'] = True
                result['query_response'] = {
                    'status': query_response.status_code,
                    'timeMs': query_duration
                }
                result['message'] = 'File and queries uploaded successfully'
            else:
                error_text = query_response.text
                print(f"[UPLOAD ERROR] Queries upload failed: {error_text}")
                result['queries_uploaded'] = False
                result['query_error'] = error_text
                result['message'] = 'File uploaded but queries failed'
        
        if is_last and not queries:
            result['message'] = 'File upload completed successfully'
        
        return jsonify(result)
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"[ERROR] /api/upload/proxy failed: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/search', methods=['POST'])
def search_proxy():
    """
    API 3: Search API - Handle search queries
    Forward to remote API with form-data format
    """
    try:
        # Accept both JSON and form data
        if request.is_json:
            data = request.get_json()
            query = data.get('query', '')
            userid = data.get('userid')
            uniquekey = data.get('uniquekey', '')
            temperature = data.get('temperature', 0.3)
        else:
            query = request.form.get('query', '')
            userid = request.form.get('userid')
            uniquekey = request.form.get('uniquekey', '')
            temperature = request.form.get('temperature', '0.3')
        
        if not query:
            return jsonify({'error': 'Query is required'}), 400
        
        if not userid:
            # Try to get from session
            userid = session.get('user_email', 'user123')
            uniquekey = session.get('unique_key', '')
        
        print(f"[SEARCH] query={query} userid={userid} uniquekey={uniquekey[:10]}... temp={temperature}")
        
        # Prepare form data for remote search API (expects form data, NOT JSON)
        search_data = {
            'userid': userid,
            'uniquekey': uniquekey,
            'query': query,
            'temperature': str(temperature)
        }
        
        # Call remote search API with form-data and Basic Auth
        start = time.time()
        response = requests.post(
            SEARCH_API_URL,
            headers={'Authorization': f'Basic {API_AUTH}'},
            data=search_data,  # form-data, not JSON
            timeout=600  # 10 minutes for long queries
        )
        duration = round((time.time() - start)*1000)
        print(f"[UPSTREAM] POST {SEARCH_API_URL} status={response.status_code} timeMs={duration}")
        
        if response.status_code == 200:
            payload = None
            try:
                payload = response.json() if response.content else None
            except Exception:
                payload = response.text
            return jsonify({
                'success': True,
                'output': payload,  # Match result.html expectation
                'results': payload,
                'query': query,
                'userid': userid,
                'meta': {'upstream': SEARCH_API_URL, 'status': response.status_code, 'timeMs': duration}
            })
        else:
            return jsonify({
                'error': 'Search failed',
                'details': response.text,
                'status_code': response.status_code,
                'meta': {'upstream': SEARCH_API_URL, 'status': response.status_code, 'timeMs': duration}
            }), response.status_code
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"[ERROR] /api/search failed: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Add alias route for frontend compatibility
@app.route('/search', methods=['POST'])
def search_alias():
    """Alias for /api/search to match frontend calls"""
    return search_proxy()

@app.route('/result')
def result_page():
    """Results page that calls the search API"""
    query = request.args.get('q', '')
    if not query:
        return redirect(url_for('index'))
    
    # Get user info from session
    userid = session.get('user_email', 'anonymous')
    
    try:
        # Call our search API
        search_data = {
            'query': query,
            'userid': userid
        }
        
        # Make internal API call
        import json
        from flask import current_app
        
        with current_app.test_client() as client:
            response = client.post('/api/search', 
                                 data=json.dumps(search_data),
                                 content_type='application/json')
            
            if response.status_code == 200:
                result_data = response.get_json()
                results = result_data.get('results', {})
            else:
                results = {'error': 'Search failed'}
    
    except Exception as e:
        results = {'error': str(e)}
    
    return render_template('result.html', query=query, results=results)

@app.route('/auth/callback', methods=['POST'])
def auth_callback():
    """Handle authentication callback from Descope"""
    try:
        data = request.get_json()
        session_token = data.get('sessionToken')
        
        if session_token:
            # Store the session token (you might want to validate it)
            session['auth_token'] = session_token
            return jsonify({'success': True})
        
        return jsonify({'error': 'No session token provided'}), 400
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health')
def health_check():
    """Simple health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'apis': {
            'db_api': DB_API_URL,
            'upload_api': UPLOAD_API_URL,
            'search_api': SEARCH_API_URL
        }
    })

if __name__ == '__main__':
    # Ensure upload folder exists
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.run(debug=True, host='0.0.0.0', port=7000)
