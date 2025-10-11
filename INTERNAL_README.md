# 🧠 AI Mentor App – Internal Developer Handbook

> Confidential engineering documentation • Do not distribute externally

---

## 🔧 Repository Layout  



services/
backend/ → Q&A API (8084)
realtime/ → Meeting + session API (8080)
clients/
browser_extension/
vscode_extension/
mobile/
infra/
docker/
scripts/


---

## ⚙️ Local Setup  

1.  Python 3.11+  
2.  Create virtual env & install deps  
3.  Add `OPENAI_API_KEY` to `.env`  
4.  Run both services (see main README)  

**Optional Flags**
| Env Var | Description | Default |
|----------|--------------|----------|
| `MOCK_MODE` | run without API key (returns simulated data) | `false` |
| `ENABLE_SCREEN_RECORDING` | capture desktop stream for meeting analysis | `false` |
| `LOG_LEVEL` | `DEBUG` / `INFO` / `ERROR` | `INFO` |

---

## 🧩 Core Services  

### 🟢 Backend (`production_backend.py`)
Handles Q&A, resume storage, embeddings, and memory lookups.  

Endpoints  


GET /api/health
POST /api/ask
POST /api/resume
GET /api/resume


### 🔵 Realtime (`production_realtime.py`)
Manages meeting sessions, caption streams, and mentor answers.  

Endpoints  


POST /api/sessions
POST /api/sessions/{id}/captions
GET /api/sessions/{id}/answers
DELETE /api/sessions/{id}


---

## 🧠 Memory Layer (Integration Plan)

Uses **Memory Cloud** subsystem to persist long-term context.

| Data Type | Storage | Notes |
|------------|----------|-------|
| Meeting Transcripts | Vector DB (Chroma) | indexed by timestamp + topic |
| Tasks / Tickets | SQL (JIRA sync) | 2-way update planned |
| Code Diff Contexts | FS + Embeddings | connect to GitHub API |

---

## 🧰 Developer Scripts  

| Command | Purpose |
|----------|----------|
| `make dev` | launch both services |
| `make lint` | run ruff + black |
| `make test` | pytest suite |
| `make docker` | build images |
| `scripts/smoke_test.sh` | end-to-end curl validation |

---

## 🧱 Testing Checklist  

- ✅ Health checks pass  
- ✅ Mock mode runs without API key  
- ✅ Realtime flow (POST captions → GET answers)  
- ⚙️ Add JIRA read-only sync tests  
- ⚙️ Add end-to-end integration pipeline  

---

## 🔐 Security & Compliance  

- Secrets in `.env`, never checked in  
- Use `docker run --network=host` only locally  
- Future: Okta SSO + AES-256 data-at-rest  
- Data retention: delete sessions > 30 days old in cron  

---

## 🧭 Future Engineering Milestones  

1. Meeting Diarization Module (VAD + Whisper)  
2. JIRA Sync Service (Read/Write)  
3. Auto-PR Generator (GitHub API)  
4. Code Diff Summarizer + Mentor Commenting  
5. Agentic Planning Loop (OpenDevin Style)  
6. Full Memory Cloud API integration  

---

## ⚠️ Confidentiality  

This file contains proprietary implementation details and internal plans.  
Do not share, copy, or upload outside approved organization repositories.

© 2025 Naga Durga Srinivas Nidamanuri – All Rights Reserved.
