"""Microsoft Teams meeting client."""
from __future__ import annotations

import logging
from typing import Iterable, Tuple, Optional
import uuid

from .base import BaseMeetingClient

log = logging.getLogger(__name__)


class TeamsClient(BaseMeetingClient):
    """Capture captions from Microsoft Teams meetings.

    Real-world usage would rely on the Teams SDK or graph APIs. This lightweight
    implementation consumes an iterable of caption tuples for demonstration.
    """

    def listen(self, caption_source: Iterable[Tuple[str, Optional[str]]]) -> None:
        for text, speaker in caption_source:
            if text:
                self.process_caption(text, speaker)
                log.debug("Teams caption forwarded: %s", text)

    @staticmethod
    def generate_meeting_link(meeting_id: Optional[str] = None) -> str:
        meeting_id = meeting_id or uuid.uuid4().hex
        return f"https://teams.microsoft.com/l/meetup-join/{meeting_id}"
