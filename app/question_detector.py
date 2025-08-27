from __future__ import annotations

"""Utilities for detecting end‑of‑question boundaries."""

from dataclasses import dataclass
from typing import Optional
import os

try:  # Allow importing without optional dependencies during tests
    from app.config import Config
except Exception:  # pragma: no cover - used only when config deps missing
    class Config:  # type: ignore
        QUESTION_SILENCE_MS_MIN = 800


@dataclass
class AnswerJob:
    meeting_id: str
    question: str
    timestamp: int


class QuestionDetector:
    """Detect question boundaries from caption text.

    A boundary is triggered when any of the following are true *and* the
    speaker is labelled ``other``:
    * silence gap >= ``silence_ms``
    * last character is '?' or '!'
    * classifier score >= ``threshold``
    """

    def __init__(self,
                 silence_ms: int = Config.QUESTION_SILENCE_MS_MIN,
                 threshold: float = float(os.getenv("QUESTION_CLASSIFIER_THRESHOLD", "0.5"))):
        self.silence_ms = silence_ms
        self.threshold = threshold
        self._last_ts: Optional[int] = None
        self._buffer: list[str] = []

    def add_chunk(self, speaker: str, text: str, ts: int, score: float = 0.0) -> Optional[str]:
        if speaker != "other":
            # only interviewer questions end up as jobs
            self._buffer = []
            self._last_ts = ts
            return None

        if text:
            self._buffer.append(text)

        gap = None if self._last_ts is None else ts - self._last_ts
        self._last_ts = ts

        joined = " ".join(self._buffer).strip()
        if not joined:
            return None

        last_char = joined[-1]
        if (gap is not None and gap >= self.silence_ms) or \
           last_char in {"?", "!"} or \
           score >= self.threshold:
            self._buffer = []
            return joined
        return None
