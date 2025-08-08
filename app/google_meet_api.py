"""Google Meet meeting streaming utilities."""
from __future__ import annotations

import json
import logging
from typing import Optional, Tuple

from .meeting_platform import MeetingStreamer

log = logging.getLogger(__name__)


class GoogleMeetStreamer(MeetingStreamer):
    """Stream captions from a Google Meet call."""

    def get_stream_url(self) -> str:
        # Google Meet exposes realtime captions over a websocket used by the web
        # client.  Access typically requires an authenticated cookie or OAuth
        # token which is supplied via headers by the base class.
        return f"wss://meet.google.com/{self.meeting_id}/captions"

    def parse_message(self, message: str) -> Tuple[Optional[str], Optional[str]]:
        try:
            data = json.loads(message)
        except json.JSONDecodeError:
            log.debug("Non JSON message received from Google Meet: %s", message)
            return None, None

        text = data.get("caption") or data.get("text")
        speaker = data.get("speaker") or data.get("participant")
        return text, speaker
