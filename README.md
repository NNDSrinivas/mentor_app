# AI Mentor – Interview Assistant (Practical Guide)

This repo implements an AI interview assistant you can run locally across three surfaces: a Flask Q&A API, a realtime session service for meetings, and optional clients (Chrome overlay, mobile app, IDE plugins).

The README has been aligned with the actual code so you can run it end-to-end today.

## Architecture at a glance

- Q&A + Resume API (port 8084): `production_backend.py`
    - POST /api/ask → generates an answer using `app/ai_assistant.py`
    - POST/GET /api/resume → store/read resume text in SQLite (persistent)
    - GET /api/health → service health
- Realtime sessions API (port 8080): `production_realtime.py`
    - POST /api/sessions → create a session
    - GET /api/sessions/{id}/answers → recent answers for polling clients
    - GET /api/sessions/{id}/stream → Server-Sent Events (SSE) for realtime
    - POST /api/sessions/{id}/captions → push caption chunks with speaker hints
    - DELETE /api/sessions/{id} → end a session
    - GET /api/sessions/{id}/recording?analyze=true → screen recording path or analysis
    - POST /api/meeting-events → legacy meeting event ingestion
- Clients
    - Chrome extension in `browser_extension/` (calls 8084 for /api/ask and /api/resume, 8080 for meeting events)
    - Mobile client in `mobile/` (Expo/React Native)
    - VS Code extension in `vscode_extension/` (calls 8084 /api/ask)

Note: Some previously advertised utilities (e.g., universal IDE bridge, check_status.py) are not present. Follow the Quick Start below.

## Quick Start

1) Python environment

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.template .env
# Edit .env and set OPENAI_API_KEY
# Optional: enable screen recording
# SCREEN_RECORDING_ENABLED=true
```

2) Start services in two terminals

```bash
# Terminal A – Q&A service (port 8084)
python production_backend.py

# Terminal B – Realtime sessions (port 8080)
python production_realtime.py
```

3) Test APIs

```bash
# Health
curl -s http://localhost:8084/api/health
curl -s http://localhost:8080/api/health

# Ask a question (Q&A service)
curl -s -X POST http://localhost:8084/api/ask \
    -H 'Content-Type: application/json' \
    -d '{"question":"Describe CAP theorem","interview_mode":true}'

# Realtime session flow
SID=$(curl -s -X POST http://localhost:8080/api/sessions -H 'Content-Type: application/json' -d '{"user_level":"IC6","user_name":"local","meeting_type":"technical_interview"}' | jq -r .session_id)
curl -s -X POST http://localhost:8080/api/sessions/$SID/captions -H 'Content-Type: application/json' -d '{"text":"Can you explain how you would design a URL shortener?","speaker":"interviewer"}'
curl -s http://localhost:8080/api/sessions/$SID/answers
```

## Mobile app (Expo)

- Location: `mobile/`
- Dependencies listed in `mobile/package.json` (Expo 49, React Native 0.72). Install with npm/yarn in that folder.
- Start with the Expo CLI, then set the Server URL field in the app to your machine IP with port 8080, e.g. `http://192.168.1.100:8080`.
- The mobile app:
    - POSTs /api/sessions to create a session
    - Polls GET /api/sessions/{id}/answers every 3s
    - Lets you view and copy answers

Tip: On the same network, push captions using the realtime API (or via the Chrome extension) so answers appear on mobile.

## Browser extension

1) Open Chrome → chrome://extensions → Enable Developer mode → Load unpacked → select `browser_extension/`.
2) The overlay calls `http://localhost:8084/api/ask` and `http://localhost:8084/api/resume` and sends meeting events to `http://localhost:8080/api/meeting-events`.
3) Grant microphone/screen permissions as prompted.

## Configuration

Edit `.env` (copied from `.env.template`):

- OPENAI_API_KEY (required for ai responses)
- Optional tuning in `app/config.py` (overlay, knowledge base, privacy flags). Missing advanced backends are handled gracefully.

## Screen sharing detection

The private overlay attempts to detect when your screen is being shared
(Zoom, Teams, etc.) using OS-specific hooks.  When sharing is active the
overlay window is marked so it remains visible locally but is excluded from
the shared feed where supported.  Platforms that expose no screen-sharing
APIs fall back to hiding the overlay off-screen or printing responses to the
console to avoid leaking content.

## API summary

- 8084 (production_backend):
    - POST /api/ask { question, interview_mode? }
    - POST /api/resume { resume_text }
    - GET /api/resume
    - GET /api/health
- 8080 (production_realtime):
    - POST /api/sessions { user_level, meeting_type, user_name }
    - GET /api/sessions/{id}/answers
    - GET /api/sessions/{id}/stream (SSE)
    - POST /api/sessions/{id}/captions { text, speaker?, timestamp? }
    - DELETE /api/sessions/{id}
    - POST /api/meeting-events { action, data }

## Notes

- Knowledge base persists to `data/chroma_db/`. Don’t commit that directory.
- Resume storage persists in a local SQLite database; your resume survives backend restarts.
- Advanced features under `backend/` are imported defensively and the app runs without them.
- `start_mentor_app.py` can start the Q&A service, but it references a bridge file not present. Prefer running the two services directly as shown above.

## Contributing

PRs welcome. Keep endpoints backward compatible or update this README alongside any changes. Please avoid introducing heavy dependencies in the browser extension to keep the overlay lightweight.


## Removed / Not Implemented (Accuracy Statement)

Sections covering advanced diarization metrics, automated task extraction, Jira/calendar sync, build/deployment intelligence, automated PR management, smart documentation sync, enterprise security/compliance, performance SLAs, monetization strategy, and multi‑platform desktop features have been removed because the current codebase does not implement them. Some stub Python files exist under `backend/` but are not wired into running services.

If you implement a feature, reintroduce documentation with concrete details: endpoints, file paths, run commands.

## License

This project is proprietary software owned by NND Srinivas (NagaDurga S Nidamanuri). All rights reserved.
See the [LICENSE](LICENSE) file for detailed terms and conditions.

**Commercial Use:** Requires explicit written permission and commercial licensing.
**Patents:** All patent rights are exclusively owned by NND Srinivas (NagaDurga S Nidamanuri).

For licensing inquiries, please contact the owner.

---

This README now reflects only implemented functionality to reduce ambiguity.

## Build & Run (scripts)

If you prefer a one-command setup, use the helper scripts:

```bash
chmod +x start_services.sh stop_services.sh
./start_services.sh
```

This will create a virtualenv (if missing), install dependencies, and start both services:
- Q&A service on http://localhost:8084
- Realtime service on http://localhost:8080

Stop the services when done:

```bash
./stop_services.sh
```

Mock mode: If `OPENAI_API_KEY` isn’t set, the backend starts in a safe mock mode that returns placeholder answers (see `app/ai_assistant.py` and `production_backend.py` fallback). This lets you verify end-to-end flows without external credentials.
