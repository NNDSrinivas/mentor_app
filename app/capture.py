"""Meeting capture module.

This module provides functions to connect to meeting platforms and capture
audio/video streams. This implementation includes real audio recording
capabilities using sounddevice.
"""
from __future__ import annotations

import logging
import os
import time
import threading
from datetime import datetime
from typing import Any, Tuple, Optional
import platform
import shutil
import subprocess

# Optional audio processing imports
try:
    import sounddevice as sd
    import scipy.io.wavfile as wav
    import numpy as np
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False
    # Mock modules for when audio libs not available
    class MockSoundDevice:
        def __init__(self): pass
        def rec(self, *args, **kwargs): return []
        def wait(self): pass
        def stop(self, *args): pass
        class InputStream:
            def __init__(self, *args, **kwargs): pass
            def start(self): pass
            def stop(self): pass
            def close(self): pass
        InputStream = InputStream
        @property
        def default(self): return MockDevice()
        
    class MockDevice:
        @property  
        def device(self): return 0
        @property
        def channels(self): return 1
        @property
        def samplerate(self): return 44100
        
    class MockWav:
        @staticmethod
        def write(filename, rate, data): pass
        
    class MockNumpy:
        @staticmethod
        def zeros(*args, **kwargs): return []
        @staticmethod
        def concatenate(seq, axis=0): return []
        float32 = float
        int16 = int
        
    sd = MockSoundDevice()
    wav = MockWav()
    np = MockNumpy()

from .config import Config
from .realtime import RealtimeSessionManager, get_session_manager

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


class BaseSystemAudioRecorder:
    """Base class for system audio recording using ffmpeg."""

    def __init__(self, output_path: str) -> None:
        self.output_path = output_path
        self.process: Optional[subprocess.Popen] = None
        self.ffmpeg = shutil.which("ffmpeg")
        if not self.ffmpeg:
            raise RuntimeError("ffmpeg is required for system audio recording")

    def start(self) -> None:  # pragma: no cover - thin wrapper around subprocess
        raise NotImplementedError

    def stop(self) -> None:
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except Exception:  # pragma: no cover - best effort cleanup
                self.process.kill()


class MacOSSystemAudioRecorder(BaseSystemAudioRecorder):
    """System audio recorder for macOS using ScreenCaptureKit via ffmpeg."""

    def start(self) -> None:
        # ScreenCaptureKit is exposed through ffmpeg's avfoundation device
        cmd = [
            self.ffmpeg,
            "-y",
            "-f",
            "avfoundation",
            "-i",
            "none:0",
            self.output_path,
        ]
        self.process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


class WindowsSystemAudioRecorder(BaseSystemAudioRecorder):
    """System audio recorder for Windows using WASAPI loopback."""

    def start(self) -> None:
        cmd = [
            self.ffmpeg,
            "-y",
            "-f",
            "wasapi",
            "-i",
            "default",
            self.output_path,
        ]
        self.process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


class LinuxSystemAudioRecorder(BaseSystemAudioRecorder):
    """System audio recorder for Linux using PulseAudio/PipeWire."""

    def start(self) -> None:
        cmd = [
            self.ffmpeg,
            "-y",
            "-f",
            "pulse",
            "-i",
            "default",
            self.output_path,
        ]
        self.process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def get_system_audio_recorder(output_path: str) -> BaseSystemAudioRecorder:
    """Return an OS-specific system audio recorder."""

    system = platform.system()
    if system == "Darwin":
        return MacOSSystemAudioRecorder(output_path)
    if system == "Windows":
        return WindowsSystemAudioRecorder(output_path)
    if system == "Linux":
        return LinuxSystemAudioRecorder(output_path)
    raise RuntimeError(f"System audio recording not supported on {system}")


def capture_meeting(meeting_id: str, record_system_audio: bool = False) -> Tuple[str, str, Optional[str]]:
    """Capture audio and video from a meeting.

    Args:
        meeting_id: Identifier for the meeting (could be a Zoom meeting ID,
            a calendar event ID or a link).
        record_system_audio: When ``True`` also capture system/loopback audio
            using an OS specific backend.

    Returns:
        A tuple ``(audio_path, video_path, system_audio_path)`` where the last
        element is ``None`` when ``record_system_audio`` is ``False`` or
        unsupported.
    """
    logger.info("Capturing meeting %s", meeting_id)

    # Create timestamped filenames
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    audio_path = os.path.join(Config.RECORDINGS_DIR, f"{meeting_id}_{timestamp}_audio.wav")
    video_path = os.path.join(Config.RECORDINGS_DIR, f"{meeting_id}_{timestamp}_video.mp4")
    system_audio_path: Optional[str] = None
    system_recorder: Optional[BaseSystemAudioRecorder] = None

    # For now, we'll just record microphone audio
    recorder = AudioRecorder()

    try:
        if record_system_audio:
            system_audio_path = os.path.join(
                Config.RECORDINGS_DIR, f"{meeting_id}_{timestamp}_system.wav"
            )
            try:
                system_recorder = get_system_audio_recorder(system_audio_path)
                system_recorder.start()
                logger.info("System audio recording started")
            except Exception as exc:  # pragma: no cover - depends on OS
                logger.error("System audio recording unavailable: %s", exc)
                system_audio_path = None

        recorder.start_recording()
        logger.info("Recording in progress. Press Ctrl+C to stop...")

        # In a real implementation, this would be controlled by meeting events
        # For demo purposes, record for 10 seconds
        time.sleep(10)

    except KeyboardInterrupt:
        logger.info("Recording interrupted by user")
    finally:
        recorder.stop_recording(audio_path)
        if system_recorder:
            system_recorder.stop()

    # Video recording placeholder - would need platform-specific implementation
    logger.debug("Video recording placeholder - would implement platform-specific capture")

    return audio_path, video_path, system_audio_path


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


class BaseCaptionClient:
    """Base client for streaming captions into the realtime system.

    This simplified implementation reads caption lines from a text file and
    forwards them to a :class:`RealtimeSession` via the global
    :func:`get_session_manager` helper.  Real integrations with meeting
    platforms would replace the file reader with API specific logic.
    """

    platform: str = "generic"

    def __init__(
        self,
        session_id: str,
        caption_file: str,
        manager: Optional[RealtimeSessionManager] = None,
    ) -> None:
        self.session_id = session_id
        self.caption_file = caption_file
        self.manager = manager or get_session_manager()

    def stream_captions(self, delay: float = 0.2) -> None:
        """Stream captions from ``caption_file`` to the session manager."""
        session = self.manager.get_session(self.session_id)
        if not session:
            raise ValueError(f"Session {self.session_id} not found")

        try:
            with open(self.caption_file, "r", encoding="utf-8") as fh:
                for idx, line in enumerate(fh, 1):
                    text = line.strip()
                    if not text:
                        continue
                    caption = {
                        "id": f"{self.session_id}_{idx}",
                        "text": text,
                        "speaker": "unknown",
                        "platform": self.platform,
                    }
                    session.add_caption(caption)
                    time.sleep(delay)
        except FileNotFoundError:
            logger.error("Caption file %s not found", self.caption_file)


class ZoomClient(BaseCaptionClient):
    """Stream captions for a Zoom meeting."""

    platform = "zoom"


class TeamsClient(BaseCaptionClient):
    """Stream captions for a Microsoft Teams meeting."""

    platform = "teams"


class GoogleMeetClient(BaseCaptionClient):
    """Stream captions for a Google Meet meeting."""

    platform = "google_meet"
