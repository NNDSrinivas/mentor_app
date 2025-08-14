"""
Enhanced Meeting Intelligence System
Provides speaker identification, context extraction, and real-time assistance
"""

import json
import logging
import os
import sqlite3
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict

from app import screen_record
from app.config import Config
from backend.diarization_service import DiarizationService

logger = logging.getLogger(__name__)
try:
    from app.summarization import SummarizationService
except Exception as e:  # pragma: no cover - optional dependency
    SummarizationService = None  # type: ignore[assignment]
    logger.warning(f"Summarization service unavailable: {e}")

try:
    from backend.memory_service import MemoryService
except Exception as e:  # pragma: no cover - optional dependency
    MemoryService = None  # type: ignore[assignment]
    logger.warning(f"Memory service unavailable: {e}")

@dataclass
class Speaker:
    speaker_id: str
    name: Optional[str] = None
    role: Optional[str] = None  # "manager", "engineer", "product", etc.
    team: Optional[str] = None
    confidence: float = 0.0

@dataclass
class MeetingContext:
    meeting_id: str
    meeting_type: str  # "standup", "planning", "review", "interview", "1on1"
    project: Optional[str] = None
    team: Optional[str] = None
    participants: List[Speaker] = None
    agenda_items: List[str] = None
    action_items: List[str] = None
    decisions: List[str] = None
    
    def __post_init__(self):
        if self.participants is None:
            self.participants = []
        if self.agenda_items is None:
            self.agenda_items = []
        if self.action_items is None:
            self.action_items = []
        if self.decisions is None:
            self.decisions = []

