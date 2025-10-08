from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Iterable, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.db import models

log = logging.getLogger(__name__)


def ensure_meeting(
    session: Session,
    *,
    session_id: uuid.UUID,
    title: Optional[str] = None,
    provider: Optional[str] = None,
    started_at: Optional[datetime] = None,
    participants: Optional[Iterable[str]] = None,
    org_id: Optional[uuid.UUID] = None,
) -> models.Meeting:
    meeting = session.execute(
        select(models.Meeting).where(models.Meeting.session_id == session_id)
    ).scalar_one_or_none()
    if meeting:
        if title and not meeting.title:
            meeting.title = title
        if provider and not meeting.provider:
            meeting.provider = provider
        if started_at and not meeting.started_at:
            meeting.started_at = started_at
        if participants:
            meeting.participants = list(participants)
        if org_id and not meeting.org_id:
            meeting.org_id = org_id
        return meeting

    meeting = models.Meeting(
        id=uuid.uuid4(),
        session_id=session_id,
        title=title,
        provider=provider,
        started_at=started_at or datetime.utcnow(),
        participants=list(participants or []),
        org_id=org_id,
    )
    session.add(meeting)
    log.debug("Created meeting %s for session %s", meeting.id, session_id)
    return meeting


def add_transcript_segment(
    session: Session,
    *,
    session_id: uuid.UUID,
    text: str,
    speaker: Optional[str],
    ts_start_ms: int,
    ts_end_ms: Optional[int] = None,
) -> models.TranscriptSegment:
    meeting = ensure_meeting(session, session_id=session_id)
    segment = models.TranscriptSegment(
        id=uuid.uuid4(),
        meeting_id=meeting.id,
        text=text,
        speaker=speaker,
        ts_start_ms=ts_start_ms,
        ts_end_ms=ts_end_ms or ts_start_ms,
    )
    session.add(segment)
    log.debug("Stored transcript segment %s for meeting %s", segment.id, meeting.id)
    return segment


def get_meeting_by_session(session: Session, session_id: uuid.UUID) -> Optional[models.Meeting]:
    return (
        session.execute(select(models.Meeting).where(models.Meeting.session_id == session_id))
        .scalar_one_or_none()
    )


def upsert_summary(
    session: Session,
    *,
    meeting_id: uuid.UUID,
    bullets: List[str],
    decisions: List[str],
    risks: List[str],
) -> models.MeetingSummary:
    summary = session.get(models.MeetingSummary, meeting_id)
    if summary is None:
        summary = models.MeetingSummary(
            meeting_id=meeting_id,
            bullets=bullets,
            decisions=decisions,
            risks=risks,
            created_at=datetime.utcnow(),
        )
        session.add(summary)
    else:
        summary.bullets = bullets
        summary.decisions = decisions
        summary.risks = risks
        summary.created_at = datetime.utcnow()
    return summary


def replace_action_items(
    session: Session,
    *,
    meeting_id: uuid.UUID,
    items: List[models.ActionItem],
) -> None:
    session.query(models.ActionItem).filter(models.ActionItem.meeting_id == meeting_id).delete()
    for item in items:
        item.meeting_id = meeting_id
        session.add(item)


def list_action_items(session: Session, meeting_id: uuid.UUID) -> List[models.ActionItem]:
    return (
        session.execute(
            select(models.ActionItem).where(models.ActionItem.meeting_id == meeting_id)
        )
        .scalars()
        .all()
    )


def list_transcript_segments(session: Session, meeting_id: uuid.UUID) -> List[models.TranscriptSegment]:
    return (
        session.execute(
            select(models.TranscriptSegment)
            .where(models.TranscriptSegment.meeting_id == meeting_id)
            .order_by(models.TranscriptSegment.ts_start_ms)
        )
        .scalars()
        .all()
    )


def mark_meeting_completed(session: Session, meeting_id: uuid.UUID) -> None:
    meeting = session.get(models.Meeting, meeting_id)
    if meeting:
        meeting.ended_at = meeting.ended_at or datetime.utcnow()


def search_meetings(
    session: Session,
    *,
    since: Optional[datetime] = None,
    people: Optional[List[str]] = None,
) -> List[models.Meeting]:
    query = select(models.Meeting)
    if since:
        query = query.where(models.Meeting.started_at >= since)

    meetings = session.execute(query.order_by(models.Meeting.started_at.desc())).scalars().all()
    if people:
        normalized = {p.strip().lower() for p in people if p}
        meetings = [
            m
            for m in meetings
            if m.participants
            and any(str(participant).lower() in normalized for participant in m.participants)
        ]
    return meetings


__all__ = [
    "ensure_meeting",
    "add_transcript_segment",
    "get_meeting_by_session",
    "upsert_summary",
    "replace_action_items",
    "list_action_items",
    "list_transcript_segments",
    "mark_meeting_completed",
    "search_meetings",
]
