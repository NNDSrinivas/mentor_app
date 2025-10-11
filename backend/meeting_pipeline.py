from __future__ import annotations

import logging
import os
import re
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import List, Sequence

import dramatiq
from dramatiq.brokers.stub import StubBroker
from pydantic import BaseModel, Field, ValidationError

from backend.db.base import session_scope
from backend.db import models
from backend.meeting_repository import (
    get_meeting_by_session,
    list_transcript_segments,
    mark_meeting_completed,
    replace_action_items,
    upsert_summary,
)
from backend.vector_store import MeetingVectorStore

try:  # pragma: no cover - optional dependency
    from backend.memory_service import MemoryService
except Exception:  # pragma: no cover - optional dependency
    MemoryService = None  # type: ignore

log = logging.getLogger(__name__)


class SummaryDocument(BaseModel):
    bullets: List[str] = Field(default_factory=list)
    decisions: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)


class ActionItemDocument(BaseModel):
    title: str
    assignee: str | None = None
    due_hint: str | None = None
    confidence: float = 0.5
    source_segment: uuid.UUID | None = None


@dataclass
class MeetingProcessingResult:
    meeting_id: uuid.UUID
    session_id: uuid.UUID
    summary: SummaryDocument
    actions: List[ActionItemDocument]


def _chunk_text(text: str, max_chars: int = 800) -> List[str]:
    chunks: List[str] = []
    buffer = []
    current_len = 0
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        if current_len + len(sentence) > max_chars and buffer:
            chunks.append(" ".join(buffer))
            buffer = [sentence]
            current_len = len(sentence)
        else:
            buffer.append(sentence)
            current_len += len(sentence)
    if buffer:
        chunks.append(" ".join(buffer))
    return [chunk.strip() for chunk in chunks if chunk.strip()]


def _summarize_transcript(normalized: str) -> SummaryDocument:
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", normalized) if s.strip()]
    bullets = sentences[:10]
    decisions = [s for s in sentences if "decided" in s.lower() or "will" in s.lower()][:5]
    risks = [s for s in sentences if "risk" in s.lower() or "concern" in s.lower()][:5]
    data = {"bullets": bullets, "decisions": decisions, "risks": risks}
    try:
        return SummaryDocument.model_validate(data)
    except ValidationError as exc:  # pragma: no cover - should not happen
        log.error("Summary validation failed: %s", exc)
        raise


def _extract_actions(segments: Sequence[models.TranscriptSegment]) -> List[ActionItemDocument]:
    action_keywords = ["action", "todo", "follow up", "next step", "will", "assign", "ship"]
    actions: List[ActionItemDocument] = []
    for segment in segments:
        lower = segment.text.lower()
        if any(keyword in lower for keyword in action_keywords):
            assignee = segment.speaker or ""
            due_hint = None
            if "tomorrow" in lower:
                due_hint = "tomorrow"
            elif "next week" in lower:
                due_hint = "next week"
            actions.append(
                ActionItemDocument(
                    title=segment.text.strip(),
                    assignee=assignee or None,
                    due_hint=due_hint,
                    confidence=0.7,
                    source_segment=segment.id,
                )
            )
    return actions


def _normalise_segments(segments: Sequence[models.TranscriptSegment]) -> str:
    lines = [f"{seg.speaker or 'Unknown'}: {seg.text.strip()}" for seg in segments]
    return "\n".join(lines)


_vector_store = MeetingVectorStore()
_memory_service = MemoryService() if MemoryService else None


def _configure_broker():
    broker_type = os.getenv("DRAMATIQ_BROKER", "stub").lower()
    if broker_type == "redis":  # pragma: no cover - optional configuration
        from dramatiq.brokers.redis import RedisBroker

        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        broker = RedisBroker(url=redis_url)
    else:
        broker = StubBroker()
    dramatiq.set_broker(broker)
    return broker


BROKER = _configure_broker()


def process_meeting(session_id: str) -> MeetingProcessingResult:
    session_uuid = uuid.UUID(str(session_id))
    with session_scope() as session:
        meeting = get_meeting_by_session(session, session_uuid)
        if not meeting:
            raise ValueError(f"No meeting found for session {session_id}")
        segments = list_transcript_segments(session, meeting.id)
        if not segments:
            raise ValueError("No transcript segments available for processing")

        normalized = _normalise_segments(segments)
        chunks = _chunk_text(normalized)
        _vector_store.index_chunks(str(meeting.id), chunks)

        summary = _summarize_transcript(normalized)
        actions = _extract_actions(segments)

        upsert_summary(
            session,
            meeting_id=meeting.id,
            bullets=summary.bullets,
            decisions=summary.decisions,
            risks=summary.risks,
        )

        replace_action_items(
            session,
            meeting_id=meeting.id,
            items=[
                models.ActionItem(
                    id=uuid.uuid4(),
                    meeting_id=meeting.id,
                    title=action.title,
                    assignee=action.assignee,
                    due_hint=action.due_hint,
                    confidence=action.confidence,
                    source_segment=action.source_segment,
                )
                for action in actions
            ],
        )

        mark_meeting_completed(session, meeting.id)

    if _memory_service:
        try:  # pragma: no cover - optional integration
            _memory_service.add_meeting_entry(
                str(meeting.id),
                "\n".join(summary.bullets),
                {"decisions": summary.decisions, "risks": summary.risks},
            )
        except Exception as exc:  # pragma: no cover - optional integration
            log.warning("Failed to push summary to memory service: %s", exc)

    log.info("Meeting %s processed with %d actions", meeting.id, len(actions))
    result = MeetingProcessingResult(
        meeting_id=meeting.id,
        session_id=session_uuid,
        summary=summary,
        actions=actions,
    )
    emit_meeting_ready(result)
    return result


@dramatiq.actor
def process_meeting_actor(session_id: str) -> None:
    result = process_meeting(session_id)
    log.info("Meeting %s ready", result.meeting_id)


def enqueue_meeting_processing(session_id: str) -> None:
    mode = os.getenv("MEETING_PIPELINE_MODE", "async")
    if mode == "sync":
        process_meeting(session_id)
        return
    process_meeting_actor.send(session_id)


def emit_meeting_ready(result: MeetingProcessingResult) -> None:
    payload = {
        "type": "meeting_ready",
        "meeting_id": str(result.meeting_id),
        "session_id": str(result.session_id),
        "summary_bullets": result.summary.bullets,
        "actions": [action.title for action in result.actions],
    }
    log.info("meeting_ready event emitted: %s", payload)


__all__ = [
    "SummaryDocument",
    "ActionItemDocument",
    "process_meeting",
    "process_meeting_actor",
    "enqueue_meeting_processing",
    "emit_meeting_ready",
]
