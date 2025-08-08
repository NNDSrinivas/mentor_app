"""Meeting capture module.

This module provides functions to connect to meeting platforms and capture
audio/video streams. This implementation includes real audio recording
capabilities using sounddevice.
"""
from __future__ import annotations

import logging
import os
import time
from datetime import datetime
from typing import Any, Dict, Tuple, Optional

import sounddevice as sd
import scipy.io.wavfile as wav
import numpy as np

from .config import Config

logger = logging.getLogger(__name__)


class AudioRecorder:
    """Real-time audio recorder."""
    
    def __init__(self):
        self.recording = False
        self.audio_data = []
        self.sample_rate = Config.SAMPLE_RATE
        self.channels = Config.CHANNELS
        
    def start_recording(self) -> None:
        """Start recording audio."""
        self.recording = True
        self.audio_data = []
        
        def audio_callback(indata, frames, time, status):
            if status:
                logger.warning(f"Audio recording status: {status}")
            if self.recording:
                self.audio_data.append(indata.copy())
        
        self.stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            callback=audio_callback,
            dtype=np.float32
        )
        self.stream.start()
        logger.info("Audio recording started")
    
    def stop_recording(self, output_path: str) -> str:
        """Stop recording and save to file."""
        if not self.recording:
            return output_path
            
        self.recording = False
        self.stream.stop()
        self.stream.close()
        
        if self.audio_data:
            # Combine all audio chunks
            audio_array = np.concatenate(self.audio_data, axis=0)
            
            # Save as WAV file
            wav.write(output_path, self.sample_rate, audio_array)
            logger.info(f"Audio saved to {output_path}")
        
        return output_path


def capture_meeting(meeting_details: Dict[str, Any]) -> Tuple[str, str]:
    """Capture audio and video from a meeting.

    Args:
        meeting_details: Dictionary containing meeting information. Must
            include ``platform`` (zoom, teams, google_meet) and an ``id``.

    Returns:
        A tuple ``(audio_path, video_path)`` pointing to recorded files.
    """
    from .meeting_connectors import (
        ZoomConnector,
        TeamsConnector,
        GoogleMeetConnector,
    )

    platform = meeting_details.get("platform", "").lower()
    meeting_id = meeting_details.get("id") or meeting_details.get("meeting_id")
    if not meeting_id:
        raise ValueError("meeting_details must include an 'id'")

    connectors = {
        "zoom": ZoomConnector,
        "teams": TeamsConnector,
        "google_meet": GoogleMeetConnector,
        "google-meet": GoogleMeetConnector,
        "googlemeet": GoogleMeetConnector,
        "meet": GoogleMeetConnector,
    }

    connector_cls = connectors.get(platform)
    if connector_cls is None:
        raise ValueError(f"Unsupported meeting platform: {platform}")

    connector = connector_cls(meeting_id)

    logger.info("Capturing meeting %s on %s", meeting_id, platform)

    try:
        connector.start()
        logger.info("Recording in progress. Press Ctrl+C to stop...")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Recording interrupted by user")
    finally:
        audio_path, video_path = connector.stop()

    return audio_path, video_path


def capture_audio_only(meeting_id: str, duration: Optional[int] = None) -> str:
    """Capture only audio from a meeting.

    Args:
        meeting_id: Identifier for the meeting.
        duration: Recording duration in seconds. If None, records until stopped.

    Returns:
        Path to the recorded audio file.
    """
    logger.info("Capturing audio for meeting %s", meeting_id)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    audio_path = os.path.join(Config.RECORDINGS_DIR, f"{meeting_id}_{timestamp}_audio.wav")
    
    recorder = AudioRecorder()
    
    try:
        recorder.start_recording()
        
        if duration:
            logger.info(f"Recording for {duration} seconds...")
            time.sleep(duration)
        else:
            logger.info("Recording in progress. Press Ctrl+C to stop...")
            while True:
                time.sleep(1)
                
    except KeyboardInterrupt:
        logger.info("Recording interrupted by user")
    finally:
        recorder.stop_recording(audio_path)
    
    return audio_path


def capture_microphone_test(duration: int = 5) -> str:
    """Test microphone capture for a short duration.
    
    Args:
        duration: Test duration in seconds.
        
    Returns:
        Path to the test recording file.
    """
    logger.info(f"Testing microphone for {duration} seconds")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    test_path = os.path.join(Config.TEMP_DIR, f"mic_test_{timestamp}.wav")
    
    recorder = AudioRecorder()
    recorder.start_recording()
    time.sleep(duration)
    recorder.stop_recording(test_path)
    
    logger.info(f"Microphone test completed: {test_path}")
    return test_path
