import importlib
import os
import sys
import uuid
from datetime import datetime

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.db.base import session_scope
from backend.db.utils import ensure_schema
from backend.meeting_pipeline import SummaryDocument
from backend.meeting_repository import (
    add_transcript_segment,
    ensure_meeting,
    list_action_items,
    list_transcript_segments,
    upsert_summary,
)


@pytest.fixture()
def knowledge_env(tmp_path, monkeypatch):
    db_path = tmp_path / "knowledge.db"
    memory_path = tmp_path / "memory"
    monkeypatch.setenv("KNOWLEDGE_DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("MEMORY_DB_PATH", str(memory_path))
    monkeypatch.setenv("MEETING_PIPELINE_MODE", "sync")
    monkeypatch.setenv("DRAMATIQ_BROKER", "stub")
    sys.modules.pop("backend.knowledge_service", None)
    meeting_pipeline = importlib.import_module("backend.meeting_pipeline")
    meeting_pipeline = importlib.reload(meeting_pipeline)
    globals()["SummaryDocument"] = meeting_pipeline.SummaryDocument
    ensure_schema()
    yield


def test_summary_document_validation():
    payload = {
        "bullets": ["First", "Second"],
        "decisions": ["Team decided to ship"],
        "risks": ["Potential risk identified"],
    }
    summary = SummaryDocument.model_validate(payload)
    assert summary.bullets[0] == "First"

    with pytest.raises(Exception):
        SummaryDocument.model_validate({"bullets": "not-a-list"})


def test_database_round_trip(knowledge_env):
    session_id = uuid.uuid4()
    with session_scope() as session:
        meeting = ensure_meeting(
            session,
            session_id=session_id,
            title="Weekly Sync",
            provider="realtime",
            started_at=datetime.utcnow(),
            participants=["Alice", "Bob"],
        )
        seg = add_transcript_segment(
            session,
            session_id=session_id,
            text="Alice will follow up tomorrow on the deployment.",
            speaker="Alice",
            ts_start_ms=0,
        )
        upsert_summary(
            session,
            meeting_id=meeting.id,
            bullets=["Discussed deployment"],
            decisions=["Team will deploy"],
            risks=["Tight timeline"],
        )
        session.flush()

    with session_scope() as session:
        segments = list_transcript_segments(session, meeting.id)
        assert len(segments) == 1
        assert segments[0].id == seg.id
        actions = list_action_items(session, meeting.id)
        assert actions == []


def test_finalize_pipeline_and_search(knowledge_env):
    session_id = uuid.uuid4()
    ensure_schema()

    with session_scope() as session:
        meeting = ensure_meeting(
            session,
            session_id=session_id,
            title="Roadmap Review",
            provider="realtime",
            started_at=datetime.utcnow(),
            participants=["Alex", "Jamie"],
        )
        add_transcript_segment(
            session,
            session_id=session_id,
            text="Alex will follow up tomorrow with the metrics dashboard.",
            speaker="Alex",
            ts_start_ms=1000,
        )
        add_transcript_segment(
            session,
            session_id=session_id,
            text="Jamie flagged a risk around infrastructure capacity.",
            speaker="Jamie",
            ts_start_ms=2000,
        )

    knowledge_service = importlib.import_module("backend.knowledge_service")
    importlib.reload(knowledge_service)
    client = TestClient(knowledge_service.app)

    response = client.post(f"/api/meetings/{session_id}/finalize")
    assert response.status_code == 202

    summary_response = client.get(f"/api/meetings/{session_id}/summary")
    assert summary_response.status_code == 200
    summary_body = summary_response.json()
    assert summary_body["bullets"]
    assert summary_body["actions"]

    actions_response = client.get(f"/api/meetings/{session_id}/actions")
    assert actions_response.status_code == 200
    actions_body = actions_response.json()
    assert len(actions_body["items"]) >= 1

    search_response = client.get("/api/meetings/search", params={"q": "metrics", "people": "Alex"})
    assert search_response.status_code == 200
    results = search_response.json()["results"]
    assert any(uuid.UUID(result["session_id"]) == session_id for result in results)
