"""Zoom meeting streaming utilities.

This module provides :class:`ZoomMeetingStreamer` which connects to Zoom's
real‑time meeting transcription service and forwards caption updates to the
mentor backend for further processing.

The implementation uses a websocket connection as described in Zoom's Meeting
SDK.  Each incoming message is expected to be JSON encoded and contain
``transcript`` and ``speaker`` fields.
"""
from __future__ import annotations

import json
import logging
from typing import Optional, Tuple

from .meeting_platform import MeetingStreamer

log = logging.getLogger(__name__)


class ZoomMeetingStreamer(MeetingStreamer):
    """Stream captions from a Zoom meeting."""

    def get_stream_url(self) -> str:
        # Zoom's WebSocket endpoint for live transcription.  The exact endpoint
        # may vary depending on account configuration; the path below mirrors
        # the official SDK documentation.
        return f"wss://ws.zoom.us/v2/meetings/{self.meeting_id}/events"

    def parse_message(self, message: str) -> Tuple[Optional[str], Optional[str]]:
        try:
            data = json.loads(message)
        except json.JSONDecodeError:
            log.debug("Non JSON message received from Zoom: %s", message)
            return None, None

        # Zoom typically nests transcript info under a 'payload' key
        if "payload" in data:
            data = data["payload"]

        text = data.get("transcript") or data.get("text")
        speaker = data.get("speaker", {}).get("name") if isinstance(data.get("speaker"), dict) else data.get("speaker")
        return text, speaker
