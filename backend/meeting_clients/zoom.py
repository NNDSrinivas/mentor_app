"""Zoom meeting client."""
from __future__ import annotations

import logging
from typing import Iterable, Tuple, Optional

from .base import BaseMeetingClient

log = logging.getLogger(__name__)


class ZoomClient(BaseMeetingClient):
    """Capture captions from Zoom meetings.

    The real integration would use the Zoom SDK or web socket hooks to obtain
    live transcription. Here we accept an iterable of ``(text, speaker)`` tuples
    for testing purposes.
    """

    def listen(self, caption_source: Iterable[Tuple[str, Optional[str]]]) -> None:
        for text, speaker in caption_source:
            if text:
                self.process_caption(text, speaker)
                log.debug("Zoom caption forwarded: %s", text)
