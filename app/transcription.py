"""Speech‑to‑text transcription module.

This module exposes functions to transcribe audio files into text.  You can
replace the placeholder implementation with calls to an external API such
as OpenAI Whisper, Google Speech‑to‑Text or your own ASR model.  The
transcription result should include timestamps to facilitate alignment
between audio, video and captured screen events.
"""
from __future__ import annotations

import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


def transcribe_audio(audio_path: str) -> Dict[str, Any]:  # type: ignore[name-defined]
    """Transcribe an audio file into text.

    Args:
        audio_path: Path to the audio file to transcribe.

    Returns:
        A dictionary containing the transcription text and optional metadata
        such as speaker labels or timestamps.  In this prototype the
        transcript is static.
    """
    logger.info("Transcribing audio at %s", audio_path)
    # TODO: call external ASR service to get real transcript
    transcript = {
        "text": "This is a placeholder transcript. Replace with ASR output.",
        "segments": [
            {"start": 0.0, "end": 10.0, "speaker": "Speaker 1", "text": "Hello everyone."},
        ],
    }
    logger.debug("Transcript: %s", transcript)
    return transcript