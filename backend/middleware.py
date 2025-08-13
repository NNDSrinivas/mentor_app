from __future__ import annotations
import time, os, threading
from typing import Dict, Tuple
from flask import request, jsonify
from .audit import audit

_RATE = {"MEETING_EVENTS_PER_MIN": 600, "ANSWERS_PER_MIN": 30}
_COST = {"TOKENS_PER_DAY": 250000, "WARN_AT": 0.8}

class Buckets:
    def __init__(self):
        self.rates = _RATE
        self.costs = _COST
        self.tokens: Dict[str, Tuple[float,int]] = {}
        self.buckets: Dict[Tuple[str,str], Tuple[float,float]] = {}
        self.lock = threading.Lock()

    def _now(self): return time.time()

    def check_rate(self, key: str, kind: str) -> bool:
        limit = self.rates["MEETING_EVENTS_PER_MIN"] if kind=="meeting" else self.rates["ANSWERS_PER_MIN"]
        per = 60.0
        with self.lock:
            cur = self.buckets.get((key, kind))
            now = self._now()
            if not cur:
                self.buckets[(key,kind)] = (now, float(limit))
                return True
            t0, tokens = cur
            tokens = min(limit, tokens + (now - t0) * (limit / per))
            if tokens < 1.0:
                self.buckets[(key,kind)] = (now, tokens)
                return False
            self.buckets[(key,kind)] = (now, tokens - 1.0)
            return True

    def add_tokens(self, key: str, n: int):
        day = int(self._now() // 86400)
        use_key = f"{key}:{day}"
        with self.lock:
            t0, used = self.tokens.get(use_key, (self._now(), 0))
            used += n
            self.tokens[use_key] = (t0, used)
            return used

    def get_cost_status(self, key: str):
        day = int(self._now() // 86400)
        used = self.tokens.get(f"{key}:{day}", (0,0))[1]
        limit = self.costs["TOKENS_PER_DAY"]
        warn_at = self.costs["WARN_AT"]
        return {"used": used, "limit": limit, "ok": used < limit, "warn": used/limit >= warn_at}

BUCKETS = Buckets()

def client_key():
    return request.headers.get("X-User-Key") or request.remote_addr or "anon"

def rate_limit(kind: str):
    def deco(fn):
        def wrapped(*args, **kwargs):
            k = client_key()
            if not BUCKETS.check_rate(k, kind):
                audit("rate_limit_block", {"key": k, "kind": kind})
                return jsonify({"ok": False, "error": "rate_limited"}), 429
            return fn(*args, **kwargs)
        wrapped.__name__ = fn.__name__
        return wrapped
    return deco

def record_cost(tokens: int):
    k = client_key()
    used = BUCKETS.add_tokens(k, tokens)
    status = BUCKETS.get_cost_status(k)
    if status["warn"]:
        audit("cost_warn", {"key": k, "used": status["used"], "limit": status["limit"]})
    return status
