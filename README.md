# AI Mentor Assistant (Prototype)

This repository contains a **prototype** for a personal AI‑mentor application.  The goal of the project is to explore how an agent can help engineers by:

* automatically capturing and summarizing meetings and screen recordings;
* building a knowledge base from a project’s code, documentation and tasks;
* answering questions about the system like a senior engineer or architect; and
* providing guidance on day‑to‑day activities such as coding and documentation.

This is **not** a full‑featured product.  It contains skeletal modules that outline how such a system could be structured.  Each component includes placeholder functions for capturing data, transcribing audio/video, summarizing content, recording the screen and integrating with a knowledge base.  You can expand these modules by plugging in real APIs (e.g., Zoom/Teams bots, OpenAI Whisper for speech‑to‑text, LLMs for summarization, or OpenCV for video analysis) and connecting them to your environment.

## Project structure

```
mentor_app/
├── README.md            – project overview and setup instructions
├── requirements.txt      – Python dependencies
└── app/
    ├── __init__.py
    ├── capture.py        – meeting and audio/video capture stubs
    ├── transcription.py  – speech‑to‑text stubs
    ├── summarization.py  – LLM summarization stubs
    ├── screen_record.py  – screen recording stubs
    ├── knowledge_base.py – knowledge‑base integration stubs
    └── main.py           – example orchestration of components
```

## Getting started

1. **Install dependencies**

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Run the prototype**

   The `main.py` script demonstrates how the different components might work together.  It currently calls placeholder functions that simply print messages.  Replace the bodies of these functions with your own logic.

   ```bash
   python -m app.main
   ```

3. **Extend the modules**

   * **capture.py** – Add functions to join meetings (via APIs or webhooks) and capture audio/video streams.
   * **transcription.py** – Integrate a speech‑to‑text engine (e.g., Whisper, Google Speech‑to‑Text) to transcribe audio.
   * **summarization.py** – Use a large language model (LLM) to summarize transcribed text, extract decisions and action items and answer questions.
   * **screen_record.py** – Implement screen capture using a browser extension (for web meetings) or native libraries (e.g., `ffmpeg`, `pyautogui`) and process frames with computer‑vision techniques.
   * **knowledge_base.py** – Build a knowledge base from your code repositories and documentation.  Store embeddings in a vector database and use them to provide context to the LLM.

## Notes on deployment

Recording meetings and screens may be subject to company policy and privacy regulations.  Always obtain consent from participants and coordinate with your IT and security teams before deploying.  For environments with strict software controls, consider implementing your capture logic as a browser extension or a server‑side meeting bot.