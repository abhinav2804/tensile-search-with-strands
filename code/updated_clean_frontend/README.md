# Simplified ESPortal 3.0

## Overview

This is a simplified version of ESPortal 3.0 that uses only 3 remote APIs without any local Elasticsearch or MCP instances.

## Architecture

The application is built with Flask and uses three remote APIs:

1. **Database API**: `http://82.112.235.26:4000/users`
2. **Upload API**: `http://82.112.235.26:7001/upload`
3. **Search API**: `http://82.112.235.26:7001/query`

## Features

### 1. User Authentication & Database Management
- When users sign in for the first time, their email is stored as primary key
- Each user gets a unique ID generated automatically
- Existing users are identified and their login status is updated (green tick for logged-in users)

### 2. File Upload with Chunking
- Supports large file uploads (>500MB) by automatically splitting into 500MB chunks
- Chunks are named sequentially: `filename_1`, `filename_2`, etc.
- The last chunk is specially named: `filename_last_message`
- Supports description queries that users can provide to describe their data
- Passes user ID and email to the remote API for proper user tracking

### 3. Search Functionality
- Users can search through uploaded data using natural language queries
- Template-based queries for common search patterns
- Real-time search results via the remote search API
- Results are displayed in a formatted interface

## API Endpoints

### Database API (`/api/user/upsert`)
```json
{
    "UserId": "unique-id",
    "ofELK": "unique-id",
    "name": "User Name",
    "email": "user@example.com"
}
```

### Upload API (`/api/upload/proxy`)
- Handles file chunking automatically
- Supports files of any size (splits into 500MB chunks)
- Passes through: userid, temperature (0.3), file chunks
- For large files: creates multiple requests with proper naming
- Final chunk includes description queries

### Search API (`/api/search`)
```json
{
    "userid": "user-id",
    "query": "search query",
    "temperature": "0.3",
    "email": "user@example.com"
}
```

## File Structure

```
esportal3.0/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── templates/
│   ├── esportal.html     # Main portal interface
│   └── result.html       # Search results page
└── .venv/                # Python virtual environment
```

## Installation & Setup

1. **Install Dependencies**:
```bash
cd esportal3.0
.venv\Scripts\activate
pip install -r requirements.txt
```

2. **Run the Application**:
```bash
python app.py
```

3. **Access the Portal**:
   - Open browser to `http://localhost:5000`
   - The application runs on all interfaces (0.0.0.0:5000)

## Usage Flow

1. **First Time Users**:
   - Click "Login / Sign Up"
   - Complete authentication via Descope
   - User data is automatically stored in remote database
   - Portal unlocks for use

2. **File Upload**:
   - Select a file (any size supported)
   - Enter description queries (required)
   - Click "Start Upload & Deploy"
   - Large files are automatically chunked and uploaded

3. **Search**:
   - Use the search bar at the bottom
   - Type natural language queries
   - Click search or press Enter
   - View formatted results

## Key Simplifications

- **No Local Infrastructure**: Eliminated Elasticsearch and MCP instances
- **Remote API Only**: All processing handled by remote services
- **Automatic Chunking**: Handles large files transparently
- **Session Management**: User state maintained in Flask sessions
- **Simplified Authentication**: Uses Descope for auth, stores minimal user data

## Configuration

The application uses these environment variables (optional):
- `DESCOPE_PROJECT_ID`: Descope authentication project ID
- `DESCOPE_FLOW_ID`: Descope authentication flow ID (defaults to 'passwords-with-explicit-sign-up')

## Remote API Credentials

The application uses Basic Authentication with the remote APIs:
- Username: `admin`
- Password: `admin123`
- Encoded: `Basic YWRtaW46YWRtaW4xMjM=`

## Security Notes

- Change the Flask `secret_key` in production
- Consider using environment variables for API credentials
- The current implementation is suitable for development/testing

## Error Handling

- Upload failures are displayed with clear error messages
- Search errors show detailed error information
- Network issues are handled gracefully with user feedback
- Large file uploads show progress indication

This simplified implementation maintains all core functionality while eliminating complex infrastructure dependencies.