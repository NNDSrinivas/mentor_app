from __future__ import annotations
import os
from flask import Blueprint, jsonify
from .middleware import BUCKETS

bp = Blueprint("healthz", __name__)

@bp.get("/healthz/full")
def full():
    checks = {}
    # Ensure OpenAI key is configured
    checks["OPENAI_API_KEY"] = bool(os.getenv("OPENAI_API_KEY"))
    # Verify vector database path exists (default ./data/chroma_db)
    vector_path = os.getenv("VECTOR_DB_PATH", "./data/chroma_db")
    checks["VECTOR_DB_PATH_EXISTS"] = os.path.exists(vector_path)
    # Webhook secrets
    checks["GITHUB_WEBHOOK_SECRET"] = bool(os.getenv("GITHUB_WEBHOOK_SECRET"))
    checks["JIRA_WEBHOOK_SECRET"] = bool(os.getenv("JIRA_WEBHOOK_SECRET"))
    # Rate limit bucket status (number of active buckets)
    checks["RATE_BUCKETS"] = len(BUCKETS.buckets)
    healthy = all(v if isinstance(v, bool) else True for v in checks.values())
    return jsonify({"ok": healthy, "checks": checks})
