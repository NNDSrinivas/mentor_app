"""Configuration module for the AI Mentor Assistant.

This module handles environment variables and application settings.
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Application configuration."""
    
    # OpenAI API settings
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
    WHISPER_MODEL = os.getenv("WHISPER_MODEL", "whisper-1")
    
        # Privacy settings
    COMPANY_SAFE_MODE = os.getenv("COMPANY_SAFE_MODE", "true").lower() == "true"
    STORE_CODE_FILES = os.getenv("STORE_CODE_FILES", "false").lower() == "true"
    AUTO_DELETE_RECORDINGS = int(os.getenv("AUTO_DELETE_RECORDINGS", "7"))  # days
    
    # AI Assistant settings
    AI_INTERACTION_MODE = os.getenv("AI_INTERACTION_MODE", "private")  # private, public, silent
    AI_RESPONSE_DELAY = int(os.getenv("AI_RESPONSE_DELAY", "3"))  # seconds before responding
    CONVERSATION_MEMORY_DAYS = int(os.getenv("CONVERSATION_MEMORY_DAYS", "30"))  # days to keep conversations

    # Session mode determines default behaviors
    SESSION_MODE = os.getenv("SESSION_MODE", "general")  # general, interview
    PRIVATE_OVERLAY_MODE = os.getenv("PRIVATE_OVERLAY_MODE", "auto")  # on, off, auto

    @classmethod
    def use_private_overlay(cls) -> bool:
        """Return True if the private overlay should be active."""
        mode = cls.PRIVATE_OVERLAY_MODE.lower()
        if mode == "on":
            return True
        if mode == "off":
            return False
        return cls.SESSION_MODE == "interview"
    
    # Private overlay settings
    OVERLAY_AUTO_HIDE_SECONDS = int(os.getenv("OVERLAY_AUTO_HIDE_SECONDS", "15"))
    OVERLAY_POSITION = os.getenv("OVERLAY_POSITION", "bottom-right")  # bottom-right, top-right, etc.
    OVERLAY_OPACITY = float(os.getenv("OVERLAY_OPACITY", "0.9"))  # 0.0 to 1.0
    
    # Real-time processing settings
    AUDIO_CHUNK_DURATION = int(os.getenv("AUDIO_CHUNK_DURATION", "5"))  # seconds per chunk
    SCREEN_ANALYSIS_INTERVAL = int(os.getenv("SCREEN_ANALYSIS_INTERVAL", "30"))  # seconds
    AI_ASSISTANCE_THRESHOLD = float(os.getenv("AI_ASSISTANCE_THRESHOLD", "0.7"))  # confidence threshold
    
    # Audio recording settings
    SAMPLE_RATE = int(os.getenv("SAMPLE_RATE", "44100"))
    CHANNELS = int(os.getenv("CHANNELS", "1"))
    CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1024"))

    # Screen recording settings
    SCREEN_FPS = int(os.getenv("SCREEN_FPS", "10"))
    SCREEN_QUALITY = int(os.getenv("SCREEN_QUALITY", "80"))
    SCREEN_RECORDING_ENABLED = os.getenv("SCREEN_RECORDING_ENABLED", "false").lower() == "true"
    SCREEN_RECORDING_DURATION = int(os.getenv("SCREEN_RECORDING_DURATION", "10"))  # seconds
    
    # Knowledge base settings
    CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./data/chroma_db")
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-ada-002")
    
    # File storage settings
    RECORDINGS_DIR = os.getenv("RECORDINGS_DIR", "./data/recordings")
    TEMP_DIR = os.getenv("TEMP_DIR", "/tmp/mentor_app")
    
    @classmethod
    def validate(cls, require_api_key=True):
        """Validate required configuration."""
        if require_api_key and not cls.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        # Create directories if they don't exist
        os.makedirs(cls.RECORDINGS_DIR, exist_ok=True)
        os.makedirs(cls.TEMP_DIR, exist_ok=True)
        os.makedirs(cls.CHROMA_PERSIST_DIR, exist_ok=True)
    
    @classmethod
    def validate_for_local_ops(cls):
        """Validate configuration for local operations only."""
        cls.validate(require_api_key=False)
