"""Multi-language support for AI Mentor Assistant.

Supports transcription and AI responses in multiple languages including
Telugu, Hindi, English, and other languages.
"""

import logging
from typing import Dict, List, Optional
from openai import OpenAI

from .config import Config

logger = logging.getLogger(__name__)


class MultiLanguageProcessor:
    """Handles multi-language transcription and AI responses."""
    
    # Language mappings for Whisper API
    SUPPORTED_LANGUAGES = {
        'english': 'en',
        'hindi': 'hi', 
        'telugu': 'te',
        'tamil': 'ta',
        'kannada': 'kn',
        'malayalam': 'ml',
        'bengali': 'bn',
        'gujarati': 'gu',
        'marathi': 'mr',
        'punjabi': 'pa',
        'spanish': 'es',
        'french': 'fr',
        'german': 'de',
        'japanese': 'ja',
        'korean': 'ko',
        'chinese': 'zh'
    }
    
    def __init__(self):
        self.client = OpenAI(api_key=Config.OPENAI_API_KEY)
        self.default_language = 'english'
        self.user_languages = ['english', 'hindi', 'telugu']  # From config
    
    def transcribe_with_language_detection(self, audio_path: str) -> Dict:
        """Transcribe audio with automatic language detection."""
        try:
            with open(audio_path, "rb") as audio_file:
                # First, detect language
                transcript = self.client.audio.transcriptions.create(
                    model=Config.WHISPER_MODEL,
                    file=audio_file,
                    response_format="verbose_json"
                )
            
            detected_language = getattr(transcript, 'language', 'en')
            
            # Convert to our language names
            language_name = self.get_language_name(detected_language)
            
            result = {
                "text": transcript.text,
                "language": language_name,
                "language_code": detected_language,
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
                        "language": language_name
                    })
            
            logger.info(f"Transcribed in {language_name}: {transcript.text[:50]}...")
            return result
            
        except Exception as e:
            logger.error(f"Multi-language transcription failed: {e}")
            return {
                "text": f"Transcription failed: {str(e)}",
                "language": "unknown",
                "error": str(e)
            }
    
    def transcribe_specific_language(self, audio_path: str, language: str) -> Dict:
        """Transcribe audio in a specific language."""
        language_code = self.SUPPORTED_LANGUAGES.get(language.lower(), 'en')
        
        try:
            with open(audio_path, "rb") as audio_file:
                transcript = self.client.audio.transcriptions.create(
                    model=Config.WHISPER_MODEL,
                    file=audio_file,
                    language=language_code,
                    response_format="verbose_json"
                )
            
            return {
                "text": transcript.text,
                "language": language,
                "language_code": language_code,
                "duration": getattr(transcript, 'duration', 0),
                "forced_language": True
            }
            
        except Exception as e:
            logger.error(f"Language-specific transcription failed: {e}")
            return {
                "text": f"Transcription failed: {str(e)}",
                "language": language,
                "error": str(e)
            }
    
    def get_ai_response_multilingual(self, question: str, context: str, 
                                   response_language: Optional[str] = None) -> str:
        """Get AI response in specified language."""
        if not response_language:
            response_language = self.default_language
        
        # Language-specific prompts
        language_instructions = {
            'telugu': "దయచేసి తెలుగులో సమాధానం ఇవ్వండి",
            'hindi': "कृपया हिंदी में उत्तर दें", 
            'english': "Please respond in English",
            'tamil': "தயவுசெய்து தமிழில் பதிலளிக்கவும்",
            'kannada': "ದಯವಿಟ್ಟು ಕನ್ನಡದಲ್ಲಿ ಉತ್ತರಿಸಿ"
        }
        
        lang_instruction = language_instructions.get(
            response_language.lower(), 
            f"Please respond in {response_language}"
        )
        
        prompt = f"""
        {lang_instruction}. Based on the following context, answer the question.
        
        Context:
        {context}
        
        Question: {question}
        
        Answer:
        """
        
        try:
            response = self.client.chat.completions.create(
                model=Config.OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300,
                temperature=0.3
            )
            
            content = response.choices[0].message.content or ""
            return content.strip()
            
        except Exception as e:
            logger.error(f"Multi-lingual AI response failed: {e}")
            return f"AI response failed: {str(e)}"
    
    def translate_text(self, text: str, target_language: str) -> str:
        """Translate text to target language."""
        language_names = {
            'telugu': 'Telugu',
            'hindi': 'Hindi',
            'english': 'English',
            'tamil': 'Tamil',
            'kannada': 'Kannada'
        }
        
        target_lang_name = language_names.get(target_language.lower(), target_language)
        
        prompt = f"""
        Translate the following text to {target_lang_name}:
        
        {text}
        
        Translation:
        """
        
        try:
            response = self.client.chat.completions.create(
                model=Config.OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                temperature=0.1
            )
            
            content = response.choices[0].message.content or ""
            return content.strip()
            
        except Exception as e:
            logger.error(f"Translation failed: {e}")
            return f"Translation failed: {str(e)}"
    
    def summarize_multilingual(self, transcript: Dict, summary_language: Optional[str] = None) -> Dict:
        """Generate summary in specified language."""
        if not summary_language:
            summary_language = transcript.get('language', self.default_language)
        
        text = transcript.get('text', '')
        if not text:
            return {"error": "No text to summarize"}
        
        # Get summary in requested language
        summary = self.get_ai_response_multilingual(
            "Summarize this meeting transcript with key points and action items",
            text,
            summary_language
        )
        
        # Get action items in requested language
        action_items_text = self.get_ai_response_multilingual(
            "Extract all action items from this meeting",
            text,
            summary_language
        )
        
        return {
            "summary": summary,
            "action_items_text": action_items_text,
            "language": summary_language,
            "original_language": transcript.get('language', 'unknown')
        }
    
    def get_language_name(self, language_code: str) -> str:
        """Convert language code to language name."""
        code_to_name = {v: k for k, v in self.SUPPORTED_LANGUAGES.items()}
        return code_to_name.get(language_code, 'unknown')
    
    def detect_meeting_language(self, participants: List[str], 
                              meeting_context: str = "") -> str:
        """Detect likely meeting language from participants and context."""
        # Simple heuristic - could be improved with ML
        
        # Check for Indian names (likely Hindi/Telugu/regional languages)
        indian_indicators = ['sharma', 'patel', 'kumar', 'singh', 'reddy', 'rao', 'krishna']
        
        participant_text = " ".join(participants).lower()
        
        if any(indicator in participant_text for indicator in indian_indicators):
            if any(word in meeting_context.lower() for word in ['hyderabad', 'bangalore', 'telangana']):
                return 'telugu'
            else:
                return 'hindi'
        
        return 'english'


# Global processor instance
ml_processor = MultiLanguageProcessor()


def transcribe_multilingual(audio_path: str, language: Optional[str] = None) -> Dict:
    """Transcribe audio with multi-language support."""
    if language:
        return ml_processor.transcribe_specific_language(audio_path, language)
    else:
        return ml_processor.transcribe_with_language_detection(audio_path)


def get_multilingual_summary(transcript: Dict, language: Optional[str] = None) -> Dict:
    """Get meeting summary in specified language."""
    return ml_processor.summarize_multilingual(transcript, language)


def ask_question_multilingual(question: str, context: str, language: str = 'english') -> str:
    """Ask question and get response in specified language."""
    return ml_processor.get_ai_response_multilingual(question, context, language)
