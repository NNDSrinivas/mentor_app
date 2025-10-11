from __future__ import annotations
from flask import Blueprint, request
from typing import Any, Dict

from backend.webhook_signatures import verify_github
try:  # pragma: no cover - optional approvals integration
    from backend.approvals import request_pr_auto_reply, approvals
except ImportError:  # pragma: no cover - fallback for tests without approvals module
    def request_pr_auto_reply(*args, **kwargs):
        return {}

    class _ApprovalsFallback:
        def submit(self, *args, **kwargs):
            return {}

        def list(self, *args, **kwargs):
            return []

        def get(self, *args, **kwargs):
            return None

        def resolve(self, *args, **kwargs):
            return {}

    approvals = _ApprovalsFallback()

from backend.patch_suggester import suggest_patch_from_url

bp = Blueprint("github", __name__)

@bp.route("/webhook/github", methods=["POST"])
def github_webhook():
    """Handle GitHub webhook events with signature verification."""
    sig = request.headers.get("X-Hub-Signature-256", "")
    body = request.get_data()
    if not verify_github(sig, body):
        return "", 401

    event = request.headers.get("X-GitHub-Event", "")
    payload: Dict[str, Any] = request.get_json(force=True) or {}

    if event == "pull_request":
        action = payload.get("action")
        if action in ("opened", "synchronize"):
            repo_full = payload.get("repository", {}).get("full_name", "")
            owner, repo = repo_full.split("/", 1) if "/" in repo_full else ("", repo_full)
            pr_number = payload.get("pull_request", {}).get("number")
            if owner and repo and pr_number:
                request_pr_auto_reply(owner, repo, pr_number)
    elif event == "workflow_run":
        action = payload.get("action")
        workflow = payload.get("workflow_run", {})
        if action == "completed" and workflow.get("conclusion") == "failure":
            logs_url = workflow.get("logs_url", "")
            patch = suggest_patch_from_url(logs_url) if logs_url else ""
            if patch:
                approvals.submit("github.apply_patch", {"patch_content": patch})

    return "", 204
