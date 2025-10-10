import importlib
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.github_integration.chunking import chunk_source


@pytest.fixture
def github_fixture_env(monkeypatch, tmp_path):
    pytest.importorskip("sqlalchemy")
    fixtures = Path(__file__).resolve().parent / "fixtures" / "mock_github"
    monkeypatch.setenv("MOCK_GITHUB", "true")
    monkeypatch.setenv("TOKEN_ENCRYPTION_SECRET", "test-secret")
    monkeypatch.setenv("GITHUB_FIXTURES_PATH", str(fixtures))
    db_url = f"sqlite:///{tmp_path/'github.db'}"
    monkeypatch.setenv("KNOWLEDGE_DATABASE_URL", db_url)

    import backend.db.base as db_base
    from backend.db import Base

    db_base._engine = None  # type: ignore[attr-defined]
    db_base._SessionLocal = None  # type: ignore[attr-defined]
    engine = db_base.get_engine(db_url)
    Base.metadata.create_all(engine)

    service_module = importlib.reload(importlib.import_module("backend.github_integration.service"))
    yield service_module


def test_chunking_preserves_line_spans():
    source = "\n".join(f"line {i}" for i in range(1, 301))
    chunks = chunk_source("demo.py", source, chunk_size=120, overlap=20)
    assert chunks[0].start_line == 1
    assert chunks[0].end_line == 120
    assert chunks[1].start_line == 101
    assert chunks[-1].end_line == 300


def test_index_and_search_flow(github_fixture_env):
    service_module = github_fixture_env
    assert service_module.github_integration_service is not None

    approvals_stub = SimpleNamespace(
        approvals=SimpleNamespace(
            list=lambda: [], get=lambda *a, **k: None, resolve=lambda *a, **k: {}
        )
    )
    approval_worker_stub = SimpleNamespace(
        on_approval_resolved=lambda *a, **k: {},
        start_worker_thread=lambda: None,
        set_dry_run_mode=lambda *a, **k: None,
        get_integration_status=lambda: {},
    )
    watcher_stub = SimpleNamespace(handle_github_webhook=lambda *a, **k: None)

    sys.modules["backend.approvals"] = approvals_stub
    sys.modules["backend.approval_worker"] = approval_worker_stub
    sys.modules["backend.watchers.ci_watcher"] = watcher_stub

    server_module = importlib.reload(importlib.import_module("backend.server"))
    client = server_module.app.test_client()

    start_resp = client.post("/api/integrations/github/oauth/start")
    assert start_resp.status_code == 200
    assert "authorization_url" in start_resp.get_json()

    callback_resp = client.get("/api/integrations/github/oauth/callback", query_string={"code": "demo"})
    assert callback_resp.status_code == 200
    assert callback_resp.get_json()["connected"] is True

    status_resp = client.get("/api/integrations/github/status")
    assert status_resp.status_code == 200
    assert status_resp.get_json()["connected"] is True

    repos_resp = client.get("/api/github/repos")
    assert repos_resp.status_code == 200
    repos_payload = repos_resp.get_json()["repos"]
    assert len(repos_payload) == 1
    repo_full_name = repos_payload[0]["full_name"]

    index_resp = client.post(
        "/api/github/index", json={"repo_full_name": repo_full_name, "mode": "git"}
    )
    assert index_resp.status_code == 202
    index_id = index_resp.get_json()["index_id"]

    for _ in range(50):
        poll = client.get(f"/api/github/index/{index_id}/status")
        assert poll.status_code == 200
        payload = poll.get_json()
        if payload["state"] in {"completed", "failed"}:
            break
        time.sleep(0.1)
    else:
        pytest.fail("index job did not finish")

    assert payload["state"] == "completed"
    assert payload["progress"] == pytest.approx(1.0)

    from backend.db import session_scope
    from backend.db.models import GHFile, GHIssuePR, GHRepo

    with session_scope() as session:
        assert session.query(GHRepo).count() == 1
        file_count = session.query(GHFile).count()
        issue_count = session.query(GHIssuePR).count()

    assert file_count > 0
    assert issue_count == 2

    code_search = client.get(
        "/api/github/search/code",
        query_string={"q": "fibonacci", "repo": repo_full_name, "top_k": 5},
    )
    assert code_search.status_code == 200
    code_results = code_search.get_json()["results"]
    assert code_results
    assert any("fibonacci" in result["snippet"].lower() for result in code_results)
    assert code_results[0]["permalink"].startswith("https://github.com/")

    issues_search = client.get(
        "/api/github/search/issues",
        query_string={"q": "fibonacci", "repo": repo_full_name, "top_k": 5},
    )
    assert issues_search.status_code == 200
    issues_results = issues_search.get_json()["results"]
    assert len(issues_results) >= 1
    assert issues_results[0]["url"].startswith("https://github.com/")

    context_resp = client.get(f"/api/github/repos/{repo_full_name}/context")
    assert context_resp.status_code == 200
    context_payload = context_resp.get_json()
    assert context_payload["languages"]
    assert context_payload["top_paths"]
    assert context_payload["last_index_at"]

    # Re-index the same repository to ensure metadata is refreshed rather than duplicated.
    second_index = client.post(
        "/api/github/index", json={"repo_full_name": repo_full_name, "mode": "api"}
    )
    second_id = second_index.get_json()["index_id"]
    for _ in range(50):
        poll = client.get(f"/api/github/index/{second_id}/status")
        state = poll.get_json()["state"]
        if state in {"completed", "failed"}:
            break
        time.sleep(0.1)
    assert state == "completed"

    with session_scope() as session:
        assert session.query(GHFile).count() == file_count
        assert session.query(GHIssuePR).count() == issue_count
