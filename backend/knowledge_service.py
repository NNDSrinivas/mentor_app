from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.db.base import get_session
from backend.db.utils import ensure_schema
from backend.db import models
from backend.meeting_pipeline import ActionItemDocument, enqueue_meeting_processing
from backend.meeting_repository import (
    ensure_meeting,
    get_meeting_by_session,
    list_action_items,
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