class MeetingIntelligence:
    def __init__(self):
        self.active_meetings: Dict[str, MeetingContext] = {}
        self.speaker_patterns: Dict[str, Dict] = {}
        # DiarizationService knows how to map speaker labels to team members
        self.diarization = DiarizationService()
        try:
            self.summarizer = SummarizationService() if SummarizationService else None
        except Exception as e:  # pragma: no cover - optional dependency
            logger.warning(f"Failed to initialize summarization service: {e}")
            self.summarizer = None
        try:
            self.memory = MemoryService() if MemoryService else None
        except Exception as e:  # pragma: no cover - optional dependency
            logger.warning(f"Failed to initialize memory service: {e}")
            self.memory = None
        
    def start_meeting(self, meeting_id: str, participants: List[str] = None) -> MeetingContext:
        """Initialize a new meeting session with intelligence tracking"""
        context = MeetingContext(
            meeting_id=meeting_id,
            meeting_type="unknown",
            participants=[Speaker(speaker_id=p) for p in (participants or [])]
        )
        self.active_meetings[meeting_id] = context
        logger.info(f"Started intelligent meeting tracking for {meeting_id}")
        return context
    
    def process_caption(self, meeting_id: str, text: str, speaker_id: str = None, timestamp: datetime = None) -> Dict[str, Any]:
        """Process meeting caption with intelligence extraction"""
        if meeting_id not in self.active_meetings:
            self.start_meeting(meeting_id)

        context = self.active_meetings[meeting_id]

        # Map diarized speaker labels to known team members for friendly output
        if speaker_id:
            resolved = self.diarization.resolve_speaker(speaker_id)
            if resolved:
                speaker_id = resolved
                # Ensure participant list includes this speaker
                if not any(p.speaker_id == speaker_id for p in context.participants):
                    context.participants.append(Speaker(speaker_id=speaker_id, name=speaker_id))
        
        # Detect meeting type from content
        meeting_type = self._detect_meeting_type(text, context)
        if meeting_type != "unknown":
            context.meeting_type = meeting_type
        
        # Extract structured information
        analysis = {
            "questions_detected": self._detect_questions(text),
            "action_items": self._extract_action_items(text),
            "decisions": self._extract_decisions(text),
            "technical_topics": self._extract_technical_topics(text),
            "task_mentions": self._extract_task_mentions(text),
            "urgency_level": self._assess_urgency(text),
            "speaker_analysis": self._analyze_speaker_context(text, speaker_id)
        }
        
        # Update meeting context
        if analysis["action_items"]:
            context.action_items.extend(analysis["action_items"])
        if analysis["decisions"]:
            context.decisions.extend(analysis["decisions"])
            
        return analysis
    
    def _detect_meeting_type(self, text: str, context: MeetingContext) -> str:
        """Detect meeting type from content patterns"""
        text_lower = text.lower()
        
        # Standup indicators
        if any(phrase in text_lower for phrase in [
            "what did you work on", "what are you working on", "any blockers",
            "yesterday i", "today i will", "stand up", "daily standup"
        ]):
            return "standup"
        
        # Planning indicators  
        if any(phrase in text_lower for phrase in [
            "sprint planning", "story points", "planning poker", "user story",
            "acceptance criteria", "definition of done", "sprint goal"
        ]):
            return "planning"
        
        # Review indicators
        if any(phrase in text_lower for phrase in [
            "code review", "pull request", "merge request", "review comments",
            "feedback on", "looks good to me", "lgtm", "approve"
        ]):
            return "review"
        
        # Interview indicators
        if any(phrase in text_lower for phrase in [
            "tell me about yourself", "what's your experience", "coding challenge",
            "technical interview", "algorithm question", "system design"
        ]):
            return "interview"
        
        # 1-on-1 indicators
        if any(phrase in text_lower for phrase in [
            "one on one", "1:1", "career development", "performance review",
            "feedback session", "check in"
        ]):
            return "1on1"
            
        return context.meeting_type
    
    def _detect_questions(self, text: str) -> List[str]:
        """Detect questions that might need answers"""
        questions = []
        sentences = text.split('.')
        
        for sentence in sentences:
            sentence = sentence.strip()
            if any(sentence.lower().startswith(q) for q in [
                "what", "how", "why", "when", "where", "which", "who",
                "can you", "could you", "would you", "do you", "did you",
                "have you", "will you", "should we", "can we"
            ]) and sentence.endswith('?'):
                questions.append(sentence)
                
        return questions
    
    def _extract_action_items(self, text: str) -> List[str]:
        """Extract action items from meeting text"""
        action_items = []
        text_lower = text.lower()
        
        # Look for action item indicators
        action_indicators = [
            "action item", "todo", "follow up", "next step", "will do",
            "i'll take care of", "assigned to", "due by", "deadline"
        ]
        
        sentences = text.split('.')
        for sentence in sentences:
            if any(indicator in sentence.lower() for indicator in action_indicators):
                action_items.append(sentence.strip())
                
        return action_items
    
    def _extract_decisions(self, text: str) -> List[str]:
        """Extract decisions made in the meeting"""
        decisions = []
        
        decision_indicators = [
            "we decided", "let's go with", "agreed on", "conclusion",
            "final decision", "we'll use", "decided to"
        ]
        
        sentences = text.split('.')
        for sentence in sentences:
            if any(indicator in sentence.lower() for indicator in decision_indicators):
                decisions.append(sentence.strip())
                
        return decisions
    
    def _extract_technical_topics(self, text: str) -> List[str]:
        """Extract technical topics mentioned"""
        technical_keywords = [
            "api", "database", "microservice", "kubernetes", "docker", "aws",
            "react", "python", "javascript", "typescript", "sql", "nosql",
            "redis", "kafka", "elasticsearch", "jenkins", "git", "github",
            "deployment", "testing", "unit test", "integration test",
            "performance", "scalability", "architecture", "design pattern"
        ]
        
        topics = []
        text_lower = text.lower()
        for keyword in technical_keywords:
            if keyword in text_lower:
                topics.append(keyword)
                
        return list(set(topics))  # Remove duplicates
    
    def _extract_task_mentions(self, text: str) -> List[str]:
        """Extract task/ticket mentions (JIRA, GitHub issues, etc.)"""
        import re
        
        # Common patterns for task mentions
        patterns = [
            r'[A-Z]+-\d+',  # JIRA style: PROJ-123
            r'#\d+',        # GitHub style: #123
            r'ticket \d+',  # Generic ticket mentions
            r'issue \d+',   # Generic issue mentions
            r'task \d+'     # Generic task mentions
        ]
        
        mentions = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            mentions.extend(matches)
            
        return mentions
    
    def _assess_urgency(self, text: str) -> str:
        """Assess urgency level of the content"""
        text_lower = text.lower()
        
        high_urgency = ["urgent", "asap", "critical", "emergency", "blocker", "production down"]
        medium_urgency = ["soon", "priority", "important", "deadline"]
        
        if any(word in text_lower for word in high_urgency):
            return "high"
        elif any(word in text_lower for word in medium_urgency):
            return "medium"
        else:
            return "low"
    
    def _analyze_speaker_context(self, text: str, speaker_id: str) -> Dict[str, Any]:
        """Analyze speaker context and patterns"""
        if not speaker_id:
            return {}
        
        # Track speaker patterns
        if speaker_id not in self.speaker_patterns:
            self.speaker_patterns[speaker_id] = {
                "topics": [],
                "question_count": 0,
                "decision_count": 0,
                "role_indicators": []
            }
        
        patterns = self.speaker_patterns[speaker_id]
        
        # Update patterns
        patterns["topics"].extend(self._extract_technical_topics(text))
        patterns["question_count"] += len(self._detect_questions(text))
        patterns["decision_count"] += len(self._extract_decisions(text))
        
        # Detect role indicators
        if any(phrase in text.lower() for phrase in ["as a manager", "team lead", "engineering manager"]):
            patterns["role_indicators"].append("manager")
        elif any(phrase in text.lower() for phrase in ["product requirement", "user story", "product manager"]):
            patterns["role_indicators"].append("product_manager")
        elif any(phrase in text.lower() for phrase in ["scrum master", "facilitating", "sprint"]):
            patterns["role_indicators"].append("scrum_master")
        
        return {
            "speaker_id": speaker_id,
            "current_topics": self._extract_technical_topics(text),
            "estimated_role": self._estimate_role(patterns),
            "engagement_level": self._calculate_engagement(patterns)
        }
    
    def _estimate_role(self, patterns: Dict) -> str:
        """Estimate speaker role based on patterns"""
        if "manager" in patterns["role_indicators"]:
            return "manager"
        elif "product_manager" in patterns["role_indicators"]:
            return "product_manager"
        elif "scrum_master" in patterns["role_indicators"]:
            return "scrum_master"
        elif patterns["question_count"] > patterns["decision_count"] * 2:
            return "junior_engineer"
        elif patterns["decision_count"] > 3:
            return "senior_engineer"
        else:
            return "engineer"
    
    def _calculate_engagement(self, patterns: Dict) -> str:
        """Calculate speaker engagement level"""
        total_interactions = patterns["question_count"] + patterns["decision_count"]
        
        if total_interactions > 10:
            return "high"
        elif total_interactions > 3:
            return "medium"
        else:
            return "low"

    def _compose_meeting_text(self, context: MeetingContext) -> str:
        parts = [f"Meeting type: {context.meeting_type}"]
        if context.participants:
            parts.append("Participants: " + ", ".join(p.speaker_id for p in context.participants))
        if context.agenda_items:
            parts.append("Agenda Items:\n" + "\n".join(context.agenda_items))
        if context.action_items:
            parts.append("Action Items:\n" + "\n".join(context.action_items))
        if context.decisions:
            parts.append("Decisions:\n" + "\n".join(context.decisions))
        return "\n".join(parts)
    
    def get_meeting_summary(self, meeting_id: str) -> Dict[str, Any]:
        """Generate comprehensive meeting summary.

        Recording path lookup priority:
        1. Sessions table in the real-time database.
        2. ``screen_record.get_recording_path`` JSON metadata fallback.
        """
        if meeting_id not in self.active_meetings:
            return {"error": "Meeting not found"}

        context = self.active_meetings[meeting_id]

        # Resolve recording path with DB-first priority
        recording_path: Optional[str] = None
        try:
            db_path = os.getenv("REALTIME_DATABASE_PATH", "production_realtime.db")
            with sqlite3.connect(db_path) as conn:
                cursor = conn.execute(
                    "SELECT recording_path FROM sessions WHERE id = ?", (meeting_id,)
                )
                row = cursor.fetchone()
                if row and row[0]:
                    recording_path = row[0]
        except Exception as e:  # pragma: no cover - best effort
            logger.debug(f"Recording path lookup in DB failed: {e}")

        if not recording_path:
            try:
                recording_path = screen_record.get_recording_path(meeting_id)
            except Exception as e:  # pragma: no cover - optional dependency
                logger.debug(f"Recording path JSON lookup failed: {e}")
                recording_path = None

        if self.summarizer:
            meeting_text = self._compose_meeting_text(context)
            try:
                summary_text = self.summarizer.generate_summary(meeting_text, summary_type="meeting")
            except Exception as e:
                logger.warning(f"Summarization failed: {e}")
                summary_text = self._generate_ai_summary(context)
        else:
            summary_text = self._generate_ai_summary(context)

        if context.action_items:
            summary_text += "\n\nAction Items:\n" + "\n".join(context.action_items)
        if context.decisions:
            summary_text += "\n\nDecisions:\n" + "\n".join(context.decisions)

        if self.memory:
            try:
                self.memory.add_meeting_entry(
                    meeting_id,
                    summary_text,
                    {"action_items": context.action_items, "decisions": context.decisions},
                )
            except Exception as e:
                logger.warning(f"Failed to store meeting summary: {e}")

        return {
            "meeting_id": meeting_id,
            "meeting_type": context.meeting_type,
            "participants": [asdict(p) for p in context.participants],
            "action_items": context.action_items,
            "decisions": context.decisions,
            "agenda_items": context.agenda_items,
            "duration": "unknown",  # Would calculate from start/end times
            "key_topics": list(
                set(
                    [topic for patterns in self.speaker_patterns.values() for topic in patterns["topics"]]
                )
            ),
            "summary": summary_text,
            "recording_path": recording_path,
        }
    
    def _generate_ai_summary(self, context: MeetingContext) -> str:
        """Generate AI-powered meeting summary"""
        # This would integrate with your AI assistant to generate summaries
        summary_prompt = f"""
        Generate a concise meeting summary for a {context.meeting_type} meeting with:
        - {len(context.participants)} participants
        - {len(context.action_items)} action items
        - {len(context.decisions)} decisions made
        
        Action items: {context.action_items}
        Decisions: {context.decisions}
        """
        
        # For now, return a template - would call AI assistant here
        return f"This {context.meeting_type} meeting covered key decisions and generated {len(context.action_items)} action items."

# Singleton instance
meeting_intelligence = MeetingIntelligence()
