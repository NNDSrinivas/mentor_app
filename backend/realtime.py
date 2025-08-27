from __future__ import annotations

"""Real-time audio processing pipeline.

This module wires together VAD, ASR and question detection for streaming
transcripts.  It is intentionally lightweight – heavy models are loaded lazily
and can be swapped out later (e.g. pyannote for diarization).
"""

from dataclasses import dataclass
from typing import Iterable, List, Optional

from app.asr_vad import StreamingASR
from app.question_detector import QuestionDetector, AnswerJob


@dataclass
class CaptionChunk:
    """Caption text with diarized speaker information."""

    speaker: str
    text: str
    ts: int  # milliseconds


class RealtimePipeline:
    """High level coordinator for real‑time caption processing."""

    def __init__(self, asr: Optional[StreamingASR] = None,
                 detector: Optional[QuestionDetector] = None):
        self.asr = asr or StreamingASR()
        self.detector = detector or QuestionDetector()

    # --- audio ingest -------------------------------------------------
    def process_audio_chunk(self, meeting_id: str, audio: bytes, ts: int) -> List[AnswerJob]:
        """Process raw audio bytes and return any ``AnswerJob``s produced.

        ``audio`` is assumed to be 16‑bit PCM at 16 kHz.  The ASR module takes
        care of VAD and diarization, yielding partial transcript chunks which
        are then fed to the question detector.
        """
        jobs: List[AnswerJob] = []
        for speaker, text in self.asr.transcribe_stream(audio):
            job = self.on_caption_chunk(meeting_id, speaker, text, ts)
            if job:
                jobs.append(job)
        return jobs

    # --- text ingest --------------------------------------------------
    def on_caption_chunk(self, meeting_id: str, speaker: str,
                         text: str, ts: int, score: float = 0.0) -> Optional[AnswerJob]:
        """Feed caption chunks into the question detector.

        When the detector signals an end of question an ``AnswerJob`` is
        returned.  The caller may enqueue it for downstream processing.
        """
        question = self.detector.add_chunk(speaker=speaker, text=text, ts=ts, score=score)
        if question:
            return AnswerJob(meeting_id=meeting_id, question=question, timestamp=ts)
        return None


__all__ = ["RealtimePipeline", "CaptionChunk"]
