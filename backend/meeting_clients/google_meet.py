"""Google Meet meeting client."""
from __future__ import annotations

import logging
from typing import Iterable, Tuple, Optional

from .base import BaseMeetingClient

log = logging.getLogger(__name__)


class GoogleMeetClient(BaseMeetingClient):
    """Capture captions from Google Meet sessions.

    This stub expects an iterable of ``(text, speaker)`` tuples. A full
    implementation would connect to the Google Meet caption stream.
    """

    def listen(self, caption_source: Iterable[Tuple[str, Optional[str]]]) -> None:
        for text, speaker in caption_source:
            if text:
                self.process_caption(text, speaker)
                log.debug("Google Meet caption forwarded: %s", text)
