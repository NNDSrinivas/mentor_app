"""Streaming ASR + VAD utilities.

This module provides a minimal real‑time transcription helper that combines
``webrtcvad`` for voice activity detection with ``faster_whisper`` for
transcription of detected speech segments.  A very small rule‑based diarizer is
included so that the speaker can be labelled ``user`` or ``other``.  The
implementation is intentionally lightweight and pluggable – the diarizer can be
replaced with a pyannote pipeline in the future.
"""

from dataclasses import dataclass
from typing import Iterable, List, Tuple

try:  # pragma: no cover - optional dependency
    import webrtcvad
except Exception:  # pragma: no cover
    webrtcvad = None  # type: ignore

try:  # pragma: no cover - model loading is expensive and not exercised in tests
    from faster_whisper import WhisperModel
except Exception:  # pragma: no cover
    WhisperModel = None  # type: ignore

SAMPLE_RATE = 16000
FRAME_MS = 20
FRAME_BYTES = int(SAMPLE_RATE * FRAME_MS / 1000) * 2  # 16‑bit audio


class RuleBasedDiarizer:
    """Very small diarizer stub using energy threshold."""

    def __init__(self, threshold: int = 500):
        self.threshold = threshold

    def label(self, frame: bytes) -> str:
        if not frame:
            return "other"
        # simple energy check
        energy = sum(abs(b - 128) for b in frame) / len(frame)
        return "other" if energy > self.threshold else "user"


@dataclass
class ReadBackAligner:
    """Tracks how far the user has read back an answer."""

    answer: str
    cursor: int = 0

    def update(self, spoken: str, window: int = 10) -> int:
        """Fuzzy match the last ``window`` words and advance cursor."""
        import difflib

        answer_lower = self.answer.lower()
        words = spoken.strip().split()
        if not words:
            return self.cursor

        window_words = words[-window:]
        segment = " ".join(window_words).lower()

        # Exact match first
        idx = answer_lower.find(segment)
        if idx != -1:
            self.cursor = idx + len(segment)
            return self.cursor

        # Fall back to fuzzy match
        matcher = difflib.SequenceMatcher(None, answer_lower, segment)
        match = matcher.find_longest_match(0, len(answer_lower), 0, len(segment))
        self.cursor = match.a + match.size
        return self.cursor


class StreamingASR:
    """Combine VAD, diarization and whisper into a streaming interface."""

    def __init__(self):
        self.vad = webrtcvad.Vad(2) if webrtcvad else None
        self.buffer = b""
        self.diarizer = RuleBasedDiarizer()
        self.model = None  # lazy load

    # ------------------------------------------------------------------
    def _ensure_model(self):  # pragma: no cover - heavy
        if self.model is None and WhisperModel is not None:
            self.model = WhisperModel("tiny", device="cpu", compute_type="int8")

    def _frames(self, chunk: bytes) -> Iterable[bytes]:
        self.buffer += chunk
        while len(self.buffer) >= FRAME_BYTES:
            frame = self.buffer[:FRAME_BYTES]
            self.buffer = self.buffer[FRAME_BYTES:]
            yield frame

    def transcribe_stream(self, chunk: bytes) -> Iterable[Tuple[str, str]]:
        """Yield ``(speaker, text)`` pairs for speech in ``chunk``."""
        speech_frames: List[bytes] = []
        for frame in self._frames(chunk):
            is_speech = self.vad.is_speech(frame, SAMPLE_RATE) if self.vad else True
            if is_speech:
                speech_frames.append(frame)
            elif speech_frames:
                yield from self._flush_frames(speech_frames)
                speech_frames = []
        if speech_frames:
            yield from self._flush_frames(speech_frames)

    def _flush_frames(self, frames: List[bytes]) -> Iterable[Tuple[str, str]]:
        speaker = self.diarizer.label(b"".join(frames))
        self._ensure_model()  # pragma: no cover
        if self.model is None:  # pragma: no cover
            text = ""  # model unavailable
        else:  # pragma: no cover
            segments, _ = self.model.transcribe(b"".join(frames), language="en")
            text = " ".join(s.text for s in segments)
        yield speaker, text.strip()
