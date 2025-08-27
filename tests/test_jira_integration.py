import json, hmac, hashlib, os, sys, types
import pytest

sys.path.append(os.getcwd())


def setup_app(monkeypatch):
    """Create a minimal Flask app with only the needed routes."""
    monkeypatch.setenv('JIRA_WEBHOOK_SECRET', 'secret')
    # Stub module to avoid OpenAI dependency
    sys.modules['backend.pr_auto_reply'] = types.SimpleNamespace(
        suggest_replies_and_patch=lambda *a, **k: {"raw": "{}"}
    )

    from flask import Flask, request, jsonify
    from backend.webhook_signatures import verify_jira
    from backend.approvals import approvals, propose_jira_from_notes
    from backend.approval_worker import on_approval_resolved

    app = Flask(__name__)

    @app.route('/webhook/jira', methods=['POST'])
    def jira_webhook():
        sig = request.headers.get('X-Shared-Secret', '')
        body = request.get_data()
        if not verify_jira(sig, body):
            return '', 401
        payload = request.get_json(force=True) or {}
        issue = payload.get('issue', {})
        key = issue.get('key')
        fields = issue.get('fields', {})
        summary = fields.get('summary', '')
        status = (fields.get('status') or {}).get('name', '')
        if key:
            pass  # memory update stubbed out
        return '', 204

    @app.route('/api/propose-jira', methods=['POST'])
    def propose():
        data = request.get_json(force=True) or {}
        project_key = data.get('project_key')
        notes = data.get('notes', [])
        items = propose_jira_from_notes(project_key, notes)
        return jsonify({'submitted': len(items), 'approvals': [vars(i) for i in items]})

    @app.route('/api/approvals/resolve', methods=['POST'])
    def resolve():
        data = request.get_json(force=True)
        item = approvals.resolve(data['id'], data['decision'])
        item['exec_result'] = on_approval_resolved(item)
        return jsonify(item)

    return app


def test_webhook_signature(monkeypatch):
    app = setup_app(monkeypatch)
    client = app.test_client()
    payload = {'issue': {'key': 'ENG-1', 'fields': {'summary': 'test', 'status': {'name': 'Open'}}}}
    body = json.dumps(payload).encode()
    sig = hmac.new(b'secret', body, hashlib.sha256).hexdigest()
    resp = client.post('/webhook/jira', data=body, headers={'Content-Type': 'application/json', 'X-Shared-Secret': sig})
    assert resp.status_code == 204
    resp = client.post('/webhook/jira', data=body, headers={'Content-Type': 'application/json', 'X-Shared-Secret': 'bad'})
    assert resp.status_code == 401


def test_propose_jira_approval_flow(monkeypatch):
    app = setup_app(monkeypatch)
    client = app.test_client()
    called = {}

    def fake_create_issue(self, project_key, summary, description, issue_type='Task'):
        called['args'] = (project_key, summary, description)
        return {'ok': True}

    monkeypatch.setattr('integrations.jira_client.JiraClient.create_issue', fake_create_issue)

    resp = client.post('/api/propose-jira', json={'project_key': 'ENG', 'notes': ['Do thing']})
    assert resp.status_code == 200
    approval_id = resp.get_json()['approvals'][0]['id']
    assert called == {}

    resp = client.post('/api/approvals/resolve', json={'id': approval_id, 'decision': 'approve'})
    assert resp.status_code == 200
    assert called['args'][0] == 'ENG'
