# File Storage API

A Python Flask API that handles file uploads and organizes them by user ID and file type.

## Features

- Upload files with user ID and file type (data or query)
- Automatic directory structure creation
- File type validation
- Secure filename handling
- File listing by user ID
- Health check endpoint
- **Basic Authentication** - Multiple authentication methods supported

## Directory Structure

The API creates the following directory structure:
```
/var/www/es/
├── {userid}/
│   ├── data/
│   └── query/
```

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create the base directory (if not exists):
```bash
sudo mkdir -p /var/www/es
sudo chmod 755 /var/www/es
```

## Authentication

The API supports multiple authentication methods:

### 1. Basic Authentication
```bash
# Using curl with Basic Auth
curl -u admin:admin123 -X POST -F "userid=user123" -F "filetype=data" -F "file=@example.txt" http://localhost:5000/upload

# Or with explicit Authorization header
curl -H "Authorization: Basic YWRtaW46YWRtaW4xMjM=" -X POST -F "userid=user123" -F "filetype=data" -F "file=@example.txt" http://localhost:5000/upload
```

### 2. API Key Authentication
```bash
# Using X-API-Key header
curl -H "X-API-Key: admin123" -X POST -F "userid=user123" -F "filetype=data" -F "file=@example.txt" http://localhost:5000/upload
```

### 3. Bearer Token Authentication
```bash
# Using Bearer token
curl -H "Authorization: Bearer admin123" -X POST -F "userid=user123" -F "filetype=data" -F "file=@example.txt" http://localhost:5000/upload
```

### Default Credentials
- **Username:** `admin`, **Password:** `admin123`
- **Username:** `user1`, **Password:** `user1pass`
- **Username:** `user2`, **Password:** `user2pass`

*Note: The health check endpoint (`/health`) does not require authentication.*

## Usage

### Start the API
```bash
python app.py
```

The API will run on `http://localhost:5000`

### Endpoints

#### 1. Upload File
**POST** `/upload`

Upload a file with user ID and file type.

**Form Data:**
- `userid`: User identifier (string)
- `filetype`: Either "data" or "query" (string)
- `file`: The file to upload

**Example using curl with authentication:**
```bash
# Using Basic Auth
curl -u admin:admin123 -X POST -F "userid=user123" -F "filetype=data" -F "file=@example.txt" http://localhost:5000/upload

# Using API Key
curl -H "X-API-Key: admin123" -X POST -F "userid=user123" -F "filetype=data" -F "file=@example.txt" http://localhost:5000/upload
```

**Response:**
```json
{
  "message": "File uploaded successfully",
  "userid": "user123",
  "filetype": "data",
  "filename": "example_abc12345.txt",
  "file_path": "/var/www/es/user123/data/example_abc12345.txt",
  "file_size": 1024
}
```

#### 2. List User Files
**GET** `/list/{userid}`

List all files for a specific user.

**Example with authentication:**
```bash
# Using Basic Auth
curl -u admin:admin123 http://localhost:5000/list/user123

# Using API Key
curl -H "X-API-Key: admin123" http://localhost:5000/list/user123
```

**Response:**
```json
{
  "userid": "user123",
  "files": [
    {
      "filename": "example_abc12345.txt",
      "filetype": "data",
      "file_path": "/var/www/es/user123/data/example_abc12345.txt",
      "file_size": 1024,
      "created_at": 1640995200.0
    }
  ],
  "total_files": 1
}
```

#### 3. Health Check
**GET** `/health`

Check if the API is running.

**Response:**
```json
{
  "status": "healthy",
  "message": "API is running"
}
```

## File Type Validation

The API accepts the following file extensions:
- Text files: txt, json, csv, xml
- Documents: pdf, doc, docx
- Images: png, jpg, jpeg, gif

## Error Handling

The API includes comprehensive error handling for:
- Missing required parameters
- Invalid file types
- File upload failures
- Directory creation issues
- File system errors

## Security Features

- **Authentication Required** - All endpoints (except health check) require authentication
- **Multiple Auth Methods** - Supports Basic Auth, API Key, and Bearer Token
- **Secure filename handling** - Prevents path traversal attacks
- **File type validation** - Only allows specified file extensions
- **Unique filename generation** - Prevents conflicts and overwrites
- **Input validation and sanitization** - Comprehensive parameter validation
- **Error handling** - Secure error messages without information leakage
