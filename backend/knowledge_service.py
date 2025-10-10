from __future__ import annotations

import json
import logging
import os
import queue
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.db.base import get_session
from backend.db.utils import ensure_schema
from backend.db import models
from backend.answer_coach import (
    AnswerGenerationService,
    AnswerJob,
    AnswerJobQueue,
    AnswerStreamBroker,
    RetrievalAdapters,
)
from backend.meeting_pipeline import ActionItemDocument, enqueue_meeting_processing
from backend.meeting_repository import (
    ensure_meeting,
    get_meeting_by_session,
    list_action_items,
    list_session_answers,
    add_transcript_segment,
    search_meetings,
)
from backend.vector_store import MeetingVectorStore

log = logging.getLogger(__name__)
app = FastAPI(title="Mentor Knowledge Service", version="1.0")


class SummaryResponse(BaseModel):
    bullets: List[str]
    decisions: List[str]
    risks: List[str]
    created_at: Optional[datetime]
    actions: List[ActionItemDocument]


class ActionsResponse(BaseModel):
    items: List[ActionItemDocument]


class CaptionPayload(BaseModel):
    text: str
    speaker: Optional[str] = None
    ts_start_ms: Optional[int] = None
    ts_end_ms: Optional[int] = None


class AnswerDocument(BaseModel):
    id: uuid.UUID
    answer: str
    citations: List[Dict[str, Any]]
    confidence: float
    token_count: int
    latency_ms: int
    created_at: datetime


class AnswersResponse(BaseModel):
    items: List[AnswerDocument]


class GenerateAnswerRequest(BaseModel):
    session_id: uuid.UUID
    window_seconds: int = Field(180, ge=0, le=900)
    topk_jira: int = Field(5, ge=0, le=20)
    topk_code: int = Field(5, ge=0, le=20)
    topk_prs: int = Field(5, ge=0, le=20)


class GenerateAnswerResponse(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    answer: str
    citations: List[Dict[str, Any]]
    confidence: float
    token_count: int
    latency_ms: int
    created_at: datetime


class MeetingSearchResult(BaseModel):
    meeting_id: uuid.UUID
    session_id: uuid.UUID
    title: Optional[str]
    started_at: Optional[datetime]
    snippet: Optional[str]
    score: Optional[float]


class MeetingSearchResponse(BaseModel):
    results: List[MeetingSearchResult]


def _get_db():
    db = get_session()
    try:
        yield db
    finally:
        db.close()


ensure_schema()
_vector_store = MeetingVectorStore()


def _api_base() -> Optional[str]:
    base = os.getenv("INTERNAL_API_BASE_URL")
    if base and base.endswith("/"):
        base = base[:-1]
    return base


def _default_search(path: str, query: str, top_k: int) -> List[Dict[str, Any]]:
    base = _api_base()
    if not base or top_k <= 0:
        return []
    url = f"{base}{path}"
    try:
        response = requests.get(url, params={"q": query, "top_k": top_k}, timeout=2)
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:  # pragma: no cover - network errors not asserted in tests
        log.warning("context lookup failed for %s: %s", url, exc)
        return []

    results = payload.get("results") or payload.get("issues") or []
    if isinstance(results, dict):
        results = results.get("issues", [])
    if not isinstance(results, list):
        return []
    return results[:top_k]


def _jira_search(query: str, top_k: int) -> List[Dict[str, Any]]:
    return _default_search("/api/jira/search", query, top_k)


def _github_code_search(query: str, top_k: int) -> List[Dict[str, Any]]:
    return _default_search("/api/github/search/code", query, top_k)


def _github_issue_search(query: str, top_k: int) -> List[Dict[str, Any]]:
    return _default_search("/api/github/search/issues", query, top_k)


def _llm_client(*, prompt: str, schema: Dict[str, Any]) -> Dict[str, Any]:
    raise RuntimeError("llm_client_not_configured")


_stream_broker = AnswerStreamBroker()


def _service_factory() -> AnswerGenerationService:
    adapters = RetrievalAdapters(
        jira_search=_jira_search,
        code_search=_github_code_search,
        issue_search=_github_issue_search,
    )
    return AnswerGenerationService(
        adapters=adapters,
        llm_client=_llm_client,
        stream_broker=_stream_broker,
    )


_job_queue = AnswerJobQueue(_service_factory, get_session)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "service": "knowledge", "time": datetime.utcnow().isoformat()}


@app.post("/api/meetings/{session_id}/finalize", status_code=202)
def finalize_meeting(session_id: uuid.UUID, db: Session = Depends(_get_db)) -> JSONResponse:
    meeting = get_meeting_by_session(db, session_id)
    if meeting is None:
        ensure_meeting(
            db,
            session_id=session_id,
            provider="realtime",
            started_at=datetime.utcnow(),
        )
        db.commit()
    enqueue_meeting_processing(str(session_id))
    return JSONResponse({"status": "queued"}, status_code=202)


