"""Zoom meeting client."""
from __future__ import annotations

import logging
from typing import Iterable, Tuple, Optional

from .base import BaseMeetingClient

log = logging.getLogger(__name__)


class ZoomClient(BaseMeetingClient):
    """Capture captions from Zoom meetings with lightweight OAuth handling."""

    def authenticate(self, oauth_token: str) -> None:
        """Store Zoom OAuth token using the base helper."""

        super().authenticate(oauth_token)
        log.debug("Authenticated Zoom client")

    # ------------------------------------------------------------------
    # Meeting control helpers
    # ------------------------------------------------------------------
    def join_meeting(self, join_url: str) -> None:
        """Join a Zoom meeting via join URL."""

        super().join_meeting(join_url)
        self.meeting_url = join_url

    def start_recording(self) -> None:
        super().start_recording()

    def stop_recording(self) -> None:
        super().stop_recording()

    # ------------------------------------------------------------------
    # Caption handling
    # ------------------------------------------------------------------
    def listen(self, caption_source: Iterable[Tuple[str, Optional[str]]]) -> None:
        for text, speaker in caption_source:
            if text:
                self.process_caption(text, speaker)
                log.debug("Zoom caption forwarded: %s", text)
