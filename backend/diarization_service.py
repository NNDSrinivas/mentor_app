# backend/diarization_service.py

import os
import tempfile
import logging
from typing import List, Dict, Any, Optional, cast

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    torch = None  # type: ignore

try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    whisper = None  # type: ignore

log = logging.getLogger(__name__)

class DiarizationService:
    """
    Handles real-time or batch diarization of meeting audio.
    Separates who is speaking and when, so the AI can respond only after a full question.
    
    Note: This is a simplified version that works with Python 3.13.
    For production, consider using WhisperX when it supports Python 3.13.
    """

    def __init__(self, device: Optional[str] = None, hf_token: Optional[str] = None):
        self.device = device or ("cuda" if TORCH_AVAILABLE and cast(Any, torch).cuda.is_available() else "cpu")
        self.hf_token = hf_token or os.getenv("HUGGINGFACE_TOKEN")
        
        # For now, use a simple speaker assignment strategy
        # In production, this would be replaced with proper diarization
        self.known_speakers = ["interviewer", "candidate", "team_member"]
        self.current_speaker_index = 0

        # Initialize whisper model if available
        if WHISPER_AVAILABLE:
            try:
                self.model = cast(Any, whisper).load_model("base")
                log.info(f"Loaded Whisper model on {self.device}")
            except Exception as e:
                log.warning(f"Failed to load Whisper model: {e}")
                self.model = None
        else:
            log.warning("Whisper not available, using mock transcription")
            self.model = None

    def process_audio_file(self, audio_path: str) -> List[Dict[str, Any]]:
        """
        Processes an audio file, returns segments with speaker labels.
        :param audio_path: path to .wav or .mp3 file
        :return: list of {speaker, text, start, end}
        """
        log.info(f"[DiarizationService] Processing {audio_path} on {self.device}...")
        
        if not self.model:
            # Mock response for testing
            return [
                {
                    "speaker": "interviewer",
                    "text": "Can you explain the architecture of your system?",
                    "start": 0.0,
                    "end": 3.5
                },
                {
                    "speaker": "candidate", 
                    "text": "Sure, we use a microservices architecture with Docker containers...",
                    "start": 4.0,
                    "end": 8.5
                }
            ]
        
        try:
            # Transcribe with Whisper
            result = cast(Any, self.model).transcribe(audio_path)
            
            # Simple speaker assignment (alternating)
            # In production, this would use proper diarization
            segments = []
            for i, segment in enumerate(cast(Any, result)["segments"]):
                seg = cast(Dict[str, Any], segment)
                speaker = self.known_speakers[i % len(self.known_speakers)]
                segments.append({
                    "speaker": speaker,
                    "text": cast(str, seg.get("text", "")).strip(),
                    "start": cast(Any, seg.get("start", 0.0)),
                    "end": cast(Any, seg.get("end", 0.0))
                })
            
            return segments
            
        except Exception as e:
            log.error(f"Error processing audio: {e}")
            return []

    def process_realtime_chunk(self, audio_chunk: bytes) -> List[Dict[str, Any]]:
        """
        Processes a short audio chunk in memory (real-time).
        :param audio_chunk: raw PCM or WAV bytes
        :return: diarized text segments
        """
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            tmp.write(audio_chunk)
            tmp.flush()
            return self.process_audio_file(tmp.name)
    
    def assign_speaker_to_text(self, text: str, context: Optional[Dict] = None) -> str:
        """
        Assigns a speaker label to text based on context.
        This is a simplified heuristic - in production use proper diarization.
        """
        text_lower = text.lower()
        
        # Simple heuristics for speaker detection
        if any(keyword in text_lower for keyword in ["can you", "tell me", "explain", "how do", "what is"]):
            return "interviewer"
        elif any(keyword in text_lower for keyword in ["yes", "sure", "let me", "i have", "my experience"]):
            return "candidate"
        else:
            # Default to alternating speakers
            self.current_speaker_index = (self.current_speaker_index + 1) % len(self.known_speakers)
            return self.known_speakers[self.current_speaker_index]


if __name__ == "__main__":
    """
    Example usage:
    python backend/diarization_service.py test.wav
    """
    import sys, json
    if len(sys.argv) < 2:
        print("Usage: python diarization_service.py <audio_file>")
        print("Note: This is a simplified version for Python 3.13 compatibility")
        sys.exit(1)

    service = DiarizationService()
    segments = service.process_audio_file(sys.argv[1])
    print(json.dumps(segments, indent=2))
