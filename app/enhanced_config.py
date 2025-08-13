"""
Configuration for enhanced AI SDLC Assistant features
"""
import os
from typing import Optional

class EnhancedConfig:
    # Existing configurations
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4')
    OPENAI_MAX_TOKENS = int(os.getenv('OPENAI_MAX_TOKENS', '2000'))
    
    # JIRA Integration
    JIRA_BASE_URL = os.getenv('JIRA_BASE_URL')  # e.g., 'https://yourcompany.atlassian.net'
    JIRA_USERNAME = os.getenv('JIRA_USERNAME')  # Your JIRA email
    JIRA_API_TOKEN = os.getenv('JIRA_API_TOKEN')  # JIRA API token
    
    # GitHub Integration  
    GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
    GITHUB_USERNAME = os.getenv('GITHUB_USERNAME')
    GITHUB_DEFAULT_REPO = os.getenv('GITHUB_DEFAULT_REPO')
    
    # Database Configuration
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///mentor_app.db')
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')
    
    # Meeting Recording
    ENABLE_RECORDING = os.getenv('ENABLE_RECORDING', 'false').lower() == 'true'
    RECORDING_STORAGE_PATH = os.getenv('RECORDING_STORAGE_PATH', './data/recordings')
    MAX_RECORDING_DURATION = int(os.getenv('MAX_RECORDING_DURATION', '7200'))  # 2 hours
    
    # Speaker Diarization
    ENABLE_SPEAKER_DIARIZATION = os.getenv('ENABLE_SPEAKER_DIARIZATION', 'false').lower() == 'true'
    DIARIZATION_MODEL = os.getenv('DIARIZATION_MODEL', 'pyannote/speaker-diarization')
    
    # Privacy and Security
    ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY')  # For encrypting sensitive data
    ENABLE_AUDIT_LOG = os.getenv('ENABLE_AUDIT_LOG', 'true').lower() == 'true'
    
    # Interview Mode
    INTERVIEW_MODE_STEALTH = os.getenv('INTERVIEW_MODE_STEALTH', 'true').lower() == 'true'
    INTERVIEW_ANSWER_DELAY = int(os.getenv('INTERVIEW_ANSWER_DELAY', '3'))  # seconds
    
    # Automated Development
    ENABLE_AUTO_CODING = os.getenv('ENABLE_AUTO_CODING', 'false').lower() == 'true'
    AUTO_COMMIT_ENABLED = os.getenv('AUTO_COMMIT_ENABLED', 'false').lower() == 'true'
    AUTO_PR_ENABLED = os.getenv('AUTO_PR_ENABLED', 'false').lower() == 'true'
    
    # IDE Integration
    VSCODE_WORKSPACE_PATH = os.getenv('VSCODE_WORKSPACE_PATH')
    INTELLIJ_PROJECT_PATH = os.getenv('INTELLIJ_PROJECT_PATH')
    
    # Memory and Context
    CONTEXT_RETENTION_DAYS = int(os.getenv('CONTEXT_RETENTION_DAYS', '30'))
    MAX_CONTEXT_SIZE = int(os.getenv('MAX_CONTEXT_SIZE', '10000'))  # tokens
    
    # Monetization
    ENABLE_BILLING = os.getenv('ENABLE_BILLING', 'false').lower() == 'true'
    STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY')
    STRIPE_PUBLISHABLE_KEY = os.getenv('STRIPE_PUBLISHABLE_KEY')
    
    # Team Features
    TEAM_MODE_ENABLED = os.getenv('TEAM_MODE_ENABLED', 'false').lower() == 'true'
    MAX_TEAM_SIZE = int(os.getenv('MAX_TEAM_SIZE', '10'))
    
    # Logging and Monitoring
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    ENABLE_METRICS = os.getenv('ENABLE_METRICS', 'false').lower() == 'true'
    
    @classmethod
    def is_jira_enabled(cls) -> bool:
        return bool(cls.JIRA_BASE_URL and cls.JIRA_USERNAME and cls.JIRA_API_TOKEN)
    
    @classmethod
    def is_github_enabled(cls) -> bool:
        return bool(cls.GITHUB_TOKEN and cls.GITHUB_USERNAME)
    
    @classmethod
    def is_recording_enabled(cls) -> bool:
        return cls.ENABLE_RECORDING
    
    @classmethod
    def is_production_mode(cls) -> bool:
        return os.getenv('ENVIRONMENT', 'development') == 'production'
