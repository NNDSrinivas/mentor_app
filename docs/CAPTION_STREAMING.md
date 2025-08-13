# Caption Streaming Demo

This repository includes simple caption clients for Zoom, Microsoft Teams, and Google Meet. Each client reads caption lines from a text file and forwards them to the real‑time session manager.

## Running the demo

```bash
python scripts/caption_flow_example.py
```

The script starts a session for each sample meeting and streams captions from files in `docs/sample_meetings/`. After streaming, the captured captions are printed to the console to verify end‑to‑end flow.
