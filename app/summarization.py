"""Summarization module.

This module provides real summarization capabilities using OpenAI's GPT models.
It can summarize meeting transcripts, extract action items, and answer questions
about the content.
"""
from __future__ import annotations

import logging
from typing import Dict, Any, List, Optional

from openai import OpenAI
from .config import Config

logger = logging.getLogger(__name__)


class SummarizationService:
    """Service for text summarization and Q&A using OpenAI GPT."""
    
    def __init__(self):
        if not Config.OPENAI_API_KEY:
            raise ValueError("OpenAI API key is required for summarization")
        self.client = OpenAI(api_key=Config.OPENAI_API_KEY)
    
    def generate_summary(self, text: str, summary_type: str = "meeting") -> str:
        """Generate a summary using GPT.
        
        Args:
            text: Text to summarize.
            summary_type: Type of summary (meeting, document, etc.)
            
        Returns:
            Generated summary.
        """
        prompt = self._get_summary_prompt(text, summary_type)
        
        try:
            response = self.client.chat.completions.create(
                model=Config.OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                temperature=0.3
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Summary generation failed: {str(e)}")
            return f"Summary generation failed: {str(e)}"
    
    def extract_action_items(self, text: str) -> List[str]:
        """Extract action items from text.
        
        Args:
            text: Text to analyze for action items.
            
        Returns:
            List of action items.
        """
        prompt = f"""
        Analyze the following meeting transcript and extract all action items.
        Return only a numbered list of clear, actionable tasks.
        
        Text:
        {text}
        
        Action Items:
        """
        
        try:
            response = self.client.chat.completions.create(
                model=Config.OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300,
                temperature=0.2
            )
            
            content = response.choices[0].message.content.strip()
            # Parse the numbered list into individual items
            action_items = []
            for line in content.split('\n'):
                line = line.strip()
                if line and (line[0].isdigit() or line.startswith('-') or line.startswith('•')):
                    # Remove numbering and bullet points
                    item = line.split('.', 1)[-1].strip() if '.' in line else line[1:].strip()
                    if item:
                        action_items.append(item)
            
            return action_items
            
        except Exception as e:
            logger.error(f"Action item extraction failed: {str(e)}")
            return [f"Action item extraction failed: {str(e)}"]
    
    def extract_decisions(self, text: str) -> List[str]:
        """Extract key decisions from text.
        
        Args:
            text: Text to analyze for decisions.
            
        Returns:
            List of decisions made.
        """
        prompt = f"""
        Analyze the following meeting transcript and extract all key decisions made.
        Return only a numbered list of clear decisions.
        
        Text:
        {text}
        
        Key Decisions:
        """
        
        try:
            response = self.client.chat.completions.create(
                model=Config.OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300,
                temperature=0.2
            )
            
            content = response.choices[0].message.content.strip()
            # Parse the numbered list into individual decisions
            decisions = []
            for line in content.split('\n'):
                line = line.strip()
                if line and (line[0].isdigit() or line.startswith('-') or line.startswith('•')):
                    # Remove numbering and bullet points
                    item = line.split('.', 1)[-1].strip() if '.' in line else line[1:].strip()
                    if item:
                        decisions.append(item)
            
            return decisions
            
        except Exception as e:
            logger.error(f"Decision extraction failed: {str(e)}")
            return [f"Decision extraction failed: {str(e)}"]
    
    def answer_question(self, question: str, context: str) -> str:
        """Answer a question based on provided context.
        
        Args:
            question: The question to answer.
            context: Context text to use for answering.
            
        Returns:
            Answer to the question.
        """
        prompt = f"""
        Based on the following context, answer the question as accurately as possible.
        If the answer cannot be found in the context, say "I cannot answer this question based on the provided context."
        
        Context:
        {context}
        
        Question: {question}
        
        Answer:
        """
        
        try:
            response = self.client.chat.completions.create(
                model=Config.OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0.1
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Question answering failed: {str(e)}")
            return f"Question answering failed: {str(e)}"
    
    def _get_summary_prompt(self, text: str, summary_type: str) -> str:
        """Get appropriate prompt for summary type."""
        if summary_type == "meeting":
            return f"""
            Summarize the following meeting transcript in a clear, structured format.
            Include:
            1. Main topics discussed
            2. Key points and decisions
            3. Action items (if any)
            4. Next steps (if mentioned)
            
            Keep the summary concise but comprehensive.
            
            Transcript:
            {text}
            
            Summary:
            """
        else:
            return f"""
            Provide a clear and concise summary of the following text:
            
            {text}
            
            Summary:
            """


def summarize_transcript(transcript: Dict[str, Any]) -> str:
    """Generate a summary from a meeting transcript.

    Args:
        transcript: A dictionary with a "text" field containing the full
            transcription and optionally a list of segments.

    Returns:
        A human-readable summary of the meeting.
    """
    logger.info("Summarizing transcript")
    
    text = transcript.get("text", "")
    if not text or text.strip() == "":
        return "No transcript text available to summarize."
    
    try:
        service = SummarizationService()
        summary = service.generate_summary(text, "meeting")
        logger.debug("Summary generated: %s", summary[:100] + "...")
        return summary
        
    except Exception as e:
        logger.error(f"Summarization failed: {str(e)}")
        return f"Summarization failed: {str(e)}"


def extract_action_items(transcript: Dict[str, Any]) -> List[str]:
    """Extract action items from a transcript.
    
    Args:
        transcript: Transcript dictionary.
        
    Returns:
        List of action items.
    """
    logger.info("Extracting action items from transcript")
    
    text = transcript.get("text", "")
    if not text:
        return ["No transcript text available for action item extraction."]
    
    try:
        service = SummarizationService()
        return service.extract_action_items(text)
        
    except Exception as e:
        logger.error(f"Action item extraction failed: {str(e)}")
        return [f"Action item extraction failed: {str(e)}"]


def extract_decisions(transcript: Dict[str, Any]) -> List[str]:
    """Extract key decisions from a transcript.
    
    Args:
        transcript: Transcript dictionary.
        
    Returns:
        List of key decisions.
    """
    logger.info("Extracting decisions from transcript")
    
    text = transcript.get("text", "")
    if not text:
        return ["No transcript text available for decision extraction."]
    
    try:
        service = SummarizationService()
        return service.extract_decisions(text)
        
    except Exception as e:
        logger.error(f"Decision extraction failed: {str(e)}")
        return [f"Decision extraction failed: {str(e)}"]


def answer_question(question: str, context: str) -> str:
    """Answer a question based on provided context (e.g. transcript).

    Args:
        question: The user's question.
        context: Relevant context to answer the question (e.g. transcript text,
            code documentation, knowledge base entries).

    Returns:
        An answer string.
    """
    logger.info("Answering question: %s", question)
    
    if not context or context.strip() == "":
        return "No context provided to answer the question."
    
    try:
        service = SummarizationService()
        answer = service.answer_question(question, context)
        logger.debug("Answer generated: %s", answer[:100] + "...")
        return answer
        
    except Exception as e:
        logger.error(f"Question answering failed: {str(e)}")
        return f"Question answering failed: {str(e)}"


def generate_meeting_report(transcript: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a comprehensive meeting report.
    
    Args:
        transcript: Transcript dictionary.
        
    Returns:
        Dictionary containing summary, action items, decisions, etc.
    """
    logger.info("Generating comprehensive meeting report")
    
    text = transcript.get("text", "")
    if not text:
        return {
            "summary": "No transcript available",
            "action_items": [],
            "decisions": [],
            "duration": transcript.get("duration", 0),
            "error": "No transcript text available"
        }
    
    try:
        service = SummarizationService()
        
        return {
            "summary": service.generate_summary(text, "meeting"),
            "action_items": service.extract_action_items(text),
            "decisions": service.extract_decisions(text),
            "duration": transcript.get("duration", 0),
            "language": transcript.get("language", "unknown"),
            "segments_count": len(transcript.get("segments", []))
        }
        
    except Exception as e:
        logger.error(f"Meeting report generation failed: {str(e)}")
        return {
            "summary": f"Report generation failed: {str(e)}",
            "action_items": [],
            "decisions": [],
            "duration": transcript.get("duration", 0),
            "error": str(e)
        }
