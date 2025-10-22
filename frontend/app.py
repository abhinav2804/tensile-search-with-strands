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
from config import CONFIG
from db_registry import DBUserRegistry
import uuid
from datetime import datetime, timedelta
import shutil
import glob
import sys
import time
import traceback
sys.stdout.reconfigure(line_buffering=True)

app = Flask(__name__)
app.secret_key = 'O26pYIWHrk9u+jk9Q3N335C75FU/mnxRbwGRfyNQ'  # Change this in production
CORS(app)

# Descope Configuration
DESCOPE_PROJECT_ID = "P32OxoFpY0ihVvncEbabQARqzw8I"
descope_client = DescopeClient(project_id=DESCOPE_PROJECT_ID)

# Enhanced Pipeline Configuration
pipeline = None
processing_status = {}
ALLOWED_EXTENSIONS = {'json', 'csv', 'xml', 'txt', 'docx', 'zip'}

# Cache for stats to reduce frequent Elasticsearch calls
stats_cache = {
    'data': None,
    'timestamp': None,
    'ttl_seconds': 30  # Cache for 30 seconds
}

# External DB user registry
user_registry = DBUserRegistry(CONFIG.get('db_api_base'))

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
            print(f"Browser opened to: {url}")
        except Exception as e:
            print(f"Failed to open browser: {e}")
    
    thread = threading.Thread(target=delayed_open)
    thread.daemon = True
    thread.start()

# Login Required Decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'session_token' not in session:
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
    return redirect('/esportal')

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

@app.route('/esportal')
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
        return jsonify({
            'logged_in': logged_in,
            'user': user_info,
            'es': es_status,
            'mcp': mcp_status,
            'index': index_status,
            'index_name': index_name,
            'db_instance': db_instance
        })
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
            print(f"[AUTH] Received session token length={len(session_token)}")
            user = descope_client.validate_session(session_token)
            print(f"[AUTH] Descope validate_session ok userId={user.get('userId')} email={user.get('email')}")
            user_id = user.get('userId')
            session['session_token'] = session_token
            session['user'] = {
                'id': user_id,
                'email': user.get('email'),
                'name': user.get('name')
            }
            # Fetch or create DB record (non-fatal if fails)
            try:
                print(f"[AUTH][DB] ensure_user start user_id={user_id}")
                db_user = user_registry.ensure_user(user_id)
                session['user_db'] = db_user
                print(f"[AUTH][DB] ensure_user success indices={db_user.get('indices')} es_host={db_user.get('es_host')} es_port={db_user.get('es_port')} mcp_url={db_user.get('mcp_url')}")
            except Exception as e:
                session['user_db_error'] = str(e)
                print(f"[AUTH][DB] ensure_user error: {e}")
            print("[AUTH] Login flow complete -> returning success")
            return jsonify({'success': True, 'redirect': '/esportal'})

        return jsonify({'success': False, 'error': 'Invalid token'}), 401

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

