"""Base client for meeting platforms.

Each client is responsible for connecting to a meeting platform, capturing
captions (and optionally audio), and forwarding those captions to both the
meeting intelligence system and the realtime service running on port 8080.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional
import uuid

import requests

from app.meeting_intelligence import meeting_intelligence

log = logging.getLogger(__name__)


class BaseMeetingClient:
    """Reusable helper that forwards caption text to downstream services.

    The base client also provides minimal OAuth handling and stubs for
    programmatically joining and recording meetings.  Concrete platform
    implementations (Zoom/Teams/Meet) only need to override the small surface
    area defined here which keeps tests light weight while still mirroring the
    behaviour of real SDKs.
    """

    def __init__(
        self,
        meeting_id: str,
        session_id: str,
        realtime_url: str = "http://localhost:8080",
    ) -> None:
        self.meeting_id = meeting_id
        self.session_id = session_id
        self.realtime_url = realtime_url.rstrip("/")

        # OAuth tokens – in production these would be fetched via an OAuth
        # handshake.  For unit tests and simple usage we simply store whatever
        # token is provided.
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None

        # Track recording state so subclasses can toggle recording without
        # re‑implementing boilerplate book keeping.
        self._recording: bool = False

    # ------------------------------------------------------------------
    # OAuth helpers
    # ------------------------------------------------------------------
    def authenticate(self, access_token: str, refresh_token: Optional[str] = None) -> None:
        """Store OAuth tokens for the meeting provider.

        Real implementations would exchange an auth code for tokens.  The base
        class simply stores the tokens so that subclasses can use them when
        making API calls.
        """

        self.access_token = access_token
        self.refresh_token = refresh_token

    # ------------------------------------------------------------------
    # Meeting/session helpers
    # ------------------------------------------------------------------
    def join_meeting(self, join_url: str) -> None:  # pragma: no cover - interface stub
        """Join the remote meeting.

        Subclasses should override this method with platform specific logic.
        The base implementation merely logs the intent so tests can exercise
        the flow without external dependencies.
        """

        log.info("Joining meeting at %s", join_url)

    def start_recording(self) -> None:  # pragma: no cover - interface stub
        """Begin recording the meeting."""

        self._recording = True
        log.info("Recording started")

    def stop_recording(self) -> None:  # pragma: no cover - interface stub
        """Stop recording the meeting."""

        self._recording = False
        log.info("Recording stopped")

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
    @staticmethod
    def generate_meeting_link(meeting_id: Optional[str] = None) -> str:
        """Generate a meeting link for the platform.

        Subclasses should override this to return a platform specific URL. The
        base implementation simply generates a placeholder link.
        """
        meeting_id = meeting_id or uuid.uuid4().hex
        return f"https://meet.example.com/{meeting_id}"

    def listen(self) -> None:  # pragma: no cover - placeholder for concrete clients
        """Start listening for captions from the platform.

        Subclasses should implement this method and call :meth:`process_caption`
        whenever a new caption fragment is available.
        """
        raise NotImplementedError
