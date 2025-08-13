# Copilot instructions for AI agents

This repo implements an “AI Mentor” across a small Flask backend, a Chrome meeting overlay, and IDE extensions. Use these notes to get productive fast and wire features in the right places.

## Architecture at a glance
- Web APIs (two servers, two ports):
  - Q&A + Resume service: `simple_web.py` on http://localhost:8084
    - POST /api/ask → generates answers using `app/ai_assistant.py`
    - POST/GET /api/resume → stores/reads resume text in memory for personalization
    - GET /api/health → { status: "healthy" }
  - Realtime sessions + events: `web_interface.py` on http://localhost:8080
    - POST /api/meeting-events → ingest meeting events (caption_chunk, start/stop, screen_shared)
    - POST /api/sessions → create session; SSE at GET /api/sessions/{id}/stream
    - Implementation via `app/realtime.py` (optional advanced backends under `backend/`)
- Browser extension: `browser_extension/`
  - `content.js` draws the private overlay in Google Meet and calls 8084 (/api/ask, /api/resume)
  - `background.js` detects meetings and posts events to 8080 (/api/meeting-events)
- IDE integrations: `vscode_extension/` (and IntelliJ sources) call /api/ask on configured service URL.
- Knowledge base: `app/knowledge_base.py` uses ChromaDB (persisted in `data/chroma_db/`) + OpenAI embeddings.

## Local dev workflow
- Python setup
  - Create venv, `pip install -r requirements.txt`, copy `.env.template` → `.env`, set `OPENAI_API_KEY`.
  - Start Q&A service (8084): run `python simple_web.py`
  - Start realtime service (8080): run `python web_interface.py` (needed for meeting-events + SSE)
- Browser extension
  - Load `browser_extension/` as an unpacked extension in Chrome (mic/screen perms). Overlay uses Web Speech API locally.
- VS Code extension
  - `cd vscode_extension && npm install && npm run compile`; configure its backend URL if needed.

## API usage patterns (examples)
- Ask a question (uses resume if uploaded):
  - POST http://localhost:8084/api/ask
    { "question": "Describe CAP theorem", "interview_mode": true }
- Upload resume (text only – paste content):
  - POST http://localhost:8084/api/resume
    { "resume_text": "…your resume text…" }
- Meeting events from the extension to realtime service:
  - POST http://localhost:8080/api/meeting-events
    { "action": "caption_chunk", "data": { "text": "question…", "speaker": "interviewer" } }

## Project conventions to follow
- Configuration via `app/config.py` (reads `.env`); prefer using `Config` over raw `os.getenv`.
- `ai_assistant.py` requires `OPENAI_API_KEY` and surfaces personalization:
  - When `interview_mode` is true, it calls `_generate_interview_response()` which uses resume/profile context.
- Resume API expects raw text (no file upload parsing in server). `content.js` guides users to paste for PDFs/DOCs.
- Optional advanced features (speaker diarization, memory service) live in `backend/` and are imported defensively in `app/realtime.py`; code must run when they’re absent.
- Knowledge base persists to `data/chroma_db/`; do not commit this directory.

## Cross-component communication
- `content.js` → 8084 for answers and resume; shows overlay/stealth window and uses Web Speech.
- `background.js` → 8080 for meeting lifecycle and caption chunks; ensures an offscreen doc for audio processing.
- `vscode_extension/src/extension.ts` → /api/ask on configured base URL.

## Gotchas
- Two ports are intentional (8084 Q&A; 8080 realtime). Start both for full flows (overlay + events/SSE).
- If `OPENAI_API_KEY` is missing, `ai_assistant.py` and knowledge base will raise; tests/demos will fail.
- Resume storage is ephemeral (process memory). Re-upload after server restart.
- Chrome overlay uses high z-index and private window for stealth; avoid heavy DOM or external libs in `content.js` to keep it fast.

## Where to add features
- New Q&A behaviors: extend `app/ai_assistant.py` and expose via `simple_web.py` (/api/ask).
- Realtime/session features: extend `app/realtime.py` and wire endpoints in `web_interface.py`.
- Overlay behavior or UX: update `browser_extension/content.js` (keep API endpoints consistent: 8084 ask/resume).

Questions or gaps? Point out unclear areas (e.g., service URLs or extension behaviors) and we’ll refine these instructions.
