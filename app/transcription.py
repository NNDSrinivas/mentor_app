"""Speech-to-text transcription module.

This module provides real transcription functionality using OpenAI's Whisper API.
It can transcribe audio files and provide timestamps for segments.
"""
from __future__ import annotations

import logging
import os
from typing import List, Dict, Any, Optional

from openai import OpenAI
from .config import Config

logger = logging.getLogger(__name__)


class TranscriptionService:
    """Service for transcribing audio using OpenAI Whisper."""
    
    def __init__(self):
        if not Config.OPENAI_API_KEY:
            raise ValueError("OpenAI API key is required for transcription")
        self.client = OpenAI(api_key=Config.OPENAI_API_KEY)
    
    def transcribe_with_timestamps(self, audio_path: str) -> Dict[str, Any]:
        """Transcribe audio file with timestamps using Whisper API.
        
        Args:
            audio_path: Path to the audio file to transcribe.
            
        Returns:
            Dictionary containing transcription with timestamps.
        """
        try:
            with open(audio_path, "rb") as audio_file:
                # Use Whisper API with timestamps
                transcript = self.client.audio.transcriptions.create(
                    model=Config.WHISPER_MODEL,
                    file=audio_file,
                    response_format="verbose_json",
                    timestamp_granularities=["segment"]
                )
            
            # Format the response
            result = {
                "text": transcript.text,
                "language": getattr(transcript, 'language', 'unknown'),
                "duration": getattr(transcript, 'duration', 0),
                "segments": []
            }
            
            # Add segments if available
            if hasattr(transcript, 'segments') and transcript.segments:
                for segment in transcript.segments:
                    result["segments"].append({
                        "start": segment.start,
                        "end": segment.end,
                        "text": segment.text,
                        "confidence": getattr(segment, 'avg_logprob', 0)
                    })
            
            logger.info(f"Successfully transcribed {audio_path}")
            return result
            
        except Exception as e:
            logger.error(f"Transcription failed for {audio_path}: {str(e)}")
            # Return a fallback response
            return {
                "text": f"Transcription failed: {str(e)}",
                "language": "unknown",
                "duration": 0,
                "segments": [],
                "error": str(e)
            }
    
    def transcribe_simple(self, audio_path: str) -> str:
        """Simple transcription without timestamps.
        
        Args:
            audio_path: Path to the audio file to transcribe.
            
        Returns:
            Transcribed text.
        """
        try:
            with open(audio_path, "rb") as audio_file:
                transcript = self.client.audio.transcriptions.create(
                    model=Config.WHISPER_MODEL,
                    file=audio_file
                )
            return transcript.text
            
        except Exception as e:
            logger.error(f"Simple transcription failed for {audio_path}: {str(e)}")
            return f"Transcription failed: {str(e)}"


def transcribe_audio(audio_path: str) -> Dict[str, Any]:
    """Transcribe an audio file into text with timestamps.

    Args:
        audio_path: Path to the audio file to transcribe.

    Returns:
        A dictionary containing the transcription text and metadata
        such as timestamps and confidence scores.
    """
    logger.info("Transcribing audio at %s", audio_path)
    
    if not os.path.exists(audio_path):
        logger.error(f"Audio file not found: {audio_path}")
        return {
            "text": "Audio file not found",
            "segments": [],
            "error": "File not found"
        }
    
    # Check if file is empty
    if os.path.getsize(audio_path) == 0:
        logger.warning(f"Audio file is empty: {audio_path}")
        return {
            "text": "Empty audio file",
            "segments": [],
            "error": "Empty file"
        }
    
    try:
        service = TranscriptionService()
        result = service.transcribe_with_timestamps(audio_path)
        logger.debug("Transcript: %s", result.get("text", "")[:100] + "...")
        return result
        
    except Exception as e:
        logger.error(f"Transcription service failed: {str(e)}")
        return {
            "text": f"Transcription service failed: {str(e)}",
            "segments": [],
            "error": str(e)
        }


def transcribe_audio_simple(audio_path: str) -> str:
    """Simple transcription without timestamps.
    
    Args:
        audio_path: Path to the audio file to transcribe.
        
    Returns:
        Transcribed text.
    """
    logger.info("Simple transcription for %s", audio_path)
    
    if not os.path.exists(audio_path):
        return "Audio file not found"
    
    try:
        service = TranscriptionService()
        return service.transcribe_simple(audio_path)
        
    except Exception as e:
        logger.error(f"Simple transcription failed: {str(e)}")
        return f"Transcription failed: {str(e)}"


def extract_speakers(transcript: Dict[str, Any]) -> List[str]:
    """Extract unique speakers from transcript segments.
    
    Args:
        transcript: Transcript dictionary with segments.
        
    Returns:
        List of unique speaker identifiers.
    """
    speakers = set()
    
    for segment in transcript.get("segments", []):
        if "speaker" in segment:
            speakers.add(segment["speaker"])
    
    return list(speakers)


def search_transcript(transcript: Dict[str, Any], query: str) -> List[Dict[str, Any]]:
    """Search for specific text in transcript segments.
    
    Args:
        transcript: Transcript dictionary with segments.
        query: Text to search for.
        
    Returns:
        List of matching segments.
    """
    query_lower = query.lower()
    matching_segments = []
    
    for segment in transcript.get("segments", []):
        if query_lower in segment.get("text", "").lower():
            matching_segments.append(segment)
    
    return matching_segments
