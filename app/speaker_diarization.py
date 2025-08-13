"""
Real-time Speaker Diarization for Interview Assistant
Identifies and separates different speakers in audio streams.
"""

import logging
import os
import io
import wave
import numpy as np
import threading
import time
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
from datetime import datetime, timedelta

try:  # Optional heavy dependency
    from pyannote.audio import Pipeline  # type: ignore
    PYANNOTE_AVAILABLE = True
except Exception:  # pragma: no cover - handled gracefully
    Pipeline = None
    PYANNOTE_AVAILABLE = False

logger = logging.getLogger(__name__)

@dataclass
class SpeakerSegment:
    """A speech segment with speaker identification."""
    start_time: float
    end_time: float
    speaker_id: str
    confidence: float
    transcript: str
    is_question: bool = False
    is_interviewer: bool = False

@dataclass
class SpeakerProfile:
    """Profile for a detected speaker."""
    speaker_id: str
    voice_features: Dict
    speaking_patterns: List[str]
    is_interviewer: bool
    confidence: float
    last_seen: datetime

class SpeakerDiarizer:
    """Real-time speaker diarization and interview flow detection."""
    
    def __init__(self):
        self.speakers: Dict[str, SpeakerProfile] = {}
        self.current_segments: List[SpeakerSegment] = []
        self.interviewer_id: Optional[str] = None
        self.candidate_id: Optional[str] = None
        self.current_question: Optional[SpeakerSegment] = None
        self.is_processing = False
        self.silence_threshold = 2.0  # seconds of silence to end a question
        self.last_speech_time = time.time()
        self.pipeline: Optional[Pipeline] = None

        if PYANNOTE_AVAILABLE:
            try:
                token = os.getenv("HUGGINGFACE_TOKEN")
                if token:
                    self.pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization", use_auth_token=token)
                else:
                    self.pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization")
                logger.info("✅ Loaded pyannote speaker diarization pipeline")
            except Exception as e:  # pragma: no cover - heavy model may be unavailable
                logger.warning(f"pyannote pipeline unavailable: {e}")
                self.pipeline = None

    def identify_speakers(self, audio_source: Union[str, bytes], timestamp: float = 0.0) -> List[SpeakerSegment]:
        """Diarize an audio source and return detected speaker segments.

        Args:
            audio_source: Path to an audio file or raw PCM bytes.
            timestamp: Optional start timestamp for the provided audio.

        Returns:
            List of :class:`SpeakerSegment` objects.
        """
        if self.pipeline is not None:
            try:  # pragma: no cover - exercised only when pyannote models are available
                diarization = self.pipeline(audio_source)
                segments: List[SpeakerSegment] = []
                for turn, _, speaker in diarization.itertracks(yield_label=True):
                    segments.append(
                        SpeakerSegment(
                            start_time=timestamp + float(turn.start),
                            end_time=timestamp + float(turn.end),
                            speaker_id=str(speaker),
                            confidence=1.0,
                            transcript="",
                        )
                    )
                return segments
            except Exception as e:  # pragma: no cover
                logger.warning(f"pyannote diarization failed, falling back to heuristic: {e}")

        return self._heuristic_diarization(audio_source, timestamp)

    def _heuristic_diarization(self, audio_source: Union[str, bytes], timestamp: float) -> List[SpeakerSegment]:
        """Fallback energy-based diarization used when pyannote isn't available."""
        try:
            if isinstance(audio_source, bytes):
                wav = wave.open(io.BytesIO(audio_source))
            else:
                wav = wave.open(audio_source, "rb")
        except Exception as e:
            logger.error(f"Failed to open audio for diarization: {e}")
            return []

        with wav:
            sample_rate = wav.getframerate()
            frames = wav.readframes(wav.getnframes())

        audio = np.frombuffer(frames, dtype=np.int16).astype(float)
        if not len(audio):
            return []

        frame_size = int(sample_rate * 0.1)  # 100ms frames for finer detection
        threshold = 0.01 * np.max(np.abs(audio))
        segments: List[SpeakerSegment] = []
        start = None
        speaker_index = 0
        for i in range(0, len(audio), frame_size):
            frame = audio[i : i + frame_size]
            energy = np.mean(np.abs(frame))
            current_time = timestamp + i / sample_rate
            if energy > threshold and start is None:
                start = current_time
            elif energy <= threshold and start is not None:
                end = current_time
                segments.append(
                    SpeakerSegment(
                        start_time=start,
                        end_time=end,
                        speaker_id=f"speaker_{speaker_index}",
                        confidence=0.5,
                        transcript="",
                    )
                )
                speaker_index += 1
                start = None
        if start is not None:
            end = timestamp + len(audio) / sample_rate
            segments.append(
                SpeakerSegment(
                    start_time=start,
                    end_time=end,
                    speaker_id=f"speaker_{speaker_index}",
                    confidence=0.5,
                    transcript="",
                )
            )

        return segments
    
    def process_transcript_with_speakers(self, transcript: str, speaker_features: Dict) -> SpeakerSegment:
        """Process transcript and identify speaker and speech type."""
        
        # Identify speaker based on voice features and patterns
        speaker_id = self.identify_speaker(speaker_features, transcript)
        
        # Determine if this is interviewer or candidate
        is_interviewer = self.is_likely_interviewer(transcript, speaker_id)
        
        # Check if this is a question
        is_question = self.is_question(transcript)
        
        segment = SpeakerSegment(
            start_time=time.time(),
            end_time=time.time() + len(transcript) * 0.05,  # Rough estimate
            speaker_id=speaker_id,
            confidence=0.8,  # Would be calculated by diarization model
            transcript=transcript,
            is_question=is_question,
            is_interviewer=is_interviewer
        )
        
        # Update speaker tracking
        self.update_speaker_profile(speaker_id, transcript, is_interviewer)
        
        return segment
    
    def identify_speaker(self, voice_features: Dict, transcript: str) -> str:
        """Identify speaker based on voice features and patterns."""
        
        # In a real implementation, this would use:
        # 1. Voice embeddings from models like x-vector or ECAPA-TDNN
        # 2. Speaker verification models
        # 3. Clustering algorithms for unseen speakers
        
        # Simple heuristic based on speech patterns for now
        if self.is_likely_interviewer_speech(transcript):
            if not self.interviewer_id:
                self.interviewer_id = "interviewer_1"
            return self.interviewer_id
        else:
            if not self.candidate_id:
                self.candidate_id = "candidate_1"
            return self.candidate_id
    
    def is_likely_interviewer(self, transcript: str, speaker_id: str) -> bool:
        """Determine if speaker is likely the interviewer."""
        
        # Check if we already know this speaker
        if speaker_id == self.interviewer_id:
            return True
        if speaker_id == self.candidate_id:
            return False
            
        # Use speech pattern analysis
        return self.is_likely_interviewer_speech(transcript)
    
    def is_likely_interviewer_speech(self, transcript: str) -> bool:
        """Analyze speech patterns to identify interviewer."""
        
        interviewer_patterns = [
            # Question patterns
            r"tell me about",
            r"can you (?:describe|explain|walk (?:me )?through)",
            r"what (?:is|are|would|do) you",
            r"how (?:do|would|did) you",
            r"why (?:do|did|would) you",
            r"have you (?:ever|worked|used)",
            r"what's your (?:experience|approach|understanding)",
            
            # Follow-up patterns
            r"(?:can|could) you (?:elaborate|expand|give me)",
            r"that's (?:interesting|good|great)",
            r"(?:ok|okay|alright),? (?:so|now|next)",
            r"let's (?:move on|talk about|discuss)",
            
            # Interview management
            r"we have (?:about|roughly)",
            r"(?:any|do you have) questions for",
            r"that (?:concludes|wraps up)",
        ]
        
        text_lower = transcript.lower()
        return any(pattern in text_lower for pattern in interviewer_patterns)
    
    def is_question(self, transcript: str) -> bool:
        """Determine if transcript contains a question."""
        
        # Direct question indicators
        if '?' in transcript:
            return True
            
        # Question word patterns
        question_starters = [
            'what', 'why', 'how', 'when', 'where', 'who', 'which',
            'tell me', 'describe', 'explain', 'can you', 'could you',
            'would you', 'have you', 'do you', 'did you', 'are you',
            'will you', 'shall we', 'let\'s'
        ]
        
        text_lower = transcript.lower().strip()
        return any(text_lower.startswith(starter) for starter in question_starters)
    
    def update_speaker_profile(self, speaker_id: str, transcript: str, is_interviewer: bool):
        """Update speaker profile with new speech data."""
        
        if speaker_id not in self.speakers:
            self.speakers[speaker_id] = SpeakerProfile(
                speaker_id=speaker_id,
                voice_features={},
                speaking_patterns=[],
                is_interviewer=is_interviewer,
                confidence=0.7,
                last_seen=datetime.now()
            )
        
        profile = self.speakers[speaker_id]
        profile.speaking_patterns.append(transcript)
        profile.last_seen = datetime.now()
        
        # Update interviewer identification
        if is_interviewer and not self.interviewer_id:
            self.interviewer_id = speaker_id
        elif not is_interviewer and not self.candidate_id:
            self.candidate_id = speaker_id
    
    def detect_question_end(self, current_segment: SpeakerSegment) -> bool:
        """Detect when a question has ended."""
        
        if not current_segment.is_question:
            return False
            
        # Question ends when:
        # 1. Speaker changes from interviewer to candidate
        # 2. There's a significant pause
        # 3. The transcript contains question-ending phrases
        
        ending_phrases = [
            'that\'s all', 'thank you', 'those are my questions',
            'anything else', 'any questions', 'what do you think'
        ]
        
        text_lower = current_segment.transcript.lower()
        return any(phrase in text_lower for phrase in ending_phrases)
    
    def get_complete_question(self) -> Optional[str]:
        """Get the complete question text when a question ends."""
        
        if not self.current_question:
            return None
            
        # Combine all segments from the current question
        question_text = self.current_question.transcript
        
        # Clean up and format the question
        question_text = question_text.strip()
        if not question_text.endswith('?') and self.is_question(question_text):
            question_text += '?'
            
        return question_text
    
    def start_new_question(self, segment: SpeakerSegment):
        """Start tracking a new question."""
        if segment.is_question and segment.is_interviewer:
            self.current_question = segment
            logger.info(f"📝 New question started: {segment.transcript[:50]}...")
    
    def should_generate_response(self, segment: SpeakerSegment) -> bool:
        """Determine if we should generate an AI response."""
        
        # Generate response when:
        # 1. A question from interviewer has ended
        # 2. Candidate hasn't started speaking yet
        # 3. There's sufficient pause indicating question is complete
        
        if not segment.is_interviewer or not segment.is_question:
            return False
            
        # Check for question completion indicators
        return self.detect_question_end(segment)
    
    def get_conversation_context(self) -> Dict:
        """Get current conversation context for AI response generation."""
        
        recent_segments = self.current_segments[-5:]  # Last 5 segments
        
        return {
            'current_question': self.current_question.transcript if self.current_question else '',
            'interviewer_id': self.interviewer_id,
            'candidate_id': self.candidate_id,
            'recent_conversation': [s.transcript for s in recent_segments],
            'speaker_profiles': {
                sid: {
                    'is_interviewer': profile.is_interviewer,
                    'confidence': profile.confidence,
                    'pattern_count': len(profile.speaking_patterns)
                }
                for sid, profile in self.speakers.items()
            }
        }

