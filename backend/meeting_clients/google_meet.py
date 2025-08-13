"""Google Meet meeting client."""
from __future__ import annotations

import logging
from typing import Iterable, Tuple, Optional
import uuid

from .base import BaseMeetingClient

log = logging.getLogger(__name__)


class GoogleMeetClient(BaseMeetingClient):
    """Capture captions from Google Meet sessions."""

    def authenticate(self, oauth_token: str) -> None:
        super().authenticate(oauth_token)
        log.debug("Authenticated Google Meet client")

    def join_meeting(self, join_url: str) -> None:
        super().join_meeting(join_url)
        self.meeting_url = join_url

    def start_recording(self) -> None:
        super().start_recording()

    def stop_recording(self) -> None:
        super().stop_recording()

    def listen(self, caption_source: Iterable[Tuple[str, Optional[str]]]) -> None:
        for text, speaker in caption_source:
            if text:
                self.process_caption(text, speaker)
                log.debug("Google Meet caption forwarded: %s", text)

    @staticmethod
    def generate_meeting_link(meeting_id: Optional[str] = None) -> str:
        meeting_id = meeting_id or uuid.uuid4().hex[:10]
        return f"https://meet.google.com/{meeting_id}"