@app.post("/api/sessions/{session_id}/captions", status_code=202)
def ingest_caption(
    session_id: uuid.UUID,
    payload: CaptionPayload,
    background_tasks: BackgroundTasks,
    db: Session = Depends(_get_db),
) -> JSONResponse:
    text = (payload.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="empty_caption")

    ts_start = payload.ts_start_ms or int(time.time() * 1000)
    ts_end = payload.ts_end_ms or ts_start

    segment = add_transcript_segment(
        db,
        session_id=session_id,
        text=text,
        speaker=payload.speaker,
        ts_start_ms=ts_start,
        ts_end_ms=ts_end,
    )
    db.commit()

    job = AnswerJob(
        session_id=session_id,
        segment_id=segment.id,
        text=text,
        ts_ms=ts_end,
    )
    _job_queue.enqueue(job)

    return JSONResponse({"status": "queued", "segment_id": str(segment.id)}, status_code=202)


@app.get("/api/meetings/{session_id}/summary", response_model=SummaryResponse)
def get_meeting_summary(session_id: uuid.UUID, db: Session = Depends(_get_db)) -> SummaryResponse:
    meeting = get_meeting_by_session(db, session_id)
    if meeting is None:
        raise HTTPException(status_code=404, detail="meeting_not_found")

    summary = db.get(models.MeetingSummary, meeting.id)
    if summary is None:
        raise HTTPException(status_code=404, detail="summary_not_ready")

    actions = list_action_items(db, meeting.id)
    action_docs = [
        ActionItemDocument(
            title=item.title,
            assignee=item.assignee,
            due_hint=item.due_hint,
            confidence=float(item.confidence) if item.confidence is not None else 0.0,
            source_segment=item.source_segment,
        )
        for item in actions
    ]

    return SummaryResponse(
        bullets=summary.bullets or [],
        decisions=summary.decisions or [],
        risks=summary.risks or [],
        created_at=summary.created_at,
        actions=action_docs,
    )


@app.get("/api/meetings/{session_id}/actions", response_model=ActionsResponse)
def get_meeting_actions(session_id: uuid.UUID, db: Session = Depends(_get_db)) -> ActionsResponse:
    meeting = get_meeting_by_session(db, session_id)
    if meeting is None:
        raise HTTPException(status_code=404, detail="meeting_not_found")

    actions = list_action_items(db, meeting.id)
    return ActionsResponse(
        items=[
            ActionItemDocument(
                title=item.title,
                assignee=item.assignee,
                due_hint=item.due_hint,
                confidence=float(item.confidence) if item.confidence is not None else 0.0,
                source_segment=item.source_segment,
            )
            for item in actions
        ]
    )


@app.get("/api/meetings/search", response_model=MeetingSearchResponse)
def search_meetings_endpoint(
    q: str = Query(""),
    since: Optional[datetime] = Query(None),
    people: Optional[str] = Query(None),
    db: Session = Depends(_get_db),
) -> MeetingSearchResponse:
    people_filter = [p.strip() for p in (people.split(",") if people else []) if p.strip()]

    meetings = search_meetings(db, since=since, people=people_filter)
    query_text = q or ""
    vector_results = {
        result.meeting_id: result for result in _vector_store.search(query_text, limit=10)
    }

    results: List[MeetingSearchResult] = []
    for meeting in meetings:
        snippet = None
        score = None
        if vector_results:
            vector = vector_results.get(str(meeting.id))
            if vector:
                snippet = vector.document
                score = vector.score
        results.append(
            MeetingSearchResult(
                meeting_id=meeting.id,
                session_id=meeting.session_id,
                title=meeting.title,
                started_at=meeting.started_at,
                snippet=snippet,
                score=score,
            )
        )
    return MeetingSearchResponse(results=results)


@app.get("/api/sessions/{session_id}/answers", response_model=AnswersResponse)
def list_session_answers_endpoint(
    session_id: uuid.UUID,
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(_get_db),
) -> AnswersResponse:
    records = list_session_answers(db, session_id, limit=limit)
    items = [
        AnswerDocument(
            id=record.id,
            answer=record.answer,
            citations=record.citations or [],
            confidence=float(record.confidence) if record.confidence is not None else 0.0,
            token_count=record.token_count or 0,
            latency_ms=record.latency_ms or 0,
            created_at=record.created_at or datetime.utcnow(),
        )
        for record in records
    ]
    return AnswersResponse(items=items)


@app.get("/api/sessions/{session_id}/stream")
def stream_session_events(session_id: uuid.UUID):
    client_queue: "queue.Queue[Dict[str, Any]]" = _stream_broker.register(session_id)

    def event_stream() -> Any:
        try:
            while True:
                try:
                    message = client_queue.get(timeout=15)
                except queue.Empty:
                    yield "event: ping\ndata: {}\n\n"
                    continue

                event = message.get("event", "message")
                data = message.get("data", {})
                yield f"event: {event}\ndata: {json.dumps(data)}\n\n"
        finally:
            _stream_broker.unregister(session_id, client_queue)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.post("/api/answers/generate", response_model=GenerateAnswerResponse)
def generate_answer_endpoint(
    payload: GenerateAnswerRequest,
    db: Session = Depends(_get_db),
) -> GenerateAnswerResponse:
    service = _service_factory()
    job = AnswerJob(
        session_id=payload.session_id,
        segment_id=uuid.uuid4(),
        text="",
        ts_ms=int(time.time() * 1000),
    )
    result = service.process_job(
        db,
        job,
        window_seconds=payload.window_seconds,
        topk_jira=payload.topk_jira,
        topk_code=payload.topk_code,
        topk_prs=payload.topk_prs,
    )
    return GenerateAnswerResponse(**result)
