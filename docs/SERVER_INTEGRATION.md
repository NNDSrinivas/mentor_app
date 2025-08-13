# Server integration

## Register healthz
```python
from backend.healthz import bp as healthz_bp
app.register_blueprint(healthz_bp)
```

## Rate limit noisy endpoints + record cost
```python
from backend.middleware import rate_limit, record_cost

@app.post('/api/meeting-events')
@rate_limit('meeting')
def meeting_events():
    # ...
    record_cost(tokens=1500)
    return jsonify({'ok': True})
```

## Verify webhook signatures
```python
from backend.webhook_signatures import verify_github, verify_jira

@app.post('/webhook/github')
def gh_webhook():
    sig = request.headers.get('X-Hub-Signature-256','')
    body = request.get_data()
    if not verify_github(sig, body):
        return '', 401
    # handle event
    return '', 204

@app.post('/webhook/jira')
def jira_webhook():
    sig = request.headers.get('X-Shared-Secret','')
    body = request.get_data()
    if not verify_jira(sig, body):
        return '', 401
    # handle event
    return '', 204
```

## Configure GitHub and Jira managers

Environment variables are used to talk to external services.  At minimum set:

```bash
export GITHUB_TOKEN="<personal access token>"
export GITHUB_API="https://api.github.com"  # optional override

export JIRA_BASE_URL="https://your-domain.atlassian.net"
export JIRA_USER="bot@example.com"
export JIRA_TOKEN="<jira api token>"
```

These values are read by `backend.integrations.github_manager.GitHubManager`
and `backend.integrations.jira_manager.JiraManager`.

## Approval flow

Actions that touch GitHub or Jira go through `backend.approvals`.  Each action
is queued and must be resolved via `POST /api/approvals/resolve` before the
`approval_worker` executes it.

Auto-reply suggestions for pull requests are created using
`backend/pr_auto_reply.py`.  The helper
`backend.approvals.request_pr_auto_reply()` fetches PR metadata, generates
suggested comments, and enqueues the result.  When a PR is merged or its state
changes, `backend.approvals.sync_jira_pr_status()` can be called to add a
comment to the related Jira issue.

This workflow provides auditable control over external integrations while still
allowing helpful automation.
