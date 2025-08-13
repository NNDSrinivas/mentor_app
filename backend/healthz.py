from __future__ import annotations
import os
from flask import Blueprint, jsonify
from .middleware import BUCKETS

bp = Blueprint("healthz", __name__)

@bp.get("/healthz/full")
def full():
    checks = {}
    checks["OPENAI_API_KEY"] = bool(os.getenv("OPENAI_API_KEY"))
    db_path = os.getenv("MEMORY_DB_PATH", "./memory_db")
    checks["VECTOR_DB_PATH_EXISTS"] = os.path.exists(db_path) or os.path.exists("./data/chroma_db")
    checks["GITHUB_WEBHOOK_SECRET"] = bool(os.getenv("GITHUB_WEBHOOK_SECRET"))
    checks["RATE_BUCKETS"] = len(BUCKETS.buckets)
    healthy = all(v if isinstance(v, bool) else True for v in checks.values())
    return jsonify({"ok": healthy, "checks": checks})
