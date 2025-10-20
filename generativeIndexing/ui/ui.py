# ui.py
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
import sys

# Ensure UTF-8 encoding for emoji handling
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

app = FastAPI(title="Live Dashboard UI")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (change if needed)
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all HTTP headers
)

# Path to your static files
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")

# Serve static files like CSS, JS
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Route for the dashboard
@app.get("/")
@app.get("/live-dashboard")
def get_dashboard():
    """
    Serves the main HTML dashboard page.
    """
    html_path = os.path.join(STATIC_DIR, "live-dashboard.html")
    return FileResponse(html_path, media_type="text/html; charset=utf-8")

if __name__ == "__main__":
    # Run the UI server on port 8001
    uvicorn.run("ui:app", host="0.0.0.0", port=8001, reload=True)
