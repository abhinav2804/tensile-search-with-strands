# Chunked Upload API Documentation

## 🌐 API Endpoint

**URL:** `https://16eae2f0d5b0.ngrok-free.app/upload`  
**Method:** `POST`  
**Authentication:** Basic Auth (Username: `admin`, Password: `admin123`)  
**Content-Type:** `multipart/form-data`

---

## 📤 Request Format

### Form Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | Binary | Yes | The chunk data (max 500MB) |
| `userid` | String | Yes | User identifier |
| `filetype` | String | Yes | Type of file (`data`, `config`, `log`) |
| `chunk_number` | String | Yes | Current chunk number (1-indexed) |
| `total_chunks` | String | Yes | Total number of chunks |
| `upload_id` | String | Yes | Unique upload session ID |
| `original_filename` | String | Yes | Original file name |

---

## 📦 Chunking Logic

### When Chunks Are Created
- Files **> 500MB** are automatically chunked
- Files **≤ 500MB** are uploaded directly (no chunking)

### Chunk Size
- **500 MB** per chunk (524,288,000 bytes)

### Chunk Naming Pattern
```
{original_name}_chunk_{number}_of_{total}.{ext}
```

**Examples:**
- `data_chunk_001_of_003.csv`
- `myfile_chunk_001_of_010.json`
- `large_dataset_chunk_005_of_020.txt`

---

## 🔧 How It Works (Flask Integration)

### 1. File Upload Detection
```python
# In app.py, line 785-790
file_size_mb = file_size / (1024 * 1024)
if file_size_mb > 500:
    logger.info(f"   🚀 LARGE FILE DETECTED: {file_size_mb:.2f} MB")
    logger.info(f"   📦 Using chunked upload API...")
```

### 2. Chunked Upload Triggered
```python
# In app.py, line 793-799
chunk_result = upload_large_file(
    file_path=temp_path,
    user_id=user_id,
    deployment=deployment_option,
    description=description
)
```

### 3. Module Processing
The `chunked_upload_module.py` handles:
- Splitting file into 500MB chunks
- Calculating total chunks needed
- Uploading each chunk sequentially
- Tracking success/failure

### 4. API Request Example

**Request for Chunk 1 of 3:**
```http
POST https://16eae2f0d5b0.ngrok-free.app/upload
Authorization: Basic YWRtaW46YWRtaW4xMjM=
Content-Type: multipart/form-data; boundary=----WebKitFormBoundary

------WebKitFormBoundary
Content-Disposition: form-data; name="file"; filename="data_chunk_001_of_003.csv"
Content-Type: application/octet-stream

[... 500MB binary data ...]
------WebKitFormBoundary
Content-Disposition: form-data; name="userid"

user123
------WebKitFormBoundary
Content-Disposition: form-data; name="filetype"

data
------WebKitFormBoundary
Content-Disposition: form-data; name="chunk_number"

1
------WebKitFormBoundary
Content-Disposition: form-data; name="total_chunks"

3
------WebKitFormBoundary
Content-Disposition: form-data; name="upload_id"

user123_data.csv_1729468800
------WebKitFormBoundary
Content-Disposition: form-data; name="original_filename"

data.csv
------WebKitFormBoundary--
```

---

## 📊 Response Format

### Successful Chunk Upload
```json
{
  "success": true,
  "chunk_number": 1,
  "total_chunks": 3,
  "upload_id": "user123_data.csv_1729468800",
  "message": "Chunk 1 of 3 uploaded successfully"
}
```

### Upload Complete (All Chunks)
```json
{
  "success": true,
  "upload_id": "user123_data.csv_1729468800",
  "total_chunks": 3,
  "successful_chunks": 3,
  "failed_chunks": 0,
  "file_size_mb": 1450.5,
  "chunk_details": [
    {
      "success": true,
      "chunk_number": 1,
      "chunk_filename": "data_chunk_001_of_003.csv"
    },
    {
      "success": true,
      "chunk_number": 2,
      "chunk_filename": "data_chunk_002_of_003.csv"
    },
    {
      "success": true,
      "chunk_number": 3,
      "chunk_filename": "data_chunk_003_of_003.csv"
    }
  ]
}
```

### Error Response
```json
{
  "success": false,
  "error": "HTTP 500: Internal Server Error",
  "chunk_number": 2
}
```

---

## 🗂️ Code Structure

### Main Module: `chunked_upload_module.py`

**Key Classes:**
- `ChunkedFileUploader` - Handles chunking and upload logic

**Key Functions:**
- `upload_large_file()` - Main entry point (called by Flask)
- `upload_file_in_chunks()` - Orchestrates chunk uploads
- `upload_chunk()` - Uploads a single chunk
- `get_chunk_filename()` - Generates chunk filenames

### Flask Integration: `app.py`

**Import:**
```python
from chunked_upload_module import upload_large_file
```

