"""Base client for meeting platforms.

Each client is responsible for connecting to a meeting platform, capturing
captions (and optionally audio), and forwarding those captions to both the
meeting intelligence system and the realtime service running on port 8080.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

import requests

from app.meeting_intelligence import meeting_intelligence

log = logging.getLogger(__name__)


class BaseMeetingClient:
    """Reusable helper that forwards caption text to downstream services."""

    def __init__(self, meeting_id: str, session_id: str, realtime_url: str = "http://localhost:8080"):
        self.meeting_id = meeting_id
        self.session_id = session_id
        self.realtime_url = realtime_url.rstrip("/")

    def process_caption(self, text: str, speaker: Optional[str] = None, timestamp: Optional[datetime] = None) -> None:
        """Send caption text to meeting intelligence and realtime API."""
        meeting_intelligence.process_caption(
            meeting_id=self.meeting_id,
            text=text,
            speaker_id=speaker,
            timestamp=timestamp,
        )

        payload = {"text": text}
        if speaker:
            payload["speaker"] = speaker
        if timestamp:
            payload["timestamp"] = timestamp.isoformat()

        try:
            requests.post(
                f"{self.realtime_url}/api/sessions/{self.session_id}/captions",
                json=payload,
                timeout=5,
            )
        except Exception as exc:  # pragma: no cover - network failures best effort
            log.warning("Failed to forward caption to realtime service: %s", exc)

    # ------------------------------------------------------------------
    # Methods expected from subclasses
    # ------------------------------------------------------------------
    def listen(self) -> None:  # pragma: no cover - placeholder for concrete clients
        """Start listening for captions from the platform.

        Subclasses should implement this method and call :meth:`process_caption`
        whenever a new caption fragment is available.
        """
        raise NotImplementedError
