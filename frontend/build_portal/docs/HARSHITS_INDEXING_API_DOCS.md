# 🚀 HARSHIT'S INDEXING API - COMPLETE DOCUMENTATION

## 📋 API Information

**Service Name:** Indexing Agent  
**Technology:** FastAPI (uvicorn)  
**Port:** 8000  
**Host:** 0.0.0.0 (accessible from any IP)

---

## 🎯 PURPOSE

This API processes uploaded files and indexes them to Elasticsearch using AWS Bedrock for AI enhancement.

**What It Does:**
1. Reads data from uploaded files (CSV/JSON)
2. Processes data in chunks
3. Enhances data using AWS Bedrock (AI processing)
4. Indexes enhanced data to Elasticsearch
5. Provides real-time progress updates via Server-Sent Events (SSE)

---

## 🔧 SETUP & INSTALLATION

### Step 1: Navigate to Project Directory
```bash
cd /home/hs/imgpt/tensile-search-with-strands/indexing-agent
```

### Step 2: Start the Service
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Command Breakdown:**
- `uvicorn` - ASGI server for FastAPI
- `app.main:app` - Module path to FastAPI app instance
- `--reload` - Auto-reload on code changes (development mode)
- `--host 0.0.0.0` - Listen on all network interfaces
- `--port 8000` - Run on port 8000

### Expected Output:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

---

## 📡 API ENDPOINT

### Trigger Live Indexing

**Endpoint:** `GET /triggerIndexingLive`

**Base URL:** `http://localhost:8000`

**Full URL:**
```
http://localhost:8000/triggerIndexingLive?user_id={user_id}&data_path={data_path}&user_query_path={user_query_path}
```

---

## 📥 REQUEST PARAMETERS

### Query Parameters (All Required)

| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| `user_id` | string | ✅ Yes | User's unique identifier | `"123"` |
| `data_path` | string | ✅ Yes | Absolute path to data file | `"/home/hs/imgpt/data"` |
| `user_query_path` | string | ✅ Yes | Absolute path to user query/config | `"/home/hs/imgpt/user"` |

---

## 🎯 EXAMPLE REQUESTS

### Example 1: Basic Call
```bash
curl "http://localhost:8000/triggerIndexingLive?user_id=123&data_path=/home/hs/imgpt/data&user_query_path=/home/hs/imgpt/user"
```

### Example 2: Using Python
```python
import requests

url = "http://localhost:8000/triggerIndexingLive"
params = {
    "user_id": "123",
    "data_path": "/home/hs/imgpt/data",
    "user_query_path": "/home/hs/imgpt/user"
}

response = requests.get(url, params=params, stream=True)

# For SSE (Server-Sent Events)
for line in response.iter_lines():
    if line:
        print(line.decode('utf-8'))
```

### Example 3: Using PowerShell
```powershell
$uri = "http://localhost:8000/triggerIndexingLive?user_id=123&data_path=/home/hs/imgpt/data&user_query_path=/home/hs/imgpt/user"
Invoke-WebRequest -Uri $uri -Method GET
```

### Example 4: Using JavaScript (EventSource for SSE)
```javascript
const userId = "123";
const dataPath = "/home/hs/imgpt/data";
const userQueryPath = "/home/hs/imgpt/user";

const url = `http://localhost:8000/triggerIndexingLive?user_id=${userId}&data_path=${dataPath}&user_query_path=${userQueryPath}`;

const eventSource = new EventSource(url);

eventSource.onmessage = (event) => {
    console.log("Progress:", event.data);
};

eventSource.onerror = (error) => {
    console.error("Error:", error);
    eventSource.close();
};
```

---

## 📤 RESPONSE FORMAT

### Response Type: Server-Sent Events (SSE)

**Content-Type:** `text/event-stream`

**Stream Format:**
```
data: {"status": "started", "message": "Starting indexing process"}

data: {"status": "progress", "percentage": 10, "message": "Reading file..."}