@app.route('/ask', methods=['POST'])
@login_required
def ask():
    try:
        data = request.get_json()
        chat_input = data.get('chatInput', '').strip()

        if not chat_input:
            return jsonify({"error": "No input provided"}), 400
        # Decide search path: direct ES vs remote webhook
        es_response_text = None
        used_path = None
        try:
            db_user = session.get('user_db') or {}
            es_host = db_user.get('es_host')
            es_port = db_user.get('es_port')
            # Basic validation: both host and port exist
            if es_host and es_port:
                used_path = 'direct-es'
                import json as _json
                from elasticsearch import Elasticsearch as _ES
                es_url = f"http://{es_host}:{es_port}" if '://' not in es_host else f"{es_host}:{es_port}" if not str(es_host).endswith(str(es_port)) else es_host
                print(f"[ASK] Using direct ES search at {es_url} query='{chat_input}'")
                es_client = _ES([es_url], verify_certs=False, request_timeout=10)
                # We search across indices that start with 'upload-' or fall back to _all
                try:
                    indices_cat = es_client.cat.indices(format='json')
                    candidate_indices = [i['index'] for i in indices_cat if i.get('index','').startswith('upload-')]
                except Exception:
                    candidate_indices = []
                target_index = ','.join(candidate_indices) if candidate_indices else '_all'
                es_result = es_client.search(index=target_index, size=5, body={
                    'query': { 'multi_match': { 'query': chat_input, 'fields': ['*'] } }
                })
                # Format a lightweight text summary
                hits = es_result.get('hits', {}).get('hits', [])
                summary_lines = [f"Top {len(hits)} results (index:_source excerpt):"]
                for h in hits:
                    src = h.get('_source', {})
                    # pick first 2 fields for brevity
                    kv = list(src.items())[:2]
                    kv_text = ', '.join(f"{k}={str(v)[:40]}" for k,v in kv)
                    summary_lines.append(f"- {h.get('_index')}: {kv_text}")
                es_response_text = '\n'.join(summary_lines) if hits else 'No matching documents found.'
            else:
                used_path = 'webhook'
        except Exception as e:
            print(f"[ASK] Direct ES path failed: {e}")
            used_path = 'webhook'

        if used_path == 'webhook':
            webhook_url = "http://54.227.251.28:5678/webhook/search"
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'insomnia/11.2.0',
                'Authorization': f'Bearer {session.get("session_token")}'
            }
            payload = {"chatInput": chat_input}
            print(f"[ASK] Using webhook search at {webhook_url} query='{chat_input}'")
            response = requests.post(webhook_url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            result_text = response.text
        else:
            result_text = es_response_text or 'No results.'

        # Indicate which path used in result string
        decorated = f"[{used_path}]\n{result_text}"
        return jsonify({
            "success": True,
            "redirect": url_for('result', query=chat_input, response=decorated)
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
<a href="/esportal">Back to Portal</a>
</body></html>'''

@app.route('/upload', methods=['POST'])
def upload_files_enhanced():
    """Enhanced file upload with MCP integration and automatic browser opening"""
    try:
        if pipeline is None:
            return jsonify({'error': 'Pipeline not initialized'}), 500
            
        files = request.files.getlist('files')
        if not files:
            return jsonify({'error': 'No files provided'}), 400
        
        # Get form data
        description = request.form.get('description', '').strip()
        user_queries_text = request.form.get('userQueries', '').strip()
        deployment_option = request.form.get('deployment', 'local')
        
        # Parse user queries
        user_queries = []
        if user_queries_text:
            user_queries = [q.strip() for q in user_queries_text.split('\n') if q.strip()]
        
        user_id = session.get('user', {}).get('id', 'anonymous')
        results = []
        
        print(f"Processing {len(files)} files with deployment: {deployment_option}")
        print(f"User queries: {len(user_queries)}")
        print(f"Description: {description}")
        if hasattr(pipeline, 'mcp_enabled'):
            print(f"MCP Integration: {'Enabled' if pipeline.mcp_enabled else 'Disabled'}")
        
        # Determine if user has existing remote instance (DB info in session); ensure DB record exists
        db_user = session.get('user_db')
        if not db_user and 'user' in session and user_registry:
            try:
                print(f"[UPLOAD][DB] No user_db in session; ensuring user in DB for user_id={user_id}")
                ensured = user_registry.ensure_user(session['user']['id'])
                session['user_db'] = ensured
                db_user = ensured
                print(f"[UPLOAD][DB] ensure_user result keys={list(ensured.keys())}")
            except Exception as e:
                print(f"[UPLOAD][DB] ensure_user failed: {e}")
        reuse_remote = False
        existing_remote_host = None
        existing_remote_port = None
        if deployment_option == 'remote' and db_user:
            existing_remote_host = db_user.get('es_host')
            existing_remote_port = db_user.get('es_port')
            if existing_remote_host and existing_remote_port:
                reuse_remote = True

        for file in files:
            if file and file.filename and allowed_file(file.filename):
                try:
                    # Save to temp file
                    filename = secure_filename(file.filename)
                    temp_path = f"temp_{filename}"
                    print(f"Saving file: {filename}")
                    file.save(temp_path)
                    
                    # Process with enhanced pipeline
                    base_name = os.path.splitext(filename)[0]
                    base_name = base_name.replace('_', '-')
                    clean_user_id = ''.join(c for c in user_id if c.isalnum())[:10]
                    
                    # Add timestamp to ensure unique index names
                    import time
                    timestamp = int(time.time())
                    index_name = f"upload-{clean_user_id}-{base_name}-{timestamp}".lower()
                    schema_file = f"schemas/{index_name}-schema.json"
                    
                    print(f"Processing {filename} -> {index_name}")
                    print(f"User queries provided: {len(user_queries)}")
                    print(f"Deploy to remote: {deployment_option == 'remote'}")
                    
                    # Decide deploy mode: True (new), 'reuse', or False
                    deploy_mode = False
                    if deployment_option == 'remote':
                        if reuse_remote:
                            deploy_mode = 'reuse'
                            os.environ['REMOTE_ES_HOST'] = existing_remote_host
                            os.environ['REMOTE_ES_PORT'] = str(existing_remote_port)
                        else:
                            deploy_mode = True

                    # Enhanced processing with MCP integration
                    processing_result = pipeline.process_file_enhanced(
                        file_path=temp_path,
                        index_name=index_name,
                        schema_file=schema_file,
                        user_queries=user_queries,
                        deploy_remote=deploy_mode
                    )
                    
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
                    elif deployment_option == 'remote' and reuse_remote:
                        # We reused an existing remote instance; just record minimal info
                        result['remote_deployment'] = {
                            'success': True,
                            'access_url': f"http://{existing_remote_host}:{existing_remote_port}",
                            'host': existing_remote_host,
                            'port': existing_remote_port,
                            'instance_name': 'existing',
                            'documents_deployed': processing_result.get('total_documents', 0)
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

                    # --- DB persistence of instance + new index ---
                    try:
                        if session.get('user_db'):
                            user_db = session['user_db']
                            depl = processing_result.get('deployment_result')
                            print(f"[UPLOAD][DB] Persistence start deployment_option={deployment_option} reuse_remote={reuse_remote} index={index_name}")
                            if deployment_option == 'remote' and depl and depl.get('success'):
                                print(f"[UPLOAD][DB] New remote deployment success host={depl.get('host')} port={depl.get('port')} mcp_url={ (depl.get('mcp_integration', {}) or {}).get('mcp_url') or depl.get('mcp_url') }")
                                user_registry.update_instances(user_db,
                                    es_host=depl.get('host'),
                                    es_port=depl.get('port'),
                                    mcp_url=(depl.get('mcp_integration', {}) or {}).get('mcp_url') or depl.get('mcp_url'),
                                    indices=(user_db.get('indices') or []) + [index_name])
                                session['user_db'] = user_registry.ensure_user(user_db.get('UserId'))
                                print(f"[UPLOAD][DB] Post-update session indices={session['user_db'].get('indices')}")
                            elif deployment_option == 'remote' and reuse_remote:
                                print(f"[UPLOAD][DB] Reusing remote instance host={existing_remote_host} port={existing_remote_port}; appending index")
                                user_registry.append_index(user_db, index_name)
                                session['user_db'] = user_registry.ensure_user(user_db.get('UserId'))
                                print(f"[UPLOAD][DB] Post-append session indices={session['user_db'].get('indices')}")
                            elif deployment_option == 'local':
                                print(f"[UPLOAD][DB] Local deployment; appending index {index_name}")
                                user_registry.append_index(user_db, index_name)
                                session['user_db'] = user_registry.ensure_user(user_db.get('UserId'))
                                print(f"[UPLOAD][DB] Post-local session indices={session['user_db'].get('indices')}")
                        else:
                            print("[UPLOAD][DB] Skipping persistence: no user_db in session")
                    except Exception as e:
                        print(f"[UPLOAD][DB] Persistence error: {e}")
                    
                    # Clean up temp file
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                    
                    print(f"Completed processing: {filename}")
                    print(f"Domain: {processing_result['domain_info'].get('domain', 'unknown')}")
                    print(f"Templates: {len(processing_result['domain_info'].get('templates', []))}")
                    print(f"Auto-queries: {processing_result['auto_queries_generated']}")
                    print(f"Attributes: {processing_result['attributes_extracted']}")
                    
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
                    # Use a low-level ping first with short timeout to avoid 10s delays
                    try:
                        pipeline.es_manager.es.ping(params={"request_timeout": 1})
                    except Exception:
                        raise RuntimeError("ES unreachable")
                    indices_info = pipeline.es_manager.es.cat.indices(format='json', params={"request_timeout": 2})
                    our_indices = [idx for idx in indices_info if idx.get('index','').startswith('upload-')]
                    total_docs = sum(int(idx.get('docs.count', 0) or 0) for idx in our_indices)
                    total_indices = len(our_indices)
                else:
                    total_docs = 0
                    total_indices = 0
            except Exception:
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

@app.route('/api/user/status', methods=['GET'])
def user_status_widget_endpoint():
    """Lightweight status endpoint consumed by the inline User Status widget.

    Contract expected by frontend widget (see DISPLAY_FIELDS in template):
      {
        login: <bool>,            # True if authenticated session
        email: <str|null>,        # User email (if available)
        userId: <str|null>,       # Internal user id (if available)
        esInstance: <str|null>,   # Simple ES host indicator (optional)
        mcpInstance: <str|null>,  # "enabled" or null if not enabled
        indexName: <str|null>     # Most recent indexed upload-* schema base name if present
      }
    """
    login = False
    user_email = None
    user_id = None
    try:
        if 'session_token' in session:
            try:
                descope_client.validate_session(session['session_token'])
                login = True
                user_info = session.get('user', {})
                user_email = user_info.get('email') or user_info.get('name')
                user_id = user_info.get('id')
            except AuthException:
                # Invalidate bad session
                session.clear()
    except Exception:
        # Fail closed (login stays False) but do not raise
        pass

    # Derive ES instance (very lightweight – just the configured host)
    es_instance = None
    if pipeline is not None:
        try:
            es_instance = CONFIG.get('es_host') or None
        except Exception:
            es_instance = None

    # MCP indicator
    mcp_instance = None
    try:
        if pipeline is not None and getattr(pipeline, 'mcp_enabled', False):
            mcp_instance = 'enabled'
    except Exception:
        mcp_instance = None

    # Attempt to discover the most recent upload index name from schemas directory
    index_name = None
    try:
        schema_dir = 'schemas'
        if os.path.isdir(schema_dir):
            upload_schema_files = [f for f in os.listdir(schema_dir) if f.endswith('-schema.json') and f.startswith('upload-')]
            if upload_schema_files:
                latest_file = max(upload_schema_files, key=lambda f: os.path.getctime(os.path.join(schema_dir, f)))
                # Strip suffix "-schema.json"
                index_name = latest_file[:-12] if latest_file.endswith('-schema.json') else latest_file
    except Exception:
        index_name = None

    # If DB record present, override with more precise instance info
    if login and 'user_db' in session:
        dbu = session['user_db']
        es_host_db = dbu.get('es_host')
        es_port_db = dbu.get('es_port')
        if es_host_db and es_port_db:
            es_instance = f"{es_host_db}:{es_port_db}".rstrip(':')
        if dbu.get('mcp_url'):
            mcp_instance = dbu.get('mcp_url')
        # Prefer last index in indices list if available
        idxs = dbu.get('indices') or []
        if idxs:
            index_name = idxs[-1]

    payload = {
        'login': login,
        'email': user_email,
        'userId': user_id,
        'esInstance': es_instance if login else None,
        'mcpInstance': mcp_instance if login else None,
        'indexName': index_name if login else None
    }
    # Never fail with 500 – frontend treats non-200 as failure and shows crosses
    return jsonify(payload), 200

@app.route('/api/user/db-sync', methods=['POST'])
def api_user_db_sync():
    """Force ensure the user exists in external DB; returns record and whether it was newly created.
    Frontend can call this right after Descope login to guarantee DB insertion and then refresh status widget."""
    try:
        if 'session_token' not in session or 'user' not in session:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        user_id = session['user']['id']
        before = session.get('user_db')
        created = False
        # If no record or missing fields, ensure again.
        try:
            ensured = user_registry.ensure_user(user_id)
            if not before:
                created = True
            else:
                # Heuristic: if previous indices list length differs, not 'created'
                created = False
            session['user_db'] = ensured
            print(f"[DB-SYNC] ensure_user user_id={user_id} created={created} indices={ensured.get('indices')} es_host={ensured.get('es_host')} es_port={ensured.get('es_port')} mcp_url={ensured.get('mcp_url')}")
            return jsonify({'success': True, 'created': created, 'record': ensured})
        except Exception as e:
            print(f"[DB-SYNC] error: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

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

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return jsonify({'error': 'Page not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    print(f"Internal server error: {error}")
    return jsonify({'error': 'Internal server error'}), 500

# --- Legacy / safety stub routes to squash stray 404 requests ---
@app.route('/user-status.js')
def legacy_user_status_js():
    """Return a harmless stub so legacy cached references stop 404ing.
    This can be removed later once you confirm browsers no longer request it."""
    stub = "console.info('[legacy-user-status.js] Stub served; widget now inlined.');"
    return stub, 200, {'Content-Type': 'application/javascript', 'Cache-Control': 'no-cache'}

@app.route('/favicon.ico')
def favicon_stub():
    return ('', 204)

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
    print("Main portal: http://localhost:7000/esportal")
    
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