**Usage (line 793-811):**
```python
# Detect large file
if file_size_mb > 500:
    # Use chunked upload
    chunk_result = upload_large_file(
        file_path=temp_path,
        user_id=user_id,
        deployment=deployment_option,
        description=description
    )
    
    if chunk_result['success']:
        results.append({
            'file': filename,
            'status': 'uploaded_in_chunks',
            'upload_id': chunk_result['upload_id'],
            'total_chunks': chunk_result['total_chunks'],
            'size_mb': file_size_mb,
            'message': f'Large file uploaded in {chunk_result["total_chunks"]} chunks'
        })
```

---

## 📈 Example Scenarios

### Scenario 1: 600MB File
- **Total Chunks:** 2
- **Chunk 1:** 500MB (0-524,288,000 bytes)
- **Chunk 2:** 100MB (524,288,000-629,145,600 bytes)
- **Filenames:**
  - `file_chunk_001_of_002.csv`
  - `file_chunk_002_of_002.csv`

### Scenario 2: 2.5GB File
- **Total Chunks:** 5
- **Chunk 1-4:** 500MB each
- **Chunk 5:** 500MB
- **Filenames:**
  - `file_chunk_001_of_005.csv`
  - `file_chunk_002_of_005.csv`
  - `file_chunk_003_of_005.csv`
  - `file_chunk_004_of_005.csv`
  - `file_chunk_005_of_005.csv`

### Scenario 3: 300MB File
- **Total Chunks:** 0 (no chunking)
- **Uploaded directly** via normal `/upload` endpoint

---

## 🔒 Server-Side Reassembly

The server receiving chunks should:

1. **Identify chunks** by `upload_id`
2. **Store chunks** temporarily
3. **Track progress** using `chunk_number` and `total_chunks`
4. **Reassemble** when all chunks received
5. **Validate** file integrity
6. **Process** the complete file
7. **Clean up** temporary chunks

**Example Server Logic:**
```python
# Pseudocode for server-side handling
uploads_in_progress = {}  # {upload_id: {chunks: []}}

def handle_chunk_upload(request):
    upload_id = request.form['upload_id']
    chunk_num = int(request.form['chunk_number'])
    total_chunks = int(request.form['total_chunks'])
    chunk_data = request.files['file'].read()
    
    # Store chunk
    if upload_id not in uploads_in_progress:
        uploads_in_progress[upload_id] = {
            'chunks': [None] * total_chunks,
            'original_filename': request.form['original_filename']
        }
    
    uploads_in_progress[upload_id]['chunks'][chunk_num - 1] = chunk_data
    
    # Check if all chunks received
    if all(c is not None for c in uploads_in_progress[upload_id]['chunks']):
        # Reassemble
        complete_file = b''.join(uploads_in_progress[upload_id]['chunks'])
        
        # Save
        with open(uploads_in_progress[upload_id]['original_filename'], 'wb') as f:
            f.write(complete_file)
        
        # Clean up
        del uploads_in_progress[upload_id]
        
        return {'status': 'complete', 'file_size': len(complete_file)}
    else:
        return {'status': 'chunk_received', 'chunk': chunk_num, 'total': total_chunks}
```

---

## 🛠️ Configuration

### Change Upload URL
Edit `chunked_upload_module.py`:

```python
# Default URL (line 308)
upload_url = os.environ.get('CHUNKED_UPLOAD_URL', 'https://YOUR_NEW_URL/upload')
```

Or set environment variable:
```bash
set CHUNKED_UPLOAD_URL=https://your-server.com/upload
```

### Change Chunk Size
Edit `chunked_upload_module.py`:

```python
# In ChunkedFileUploader.__init__ (line 33)
self.chunk_size = 500 * 1024 * 1024  # Change 500 to desired MB
```

### Change Auth Credentials
Edit `chunked_upload_module.py`:

```python
# In ChunkedFileUploader.__init__ (line 27)
def __init__(self, upload_url: str, username: str = "admin", password: str = "admin123"):
```

---

## 🧪 Testing

### Test Script Included
```bash
python test_chunked_upload.py
```

Tests:
- Small file (<500MB) - no chunking
- Large file (600MB) - 2 chunks
- Edge case (500MB exactly) - 1 chunk
- Multiple chunks (2.5GB) - 5 chunks

### Manual Testing
```python
from chunked_upload_module import upload_large_file

result = upload_large_file(
    file_path="large_file.csv",
    user_id="test_user",
    deployment="remote",
    description="Test upload"
)

print(result)
```

---

## 📝 Summary

| Aspect | Details |
|--------|---------|
| **API URL** | `https://16eae2f0d5b0.ngrok-free.app/upload` |
| **Method** | `POST` (multipart/form-data) |
| **Auth** | Basic Auth (admin:admin123) |
| **Trigger** | Files > 500MB |
| **Chunk Size** | 500 MB |
| **Module** | `chunked_upload_module.py` |
| **Function** | `upload_large_file()` |
| **Used in** | `app.py` line 793 |

---

**Status:** ✅ Implemented and ready to use for files > 500MB