data: {"status": "progress", "percentage": 25, "message": "Processing chunk 1/4"}

data: {"status": "progress", "percentage": 50, "message": "AWS Bedrock enhancing data..."}

data: {"status": "progress", "percentage": 75, "message": "Indexing to Elasticsearch..."}

data: {"status": "complete", "percentage": 100, "message": "Indexing complete", "documents_indexed": 1000}
```

### Status Types

| Status | Description |
|--------|-------------|
| `started` | Indexing process has begun |
| `progress` | In-progress update with percentage |
| `complete` | Successfully completed |
| `error` | An error occurred |

---

## 🔗 INTEGRATION WITH YOUR FLASK APP

### Current Integration in `app.py`

Your Flask app already has the integration code at lines 1761-1900:

```python
@app.route('/api/trigger-indexing-live')
def trigger_indexing_live():
    """
    Trigger live indexing via Harshit's API
    Streams progress updates using Server-Sent Events
    """
    deployment_id = request.args.get('deployment_id')
    
    if not deployment_id:
        return jsonify({"error": "deployment_id is required"}), 400
    
    # Fetch deployment details from database
    db_result = get_user_deployment_details(deployment_id)
    
    if not db_result["success"]:
        return jsonify({"error": "Failed to fetch deployment details"}), 500
    
    user_data = db_result["data"]
    
    # Extract Elasticsearch details
    es_host = user_data.get("es_host")
    es_port = user_data.get("es_port")
    user_id = user_data.get("UserId")
    
    # Call Harshit's API
    harshit_api_url = f"http://localhost:8000/triggerIndexingLive"
    params = {
        "user_id": user_id,
        "data_path": f"/path/to/data/{deployment_id}",  # Adjust path
        "user_query_path": f"/path/to/queries/{user_id}"  # Adjust path
    }
    
    def generate():
        try:
            response = requests.get(harshit_api_url, params=params, stream=True)
            for line in response.iter_lines():
                if line:
                    yield f"data: {line.decode('utf-8')}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'
        }
    )
```

### How to Use from Frontend

```javascript
// Trigger indexing for a deployment
const deploymentId = "upload-anonymous-10k-kwds-1758005731";

const eventSource = new EventSource(
    `/api/trigger-indexing-live?deployment_id=${deploymentId}`
);

eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log("Progress:", data);
    
    // Update UI with progress
    updateProgressBar(data.percentage);
    updateStatusMessage(data.message);
    
    if (data.status === 'complete') {
        console.log("Indexing complete!");
        eventSource.close();
    }
};

eventSource.onerror = (error) => {
    console.error("Error:", error);
    eventSource.close();
};
```

---

## 🧪 TESTING

### Test 1: Check if Service is Running

```bash
# Test health/root endpoint
curl http://localhost:8000/
```

**Expected Response:**
```json
{
    "message": "Indexing Agent API",
    "version": "1.0",
    "status": "running"
}
```

### Test 2: Trigger Indexing

```bash
curl "http://localhost:8000/triggerIndexingLive?user_id=test123&data_path=/tmp/test_data&user_query_path=/tmp/test_query"
```

**Expected Response:**
Stream of SSE messages with progress updates

### Test 3: Test from Python

```python
import requests

def test_indexing_api():
    """Test Harshit's indexing API"""
    
    url = "http://localhost:8000/triggerIndexingLive"
    params = {
        "user_id": "test123",
        "data_path": "/tmp/test_data",
        "user_query_path": "/tmp/test_query"
    }
    
    try:
        response = requests.get(url, params=params, stream=True, timeout=5)
        
        if response.status_code == 200:
            print("✅ API is accessible")
            print("✅ Streaming response received")
            
            # Read first few lines
            for i, line in enumerate(response.iter_lines()):
                if i >= 5:  # Only read first 5 lines
                    break
                if line:
                    print(f"Progress: {line.decode('utf-8')}")
            
            return True
        else:
            print(f"❌ Unexpected status: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect - Is the service running?")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    test_indexing_api()
