"""Microsoft Teams meeting client."""
from __future__ import annotations

import logging
from typing import Iterable, Tuple, Optional

from .base import BaseMeetingClient

log = logging.getLogger(__name__)


class TeamsClient(BaseMeetingClient):
    """Capture captions from Microsoft Teams meetings."""

    def authenticate(self, oauth_token: str) -> None:
        super().authenticate(oauth_token)
        log.debug("Authenticated Teams client")

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
                log.debug("Teams caption forwarded: %s", text)
