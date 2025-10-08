import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.db.base import session_scope
from backend.db.models import JiraConnection, JiraProjectConfig
from backend.db.utils import ensure_schema


@pytest.fixture(autouse=True)
def configure_env(monkeypatch, tmp_path):
    db_url = f"sqlite:///{tmp_path}/jira.db"
    monkeypatch.setenv("KNOWLEDGE_DATABASE_URL", db_url)
    monkeypatch.setenv("MOCK_JIRA", "true")
    monkeypatch.setenv("JIRA_SYNC_INLINE", "true")
    monkeypatch.setenv("JIRA_CLIENT_ID", "test-client")
    monkeypatch.setenv("JIRA_CLIENT_SECRET", "test-secret")
    monkeypatch.setenv("JIRA_REDIRECT_URI", "http://localhost/callback")
    monkeypatch.setenv("JIRA_ENCRYPTION_KEY", "integration-test-key")
    ensure_schema()
    yield


def test_token_refresh(monkeypatch):
    monkeypatch.setenv("MOCK_JIRA", "false")
    from backend.integrations.jira_service import JiraIntegrationService, _now

    service = JiraIntegrationService()
    with session_scope() as session:
        connection = JiraConnection(
            org_id=service.resolve_context({})[0],
            user_id=service.resolve_context({})[1],
            cloud_base_url="https://example.atlassian.net",
            client_id="test-client",
            token_type="Bearer",
            access_token=service.cipher.encrypt("stale"),
            refresh_token=service.cipher.encrypt("refresh-old"),
            expires_at=_now() - timedelta(minutes=1),
            scopes=["read"],
        )
        session.add(connection)
        session.flush()
        connection_id = connection.id

    class DummyResponse:
        def __init__(self):
            self._payload = {
                "access_token": "new-access",
                "refresh_token": "new-refresh",
                "token_type": "Bearer",
                "expires_in": 7200,
                "scope": "read:jira-work",
            }

        def json(self):
            return self._payload

        def raise_for_status(self):
            return None

        status_code = 200

    def fake_post(url, json=None, timeout=30):  # noqa: A002 - match requests signature
        assert json["grant_type"] == "refresh_token"
        return DummyResponse()

    monkeypatch.setattr("requests.post", fake_post)

    with session_scope() as session:
        connection = session.get(JiraConnection, connection_id)
        updated = service.ensure_access_token(session, connection)

    assert service.cipher.decrypt(updated.access_token) == "new-access"
    assert service.cipher.decrypt(updated.refresh_token) == "new-refresh"
    assert updated.scopes == ["read:jira-work"]


def test_upsert_issue_updates(monkeypatch):
    from backend.integrations.jira_service import JiraIntegrationService

    class StubVector:
        def __init__(self):
            self.calls: List[Dict[str, str]] = []

        def index_issue(self, issue_key, text, metadata):
            self.calls.append({"key": issue_key, "text": text, **metadata})

        def search(self, query, limit=10):
            return {}

    service = JiraIntegrationService(vector_store=StubVector())
    org_id, user_id = service.resolve_context({})

    tokens = service.exchange_code_for_tokens("dummy")
    connection = service.store_tokens(
        org_id=org_id,
        user_id=user_id,
        cloud_base_url="https://example.atlassian.net",
        tokens=tokens,
    )

    issue_payload = {
        "key": "PROJ-99",
        "fields": {
            "summary": "Initial summary",
            "description": "Initial description",
            "status": {"name": "To Do"},
            "priority": {"name": "Low"},
            "assignee": {"displayName": "Alice"},
            "updated": "2024-04-25T00:00:00.000+0000",
        },
    }

    with session_scope() as session:
        issue, reindexed = service._upsert_issue(session, connection, issue_payload)  # noqa: SLF001
        assert reindexed is True
        assert issue.summary == "Initial summary"

    updated_payload = json.loads(json.dumps(issue_payload))
    updated_payload["fields"]["summary"] = "Updated summary"
    updated_payload["fields"]["updated"] = "2024-04-26T00:00:00.000+0000"

    with session_scope() as session:
        session.add(connection)
        session.flush()
        refreshed = session.get(JiraConnection, connection.id)
        issue, reindexed = service._upsert_issue(session, refreshed, updated_payload)  # noqa: SLF001
        assert reindexed is True
        assert issue.summary == "Updated summary"
    assert len(service.vector_store.calls) == 2


