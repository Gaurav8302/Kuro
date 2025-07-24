"""
Replit Production Entry Point

This file is optimized for Replit hosting with proper environment handling.
"""

import os
import sys
import uvicorn

# Add the backend directory to Python path
backend_path = os.path.join(os.path.dirname(__file__), 'backend')
sys.path.insert(0, backend_path)

# Import the FastAPI app
try:
    from chatbot import app
    print("✅ Successfully imported FastAPI app")
except ImportError as e:
    print(f"❌ Error importing app: {e}")
    print("🔍 Available modules:", os.listdir(backend_path))
    sys.exit(1)

if __name__ == "__main__":
    # Replit environment configuration
    host = "0.0.0.0"
    port = int(os.getenv("PORT", 8000))
    is_replit = os.getenv("REPL_ID") is not None
    
    print("🚀 Canvas Chat AI - Starting Server")
    print(f"📍 Host: {host}:{port}")
    print(f"🌍 Environment: {'Replit Production' if is_replit else 'Local Development'}")
    print(f"🔐 Debug Mode: {'Disabled' if is_replit else 'Enabled'}")
    
    # Additional environment info for debugging
    if is_replit:
        repl_url = f"https://{os.getenv('REPL_SLUG', 'unknown')}.{os.getenv('REPL_OWNER', 'unknown')}.repl.co"
        print(f"🔗 Replit URL: {repl_url}")
    
    print("🎯 Starting FastAPI server...")
    
    try:
        uvicorn.run(
            app,
            host=host,
            port=port,
            reload=not is_replit,  # Disable reload in production
            access_log=True,
            log_level="info" if is_replit else "debug"
        )
    except Exception as e:
        print(f"❌ Server failed to start: {e}")
        sys.exit(1)
