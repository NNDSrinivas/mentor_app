from __future__ import annotations
import json, os, time, threading
from typing import Dict, Any

_AUDIT_PATH = os.getenv("AUDIT_LOG_PATH", "./logs/audit.log")
os.makedirs(os.path.dirname(_AUDIT_PATH), exist_ok=True)
_lock = threading.Lock()

def audit(event: str, data: Dict[str, Any]):
    rec = {"ts": time.time(), "event": event, "data": data}
    line = json.dumps(rec, ensure_ascii=False)
    with _lock:
        with open(_AUDIT_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")
