"""Utilities for streaming meeting data to the backend service.

This module defines :class:`MeetingStreamer` – a small helper that manages
websocket connections to meeting providers (Zoom, Teams, Google Meet) and
forwards transcript data to the existing ``/api/meeting-events`` endpoint.

Sub‑classes only need to implement :meth:`get_stream_url` and optionally
:meth:`parse_message` for provider specific payloads.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Optional, Dict, Any

import requests
import websockets

log = logging.getLogger(__name__)


class MeetingStreamer:
    """Base class for meeting platform streamers.

    Parameters
    ----------
    meeting_id:
        Identifier for the meeting or call being observed.
    token:
        Authentication token or API key used when connecting to the provider.
    backend_url:
        Base URL for the mentor application's backend.  Transcript snippets are
        forwarded here for further processing.
    """

    def __init__(self, meeting_id: str, token: str, backend_url: str = "http://localhost:8080"):
        self.meeting_id = meeting_id
        self.token = token
        self.backend_url = backend_url.rstrip("/")

    # ------------------------------------------------------------------
    # Backend communication helpers
    async def post_caption(self, text: str, speaker: Optional[str] = None) -> None:
        """Send a caption chunk to the backend service."""
        payload = {
            "action": "caption_chunk",
            "data": {
                "meetingId": self.meeting_id,
                "text": text,
                "speaker": speaker,
            },
        }
        try:
            requests.post(f"{self.backend_url}/api/meeting-events", json=payload, timeout=5)
        except Exception as exc:  # pragma: no cover - network failures
            log.warning("Failed to notify backend: %s", exc)

    # ------------------------------------------------------------------
    # Streaming logic
    async def stream(self) -> None:
        """Connect to the provider and relay caption data.

        Sub‑classes implement :meth:`get_stream_url` and optionally override
        :meth:`parse_message` to handle provider specific payloads.
        """
        url = self.get_stream_url()
        headers = self.auth_headers()
        async with websockets.connect(url, extra_headers=headers) as ws:
            async for raw in ws:
                text, speaker = self.parse_message(raw)
                if text:
                    await self.post_caption(text, speaker)

    def auth_headers(self) -> Dict[str, str]:
        """Return headers used for authentication."""
        return {"Authorization": f"Bearer {self.token}"}

    # ------------------------------------------------------------------
    # Hooks for subclasses
    def get_stream_url(self) -> str:  # pragma: no cover - to be implemented by subclasses
        raise NotImplementedError

    def parse_message(self, message: str) -> tuple[Optional[str], Optional[str]]:
        """Parse incoming websocket message.

        Returns
        -------
        (text, speaker):
            Extracted transcript text and optional speaker label.
        """
        try:
            data: Dict[str, Any] = json.loads(message)
        except json.JSONDecodeError:
            log.debug("Received non JSON message: %s", message)
            return None, None

        text = data.get("text") or data.get("transcript") or data.get("caption")
        speaker = data.get("speaker") or data.get("speakerId") or data.get("user")
        return text, speaker

    # Convenience synchronous runner -------------------------------------------------
    def run(self) -> None:
        """Start the streaming loop using ``asyncio.run``."""
        asyncio.run(self.stream())
