from __future__ import annotations
from flask import Blueprint, request, jsonify
from typing import Any, List

from backend.webhook_signatures import verify_jira
from backend.memory_service import MemoryService
try:  # pragma: no cover - optional approvals integration
    from backend.approvals import propose_jira_from_notes
except ImportError:  # pragma: no cover - fallback for tests without approvals module
    def propose_jira_from_notes(*args, **kwargs):
        return {}
from backend.payments import subscription_required

bp = Blueprint('jira', __name__)
mem = MemoryService()

@bp.route('/webhook/jira', methods=['POST'])
def jira_webhook():
    """Handle Jira webhook callbacks with signature verification."""
    sig = request.headers.get('X-Shared-Secret', '')
    body = request.get_data()
    if not verify_jira(sig, body):
        return "", 401
    payload = request.get_json(force=True) or {}
    issue = payload.get('issue', {})
    key = issue.get('key')
    fields = issue.get('fields', {})
    summary = fields.get('summary', '')
    status = (fields.get('status') or {}).get('name', '')
    if key:
        text = f"[{key}] {summary} — status: {status}"
        mem.add_task(key, text, metadata={'summary': summary, 'status': status, 'jira_key': key})
    return "", 204

@bp.route('/api/propose-jira', methods=['POST'])
@subscription_required
def propose_jira():
    """Create approvals for Jira tickets derived from meeting notes."""
    data = request.get_json(force=True) or {}
    project_key = data.get('project_key') or data.get('project')
    notes: List[Any] = data.get('notes') or []
    if not project_key or not isinstance(notes, list):
        return jsonify({'error': 'Missing project_key or notes'}), 400
    items = propose_jira_from_notes(project_key, notes)
    return jsonify({
        'submitted': len(items),
        'approvals': [vars(i) for i in items]
    })
