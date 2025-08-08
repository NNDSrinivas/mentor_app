# backend/audit.py
from __future__ import annotations
import json, time, os
from typing import Dict, Any

AUDIT_LOG = os.getenv("AUDIT_LOG_PATH","./audit.log")

def audit(event: str, data: Dict[str, Any]):
    rec = {"ts": time.time(), "event": event, "data": data}
    with open(AUDIT_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")
