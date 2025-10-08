"""Utilities for routing meeting events into the intelligence stack.

The browser extension and native capture clients post structured ``meeting
events`` to the realtime service.  Historically the Flask endpoint simply
acknowledged these payloads which meant that caption intelligence, question
detection, and meeting summaries only worked when tests invoked the lower
level helpers directly.  This module provides a lightweight in-memory router
that wires those pieces together so the `/api/meeting-events` endpoint does
useful work even in the single-process dev environment used by the tests.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
from typing import Any, Deque, Dict, List, Optional

from app.meeting_intelligence import meeting_intelligence
from backend.realtime import RealtimePipeline

log = logging.getLogger(__name__)


@dataclass
class MeetingState:
    """Runtime state for a meeting tracked via the router."""

    meeting_id: str
    session_id: Optional[str] = None
    captions: Deque[Dict[str, Any]] = field(default_factory=lambda: deque(maxlen=200))
    questions: List[Dict[str, Any]] = field(default_factory=list)
    flags: Dict[str, Any] = field(default_factory=dict)
    last_activity: datetime = field(default_factory=datetime.utcnow)


class MeetingEventRouter:
    """Process meeting events coming from browser/desktop capture clients."""

    def __init__(self, pipeline: Optional[RealtimePipeline] = None):
        self.pipeline = pipeline or RealtimePipeline()
        self._meetings: Dict[str, MeetingState] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def handle_event(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and route an incoming meeting event."""

        action = (payload or {}).get("action")
        data = (payload or {}).get("data") or {}
        if not action:
            raise ValueError("Missing 'action' in meeting event payload")

        meeting_id = data.get("meetingId") or data.get("meeting_id")
        if not meeting_id:
            raise ValueError("Missing meeting identifier in event data")

        handler = getattr(self, f"_handle_{action}", None)
        state = self._ensure_state(meeting_id)
        state.last_activity = datetime.utcnow()

        if handler is None:
            log.debug("No handler for meeting event action %s", action)
            return {
                "action": action,
                "meeting_id": meeting_id,
                "status": "ignored",
            }

        result = handler(state, data) or {}
        result.setdefault("action", action)
        result.setdefault("meeting_id", meeting_id)
        return result

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------
    def _handle_meeting_started(self, state: MeetingState, data: Dict[str, Any]) -> Dict[str, Any]:
        participants_raw = data.get("participants") or []
        participants: List[str] = []
        for entry in participants_raw:
            if isinstance(entry, str):
                participants.append(entry)
            elif isinstance(entry, dict):
                for key in ("id", "email", "name"):
                    value = entry.get(key)
                    if value:
                        participants.append(str(value))
                        break

        meeting_intelligence.start_meeting(state.meeting_id, participants)
        state.session_id = data.get("sessionId") or data.get("session_id")
        state.flags.update({k: v for k, v in data.items() if k not in {"meetingId", "meeting_id", "participants", "sessionId", "session_id"}})

        return {
            "status": "started",
            "session_id": state.session_id,
            "participants": participants,
        }

    def _handle_caption_chunk(self, state: MeetingState, data: Dict[str, Any]) -> Dict[str, Any]:
        text = (data.get("text") or "").strip()
        if not text:
            return {"status": "skipped", "reason": "empty_text"}

        speaker = (data.get("speaker") or "unknown").strip() or "unknown"
        timestamp_raw = data.get("timestamp")
        timestamp_dt = self._parse_timestamp(timestamp_raw)

        analysis = meeting_intelligence.process_caption(
            state.meeting_id,
            text=text,
            speaker_id=speaker,
            timestamp=timestamp_dt,
        )

        caption_entry = {
            "text": text,
            "speaker": speaker,
            "timestamp": timestamp_dt.isoformat() if timestamp_dt else None,
        }
        state.captions.append(caption_entry)

        ts_ms = self._timestamp_ms(timestamp_dt, timestamp_raw)
        detector_speaker = self._normalise_speaker_for_detector(speaker)
        job = self.pipeline.on_caption_chunk(state.meeting_id, detector_speaker, text, ts_ms)

        question_payload: Optional[Dict[str, Any]] = None
        if job:
            question_payload = {
                "question": job.question,
                "timestamp": job.timestamp,
            }
            state.questions.append(question_payload)

        return {
            "status": "processed",
            "analysis": analysis,
            "question_detected": question_payload is not None,
            "question": question_payload,
            "captions_buffered": len(state.captions),
        }

    def _handle_screen_shared(self, state: MeetingState, data: Dict[str, Any]) -> Dict[str, Any]:
        active = bool(data.get("active", True))
        state.flags["screen_shared"] = active
        return {"status": "updated", "screen_shared": active}

    def _handle_meeting_ended(self, state: MeetingState, data: Dict[str, Any]) -> Dict[str, Any]:
        summary = meeting_intelligence.get_meeting_summary(state.meeting_id)
        pending_questions = list(state.questions)
        self._meetings.pop(state.meeting_id, None)
        return {
            "status": "ended",
            "summary": summary,
            "pending_questions": pending_questions,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _ensure_state(self, meeting_id: str) -> MeetingState:
        if meeting_id not in self._meetings:
            self._meetings[meeting_id] = MeetingState(meeting_id=meeting_id)
        return self._meetings[meeting_id]

    @staticmethod
    def _parse_timestamp(raw: Any) -> Optional[datetime]:
        if isinstance(raw, datetime):
            return raw
        if isinstance(raw, (int, float)):
            # Treat large values as milliseconds.
            if raw > 10**12:
                raw = raw / 1000.0
            return datetime.fromtimestamp(raw, tz=timezone.utc).replace(tzinfo=None)
        if isinstance(raw, str):
            try:
                return datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone(timezone.utc).replace(tzinfo=None)
            except ValueError:
                log.debug("Failed to parse timestamp %s", raw)
        return None

    @staticmethod
    def _timestamp_ms(timestamp: Optional[datetime], raw: Any) -> int:
        if timestamp:
            return int(timestamp.replace(tzinfo=timezone.utc).timestamp() * 1000)
        if isinstance(raw, (int, float)):
            if raw > 10**12:
                return int(raw)
            if raw > 10**9:
                return int(raw * 1000)
        return int(datetime.utcnow().timestamp() * 1000)

    @staticmethod
    def _normalise_speaker_for_detector(speaker: str) -> str:
        lower = speaker.lower()
        if lower in {"interviewer", "recruiter", "panel", "other"}:
            return "other"
        if lower in {"candidate", "self", "me"}:
            return "self"
        return lower or "unknown"


__all__ = ["MeetingEventRouter", "MeetingState"]
