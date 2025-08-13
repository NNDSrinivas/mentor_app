import base64
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