```

---

## ⚠️ TROUBLESHOOTING

### Issue 1: Connection Refused

**Error:** `Connection refused on port 8000`

**Solution:**
```bash
# Check if service is running
netstat -an | grep 8000

# If not running, start it:
cd /home/hs/imgpt/tensile-search-with-strands/indexing-agent
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Issue 2: Port Already in Use

**Error:** `Address already in use`

**Solution:**
```bash
# Find process using port 8000
lsof -i :8000

# Kill the process
kill -9 <PID>

# Or use a different port
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

### Issue 3: Module Not Found

**Error:** `ModuleNotFoundError: No module named 'app'`

**Solution:**
```bash
# Make sure you're in the correct directory
cd /home/hs/imgpt/tensile-search-with-strands/indexing-agent

# Check if app directory exists
ls -la app/

# Install dependencies
pip install -r requirements.txt
```

### Issue 4: Path Not Found

**Error:** Data path or query path doesn't exist

**Solution:**
- Ensure paths are absolute (start with `/`)
- Verify paths exist on the server
- Check file permissions

---

## 📊 INTEGRATION WORKFLOW

### Complete Flow:

```
1. User uploads file to Flask
   ↓
2. Flask saves file and creates deployment
   ↓
3. User clicks "Index Data" button
   ↓
4. Frontend calls Flask: /api/trigger-indexing-live?deployment_id=xxx
   ↓
5. Flask fetches deployment details from database
   ↓
6. Flask calls Harshit's API: http://localhost:8000/triggerIndexingLive
   ↓
7. Harshit's API processes data with AWS Bedrock
   ↓
8. Progress updates stream back through Flask to frontend
   ↓
9. Data indexed to Elasticsearch
   ↓
10. User can query via MCP
```

---

## 🔐 SECURITY NOTES

### Current Setup (Development):
- Service runs on `0.0.0.0` (accessible from any IP)
- No authentication required
- No rate limiting

### For Production:
```bash
# Run on localhost only
uvicorn app.main:app --host 127.0.0.1 --port 8000

# Or add authentication/API keys in the FastAPI app
```

---

## 📝 CONFIGURATION

### Environment Variables (if needed)

Create `.env` file in indexing-agent directory:
```bash
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_REGION=us-east-1
ELASTICSEARCH_HOST=localhost
ELASTICSEARCH_PORT=9200
```

### Load in FastAPI:
```python
from dotenv import load_dotenv
import os

load_dotenv()

aws_key = os.getenv('AWS_ACCESS_KEY_ID')
```

---

## 🎯 QUICK REFERENCE

### Start Service:
```bash
cd /home/hs/imgpt/tensile-search-with-strands/indexing-agent
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Stop Service:
```bash
# Press CTRL+C in the terminal where it's running
# Or find and kill process:
pkill -f "uvicorn app.main:app"
```

### Test Endpoint:
```bash
curl "http://localhost:8000/triggerIndexingLive?user_id=123&data_path=/home/hs/imgpt/data&user_query_path=/home/hs/imgpt/user"
```

### Check Status:
```bash
curl http://localhost:8000/
```

---

## 📞 INTEGRATION CHECKLIST

- [ ] Service is running on port 8000
- [ ] Can access `http://localhost:8000/`
- [ ] Paths are correctly configured
- [ ] Flask integration endpoint exists at `/api/trigger-indexing-live`
- [ ] Frontend can connect via EventSource/SSE
- [ ] Database returns correct deployment details
- [ ] Progress updates stream correctly
- [ ] Elasticsearch is accessible for indexing

---

## 🎉 STATUS

**Service:** Harshit's Indexing API  
**Status:** ⏸️ Ready to start  
**Integration:** ✅ Code complete in Flask  
**Documentation:** ✅ Complete  
**Testing:** ⏳ Waiting for service to start

**To Test:** Start the service and run comprehensive tests!
