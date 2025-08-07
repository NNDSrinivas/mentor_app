from __future__ import annotations
from typing import Optional
import time

class QuestionBoundaryDetector:
    """Simple end-of-question detector using timestamps/silence.
    In production, combine VAD + punctuation-aware heuristics.
    """
    def __init__(self, min_gap_ms: int = 600, max_len_chars: int = 2000):
        self.min_gap_ms = min_gap_ms
        self.max_len_chars = max_len_chars
        self._last_token_time = None
        self._buffer = []

    def add_token(self, text: str) -> Optional[str]:
        now = int(time.time() * 1000)
        if self._last_token_time is None:
            self._last_token_time = now
        gap = now - self._last_token_time
        self._last_token_time = now

        self._buffer.append(text)

        # Heuristic: gap long enough OR question punctuation at end
        joined = ''.join(self._buffer)
        if len(joined) >= self.max_len_chars:
            out = joined
            self._buffer = []
            return out

        if text.strip().endswith( ('?', '？') ) or gap >= self.min_gap_ms:
            out = joined.strip()
            self._buffer = []
            return out

        return None
