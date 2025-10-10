# AI Mentor System - Clean Setup

This document describes the streamlined AI Mentor system with all unnecessary duplicates removed and proper service management.

## Services Architecture

The system now runs three main services in a clean, organized manner:

### 1. FastAPI Knowledge Service (Port 8085)
- **Purpose**: Modern Meeting Intelligence backend
- **Technology**: FastAPI + SQLAlchemy + PostgreSQL/SQLite
- **Features**: Meeting summarization, action item extraction, semantic search
- **Endpoints**: `/api/health`, `/api/meetings/*`, `/docs`

### 2. Flask Backend Service (Port 8084) 
- **Purpose**: Main Q&A and Resume service with Meeting Intelligence proxy
- **Technology**: Flask + OpenAI integration
- **Features**: Q&A chat, resume processing, authentication, Meeting Intelligence proxy
- **Endpoints**: `/api/ask`, `/api/resume`, `/api/health`, `/api/meetings/*` (proxied)

### 3. Real-time Session Service (Port 8080)
- **Purpose**: Live session handling and transcript capture
- **Technology**: Flask + WebSocket + Speaker Diarization
- **Features**: Real-time caption processing, session management
- **Endpoints**: `/api/sessions`, `/api/health`, WebSocket endpoints

## Quick Start

### Start All Services
```bash
python start_services.py
```

### Check Service Status
```bash
python check_status.py
```

### Stop All Services
```bash
# Ctrl+C in the start_services.py terminal
# Or kill the process group
```

## Service Management

The system includes intelligent service management:

- **Automatic Port Cleanup**: Kills existing processes on required ports
- **Dependency Order**: Starts services in the correct dependency order
- **Health Monitoring**: Monitors services and reports failures
- **Graceful Shutdown**: Properly stops all services on interrupt

## API Documentation

### Available Endpoints

#### Q&A Service (Port 8084)
- `POST /api/ask` - Ask AI questions
- `POST /api/resume` - Upload resume
- `GET /api/resume` - Get resume
- `POST /api/register` - Register user
- `POST /api/login` - Login user
- `GET /api/health` - Health check

#### Meeting Intelligence (Port 8085)
- `POST /api/meetings/{session_id}/finalize` - Finalize meeting
- `GET /api/meetings/{session_id}/summary` - Get meeting summary  
- `GET /api/meetings/{session_id}/actions` - Get action items
- `GET /api/meetings/search` - Search meetings
- `GET /api/health` - Health check
- `GET /docs` - Interactive API documentation

#### Real-time Service (Port 8080)
- `POST /api/sessions` - Create session
- `GET /api/sessions/{session_id}` - Get session
- `POST /api/sessions/{session_id}/captions` - Add captions
- `GET /api/health` - Health check

## Cleaned Up Items

The following items have been removed or cleaned up:

### Removed Files
- Duplicate database files (`mentor_memory.db`, `knowledge.db`, `production_mentor.db`)
- Python cache files (`__pycache__` directories)
- Old log files
- Temporary files

### Consolidated Services
- No more port conflicts or duplicate processes
- Single startup script for all services
- Unified health checking
- Proper service dependency management

### Database Cleanup
- All databases now properly located in `data/` directory
- No duplicate or conflicting database files
- Clean schema management

## Development Workflow

1. **Start Development**:
   ```bash
   python start_services.py
   ```

2. **Check Everything is Running**:
   ```bash
   python check_status.py
   ```

3. **Test APIs**:
   - Visit http://localhost:8085/docs for Meeting Intelligence API
   - Test Q&A at http://localhost:8084/api/ask
   - Test real-time at http://localhost:8080/api/health

4. **Monitor Logs**:
   - All services log to stdout
   - Monitor in the start_services.py terminal

5. **Stop Services**:
   - Ctrl+C in the start_services.py terminal
   - Services stop gracefully

## Integration Points

### Browser Extension → Backend Service (8084)
- Q&A functionality
- Resume processing
- Meeting Intelligence proxy

### VS Code/IntelliJ Plugins → Backend Service (8084)
- Code assistance
- Q&A integration

### Real-time Capture → Real-time Service (8080)
- Live caption processing
- Session management

### Meeting Intelligence → Knowledge Service (8085)
- Meeting processing
- Summarization
- Action item extraction
- Semantic search

## Next Steps

With the clean system in place, you can now:

1. **Test End-to-End Workflows**: Create a meeting session and test the full pipeline
2. **Develop New Features**: Use the clean architecture to add new capabilities
3. **Deploy to Production**: The services are now properly separated and deployable
4. **Monitor Performance**: Use the health checks and logging for monitoring

All services are now running cleanly without conflicts or duplicates!
