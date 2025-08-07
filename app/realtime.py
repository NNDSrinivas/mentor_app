from __future__ import annotations
import time, threading, queue, logging
from typing import Dict, Any, Optional, List
from .question_detector import QuestionBoundaryDetector
from .prompting import build_answer_prompt
from .rag import retrieve_context_snippets
from .profile_loader import load_profile
from .llm import generate_answer

log = logging.getLogger(__name__)

class MeetingSession:
    """Buffers caption chunks, detects complete questions,
    and publishes answers to an in-memory queue (SSE)."""
    def __init__(self, meeting_id: str, ic_level: str = "IC6"):
        self.meeting_id = meeting_id
        self.ic_level = ic_level
        self.qd = QuestionBoundaryDetector(min_gap_ms=700)
        self.caption_buffer: List[str] = []
        self.events: "queue.Queue[str]" = queue.Queue(maxsize=100)
        self.profile = load_profile()  # user resume/profile
        self._lock = threading.Lock()

    def on_caption_chunk(self, text: str, speaker: Optional[str] = None):
        chunk = text.strip()
        if not chunk:
            return
        with self._lock:
            self.caption_buffer.append(chunk)
        maybe = self.qd.add_token(chunk)
        if maybe:
            self._handle_complete_question(maybe)

    def _handle_complete_question(self, question_text: str):
        try:
            context = retrieve_context_snippets(question_text, top_k=5)
            prompt = build_answer_prompt(question_text, self.profile, self.ic_level, context)
            answer = generate_answer(prompt)
            payload = {"type": "answer", "meetingId": self.meeting_id, "text": answer, "ts": time.time()}
            self._publish(payload)
        except Exception as e:
            log.exception("Failed to generate answer")
            self._publish({"type": "error", "meetingId": self.meeting_id, "error": str(e), "ts": time.time()})

    def _publish(self, obj: Dict[str, Any]):
        try:
            self.events.put_nowait(json_dumps(obj))
        except queue.Full:
            try:
                _ = self.events.get_nowait()
            except Exception:
                pass
            try:
                self.events.put_nowait(json_dumps(obj))
            except Exception:
                pass

def json_dumps(obj: Dict[str, Any]) -> str:
    import json
    return json.dumps(obj, ensure_ascii=False)

_sessions: Dict[str, MeetingSession] = {}
_sessions_lock = threading.Lock()

def get_or_create_session(meeting_id: str, ic_level: str = "IC6") -> MeetingSession:
    with _sessions_lock:
        s = _sessions.get(meeting_id)
        if not s:
            s = MeetingSession(meeting_id, ic_level=ic_level)
            _sessions[meeting_id] = s
        return s

def push_caption(meeting_id: str, text: str, speaker: Optional[str] = None):
    s = get_or_create_session(meeting_id)
    s.on_caption_chunk(text=text, speaker=speaker)

def pop_event_generator(meeting_id: str):
    s = get_or_create_session(meeting_id)
    while True:
        try:
            data = s.events.get()
            yield f"data: {data}\n\n"
        except GeneratorExit:
            break
        except Exception:
            time.sleep(0.1)
