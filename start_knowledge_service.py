#!/usr/bin/env python3
"""
Start the FastAPI Knowledge Service for Meeting Intelligence.
This service runs on port 8085 and provides Meeting Intelligence endpoints.
"""

import os
import sys
import uvicorn
from pathlib import Path

# Add the project root to Python path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

def main():
    """Start the FastAPI Knowledge Service."""
    # Set environment variables for development
    os.environ.setdefault('KNOWLEDGE_DATABASE_URL', 'sqlite:///data/knowledge.db')
    os.environ.setdefault('MEMORY_DB_PATH', 'data/memory')
    os.environ.setdefault('MEETING_PIPELINE_MODE', 'sync')
    os.environ.setdefault('DRAMATIQ_BROKER', 'stub')
    
    print("🚀 Starting Meeting Intelligence Knowledge Service...")
    print("📊 Database: SQLite (data/knowledge.db)")
    print("🧠 Memory: Local storage (data/memory)")
    print("⚡ Pipeline: Synchronous mode")
    print("🎯 Available endpoints:")
    print("   GET  /api/health")
    print("   POST /api/meetings/{session_id}/finalize")
    print("   GET  /api/meetings/{session_id}/summary")
    print("   GET  /api/meetings/{session_id}/actions")
    print("   GET  /api/meetings/search")
    print("")
    print("🌐 Starting server on http://localhost:8085")
    
    # Import and run the FastAPI app
    from backend.knowledge_service import app
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8085,
        log_level="info",
        reload=False
    )

if __name__ == "__main__":
    main()
