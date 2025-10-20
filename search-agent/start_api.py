#!/usr/bin/env python3
"""
Startup script for the Simple Doc Agent API wrapper (without MCP)
"""

import uvicorn
import sys
import os

def main():
    """Start the API server"""
    print("🚀 Starting Doc Agent API Wrapper...")
    print("📍 API will be available at: http://localhost:5000")
    print("📖 API docs will be available at: http://localhost:5000/docs")
    print("🔍 Health check: http://localhost:5000/health")
    print("\nPress Ctrl+C to stop the server")
    
    try:
        uvicorn.run(
            "api_wrapper:app",
            host="0.0.0.0",
            port=5000,
            reload=True,  # Auto-reload on code changes
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n👋 Server stopped")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()