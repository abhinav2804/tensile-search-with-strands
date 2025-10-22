# Flask Elasticsearch Portal - Python Host

## 🎯 Overview

This is the Python Flask backend for the Elasticsearch data pipeline and management portal.

## 📁 Project Structure

```
python_host/
├── app.py                          # Main Flask application
├── config.py                       # Configuration settings
├── requirements.txt                # Python dependencies
├── enhanced_data_pipeline.py       # Data processing pipeline
├── database_module.py              # Database API integration
├── chunked_upload_module.py        # Chunked file upload handling
├── upload_api_module.py            # Upload API module
├── mcp_elasticsearch_server.py     # MCP server integration
├── mcp_integration.py              # MCP integration utilities
├── remote_instance_manager.py      # Remote ES instance management
├── remote_log_viewer.py            # Log viewer functionality
├── templates/                      # HTML templates (29 static files)
├── static/                         # CSS, JS, and static assets
├── uploads/                        # Uploaded files storage
├── schemas/                        # Generated schemas
├── mcp_configs/                    # MCP configuration files
├── data/                           # Data files
└── docs/                           # Documentation
    ├── DATABASE_API_FINAL_DOCS.md
    ├── CHUNKED_UPLOAD_API_DOCS.md
    ├── HARSHITS_INDEXING_API_DOCS.md
    ├── FINAL_STATUS_REPORT.md
    └── QUICK_REFERENCE.md
```

## 🚀 Quick Start

### 1. Activate Virtual Environment

```bash
# The venv is already set up in this directory
# Activate it:
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the Application

```bash
python app.py
```

The server will start on `http://localhost:7000`

## 🔧 Configuration

Edit `config.py` to configure:
- Database API endpoints
- Upload API settings
- MCP server settings
- Remote ES instance settings

## 📚 API Documentation

### Main Endpoints

- `GET /` - Home page
- `GET /health` - Health check
- `GET /esportal` - Main portal interface
- `POST /upload` - File upload
- `GET /api/mcp-status` - MCP connection status
- `GET /api/trigger-indexing-live` - Trigger live indexing

See `docs/FINAL_STATUS_REPORT.md` for complete API documentation.

## 🔌 External API Integration

### Database API
- **Endpoint:** `http://82.112.235.26:4000`
- **Docs:** `docs/DATABASE_API_FINAL_DOCS.md`

### Chunked Upload API
- **Endpoint:** Configured in `config.py`
- **Docs:** `docs/CHUNKED_UPLOAD_API_DOCS.md`

### Harshit's Indexing API
- **Endpoint:** `http://[SERVER_IP]:8000`
- **Docs:** `docs/HARSHITS_INDEXING_API_DOCS.md`

## 🧪 Testing

```bash
# Test database API
python -c "from database_module import *; print(test_db_connection())"

# Test MCP integration
python -c "from mcp_integration import *; print(get_mcp_status())"
```

## 📊 Features

✅ Static UI (29 HTML templates)
✅ Chunked file upload (500MB chunks)
✅ Database integration (user CRUD)
✅ MCP server integration
✅ Remote ES instance management
✅ Log viewer
✅ SSE (Server-Sent Events) for live updates
✅ Modular architecture

## 🔑 Key Modules

### `enhanced_data_pipeline.py`
Main data processing pipeline - handles CSV/JSON processing, schema generation, and ES indexing.

### `database_module.py`
Database API integration - user management with correct field format (`ofELK` not `offELK`).

### `chunked_upload_module.py`
Handles large file uploads by splitting into 500MB chunks.

### `remote_instance_manager.py`
Manages remote Elasticsearch instances, deployments, and instance lifecycle.

### `mcp_elasticsearch_server.py`
MCP server for Elasticsearch integration.

## ⚙️ Environment Variables

Create a `.env` file:

```bash
# Database API
DB_API_HOST=82.112.235.26
DB_API_PORT=4000

# Harshit's Indexing API
HARSHIT_API_HOST=localhost
HARSHIT_API_PORT=8000

# Flask
FLASK_ENV=development
FLASK_DEBUG=True
```

## 🐛 Troubleshooting

### Port 7000 Already in Use
```bash
# Windows
Get-Process -Id (Get-NetTCPConnection -LocalPort 7000).OwningProcess | Stop-Process

# Linux
lsof -ti:7000 | xargs kill -9
```

### MCP Not Connecting
1. Deploy at least one ES instance
2. Check MCP configuration in `mcp_configs/`
3. Verify ES instances are running

### Database API Errors
- Ensure all 4 fields present: `UserId`, `ofELK`, `name`, `email`
- Field name is `ofELK` (one 'f', not two!)

## 📖 Documentation

All documentation is in the `docs/` folder:

- **FINAL_STATUS_REPORT.md** - Complete system status
- **DATABASE_API_FINAL_DOCS.md** - Database API reference
- **CHUNKED_UPLOAD_API_DOCS.md** - Upload API reference
- **HARSHITS_INDEXING_API_DOCS.md** - Indexing API reference
- **QUICK_REFERENCE.md** - Quick command reference

## 🎯 System Status

**Current Status:** 85% Production Ready

- ✅ Flask Application (100%)
- ✅ Database API (100%)
- ✅ UI Static Content (100%)
- ✅ Chunked Upload Logic (100%)
- ✅ SSE Integration (100%)
- ⏸️ Harshit's API (needs server IP)
- ⏸️ MCP Connections (needs ES deployment)

## 🚀 Deployment

### Production Checklist

- [ ] Update `config.py` with production settings
- [ ] Set `FLASK_ENV=production`
- [ ] Use proper WSGI server (gunicorn/waitress)
- [ ] Configure reverse proxy (nginx/Apache)
- [ ] Set up SSL certificates
- [ ] Configure firewall rules
- [ ] Set up monitoring/logging
- [ ] Create backup strategy

### Example Production Start

```bash
# Using gunicorn
gunicorn -w 4 -b 0.0.0.0:7000 app:app

# Using waitress (Windows)
waitress-serve --host=0.0.0.0 --port=7000 app:app
```

## 📞 Support

For issues or questions:
1. Check `docs/FINAL_STATUS_REPORT.md`
2. Review API documentation in `docs/`
3. Check Flask logs in console

## 📝 License

[Your License Here]

## 🎉 Credits

Built with Flask, Elasticsearch, and MCP integration.
