from __future__ import annotations
import os
from flask import Blueprint, jsonify
from .middleware import BUCKETS
from .memory_service import MemoryService
from .approvals import approvals

bp = Blueprint("healthz", __name__)

@bp.get("/healthz/full")
def full():
    checks = {}
    checks["OPENAI_API_KEY"] = bool(os.getenv("OPENAI_API_KEY"))

    # Vector DB connectivity
    try:
        ms = MemoryService()
        if ms.client:
            ms.client.list_collections()
        checks["VECTOR_DB_CONNECTED"] = True
    except Exception:
        checks["VECTOR_DB_CONNECTED"] = False

    # Approvals queue depth
    checks["APPROVALS_QUEUE_DEPTH"] = approvals.q.qsize()

    # Webhook secret presence (GitHub/Jira/Stripe)
    checks["WEBHOOK_SECRET_PRESENT"] = bool(
        os.getenv("GITHUB_WEBHOOK_SECRET")
        or os.getenv("JIRA_WEBHOOK_SECRET")
        or os.getenv("STRIPE_WEBHOOK_SECRET")
    )

    checks["RATE_BUCKETS"] = len(BUCKETS.buckets)
    healthy = all(v if isinstance(v, bool) else True for v in checks.values())
    return jsonify({"ok": healthy, "checks": checks})
