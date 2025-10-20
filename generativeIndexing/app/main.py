# -*- coding: utf-8 -*-
"""
UTF-8-safe FastAPI app configuration for Generative Indexing Service.
This ensures emojis, gradients, and multilingual text render correctly,
without affecting other apps on the same server.
"""

import sys

# ✅ Reconfigure std I/O to UTF-8 only for this process
if hasattr(sys, "stdout"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys, "stderr"):
    sys.stderr.reconfigure(encoding="utf-8")

# ✅ Make sure Python internally uses UTF-8 (affects this process only)
import locale
try:
    locale.setlocale(locale.LC_ALL, "C.UTF-8")
except locale.Error:
    # Fallback in minimal systems (won’t crash your app)
    pass

import uvicorn
import socket
import time
import os

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from datetime import datetime

from app.routes.indexing import router as indexing_router
from app.config.config_loader import config

# Track app uptime and request count
START_TIME = time.time()
REQUEST_COUNT = 0

def find_free_port(default: int = 8000) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1] or default

app = FastAPI(title="Generative Indexing API", version="1.0.0")
app.include_router(indexing_router)

# ✅ Get absolute path to 'static' directory (works no matter where you run from)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

# ✅ Mount /static correctly
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# ✅ Serve real favicon (redirect or direct)
@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return RedirectResponse(url="/static/api.png")

@app.middleware("http")
async def enforce_utf8(request, call_next):
    response = await call_next(request)
    if "charset" not in response.headers.get("content-type", ""):
        response.headers["content-type"] = response.headers.get("content-type", "text/html") + "; charset=utf-8"
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def count_requests(request, call_next):
    global REQUEST_COUNT
    REQUEST_COUNT += 1
    response = await call_next(request)
    return response

@app.get("/", response_class=HTMLResponse)
def home():
    uptime_seconds = int(time.time() - START_TIME)
    uptime_str = f"{uptime_seconds // 3600}h {(uptime_seconds % 3600) // 60}m {uptime_seconds % 60}s"
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>⚡ Generative Indexing Service</title>
        <link rel="icon" href="/static/favicon.ico" type="image/x-icon" />
        <meta http-equiv="refresh" content="15" />
        <style>
            @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&display=swap');

            :root {{
                --bg: radial-gradient(circle at top left, #0f2027, #203a43, #2c5364);
                --accent: #00FFB2;
                --accent2: #00BFFF;
                --text: #eaeaea;
                --glass: rgba(255, 255, 255, 0.08);
                --border: rgba(255, 255, 255, 0.12);
                --shadow: 0 0 40px rgba(0, 255, 178, 0.3);
            }}

            * {{ box-sizing: border-box; }}
            body {{
                margin: 0;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                height: 100vh;
                background: var(--bg);
                color: var(--text);
                font-family: 'JetBrains Mono', monospace;
                overflow: hidden;
            }}

            h1 {{
                font-size: 4em;
                font-weight: 700;
                background: linear-gradient(90deg, var(--accent), var(--accent2), var(--accent));
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-size: 200% 200%;
                animation: gradientFlow 4s infinite ease-in-out;
                text-align: center;
                text-shadow: 0 0 15px rgba(0,255,178,0.7);
                z-index: 2;
            }}

            .dashboard {{
                display: flex;
                flex-wrap: wrap;
                justify-content: center;
                gap: 2rem;
                margin-top: 2rem;
                z-index: 2;
            }}

            .card {{
                background: var(--glass);
                border: 1px solid var(--border);
                border-radius: 18px;
                padding: 1.5rem 2.5rem;
                box-shadow: var(--shadow);
                text-align: center;
                backdrop-filter: blur(8px);
                min-width: 200px;
                animation: fadeIn 1s ease-in-out;
            }}

            .metric-value {{
                font-size: 2rem;
                color: var(--accent);
                margin-top: 0.3rem;
                text-shadow: 0 0 10px var(--accent);
            }}

            .status {{
                margin-top: 2rem;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 1rem;
                font-size: 1.6rem;
                background: var(--glass);
                border: 1px solid var(--border);
                border-radius: 20px;
                padding: 1rem 3rem;
                box-shadow: var(--shadow);
                backdrop-filter: blur(8px);
                animation: fadeIn 1.5s ease-in-out;
            }}

            .checkmark {{
                color: var(--accent);
                font-size: 2.3rem;
                animation: pulse 1.5s infinite;
            }}

            .timestamp {{
                margin-top: 1.5rem;
                font-size: 1.2rem;
                opacity: 0.85;
                text-shadow: 0 0 6px var(--accent);
            }}

            footer {{
                position: fixed;
                bottom: 18px;
                width: 100%;
                text-align: center;
                font-size: 1rem;
                opacity: 0.7;
                letter-spacing: 0.5px;
            }}

            @keyframes gradientFlow {{
                0% {{ background-position: 0% 50%; }}
                50% {{ background-position: 100% 50%; }}
                100% {{ background-position: 0% 50%; }}
            }}

            @keyframes fadeIn {{
                from {{ opacity: 0; transform: translateY(10px); }}
                to {{ opacity: 1; transform: translateY(0); }}
            }}

            @keyframes pulse {{
                0%, 100% {{ transform: scale(1); opacity: 1; }}
                50% {{ transform: scale(1.2); opacity: 0.85; }}
            }}
        </style>
    </head>
    <body>
        <h1>⚡ Generative Indexing Service</h1>

        <div class="dashboard">
            <div class="card">
                <div>⏱ Uptime</div>
                <div class="metric-value">{uptime_str}</div>
            </div>
            <div class="card">
                <div>📨 Total Requests</div>
                <div class="metric-value">{REQUEST_COUNT}</div>
            </div>
            <div class="card">
                <div>🧠 Index Status</div>
                <div class="metric-value">Active</div>
            </div>
        </div>

        <div class="status">
            <span class="checkmark">✔</span>
            <span>Service is <strong style="color: var(--accent)">Alive & Kicking</strong></span>
        </div>

        <div class="timestamp">🕒 {now}</div>

        <footer>Built with 💚 FastAPI • Bedrock • Elasticsearch • DynamoDB</footer>
    </body>
    </html>
    """
    return HTMLResponse(content=html)

def is_port_in_use(port: int) -> bool:
    """Check if a port is already in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0

if __name__ == "__main__":
    # ✅ Get port from already loaded config
    port = config["app"]["port"]

    # ✅ If busy, pick a random free port
    if is_port_in_use(port):
        print(f"⚠️ Port {port} is busy. Selecting a random free port...")
        port = find_free_port(port)
    else:
        print(f"✅ Using configured port {port}")

    # ✅ Debug mode from config
    debug_mode = config["app"].get("debug", False)

    print(f"🚀 Running on http://{config['app']['host']}:{port}")
    uvicorn.run(
        "app.main:app",
        host=config["app"]["host"],
        port=port,
        reload=debug_mode
    )

