from __future__ import annotations

import copy
import importlib
import sys
import time
import types
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Iterable, List

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import pytest


@dataclass
class JiraTestEnv:
    jira_module: object
    models: object


@pytest.fixture
def jira_env(tmp_path, monkeypatch) -> Iterable[JiraTestEnv]:
    db_path = tmp_path / "jira.db"
    memory_path = tmp_path / "memory"
    monkeypatch.setenv("KNOWLEDGE_DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("MEMORY_DB_PATH", str(memory_path))
    monkeypatch.setenv("JIRA_ENCRYPTION_KEY", "integration-test-key")

    db_base = importlib.import_module("backend.db.base")
    models = importlib.import_module("backend.db.models")
    jira_module = importlib.import_module("backend.jira_integration")

    db_base.get_sessionmaker(f"sqlite:///{db_path}")
    engine = db_base.get_engine()
    tables = [
        models.JiraConnection.__table__,
        models.JiraProjectConfig.__table__,
        models.JiraIssue.__table__,
    ]
    for table in tables:
        table.drop(engine, checkfirst=True)
    for table in tables:
        table.create(engine, checkfirst=True)
    jira_module.integration_service = jira_module.JiraIntegrationService()

    yield JiraTestEnv(jira_module=jira_module, models=models)

    for table in tables:
        table.drop(engine, checkfirst=True)


def _create_connection(env: JiraTestEnv, org_id: uuid.UUID, user_id: uuid.UUID, **kwargs):
    jira = env.jira_module
    models = env.models
    with jira.session_scope() as session:
        connection = models.JiraConnection(
            org_id=org_id,
            user_id=user_id,
            cloud_base_url=kwargs.get("cloud_base_url", "https://example.atlassian.net"),
            client_id=kwargs.get("client_id", "client"),
            token_type=kwargs.get("token_type", "Bearer"),
            access_token=jira._encrypt(kwargs.get("access_token", "token")),
            refresh_token=jira._encrypt(kwargs.get("refresh_token", "refresh")),
            expires_at=kwargs.get("expires_at", jira._now() + timedelta(hours=1)),
            scopes=kwargs.get("scopes", ["read:jira-work"]),
        )
        session.add(connection)
        session.flush()
        connection_id = connection.id
    return connection_id


def _create_config(env: JiraTestEnv, org_id: uuid.UUID, connection_id, project_keys: List[str]):
    jira = env.jira_module
    models = env.models
    with jira.session_scope() as session:
        config = models.JiraProjectConfig(
            org_id=org_id,
            connection_id=connection_id,
            project_keys=project_keys,
        )
        session.add(config)
        session.flush()
        return config.id


def test_token_refresh_updates_connection(jira_env, monkeypatch):
    env = jira_env
    jira = env.jira_module
    models = env.models
    monkeypatch.delenv("MOCK_JIRA", raising=False)
    monkeypatch.setenv("JIRA_CLIENT_SECRET", "super-secret")

    org_id = uuid.uuid4()
    user_id = uuid.uuid4()
    connection_id = _create_connection(
        env,
        org_id,
        user_id,
        access_token="expired-token",
        refresh_token="refresh-token",
        expires_at=jira._now() - timedelta(seconds=5),
    )

    calls: Dict[str, Dict[str, object]] = {}

    class _TokenResponse:
        status_code = 200

        def json(self):
            return {"access_token": "new-access", "expires_in": 3600}

        def raise_for_status(self):
            return None

    def _fake_post(url, json=None, timeout=None):
        calls["payload"] = json
        return _TokenResponse()

    monkeypatch.setattr(jira.requests, "post", _fake_post)

    with jira.session_scope() as session:
        connection = session.get(models.JiraConnection, connection_id)
        token = jira.integration_service._ensure_access_token(session, connection)

    assert token == "new-access"
    assert calls["payload"]["grant_type"] == "refresh_token"
    with jira.session_scope() as session:
        connection = session.get(models.JiraConnection, connection_id)
        assert jira._decrypt(connection.access_token) == "new-access"


def test_sync_upsert_and_status(jira_env, monkeypatch):
    env = jira_env
    jira = env.jira_module
    models = env.models
    monkeypatch.setenv("MOCK_JIRA", "true")

    org_id = uuid.uuid4()
    user_id = uuid.uuid4()
    connection_id = _create_connection(env, org_id, user_id)
    _create_config(env, org_id, connection_id, ["PROJ", "OPS"])

    result = jira.integration_service.sync_now(org_id)
    assert result.fetched == 3
    assert result.updated == 3
    assert result.indexed == 3

    status = jira.integration_service.get_status(org_id)
    assert status["connected"] is True
    assert set(status["projects"]) == {"PROJ", "OPS"}

    tasks = jira.integration_service.list_tasks(org_id, assignee="Alice Doe", status="In Progress", project="PROJ")
    assert len(tasks) == 1
    assert tasks[0]["key"] == "PROJ-1"

    original_loader = jira._load_mock_fixture

    def _patched_loader(name: str):
        data = original_loader(name)
        if name == "issues.json":
            updated = copy.deepcopy(data)
            updated["issues"][0]["fields"]["summary"] = "Implement OAuth flow (updated)"
            return updated
        return data

    monkeypatch.setattr(jira, "_load_mock_fixture", _patched_loader)
    jira.integration_service.sync_now(org_id)

    with jira.session_scope() as session:
        issue = (
            session.query(models.JiraIssue)
            .filter(
                models.JiraIssue.connection_id == connection_id,
                models.JiraIssue.issue_key == "PROJ-1",
            )
            .one()
        )
        assert issue.summary.endswith("(updated)")


def test_sync_allows_duplicate_issue_keys_per_connection(jira_env, monkeypatch):
    env = jira_env
    jira = env.jira_module
    models = env.models
    monkeypatch.delenv("MOCK_JIRA", raising=False)

    org_a = uuid.uuid4()
    org_b = uuid.uuid4()
    user_a = uuid.uuid4()
    user_b = uuid.uuid4()

    connection_a = _create_connection(env, org_a, user_a, cloud_base_url="https://alpha.atlassian.net")
    connection_b = _create_connection(env, org_b, user_b, cloud_base_url="https://beta.atlassian.net")
    _create_config(env, org_a, connection_a, ["PROJ"])
    _create_config(env, org_b, connection_b, ["PROJ"])

    payloads = {
        connection_a: [
            {"key": "PROJ-1", "fields": {"project": {"key": "PROJ"}, "summary": "Alpha summary"}},
        ],
        connection_b: [
            {"key": "PROJ-1", "fields": {"project": {"key": "PROJ"}, "summary": "Beta summary"}},
        ],
    }

    def _fake_fetch(self, connection, access_token, jql, mock_mode=False, max_results=100):
        for item in payloads[connection.id]:
            yield item

    monkeypatch.setattr(
        jira.integration_service,
        "_fetch_issues",
        types.MethodType(_fake_fetch, jira.integration_service),
    )

    jira.integration_service.sync_now(org_a)
    jira.integration_service.sync_now(org_b)

    with jira.session_scope() as session:
        issues = (
            session.query(models.JiraIssue)
            .filter(models.JiraIssue.issue_key == "PROJ-1")
            .order_by(models.JiraIssue.connection_id)
            .all()
        )

    assert len(issues) == 2
    summaries = {issue.connection_id: issue.summary for issue in issues}
    assert summaries[connection_a] == "Alpha summary"
    assert summaries[connection_b] == "Beta summary"


def test_fetch_pagination_handles_multiple_pages(jira_env, monkeypatch):
    env = jira_env
    jira = env.jira_module
    models = env.models
    monkeypatch.delenv("MOCK_JIRA", raising=False)

    org_id = uuid.uuid4()
    user_id = uuid.uuid4()
    connection_id = _create_connection(env, org_id, user_id)

    with jira.session_scope() as session:
        connection = session.get(models.JiraConnection, connection_id)

    responses = [
        {
            "issues": [
                {"key": "PROJ-10", "fields": {"project": {"key": "PROJ"}, "summary": "Page1"}},
                {"key": "PROJ-11", "fields": {"project": {"key": "PROJ"}, "summary": "Page1B"}},
            ],
            "total": 3,
        },
        {
            "issues": [
                {"key": "PROJ-12", "fields": {"project": {"key": "PROJ"}, "summary": "Page2"}},
            ],
            "total": 3,
        },
    ]
    calls: List[int] = []

    class _Resp:
        def __init__(self, payload):
            self.payload = payload
            self.status_code = 200
            self.headers = {}

        def json(self):
            return self.payload

        def raise_for_status(self):
            return None

    def _fake_get(url, headers=None, params=None, timeout=None):
        calls.append(params["startAt"])
        payload = responses[len(calls) - 1]
        return _Resp(payload)

    monkeypatch.setattr(jira.requests, "get", _fake_get)

    issues = list(jira.integration_service._fetch_issues(connection, "token", "project=PROJ", mock_mode=False, max_results=2))
    assert len(issues) == 3
    assert calls == [0, 2]


def test_integration_flow_and_search(jira_env, monkeypatch):
    env = jira_env
    jira = env.jira_module
    monkeypatch.setenv("MOCK_JIRA", "true")

    org_id = uuid.uuid4()
    user_id = uuid.uuid4()

    start = jira.integration_service.start_oauth(org_id, user_id)
    assert "auth_url" in start
    state = start["state"]

    callback = jira.integration_service.complete_oauth("dummy-code", state=state)
    assert callback["connected"] is True

    jira.integration_service.update_project_config(org_id, user_id, project_keys=["PROJ", "OPS"])
    jira.integration_service.sync_now(org_id)

    tasks = jira.integration_service.list_tasks(org_id, assignee="Alice Doe", project="PROJ")
    assert tasks and tasks[0]["key"] == "PROJ-1"

    results = jira.integration_service.search(org_id, "integration", project="PROJ")
    assert results and results[0]["key"] == "PROJ-1"

    detail = jira.integration_service.get_issue(org_id, "PROJ-1")
    assert detail["key"] == "PROJ-1"
    assert detail["description"]


def test_sync_handles_large_batch_quickly(jira_env, monkeypatch):
    env = jira_env
    jira = env.jira_module
    models = env.models
    monkeypatch.setenv("MOCK_JIRA", "false")

    org_id = uuid.uuid4()
    user_id = uuid.uuid4()
    connection_id = _create_connection(env, org_id, user_id)
    _create_config(env, org_id, connection_id, ["LOAD"])

    issues = []
    base_time = datetime(2024, 3, 1, tzinfo=timezone.utc)
    for idx in range(5000):
        key = f"LOAD-{idx}"
        issues.append(
            {
                "key": key,
                "fields": {
                    "summary": f"Bulk issue {idx}",
                    "description": "Synthetic data",
                    "status": {"name": "In Progress"},
                    "project": {"key": "LOAD"},
                    "updated": (base_time + timedelta(minutes=idx)).isoformat(),
                },
            }
        )

    def _fake_fetch(connection, access_token, jql, mock_mode=False, max_results=100):
        return iter(issues)

    monkeypatch.setattr(jira.integration_service, "_fetch_issues", _fake_fetch)
    monkeypatch.setattr(jira.integration_service, "_ensure_access_token", lambda session, conn: "token")

    start = time.time()
    result = jira.integration_service.sync_now(org_id)
    duration = time.time() - start

    assert result.fetched == 5000
    assert result.updated == 5000
    assert duration < 5

    with jira.session_scope() as session:
        count = session.query(models.JiraIssue).count()
    assert count == 5000
