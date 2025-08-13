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

    def process_audio_file(self, audio_path: str) -> List[Dict[str, Any]]:
        """
        Processes an audio file, returns segments with speaker labels.
        :param audio_path: path to .wav or .mp3 file
        :return: list of {speaker, text, start, end}
        """
        log.info(f"[DiarizationService] Processing {audio_path} on {self.device}...")
        
        if not self.model:
            # Mock response for testing.  Map the heuristic speaker labels to
            # real team members when possible so downstream components can show
            # friendly names.
            return [
                {
                    "speaker": self.resolve_speaker("interviewer") or "interviewer",
                    "text": "Can you explain the architecture of your system?",
                    "start": 0.0,
                    "end": 3.5,
                },
                {
                    "speaker": self.resolve_speaker("candidate") or "candidate",
                    "text": "Sure, we use a microservices architecture with Docker containers...",
                    "start": 4.0,
                    "end": 8.5,
                },
            ]
        
        try:
            # Transcribe with Whisper
            result = cast(Any, self.model).transcribe(audio_path)
            
            # Simple speaker assignment (alternating)
            # In production, this would use proper diarization
            segments = []
            for i, segment in enumerate(cast(Any, result)["segments"]):
                seg = cast(Dict[str, Any], segment)
                speaker_label = self.known_speakers[i % len(self.known_speakers)]
                speaker_name = self.resolve_speaker(speaker_label) or speaker_label
                segments.append(
                    {
                        "speaker": speaker_name,
                        "text": cast(str, seg.get("text", "")).strip(),
                        "start": cast(Any, seg.get("start", 0.0)),
                        "end": cast(Any, seg.get("end", 0.0)),
                    }
                )
            
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
