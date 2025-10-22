# 🚀 SETUP GUIDE - Python Host

## 📍 Location
```
C:\tensile-search-with-strands\code\python_host
```

## ✅ What Was Copied

### Core Application Files (11 files)
- ✅ `app.py` - Main Flask application
- ✅ `config.py` - Configuration settings
- ✅ `enhanced_data_pipeline.py` - Data processing
- ✅ `database_module.py` - Database API integration
- ✅ `chunked_upload_module.py` - Chunked uploads
- ✅ `upload_api_module.py` - Upload API
- ✅ `mcp_elasticsearch_server.py` - MCP server
- ✅ `mcp_integration.py` - MCP utilities
- ✅ `remote_instance_manager.py` - Instance management
- ✅ `remote_log_viewer.py` - Log viewer
- ✅ `.gitignore` - Git ignore rules

### Directories (6 folders)
- ✅ `templates/` - 29 static HTML templates
- ✅ `static/` - CSS, JavaScript, images
- ✅ `uploads/` - File upload storage
- ✅ `schemas/` - Generated schemas
- ✅ `mcp_configs/` - MCP configurations
- ✅ `data/` - Data files

### Documentation (6 files)
- ✅ `README.md` - Project overview
- ✅ `docs/DATABASE_API_FINAL_DOCS.md`
- ✅ `docs/CHUNKED_UPLOAD_API_DOCS.md`
- ✅ `docs/HARSHITS_INDEXING_API_DOCS.md`
- ✅ `docs/FINAL_STATUS_REPORT.md`
- ✅ `docs/QUICK_REFERENCE.md`

### Configuration (2 files)
- ✅ `requirements.txt` - Python dependencies
- ✅ `.env.example` - Environment template

## ❌ What Was NOT Copied (Excluded)

### Backup/Old Files
- ❌ `app.py_bak`, `app.py_bak_need`, `app.py_getback`, etc.
- ❌ `enhanced_data_pipeline.py_*` (backup versions)
- ❌ `remote_elasticsearch.py_*` (old versions)

### Test Files
- ❌ `test_*.py` (various test scripts)
- ❌ `quick_api_test.py`
- ❌ `verify_production_config.py`

### Temporary/Generated Files
- ❌ `temp_*.csv` (temporary CSV files)
- ❌ `__pycache__/` (Python cache)
- ❌ `.continue/` (editor cache)

### Node.js/Frontend Files
- ❌ `package.json`, `pnpm-lock.yaml`
- ❌ `next.config.mjs`, `tsconfig.json`
- ❌ `tailwind.config.ts`, `postcss.config.mjs`
- ❌ `components/`, `app/`, `hooks/`, `lib/` (Next.js folders)

### Extra Documentation
- ❌ Multiple intermediate documentation files
- ❌ Test result reports
- ❌ Fix summaries

### Other
- ❌ `venv/` (will use the existing venv in new location)
- ❌ `setup.py`
- ❌ Duplicate modules

---

## 🎯 SETUP STEPS

### Step 1: Activate Virtual Environment

```bash
cd C:\tensile-search-with-strands\code\python_host

# Activate existing venv (already present in this directory)
venv\Scripts\activate
```

### Step 2: Install Dependencies

```bash
# Install all required packages
pip install -r requirements.txt
```

### Step 3: Configure Environment

```bash
# Copy the example to create your .env file
copy .env.example .env

# Edit .env with your settings
notepad .env
```

**Important Settings:**
- Update `HARSHIT_API_HOST` with actual server IP when available
- Verify `DB_API_HOST` is correct (currently 82.112.235.26)

### Step 4: Verify Installation

```bash
# Check if Flask is installed
python -c "import flask; print(f'Flask {flask.__version__}')"

# Check if all modules load
python -c "import enhanced_data_pipeline, database_module; print('✅ All modules OK')"
```

### Step 5: Run the Application

```bash
python app.py
```

**Expected Output:**
```
 * Running on http://0.0.0.0:7000
 * MCP Integration: Enabled
 * Health endpoint: http://localhost:7000/health
```

### Step 6: Test the Application

Open browser and navigate to:
- Health Check: http://localhost:7000/health
- Portal: http://localhost:7000/esportal
- Home: http://localhost:7000/

---

## 🔍 VERIFICATION CHECKLIST

After setup, verify:

- [ ] Virtual environment activated
- [ ] Dependencies installed (`pip list | findstr Flask`)
- [ ] `.env` file created and configured
- [ ] Application starts without errors
- [ ] Health endpoint returns 200 OK
- [ ] Portal page loads correctly
- [ ] Templates directory accessible
- [ ] Static files serve correctly
- [ ] Upload directory writable
- [ ] MCP integration enabled (check /health response)

---

## 📊 FILE STRUCTURE COMPARISON

### Before (D:\es_prompt2.0)
```
D:\es_prompt2.0/
├── 150+ files (including backups, tests, docs)
├── Many duplicate/old versions
├── Test scripts
└── Temporary files
```

### After (C:\tensile-search-with-strands\code\python_host)
```
python_host/
├── 11 core Python files
├── 6 essential directories
├── 5 documentation files
├── 2 configuration files
└── Clean, production-ready structure
```

**Size Reduction:** ~140 unnecessary files removed! ✅

---

## 🎯 QUICK START COMMANDS

```bash
# Navigate to directory
cd C:\tensile-search-with-strands\code\python_host

# Activate venv
venv\Scripts\activate

# Install dependencies (first time only)
pip install -r requirements.txt

# Run application
python app.py

# Access portal
start http://localhost:7000/esportal
```

---

## 🐛 TROUBLESHOOTING

### Issue: Virtual Environment Not Found

```bash
# Create new venv if needed
python -m venv venv

# Activate it
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Issue: Port 7000 Already in Use

```powershell
# Windows - Kill process on port 7000
Get-Process -Id (Get-NetTCPConnection -LocalPort 7000).OwningProcess | Stop-Process -Force
```

### Issue: Module Import Errors

```bash
# Verify you're in correct directory
cd C:\tensile-search-with-strands\code\python_host

# Verify venv is activated (should see (venv) in prompt)
venv\Scripts\activate

# Reinstall requirements
pip install -r requirements.txt --upgrade
```

### Issue: Templates Not Found

```bash
# Verify templates directory exists
dir templates

# Should show 29 HTML files
dir templates\*.html
```

---

## 📚 NEXT STEPS

1. **Read Documentation**
   - Start with `docs/FINAL_STATUS_REPORT.md`
   - Review API docs in `docs/` folder

2. **Configure APIs**
   - Update Harshit's API IP in `.env`
   - Verify database API connection

3. **Test Features**
   - Upload a test CSV
   - Deploy to remote ES
   - Check MCP integration

4. **Deploy (Optional)**
   - Configure production settings
   - Set up reverse proxy
   - Enable SSL

---

## ✅ SUCCESS INDICATORS

You'll know setup is complete when:

1. ✅ `python app.py` starts without errors
2. ✅ http://localhost:7000/health returns JSON
3. ✅ http://localhost:7000/esportal loads the portal
4. ✅ No missing module errors
5. ✅ Can upload files through portal
6. ✅ Templates render correctly

---

## 🎉 YOU'RE ALL SET!

Your Flask application is now in a clean, organized structure ready for:
- ✅ Version control (Git)
- ✅ Team collaboration
- ✅ Production deployment
- ✅ Continuous development

**Repository Location:**
```
C:\tensile-search-with-strands\code\python_host
```

**Working Directory:** Clean and production-ready! 🚀
