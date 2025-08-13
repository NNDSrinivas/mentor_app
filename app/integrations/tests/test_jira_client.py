import base64, time
from app.integrations.jira_client import JiraClient


def test_headers_are_base64_encoded(monkeypatch):
    user = 'user'
    token = 'token'
    monkeypatch.setenv('JIRA_USER', user)
    monkeypatch.setenv('JIRA_TOKEN', token)

    client = JiraClient()
    headers = client._headers()

    expected = base64.b64encode(f"{user}:{token}".encode()).decode()
    assert headers['Authorization'] == f'Basic {expected}'
    assert headers['Content-Type'] == 'application/json'


def test_get_assigned_issues_dry_run(monkeypatch):
    monkeypatch.setenv('JIRA_USER', 'user')
    monkeypatch.setenv('JIRA_TOKEN', 'token')
    client = JiraClient()
    issues = client.get_assigned_issues('me')
    assert issues['dry_run'] is True
    assert issues['assignee'] == 'me'


def test_polling(monkeypatch):
    monkeypatch.setenv('JIRA_USER', 'user')
    monkeypatch.setenv('JIRA_TOKEN', 'token')
    client = JiraClient()
    collected = []

    def cb(data):
        collected.append(data)
        client.stop_polling()

    client.start_polling_assigned('me', 1, cb)
    time.sleep(0.1)
    assert collected and collected[0]['dry_run']
