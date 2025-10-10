from __future__ import annotations

import json
import logging
import queue
import re
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Deque, Dict, Iterable, List, Optional, Protocol

from sqlalchemy.orm import Session

from backend.meeting_repository import (
    list_recent_segments,
    record_session_answer,
)

log = logging.getLogger(__name__)


class CitationValidationError(ValueError):
    """Raised when model output fails structured validation."""


class LLMClient(Protocol):
    def __call__(self, *, prompt: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an LLM call returning parsed JSON."""


class SearchClient(Protocol):
    def search(self, query: str, *, top_k: int) -> List[Dict[str, Any]]:
        ...


@dataclass
class AnswerJob:
    session_id: uuid.UUID
    segment_id: uuid.UUID
    text: str
    ts_ms: int
    enqueued_at: float = field(default_factory=time.perf_counter)


@dataclass
class RetrievalAdapters:
    jira_search: Callable[[str, int], List[Dict[str, Any]]]
    code_search: Callable[[str, int], List[Dict[str, Any]]]
    issue_search: Callable[[str, int], List[Dict[str, Any]]]


def select_context_window(
    segments: Iterable[Dict[str, Any]],
    *,
    window_seconds: int,
) -> List[Dict[str, Any]]:
    """Return segments whose ``ts_end_ms`` falls within ``window_seconds`` of the most recent."""

    seg_list = list(segments)
    if not seg_list:
        return []

    seg_list.sort(key=lambda seg: seg.get("ts_end_ms", seg.get("ts_start_ms", 0)))
    latest = seg_list[-1].get("ts_end_ms", seg_list[-1].get("ts_start_ms", 0))
    threshold = max(0, latest - window_seconds * 1000)
    window: List[Dict[str, Any]] = [
        seg
        for seg in seg_list
        if seg.get("ts_end_ms", seg.get("ts_start_ms", 0)) >= threshold
    ]
    return window


def extract_noun_phrases(text: str) -> List[str]:
    """Extract a set of lightweight noun phrases/keywords from ``text``.

    The implementation avoids heavyweight NLP dependencies by combining
    heuristic rules:
    * preserve all-caps tokens and identifiers with digits (e.g. ``PROJ-15``)
    * capture sequences of capitalised words ("JWT expiry")
    * include final noun-like token
    """

    if not text:
        return []

    tokens = re.findall(r"[A-Za-z0-9]+(?:[-_][A-Za-z0-9]+)*", text)
    keywords: List[str] = []
    buffer: List[str] = []
    for token in tokens:
        if token.isupper() or re.search(r"\d", token):
            keywords.append(token)
            buffer = []
            continue

        if token[0].isupper():
            buffer.append(token)
        else:
            if buffer:
                keywords.append(" ".join(buffer))
                buffer = []

    if buffer:
        keywords.append(" ".join(buffer))

    # Always include final token for recall when others fail
    if tokens:
        final = tokens[-1]
        if final.lower() not in {k.lower() for k in keywords}:
            keywords.append(final)

    # Deduplicate preserving order
    seen = set()
    deduped: List[str] = []
    for keyword in keywords:
        key = keyword.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(keyword)
    return deduped


def validate_citations(answer: str, citations: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Ensure ``citations`` is non-empty when ``answer`` contains factual claims."""

    citation_list = list(citations or [])
    if not answer.strip():
        raise CitationValidationError("answer_text_empty")

    if not citation_list:
        raise CitationValidationError("missing_citations")

    for citation in citation_list:
        if not isinstance(citation, dict):
            raise CitationValidationError("invalid_citation_type")
        if "source" not in citation or "uri" not in citation:
            raise CitationValidationError("citation_missing_fields")
    return citation_list


class AnswerStreamBroker:
    """Manage per-session fan-out queues for SSE streams."""

    def __init__(self) -> None:
        self._queues: Dict[uuid.UUID, List[queue.Queue]] = {}
        self._lock = threading.Lock()

    def register(self, session_id: uuid.UUID) -> queue.Queue:
        q: queue.Queue = queue.Queue()
        with self._lock:
            self._queues.setdefault(session_id, []).append(q)
        return q

    def unregister(self, session_id: uuid.UUID, q: queue.Queue) -> None:
        with self._lock:
            queues = self._queues.get(session_id)
            if not queues:
                return
            try:
                queues.remove(q)
            except ValueError:
                pass
            if not queues:
                self._queues.pop(session_id, None)

    def publish(self, session_id: uuid.UUID, event: Dict[str, Any]) -> None:
        with self._lock:
            queues = list(self._queues.get(session_id, []))

        for q in queues:
            try:
                q.put_nowait(event)
            except queue.Full:  # pragma: no cover - defensive
                log.warning("answer stream queue full for session %s", session_id)


class SegmentCache:
    """Lightweight in-memory cache for recent segments keyed by session."""

    def __init__(self, maxlen: int = 256, ttl_seconds: int = 30) -> None:
        self._store: Dict[uuid.UUID, Deque[Dict[str, Any]]] = {}
        self._timestamps: Dict[uuid.UUID, float] = {}
        self.maxlen = maxlen
        self.ttl_seconds = ttl_seconds

    def get(self, session_id: uuid.UUID) -> Optional[List[Dict[str, Any]]]:
        cached = self._store.get(session_id)
        ts = self._timestamps.get(session_id)
        if cached is None or ts is None:
            return None
        if time.time() - ts > self.ttl_seconds:
            return None
        return list(cached)

    def set(self, session_id: uuid.UUID, segments: Iterable[Dict[str, Any]]) -> None:
        dq: Deque[Dict[str, Any]] = deque(maxlen=self.maxlen)
        for segment in segments:
            dq.append(segment)
        self._store[session_id] = dq
        self._timestamps[session_id] = time.time()


class AnswerGenerationService:
    def __init__(
        self,
        *,
        adapters: RetrievalAdapters,
        llm_client: LLMClient,
        stream_broker: AnswerStreamBroker,
        segment_cache: Optional[SegmentCache] = None,
    ) -> None:
        self._adapters = adapters
        self._llm_client = llm_client
        self._stream = stream_broker
        self._segment_cache = segment_cache or SegmentCache()

    # --- helpers -----------------------------------------------------
    def _load_segments(
        self,
        session: Session,
        session_id: uuid.UUID,
        window_seconds: int,
    ) -> List[Dict[str, Any]]:
        cached = self._segment_cache.get(session_id)
        if cached is not None:
            return select_context_window(cached, window_seconds=window_seconds)

        segments = list_recent_segments(
            session,
            session_id=session_id,
            window_seconds=window_seconds,
        )
        payload = [
            {
                "id": str(segment.id),
                "speaker": segment.speaker,
                "text": segment.text,
                "ts_start_ms": segment.ts_start_ms,
                "ts_end_ms": segment.ts_end_ms,
            }
            for segment in segments
        ]
        self._segment_cache.set(session_id, payload)
        return payload

    def _retrieve_context(
        self,
        keywords: Iterable[str],
        *,
        topk_jira: int,
        topk_code: int,
        topk_prs: int,
    ) -> Dict[str, Any]:
        joined = " ".join(keyword for keyword in keywords if keyword)
        if not joined:
            joined = "recent meeting questions"

        jira_results = self._safe_search(self._adapters.jira_search, joined, topk_jira)
        code_results = self._safe_search(self._adapters.code_search, joined, topk_code)
        issue_results = self._safe_search(self._adapters.issue_search, joined, topk_prs)

        return {
            "jira": jira_results,
            "code": code_results,
            "issues": issue_results,
        }

    @staticmethod
    def _safe_search(
        func: Callable[[str, int], List[Dict[str, Any]]],
        query: str,
        top_k: int,
    ) -> List[Dict[str, Any]]:
        if top_k <= 0:
            return []
        try:
            return func(query, top_k)
        except Exception as exc:  # pragma: no cover - defensive log
            log.warning("context retrieval failed: %s", exc)
            return []

    def _call_llm(self, prompt: str) -> Dict[str, Any]:
        schema = {
            "type": "object",
            "properties": {
                "answer": {"type": "string"},
                "citations": {"type": "array", "items": {"type": "object"}},
                "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
            },
            "required": ["answer", "citations", "confidence"],
        }
        response = self._llm_client(prompt=prompt, schema=schema)
        if not isinstance(response, dict):
            raise CitationValidationError("invalid_llm_payload")
        return response

    # --- public API --------------------------------------------------
    def process_job(
        self,
        session: Session,
        job: AnswerJob,
        *,
        window_seconds: int = 180,
        topk_jira: int = 5,
        topk_code: int = 5,
        topk_prs: int = 5,
    ) -> Dict[str, Any]:
        segments = self._load_segments(session, job.session_id, window_seconds)
        latest_text = job.text or (segments[-1]["text"] if segments else "")
        keywords = extract_noun_phrases(latest_text)
        context_bundle = self._retrieve_context(
            keywords,
            topk_jira=topk_jira,
            topk_code=topk_code,
            topk_prs=topk_prs,
        )

        prompt_payload = {
            "question": latest_text,
            "transcript": segments,
            "context": context_bundle,
        }
        prompt = json.dumps(prompt_payload, ensure_ascii=False)

        try:
            llm_output = self._call_llm(prompt)
            citations = validate_citations(llm_output.get("answer", ""), llm_output.get("citations", []))
            confidence = float(llm_output.get("confidence", 0.0))
            answer_text = llm_output.get("answer", "").strip()
        except Exception as exc:
            log.warning("LLM output invalid, falling back: %s", exc)
            citations = [
                {
                    "source": "system",
                    "uri": "context://pending",
                    "note": "context loading",
                }
            ]
            confidence = 0.1
            answer_text = "I'm still loading the latest context. I'll provide details shortly."

        latency_ms = int((time.perf_counter() - job.enqueued_at) * 1000)
        token_count = len(answer_text.split())

        record = record_session_answer(
            session,
            session_id=job.session_id,
            answer=answer_text,
            citations=citations,
            confidence=confidence,
            token_count=token_count,
            latency_ms=latency_ms,
        )
        session.commit()

        payload = {
            "id": str(record.id),
            "session_id": str(job.session_id),
            "answer": answer_text,
            "citations": citations,
            "confidence": confidence,
            "token_count": token_count,
            "latency_ms": latency_ms,
            "created_at": record.created_at.isoformat() if record.created_at else datetime.utcnow().isoformat(),
        }

        self._stream.publish(job.session_id, {"event": "answer", "data": payload})
        return payload


class AnswerJobQueue:
    """Simple background worker consuming ``AnswerJob``s."""

    def __init__(self, service_factory: Callable[[], AnswerGenerationService], session_factory: Callable[[], Session]):
        self._queue: "queue.Queue[AnswerJob]" = queue.Queue()
        self._service_factory = service_factory
        self._session_factory = session_factory
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def enqueue(self, job: AnswerJob) -> None:
        self._queue.put(job)

    def _run(self) -> None:
        while True:
            job = self._queue.get()
            if job is None:  # pragma: no cover - graceful shutdown hook
                break
            service = self._service_factory()
            session = self._session_factory()
            try:
                service.process_job(session, job)
            except Exception:  # pragma: no cover - defensive logging
                log.exception("failed to process answer job")
                session.rollback()
            finally:
                session.close()


__all__ = [
    "AnswerJob",
    "AnswerJobQueue",
    "AnswerGenerationService",
    "AnswerStreamBroker",
    "CitationValidationError",
    "extract_noun_phrases",
    "select_context_window",
    "validate_citations",
]
