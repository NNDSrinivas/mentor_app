from __future__ import annotations

import json
import queue
import uuid

import pytest
from decimal import Decimal

sqlalchemy = pytest.importorskip("sqlalchemy")
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.answer_coach import (
    AnswerGenerationService,
    AnswerJob,
    AnswerStreamBroker,
    RetrievalAdapters,
    estimate_token_count,
    extract_noun_phrases,
    normalize_confidence,
    serialize_confidence,
    select_context_window,
    validate_citations,
)
from backend.db import models
from backend.db.base import Base
from backend.meeting_repository import add_transcript_segment, ensure_meeting


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    return factory()


def test_select_context_window_filters_segments():
    segments = [
        {"text": "a", "ts_start_ms": 0, "ts_end_ms": 1000},
        {"text": "b", "ts_start_ms": 1000, "ts_end_ms": 2000},
        {"text": "c", "ts_start_ms": 2000, "ts_end_ms": 3000},
    ]
    window = select_context_window(segments, window_seconds=2)
    assert [seg["text"] for seg in window] == ["b", "c"]


def test_select_context_window_inclusive_boundary(monkeypatch):
    """Test context window filtering with inclusive boundary configuration."""
    segments = [
        {"text": "a", "ts_start_ms": 0, "ts_end_ms": 1000},
        {"text": "b", "ts_start_ms": 1000, "ts_end_ms": 2000},
        {"text": "c", "ts_start_ms": 2000, "ts_end_ms": 3000},
    ]
    
    # Test strict boundary (default behavior)
    monkeypatch.setenv("CONTEXT_WINDOW_INCLUSIVE", "false")
    window = select_context_window(segments, window_seconds=2)
    assert [seg["text"] for seg in window] == ["b", "c"]
    
    # Test inclusive boundary (backward compatibility)
    monkeypatch.setenv("CONTEXT_WINDOW_INCLUSIVE", "true")
    window = select_context_window(segments, window_seconds=2)
    # With inclusive boundary, segment "a" ending at exactly threshold (1000ms) should be included
    assert [seg["text"] for seg in window] == ["a", "b", "c"]


def test_add_transcript_segment_preserves_zero_timestamp():
    session = _session()
    session_id = uuid.uuid4()
    ensure_meeting(session, session_id=session_id, title="Zero")

    segment = add_transcript_segment(
        session,
        session_id=session_id,
        text="first",
        speaker="agent",
        ts_start_ms=0,
        ts_end_ms=0,
    )

    assert segment.ts_start_ms == 0
    assert segment.ts_end_ms == 0


def test_extract_noun_phrases_captures_identifiers():
    text = "What's the status of PROJ-15 and OAuth token expiry?"
    phrases = extract_noun_phrases(text)
    assert "PROJ-15" in phrases
    assert any("OAuth" in phrase for phrase in phrases)


def test_validate_citations_requires_entries():
    with pytest.raises(Exception):
        validate_citations("Answer", [])


def test_confidence_helpers_round_and_bound():
    assert normalize_confidence(1.4) == Decimal("1.0000")
    assert normalize_confidence(-0.2) == Decimal("0.0000")
    rounded = serialize_confidence(Decimal("0.123456"))
    assert rounded == pytest.approx(0.1235)


def test_estimate_token_count_falls_back(monkeypatch):
    import backend.answer_coach as module

    module._encoding_for_model.cache_clear()
    monkeypatch.setattr(module, "tiktoken", None)
    module._encoding_for_model.cache_clear()

    assert estimate_token_count("one two three", model="irrelevant") == 3


def _service_with_stubs(jira_payload, code_payload, issue_payload):
    adapters = RetrievalAdapters(
        jira_search=lambda query, top_k: jira_payload,
        code_search=lambda query, top_k: code_payload,
        issue_search=lambda query, top_k: issue_payload,
    )

    def _llm_stub(*, prompt: str, schema):
        bundle = json.loads(prompt)
        jira = bundle["context"].get("jira", [])
        code = bundle["context"].get("code", [])
        source = "jira" if jira else "code"
        citation = jira[0] if jira else code[0]
        uri = citation.get("url") or citation.get("html_url") or citation.get("permalink", "http://example.com")
        return {
            "answer": f"Refer to {citation.get('key') or citation.get('path')} for details.",
            "citations": [
                {
                    "source": source,
                    "uri": uri,
                    "note": citation.get("title") or citation.get("name", "context"),
                }
            ],
            "confidence": 0.6,
        }

    broker = AnswerStreamBroker()
    service = AnswerGenerationService(adapters=adapters, llm_client=_llm_stub, stream_broker=broker)
    return service, broker


def _prepare_meeting(session: Session, session_id: uuid.UUID, text: str) -> models.TranscriptSegment:
    ensure_meeting(session, session_id=session_id, title="Demo")
    segment = add_transcript_segment(
        session,
        session_id=session_id,
        text=text,
        speaker="interviewer",
        ts_start_ms=0,
        ts_end_ms=1000,
    )
    session.commit()
    return segment


def test_integration_generates_answer_with_jira_citation():
    session = _session()
    session_id = uuid.uuid4()
    segment = _prepare_meeting(session, session_id, "What is the status of PROJ-15?")

    jira_payload = [{"key": "PROJ-15", "url": "https://jira.local/browse/PROJ-15", "title": "Fix login"}]
    service, broker = _service_with_stubs(jira_payload, [], [])
    listener = broker.register(session_id)

    job = AnswerJob(session_id=session_id, segment_id=segment.id, text=segment.text, ts_ms=segment.ts_end_ms)
    result = service.process_job(session, job)

    assert "PROJ-15" in result["answer"]
    assert result["citations"][0]["source"] == "jira"
    event = listener.get(timeout=0.1)
    assert event["event"] == "answer"
    broker.unregister(session_id, listener)


def test_integration_generates_answer_with_code_citation():
    session = _session()
    session_id = uuid.uuid4()
    segment = _prepare_meeting(session, session_id, "Where is JWT expiry parsed?")

    code_payload = [
        {
            "path": "auth/token.py",
            "permalink": "https://github.com/org/repo/blob/main/auth/token.py#L10-L20",
            "name": "token.py",
        }
    ]
    service, broker = _service_with_stubs([], code_payload, [])
    listener = broker.register(session_id)

    job = AnswerJob(session_id=session_id, segment_id=segment.id, text=segment.text, ts_ms=segment.ts_end_ms)
    result = service.process_job(session, job)

    assert "token.py" in result["answer"]
    assert "github" in result["citations"][0]["uri"] or result["citations"][0]["uri"].startswith("http")
    event = listener.get(timeout=0.1)
    assert event["event"] == "answer"
    broker.unregister(session_id, listener)


def test_generate_direct_answer_streams_and_persists():
    session = _session()
    session_id = uuid.uuid4()
    _prepare_meeting(session, session_id, "What is the status of PROJ-15?")

    jira_payload = [{"key": "PROJ-15", "url": "https://jira.local/browse/PROJ-15", "title": "Fix login"}]
    service, broker = _service_with_stubs(jira_payload, [], [])
    listener = broker.register(session_id)

    result = service.generate_direct_answer(
        session,
        session_id=session_id,
        latest_text="Any update on PROJ-15?",
    )

    assert "PROJ-15" in result["answer"]
    event = listener.get(timeout=0.1)
    assert event["event"] == "answer"
    assert event["data"]["id"] == result["id"]
    broker.unregister(session_id, listener)

    stored = session.get(models.SessionAnswer, uuid.UUID(result["id"]))
    assert stored is not None
    assert stored.answer == result["answer"]
