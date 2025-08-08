from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Tuple

from .config import Config
from .capture import AudioRecorder

logger = logging.getLogger(__name__)


class BaseConnector:
    """Base class for meeting platform connectors."""

    def __init__(self, meeting_id: str):
        self.meeting_id = meeting_id
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        os.makedirs(Config.RECORDINGS_DIR, exist_ok=True)
        self.audio_path = os.path.join(Config.RECORDINGS_DIR, f"{meeting_id}_{timestamp}_audio.wav")
        self.video_path = os.path.join(Config.RECORDINGS_DIR, f"{meeting_id}_{timestamp}_video.mp4")
        self.recorder = AudioRecorder()

    def start(self) -> None:
        """Start capturing audio and video streams."""
        logger.info("Starting %s stream for %s", self.__class__.__name__, self.meeting_id)
        self.recorder.start_recording()
        logger.debug("Video capture not implemented for %s", self.__class__.__name__)

    def stop(self) -> Tuple[str, str]:
        """Stop capturing and return paths to recordings."""
        logger.info("Stopping %s stream for %s", self.__class__.__name__, self.meeting_id)
        self.recorder.stop_recording(self.audio_path)
        if not os.path.exists(self.video_path):
            open(self.video_path, "wb").close()
        return self.audio_path, self.video_path


class ZoomConnector(BaseConnector):
    """Connector for Zoom meetings."""
    pass


class TeamsConnector(BaseConnector):
    """Connector for Microsoft Teams meetings."""
    pass


class GoogleMeetConnector(BaseConnector):
    """Connector for Google Meet meetings."""
    pass
