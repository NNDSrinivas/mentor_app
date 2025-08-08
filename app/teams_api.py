"""Microsoft Teams meeting streaming utilities."""
from __future__ import annotations

import json
import logging
from typing import Optional, Tuple

from .meeting_platform import MeetingStreamer

log = logging.getLogger(__name__)


class TeamsMeetingStreamer(MeetingStreamer):
    """Stream captions from a Microsoft Teams meeting."""

    def get_stream_url(self) -> str:
        # Teams provides a realtime caption websocket as part of the Graph API.
        # The token supplied during construction is passed via headers by the
        # base class.  Here we simply compose the URL for the meeting ID.
        return f"wss://teams.microsoft.com/meetings/{self.meeting_id}/captions"

    def parse_message(self, message: str) -> Tuple[Optional[str], Optional[str]]:
        try:
            data = json.loads(message)
        except json.JSONDecodeError:
            log.debug("Non JSON message received from Teams: %s", message)
            return None, None

        text = data.get("displayText") or data.get("text")
        speaker = data.get("speakerId") or data.get("speaker")
        return text, speaker
