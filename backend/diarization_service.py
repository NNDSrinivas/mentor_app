# backend/diarization_service.py

import os
import tempfile
import logging
import wave
from typing import List, Dict, Any, Optional, Tuple, cast

import numpy as np

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

    def __init__(self, device: Optional[str] = None, hf_token: Optional[str] = None, team_source: str = "github"):
        self.device = device or ("cuda" if TORCH_AVAILABLE and cast(Any, torch).cuda.is_available() else "cpu")
        self.hf_token = hf_token or os.getenv("HUGGINGFACE_TOKEN")

        # For now, use a simple speaker assignment strategy
        # In production, this would be replaced with proper diarization
        self.known_speakers = ["interviewer", "candidate", "team_member"]
        self.current_speaker_index = 0

        # Load potential team members from integrations so that diarized speaker
        # IDs can be mapped to real users.  This keeps the mapping logic in one
        # place and allows meeting_intelligence to ask for friendly names.
        self.team_members = self._load_team_members(team_source)

        # Initialize whisper model if available (tiny for <1s latency)
        if WHISPER_AVAILABLE:
            try:
                self.model = cast(Any, whisper).load_model("tiny", device=self.device)
                log.info(f"Loaded Whisper tiny model on {self.device}")
            except Exception as e:
                log.warning(f"Failed to load Whisper model: {e}")
                self.model = None
        else:
            log.warning("Whisper not available, proceeding without ASR")
            self.model = None

    # ------------------------------------------------------------------
    # Team member helpers
    # ------------------------------------------------------------------
    def _load_team_members(self, source: str) -> List[str]:
        """Fetch team member names from GitHub or Jira integrations."""

        members: List[str] = []
        if source == "github":
            try:
                from backend.integrations.github_manager import GitHubManager

                gh = GitHubManager()
                owner = os.getenv("GITHUB_OWNER", "")
                repo = os.getenv("GITHUB_REPO", "")
                info = gh.get_repo_info(owner, repo)
                owner_info = info.get("owner")
                if isinstance(owner_info, dict):
                    login = owner_info.get("login")
                    if login:
                        members.append(login)
            except Exception as exc:  # pragma: no cover - network call
                log.debug("Failed to load GitHub team members: %s", exc)
        else:
            try:
                from backend.integrations.jira_manager import JiraManager

                jira = JiraManager()
                result = jira.search_issues("order by assignee", max_results=50)
                for issue in result.get("issues", []):
                    assignee = issue.get("fields", {}).get("assignee")
                    if assignee and assignee.get("displayName"):
                        members.append(assignee["displayName"])
            except Exception as exc:  # pragma: no cover - network call
                log.debug("Failed to load Jira team members: %s", exc)

        return members

    def resolve_speaker(self, speaker_label: str) -> Optional[str]:
        """Map a diarized speaker label to a known team member."""

        if not speaker_label:
            return None

        for member in self.team_members:
            if member.lower() == speaker_label.lower():
                return member

        if speaker_label.startswith("speaker"):
            try:
                idx = int(speaker_label.replace("speaker", "")) - 1
                if 0 <= idx < len(self.team_members):
                    return self.team_members[idx]
            except ValueError:
                pass

        return None

    def _load_audio(self, audio_path: str) -> Tuple[np.ndarray, int]:
        """Load mono audio as float32 numpy array."""
        with wave.open(audio_path, "rb") as wf:
            sr = wf.getframerate()
            pcm = wf.readframes(wf.getnframes())
        audio = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0
        return audio, sr

    def _detect_voice_segments(
        self, audio: np.ndarray, sr: int, frame_ms: int = 30, energy_thresh: float = 0.0005
    ) -> List[Tuple[float, float]]:
        """Very small energy based VAD returning [(start, end), ...]."""
        frame_len = int(sr * frame_ms / 1000)
        if frame_len <= 0:
            return []
        energies = [
            float(np.mean(audio[i : i + frame_len] ** 2))
            for i in range(0, len(audio), frame_len)
        ]
        threshold = max(np.mean(energies) * 0.5, energy_thresh)
        segments: List[Tuple[float, float]] = []
        start: Optional[float] = None
        for idx, energy in enumerate(energies):
            t = idx * frame_ms / 1000.0
            if energy > threshold:
                if start is None:
                    start = t
            elif start is not None:
                end = t
                if end - start > 0.1:
                    segments.append((start, end))
                start = None
        if start is not None:
            segments.append((start, len(audio) / sr))
        return segments

    def _save_wav(self, path: str, audio: np.ndarray, sr: int) -> None:
        pcm = (audio * 32767).astype("<i2")
        with wave.open(path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(pcm.tobytes())

    def process_audio_file(self, audio_path: str) -> List[Dict[str, Any]]:
        """
        Processes an audio file using VAD + small ASR, returns diarized segments.
        :param audio_path: path to .wav or .mp3 file
        :return: list of {speaker, text, start, end}
        """
        log.info(f"[DiarizationService] Processing {audio_path} on {self.device}...")
        audio, sr = self._load_audio(audio_path)
        voice_segments = self._detect_voice_segments(audio, sr)
        results: List[Dict[str, Any]] = []
        for i, (start, end) in enumerate(voice_segments):
            segment_audio = audio[int(start * sr) : int(end * sr)]
            text = ""
            if self.model is not None and len(segment_audio) > 0:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                    self._save_wav(tmp.name, segment_audio, sr)
                    try:
                        trans = cast(Any, self.model).transcribe(tmp.name)
                        text = cast(str, trans.get("text", "")).strip()
                    finally:
                        os.unlink(tmp.name)
            speaker_label = self.known_speakers[i % len(self.known_speakers)]
            speaker_name = self.resolve_speaker(speaker_label) or speaker_label
            results.append(
                {
                    "speaker": speaker_name,
                    "text": text,
                    "start": start,
                    "end": end,
                }
            )
        return results

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
            label = "interviewer"
        elif any(keyword in text_lower for keyword in ["yes", "sure", "let me", "i have", "my experience"]):
            label = "candidate"
        else:
            # Default to alternating speakers
            self.current_speaker_index = (self.current_speaker_index + 1) % len(self.known_speakers)
            label = self.known_speakers[self.current_speaker_index]

        return self.resolve_speaker(label) or label


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
