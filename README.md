# 🧠 AI Mentor App  
> *The Autonomous Engineering Intelligence Platform*

---

## 🚀 Overview  

AI Mentor App is an **autonomous AI engineering assistant** that listens to meetings, understands JIRA tickets, reviews and writes code, and collaborates with teams in real time.  
It behaves like a full-time digital coworker — remembering every decision, task, and context so engineers can focus on innovation.

---

## 💡 Key Capabilities  

- 🗓 **Meeting Intelligence** – Captures discussions → action items automatically  
- 📋 **JIRA & GitHub Sync** – Understands open tasks and pull requests  
- 💻 **Autonomous Coding** – Plans → writes → tests → commits under supervision  
- 🧠 **Persistent Memory** – Retains full project context via integrated *Memory Cloud*  
- 🗣 **Live Participation** – Answers or summarizes in meetings using current state  
- 🔒 **Enterprise Security** – Local-first processing + Okta/SSO ready  

---

## 🏗 Architecture at a Glance  



Frontend Clients → [Chrome Extension | VS Code Plugin | Mobile App]
│
▼
+-----------------------------+
| AI Mentor Core |
|-----------------------------|
| Q&A API (8084) | Realtime API (8080) |
+-----------------------------+
| LLM + Planning Engine |
| (GPT-4o / Claude / Llama) |
+-----------------------------+
| Memory Graph + Chroma DB |
+-----------------------------+


---

## ⚙️ Quick Start  

```bash
git clone https://github.com/NNDSrinivas/mentor_app.git
cd mentor_app
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.template .env    # add your OPENAI_API_KEY
```


Run services

```
python production_backend.py      # 8084
python production_realtime.py     # 8080
```


Check

```
curl http://localhost:8084/api/health
curl http://localhost:8080/api/health
```

🧭 Roadmap Highlights
PhaseFocusETA
✅ MVPRealtime & Q&A APIs runningQ1 2025
🧩 Phase 2JIRA / GitHub IntegrationsQ2 2025
🧠 Phase 3Autonomous Code ExecutionQ3 2025
🏢 Phase 4Enterprise Security + SSOQ4 2025
🌐 Phase 5Global Platform API2026
👤 Founder

Naga Durga Srinivas Nidamanuri
📧 srinivasn7779@gmail.com
 | LinkedIn:https://www.linkedin.com/in/nnd-srinivas/
 | GitHub:https://github.com/NNDSrinivas

⚠️ Notice

This repository represents pre-release proprietary technology currently under patent consideration.
All rights reserved © 2025 Naga Durga Srinivas Nidamanuri.
