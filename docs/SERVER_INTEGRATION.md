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
