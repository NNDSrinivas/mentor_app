from __future__ import annotations
import os, time
from datetime import datetime, timedelta

def _days(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except Exception:
        return default

RAW_DAYS = _days("RETENTION_RAW_VIDEO_DAYS", 7)
TXT_DAYS = _days("RETENTION_TRANSCRIPT_DAYS", 30)
VEC_DAYS = _days("RETENTION_VECTOR_DAYS", 180)

def prune_path(path: str, older_than_days: int):
    if not os.path.exists(path): return
    cutoff = time.time() - older_than_days*86400
    for root, _, files in os.walk(path):
        for fn in files:
            p = os.path.join(root, fn)
            try:
                if os.path.getmtime(p) < cutoff:
                    os.remove(p)
            except Exception:
                pass

def run_once():
    prune_path("./data/recordings", RAW_DAYS)
    prune_path("./data/transcripts", TXT_DAYS)
    prune_path("./data/chroma_db", VEC_DAYS)

if __name__ == "__main__":
    run_once()