class InterviewFlowManager:
    """Manages the flow of interview questions and responses."""
    
    def __init__(self):
        self.diarizer = SpeakerDiarizer()
        self.current_state = 'waiting'  # waiting, question_active, response_pending, answering
        self.question_buffer = []
        self.response_callbacks = []
        self.segment_callbacks = []
        
    def process_speech_segment(self, transcript: str, voice_features: Dict) -> Optional[str]:
        """Process a speech segment and return AI response if appropriate."""
        
        # Create speaker segment
        segment = self.diarizer.process_transcript_with_speakers(transcript, voice_features)
        self.diarizer.current_segments.append(segment)
        for callback in self.segment_callbacks:
            try:
                callback(segment)
            except Exception as e:
                logger.error(f"Error in segment callback: {e}")
        
        # Update conversation state
        if segment.is_interviewer and segment.is_question:
            if self.current_state == 'waiting':
                self.current_state = 'question_active'
                self.diarizer.start_new_question(segment)
            elif self.current_state == 'question_active':
                # Continue building the question
                self.question_buffer.append(transcript)
        
        # Check if question is complete and we should respond
        if self.diarizer.should_generate_response(segment):
            self.current_state = 'response_pending'
            complete_question = self.diarizer.get_complete_question()
            
            if complete_question:
                logger.info(f"🤖 Generating response for: {complete_question}")
                return complete_question
        
        return None

    def register_response_callback(self, callback):
        """Register a callback for when responses are ready."""
        self.response_callbacks.append(callback)

    def register_segment_callback(self, callback):
        """Register a callback that fires whenever a new segment is processed."""
        self.segment_callbacks.append(callback)
    
    def notify_response_generated(self, question: str, response: str):
        """Notify that a response has been generated."""
        for callback in self.response_callbacks:
            try:
                callback(question, response)
            except Exception as e:
                logger.error(f"Error in response callback: {e}")
        
        # Reset state for next question
        self.current_state = 'waiting'
        self.question_buffer = []