def test_jql_pagination(monkeypatch):
    monkeypatch.setenv("MOCK_JIRA", "false")
    from backend.integrations.jira_service import JiraIntegrationService

    from backend.integrations.jira_service import OAuthTokens

    service = JiraIntegrationService()
    service.mock_mode = False

    tokens = OAuthTokens(
        access_token="token",
        refresh_token="refresh",
        token_type="Bearer",
        expires_in=3600,
        scope=["read"],
    )
    connection = service.store_tokens(
        org_id=service.resolve_context({})[0],
        user_id=service.resolve_context({})[1],
        cloud_base_url="https://example.atlassian.net",
        tokens=tokens,
    )

    with session_scope() as session:
        config = JiraProjectConfig(
            org_id=connection.org_id,
            connection_id=connection.id,
            project_keys=["PROJ"],
        )
        session.add(config)
        session.flush()
        config_id = config.id

    payloads = iter(
        [
            {"issues": [{"key": "PROJ-1", "fields": {"summary": "One"}}], "total": 2},
            {"issues": [{"key": "PROJ-2", "fields": {"summary": "Two"}}], "total": 2},
        ]
    )

    class DummyResponse:
        def __init__(self, data):
            self.data = data
            self.status_code = 200

        def json(self):
            return self.data

        def raise_for_status(self):
            return None

    service._request_with_retry = lambda *args, **kwargs: DummyResponse(next(payloads))  # type: ignore[attr-defined]

    with session_scope() as session:
        config = session.get(JiraProjectConfig, config_id)
        issues = list(service._fetch_updated_issues(connection, config))  # noqa: SLF001
    assert {issue["key"] for issue in issues} == {"PROJ-1", "PROJ-2"}


def test_integration_flow():
    from backend.integrations.jira_service import JiraIntegrationService

    service = JiraIntegrationService()
    org_id, user_id = service.resolve_context({})

    start_payload = service.build_oauth_url()
    assert "url" in start_payload

    tokens = service.exchange_code_for_tokens("mock-code")
    connection = service.store_tokens(
        org_id=org_id,
        user_id=user_id,
        cloud_base_url="https://example.atlassian.net",
        tokens=tokens,
    )

    config = service.update_project_config(
        org_id=org_id,
        connection_id=connection.id,
        project_keys=["PROJ"],
        board_ids=[],
        default_jql=None,
    )
    assert config.project_keys == ["PROJ"]

    summary = service.perform_sync(org_id)
    assert summary["processed"] >= 3

    status = service.get_status(org_id)
    assert status["connected"] is True
    assert status["projects"] == ["PROJ"]

    tasks = service.list_tasks(org_id, "me", None, "PROJ", None, me_identifier="Alice")
    assert any(task["assignee"] == "Alice" for task in tasks)

    search_results = service.search(org_id, "OAuth", "PROJ")
    assert any("oauth" in (item["description"] or "").lower() for item in search_results)

    issue = service.get_issue(org_id, "PROJ-1")
    assert issue["key"] == "PROJ-1"


def test_load_sync_scalability(monkeypatch):
    from backend.integrations.jira_service import JiraIntegrationService

    class CountingVector:
        def __init__(self):
            self.count = 0

        def index_issue(self, issue_key, text, metadata):
            self.count += 1

        def search(self, query, limit=10):
            return {}

    from backend.integrations.jira_service import OAuthTokens

    from backend.db.models import JiraIssue

    with session_scope() as session:
        session.query(JiraIssue).delete()
        session.query(JiraProjectConfig).delete()
        session.query(JiraConnection).delete()

    service = JiraIntegrationService(vector_store=CountingVector())
    service.mock_mode = False

    tokens = OAuthTokens(
        access_token="token",
        refresh_token="refresh",
        token_type="Bearer",
        expires_in=3600,
        scope=["read"],
    )
    connection = service.store_tokens(
        org_id=service.resolve_context({})[0],
        user_id=service.resolve_context({})[1],
        cloud_base_url="https://example.atlassian.net",
        tokens=tokens,
    )

    with session_scope() as session:
        config = JiraProjectConfig(
            org_id=connection.org_id,
            connection_id=connection.id,
            project_keys=["PROJ"],
            last_sync_at=datetime.now(timezone.utc) - timedelta(days=1),
        )
        session.add(config)
        session.flush()
        org_id = connection.org_id

    def generator():
        for idx in range(5000):
            yield {
                "key": f"PROJ-{idx}",
                "fields": {
                    "summary": f"Issue {idx}",
                    "description": "Synthetic load issue",
                    "status": {"name": "In Progress"},
                    "priority": {"name": "Medium"},
                    "assignee": {"displayName": "Load"},
                    "updated": "2024-04-27T00:00:00.000+0000",
                },
            }

    service._fetch_updated_issues = lambda *args, **kwargs: generator()  # type: ignore[attr-defined]
    result = service.perform_sync(org_id)
    assert result["processed"] == 5000
    assert service.vector_store.count == 5000

    with session_scope() as session:
        count = session.query(JiraConnection).filter(JiraConnection.org_id == org_id).count()
        assert count == 1
        issue_count = session.query(JiraIssue).count()
        assert issue_count >= 5000
