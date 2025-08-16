from __future__ import annotations
from typing import Optional
import time

from app.config import Config

class QuestionBoundaryDetector:
    """End-of-question detector using silence and punctuation."""

    def __init__(
        self,
        min_gap_ms: int = Config.QUESTION_SILENCE_MS_MIN,
        max_gap_ms: int = Config.QUESTION_SILENCE_MS_MAX,
        max_len_chars: int = Config.QUESTION_MAX_LEN_CHARS,
    ):
        self.min_gap_ms = min_gap_ms
        self.max_gap_ms = max_gap_ms
        self.max_len_chars = max_len_chars
        self._last_token_time = None
        self._buffer: list[str] = []

    def add_token(self, text: str) -> Optional[str]:
        now = int(time.time() * 1000)
        if self._last_token_time is None:
            self._last_token_time = now
        gap = now - self._last_token_time
        self._last_token_time = now

        self._buffer.append(text)

        # Heuristic: gap within threshold or ending punctuation
        joined = ''.join(self._buffer)
        if len(joined) >= self.max_len_chars:
            out = joined
            self._buffer = []
            return out

        stripped = text.strip()
        if stripped.endswith( ('?', '？', '.', '!', '！', '。') ):
            out = joined.strip()
            self._buffer = []
            return out

        if self.min_gap_ms <= gap <= self.max_gap_ms or gap > self.max_gap_ms:
            out = joined.strip()
            self._buffer = []
            return out

        return None
