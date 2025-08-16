from __future__ import annotations
import json, os, time, threading
from typing import Dict, Any
from flask import request

_AUDIT_PATH = os.getenv("AUDIT_LOG_PATH", "./logs/audit.log")
os.makedirs(os.path.dirname(_AUDIT_PATH), exist_ok=True)
_lock = threading.Lock()

def audit(event: str, data: Dict[str, Any]):
    """Record a structured audit log entry."""
    try:
        actor = request.headers.get("X-User-Key") or request.remote_addr or "anon"
        path = request.path
    except Exception:
        actor = None
        path = None

    rec = {
        "ts": time.time(),
        "event": event,
        "actor": actor,
        "path": path,
        "data": data,
    }
    line = json.dumps(rec, ensure_ascii=False)
    with _lock:
        with open(_AUDIT_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")
