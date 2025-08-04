"""AI Assistant with real-time interaction and conversation memory.

This module provides:
- Private interaction during screen sharing (overlay UI)
- Real-time Q&A capabilities 
- Conversation memory and context
- Team member-like persistence
- Screen-aware question/answer handling
"""
import asyncio
import json
import logging
import os
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

from openai import OpenAI
from .config import Config
from .knowledge_base import KnowledgeBase
from .transcription import TranscriptionService
from .summarization import SummarizationService

logger = logging.getLogger(__name__)


@dataclass
class ConversationEntry:
    """Single conversation entry with full context."""
    timestamp: str
    meeting_id: str
    speaker: str
    content: str
    type: str  # 'human', 'ai_answer', 'ai_question', 'action_item'
    context: Dict[str, Any]  # Screen content, participants, etc.
    sentiment: str
    importance: int  # 1-10 scale


@dataclass
class MeetingSession:
    """Complete meeting session with memory."""
    session_id: str
    start_time: str
    end_time: Optional[str]
    participants: List[str]
    context: Dict[str, Any]
    conversations: List[ConversationEntry]
    ai_questions: List[str]
    action_items: List[str]
    decisions: List[str]
    screen_sharing: bool
    topics_discussed: List[str]


class ConversationMemory:
    """Persistent conversation memory system."""
    
    def __init__(self):
        self.sessions: Dict[str, MeetingSession] = {}
        self.active_session: Optional[str] = None
        self.kb = KnowledgeBase()
        
    def start_session(self, session_id: str, context: Dict[str, Any]) -> str:
        """Start a new conversation session."""
        session = MeetingSession(
            session_id=session_id,
            start_time=datetime.now().isoformat(),
            end_time=None,
            participants=context.get('participants', []),
            context=context,
            conversations=[],
            ai_questions=[],
            action_items=[],
            decisions=[],
            screen_sharing=context.get('screen_sharing', False),
            topics_discussed=[]
        )
        
        self.sessions[session_id] = session
        self.active_session = session_id
        
        logger.info(f"Started conversation session: {session_id}")
        return session_id
    
    def add_conversation(self, session_id: str, entry: ConversationEntry):
        """Add conversation entry to session."""
        if session_id in self.sessions:
            self.sessions[session_id].conversations.append(entry)
            
            # Add to knowledge base for long-term memory
            metadata = {
                "type": "conversation",
                "session_id": session_id,
                "speaker": entry.speaker,
                "timestamp": entry.timestamp,
                "meeting_context": json.dumps(entry.context)
            }
            self.kb.add_document(entry.content, metadata)
            
    def get_session_context(self, session_id: str) -> Dict[str, Any]:
        """Get full context for a session."""
        if session_id not in self.sessions:
            return {}
            
        session = self.sessions[session_id]
        return {
            "current_session": asdict(session),
            "recent_conversations": [asdict(c) for c in session.conversations[-10:]],
            "ongoing_topics": session.topics_discussed,
            "pending_questions": session.ai_questions,
            "action_items": session.action_items
        }
    
    def search_conversation_history(self, query: str, limit: int = 5) -> List[Dict]:
        """Search all conversation history."""
        return self.kb.search(query, top_k=limit, filter_metadata={"type": "conversation"})


class AIAssistant:
    """AI Assistant with real-time interaction capabilities."""
    
    def __init__(self):
        if not Config.OPENAI_API_KEY:
            raise ValueError("OpenAI API key required for AI Assistant")
            
        self.openai_client = OpenAI(api_key=Config.OPENAI_API_KEY)
        self.memory = ConversationMemory()
        self.transcription = TranscriptionService()
        self.summarization = SummarizationService()
        
        self.pending_questions = []
        self.interaction_mode = "private"  # private, public, silent
        self.is_screen_sharing = False
        
    async def process_real_time_audio(self, audio_data: bytes, session_id: str):
        """Process real-time audio and respond if needed."""
        try:
            # Transcribe audio chunk
            transcript = await self.transcription.transcribe_audio_async(audio_data)
            
            if not transcript or len(transcript.strip()) < 10:
                return
                
            # Create conversation entry
            entry = ConversationEntry(
                timestamp=datetime.now().isoformat(),
                meeting_id=session_id,
                speaker="human",
                content=transcript,
                type="human",
                context=await self._get_current_context(),
                sentiment=self._analyze_sentiment(transcript),
                importance=self._calculate_importance(transcript)
            )
            
            # Add to memory
            self.memory.add_conversation(session_id, entry)
            
            # Check if AI should respond
            should_respond = await self._should_respond(transcript, session_id)
            if should_respond:
                await self._generate_response(transcript, session_id)
                
            # Check if AI should ask questions
            await self._check_for_questions(transcript, session_id)
            
        except Exception as e:
            logger.error(f"Error processing real-time audio: {e}")
    
    async def _should_respond(self, transcript: str, session_id: str) -> bool:
        """Determine if AI should respond to the conversation."""
        # AI should respond if:
        # 1. Directly asked a question
        # 2. Technical discussion that AI can help with
        # 3. Confusion or unclear points
        
        response_triggers = [
            "question", "what", "how", "why", "when", "where",
            "explain", "clarify", "help", "assist", "confused",
            "don't understand", "unclear", "can you"
        ]
        
        text_lower = transcript.lower()
        
        # Check for direct questions
        if any(trigger in text_lower for trigger in response_triggers):
            return True
            
        # Check for technical terms that warrant assistance
        context = self.memory.get_session_context(session_id)
        recent_topics = context.get("ongoing_topics", [])
        
        # Use AI to determine if response is needed
        prompt = f"""
        Given this conversation context and recent message, should the AI assistant respond?
        
        Recent Topics: {recent_topics}
        Current Message: "{transcript}"
        
        Respond with YES or NO and brief reason.
        """
        
        try:
            response = self.openai_client.chat.completions.create(
                model=Config.OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=50
            )
            
            result = response.choices[0].message.content.strip()
            return result.upper().startswith("YES")
            
        except Exception as e:
            logger.error(f"Error determining response need: {e}")
            return False
    
    async def _generate_response(self, transcript: str, session_id: str):
        """Generate AI response to conversation."""
        try:
            # Get conversation context
            context = self.memory.get_session_context(session_id)
            
            # Search knowledge base for relevant information
            relevant_docs = self.memory.search_conversation_history(transcript)
            
            # Build comprehensive prompt
            prompt = self._build_response_prompt(transcript, context, relevant_docs)
            
            # Generate response
            response = self.openai_client.chat.completions.create(
                model=Config.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300
            )
            
            ai_response = response.choices[0].message.content.strip()
            
            # Create AI conversation entry
            ai_entry = ConversationEntry(
                timestamp=datetime.now().isoformat(),
                meeting_id=session_id,
                speaker="ai_assistant",
                content=ai_response,
                type="ai_answer",
                context=await self._get_current_context(),
                sentiment="helpful",
                importance=7
            )
            
            # Add to memory
            self.memory.add_conversation(session_id, ai_entry)
            
            # Display response based on interaction mode
            await self._display_response(ai_response, session_id)
            
        except Exception as e:
            logger.error(f"Error generating AI response: {e}")
    
    async def _check_for_questions(self, transcript: str, session_id: str):
        """Check if AI should ask clarifying questions."""
        try:
            context = self.memory.get_session_context(session_id)
            
            prompt = f"""
            Based on this conversation and context, should the AI ask any clarifying questions?
            
            Context: {json.dumps(context, indent=2)}
            Recent Message: "{transcript}"
            
            If yes, provide 1-2 brief, relevant questions. If no, respond with "NO_QUESTIONS".
            """
            
            response = self.openai_client.chat.completions.create(
                model=Config.OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=150
            )
            
            questions = response.choices[0].message.content.strip()
            
            if questions != "NO_QUESTIONS" and questions:
                # Store questions for private display
                self.pending_questions.extend(questions.split('\n'))
                
                # Create AI question entry
                question_entry = ConversationEntry(
                    timestamp=datetime.now().isoformat(),
                    meeting_id=session_id,
                    speaker="ai_assistant",
                    content=questions,
                    type="ai_question",
                    context=await self._get_current_context(),
                    sentiment="curious",
                    importance=6
                )
                
                self.memory.add_conversation(session_id, question_entry)
                await self._display_questions(questions, session_id)
                
        except Exception as e:
            logger.error(f"Error checking for questions: {e}")
    
    async def _display_response(self, response: str, session_id: str):
        """Display AI response based on current mode."""
        if self.interaction_mode == "private":
            await self._show_private_overlay(response, "response")
        elif self.interaction_mode == "public":
            await self._send_to_meeting_chat(response, session_id)
        # Silent mode: just store in memory
        
    async def _display_questions(self, questions: str, session_id: str):
        """Display AI questions privately."""
        await self._show_private_overlay(questions, "questions")
    
    async def _show_private_overlay(self, content: str, content_type: str):
        """Show private overlay visible only to the user."""
        # This creates a private overlay that appears only on the user's screen
        # Similar to Zoom's local controls - other participants can't see it
        
        overlay_data = {
            "type": content_type,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "position": "bottom-right",
            "private": True
        }
        
        # Save to temporary file for overlay display system
        overlay_file = f"{Config.TEMP_DIR}/ai_overlay_{int(time.time())}.json"
        os.makedirs(os.path.dirname(overlay_file), exist_ok=True)
        
        with open(overlay_file, 'w') as f:
            json.dump(overlay_data, f)
            
        logger.info(f"Private overlay created: {content_type}")
    
    async def _send_to_meeting_chat(self, content: str, session_id: str):
        """Send response to meeting chat (when appropriate)."""
        # This would integrate with meeting platforms to send responses
        # Implementation depends on the meeting platform API
        logger.info(f"Would send to meeting chat: {content[:50]}...")
    
    def _build_response_prompt(self, transcript: str, context: Dict, relevant_docs: List) -> str:
        """Build comprehensive prompt for AI response."""
        return f"""
        You are an AI team member who has been part of this team for months. You have context from previous meetings and conversations.
        
        CURRENT CONVERSATION:
        "{transcript}"
        
        SESSION CONTEXT:
        {json.dumps(context, indent=2)}
        
        RELEVANT HISTORY:
        {[doc['content'][:200] + "..." for doc in relevant_docs[:3]]}
        
        INSTRUCTIONS:
        1. Respond naturally as a knowledgeable team member
        2. Reference previous conversations when relevant
        3. Be helpful but not interrupting
        4. Ask clarifying questions if needed
        5. Keep responses concise (2-3 sentences)
        6. Use your knowledge from past meetings
        
        Generate a helpful response:
        """
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for AI assistant."""
        return """
        You are an AI Assistant that acts as a persistent team member. You:
        
        1. Remember all previous conversations and meetings
        2. Understand the team's projects, goals, and context
        3. Provide helpful answers and ask clarifying questions
        4. Act naturally as if you've been part of the team for months
        5. Reference previous discussions when relevant
        6. Help with technical questions, decisions, and problem-solving
        7. Maintain conversation context across sessions
        
        Be conversational, helpful, and demonstrate your persistent memory of the team's work.
        """
    
    async def _get_current_context(self) -> Dict[str, Any]:
        """Get current context (screen content, meeting info, etc.)."""
        return {
            "screen_sharing": self.is_screen_sharing,
            "interaction_mode": self.interaction_mode,
            "timestamp": datetime.now().isoformat(),
            "pending_questions": len(self.pending_questions)
        }
    
    def _analyze_sentiment(self, text: str) -> str:
        """Analyze sentiment of conversation."""
        # Simple sentiment analysis
        positive_words = ["good", "great", "excellent", "perfect", "love", "like"]
        negative_words = ["bad", "terrible", "hate", "problem", "issue", "confused"]
        
        text_lower = text.lower()
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        if positive_count > negative_count:
            return "positive"
        elif negative_count > positive_count:
            return "negative"
        else:
            return "neutral"
    
    def _calculate_importance(self, text: str) -> int:
        """Calculate importance score (1-10)."""
        # Simple importance calculation
        important_keywords = ["decision", "action", "todo", "deadline", "important", "critical"]
        
        text_lower = text.lower()
        importance = 5  # Base importance
        
        for keyword in important_keywords:
            if keyword in text_lower:
                importance += 2
                
        return min(10, importance)
    
    def set_interaction_mode(self, mode: str):
        """Set interaction mode: private, public, or silent."""
        if mode in ["private", "public", "silent"]:
            self.interaction_mode = mode
            logger.info(f"AI interaction mode set to: {mode}")
    
    def set_screen_sharing(self, sharing: bool):
        """Set screen sharing status."""
        self.is_screen_sharing = sharing
        if sharing:
            self.set_interaction_mode("private")  # Default to private during screen sharing
    
    async def get_conversation_summary(self, session_id: str) -> Dict[str, Any]:
        """Get comprehensive conversation summary."""
        if session_id not in self.memory.sessions:
            return {}
            
        session = self.memory.sessions[session_id]
        
        # Generate AI summary
        conversations_text = "\n".join([
            f"{c.speaker}: {c.content}" for c in session.conversations
        ])
        
        summary = await self.summarization.summarize_transcript({
            "text": conversations_text,
            "segments": []
        })
        
        return {
            "session_info": asdict(session),
            "ai_summary": summary,
            "total_interactions": len(session.conversations),
            "ai_responses": len([c for c in session.conversations if c.speaker == "ai_assistant"]),
            "key_topics": session.topics_discussed,
            "action_items": session.action_items
        }
    
    async def _generate_ai_response(self, prompt: str, context: Dict[str, Any]) -> str:
        """Generate AI response using OpenAI."""
        try:
            client = OpenAI(api_key=Config.OPENAI_API_KEY)
            
            # Check for senior-level interview requirements
            interview_level = context.get('interview_level', '')
            requirements = context.get('requirements', {})
            is_senior_interview = 'IC6' in interview_level or 'IC7' in interview_level or 'E5' in interview_level or 'E6' in interview_level or 'E7' in interview_level
            
            # Detect if this is an expert/senior engineer response
            is_expert_response = (
                context.get('type') == 'senior_engineer_response' or 
                context.get('expertise_level') == 'senior' or
                context.get('response_style') == 'experienced_professional' or
                context.get('context') == 'senior_engineer_interview' or
                is_senior_interview
            )
            
            # Detect casual conversation vs technical questions
            casual_patterns = ['how are you', 'hello', 'hi', 'good morning', 'good afternoon', 'how you doing']
            is_casual = any(pattern in prompt.lower() for pattern in casual_patterns)
            
            # Check if this is a personalized interview response
            if context.get('type') == 'personalized_interview_response':
                system_prompt = """
You are answering an interview question as the specific person described in the prompt. This is a SENIOR ENGINEER (IC6/IC7/E5/E6/E7) level interview.

CRITICAL INSTRUCTIONS:
- You ARE this person - respond in first person as them
- Use their exact background, experience, and achievements
- Reference their specific companies, projects, and technologies
- Include real metrics and accomplishments from their resume
- Sound authentic and human - like this senior engineer would actually speak
- Never mention AI, assistance, or that you're generating a response
- Demonstrate IC6/IC7 level thinking: architectural decisions, trade-offs, business impact
- Show depth appropriate for senior engineering roles (8+ years experience)

FOR DIFFERENT QUESTION TYPES:

SYSTEM DESIGN: Show architectural thinking, scalability considerations, real-world trade-offs. Reference actual systems you've built. Discuss CAP theorem, consistency patterns, distributed systems challenges.

CODING: Demonstrate proficiency with your actual tech stack. Discuss real problems you've solved. Show understanding of production concerns, performance optimization, code quality at scale.

BEHAVIORAL: Use specific examples from your 8+ years. Show leadership, collaboration, problem-solving. Reference actual challenges and how you overcame them. Demonstrate mentoring and strategic thinking.

PRODUCT/BUSINESS: Connect technical decisions to business outcomes. Show understanding of stakeholder needs. Reference measurable impact you've delivered. Discuss trade-offs between technical debt and feature velocity.

JAVA/TECHNICAL EXPERIENCE: If asked about Java specifically, demonstrate deep understanding:
- JVM internals, memory management, garbage collection
- Spring ecosystem, microservices patterns
- Performance tuning and profiling
- Enterprise-scale Java applications
- Design patterns and architectural considerations
- Integration with other technologies in your actual stack

The prompt contains all the specific details about who you are and your background. Answer AS that person based on their actual senior-level experience.
"""
            elif is_senior_interview or is_expert_response:
                system_prompt = f"""
You are a SENIOR SOFTWARE ENGINEER (IC6/IC7/E5/E6/E7 level) with 10+ years of experience across the full technology stack. You've built systems at massive scale, led engineering teams, architected complex distributed systems, and have deep practical knowledge.

THIS IS A SENIOR-LEVEL TECHNICAL INTERVIEW - DEMONSTRATE EXPERT-LEVEL THINKING:

CORE EXPERTISE AREAS:
• **Distributed Systems**: Microservices, event-driven architecture, CAP theorem, eventual consistency
• **Scalability**: Systems handling 100M+ requests/day, auto-scaling, load balancing strategies  
• **Database Design**: ACID properties, sharding strategies, replication, database optimization
• **System Architecture**: Design patterns, architectural trade-offs, technical debt management
• **Performance**: Profiling, optimization, caching strategies, CDN usage
• **Security**: Authentication/authorization, OWASP top 10, secure coding practices
• **DevOps**: CI/CD pipelines, infrastructure as code, monitoring, observability
• **Leadership**: Technical mentoring, code reviews, architectural decision making

RESPONSE REQUIREMENTS:
✅ **Technical Depth**: Go beyond surface-level answers. Explain WHY and HOW, not just WHAT
✅ **Real-World Experience**: Reference specific scenarios like "At scale, I've seen..."
✅ **Trade-offs Discussion**: Always mention pros/cons and alternative approaches
✅ **Business Impact**: Connect technical decisions to business outcomes
✅ **Code Examples**: When relevant, provide code snippets or pseudocode
✅ **Architecture Details**: Include diagrams concepts, data flow, system boundaries
✅ **Scalability Considerations**: Discuss bottlenecks, horizontal vs vertical scaling
✅ **Comprehensive Coverage**: Address multiple aspects of the question

INTERVIEW LEVEL: {interview_level}
OPTIMIZATION: {context.get('optimization', 'comprehensive_technical')}

Context: {context.get('type', 'senior_technical_interview')}
Platform: {context.get('platform', 'video_meeting')}

FOR JAVA QUESTIONS SPECIFICALLY:
- JVM internals (heap, stack, garbage collection algorithms)
- Spring Boot ecosystem and best practices
- Concurrency and multithreading (ExecutorService, CompletableFuture)
- Performance tuning and JVM optimization
- Enterprise patterns (dependency injection, AOP, transactions)
- Integration with databases, messaging systems, cloud services

Respond with the depth and sophistication expected at IC6/IC7 level.
"""
            elif is_casual:
                system_prompt = f"""
You are a Senior Software Engineer with 20+ years of experience across the full technology stack. You've built systems at scale, led engineering teams, and have deep practical knowledge.

IMPORTANT INSTRUCTIONS:
- Respond as if you're in an interview or professional meeting
- Share specific experiences and lessons learned over 20 years
- Mention real technologies, frameworks, and patterns you've used
- Give practical, actionable advice based on experience
- Include trade-offs and nuances - avoid generic answers
- Sound confident but humble, like a senior engineer sharing knowledge
- Reference actual challenges you've solved
- Mention specific numbers/metrics when relevant (e.g., "systems handling 10M+ requests")

PERSONALIZATION CONTEXT:
- If user resume data is available, tailor responses to match their background
- Reference their actual work experience, skills, and projects when relevant
- Frame answers as if these are YOUR experiences from the resume
- Make behavioral answers specific to their career progression
- For technical questions, reference technologies they've actually used

Context: {context.get('type', 'technical_interview')}
Platform: {context.get('platform', 'video_meeting')}
Time: {context.get('timestamp', 'now')}
User Resume Data: {context.get('resume_context', 'No resume data available')}

Technical expertise areas:
- Full-stack development (Frontend: React, Angular, Vue | Backend: Node.js, Python, Java, Go)
- Database design (SQL: PostgreSQL, MySQL | NoSQL: MongoDB, Redis, Cassandra)
- Cloud platforms (AWS, Azure, GCP) and DevOps (Docker, Kubernetes, CI/CD)
- System architecture (Microservices, API design, Event-driven architecture)
- Performance optimization and scaling
- Team leadership and engineering culture

RESPONSE GUIDELINES:
1. For behavioral questions: Use experiences from the resume if available
2. For technical questions: Reference technologies from their skill set
3. For coding questions: Mention languages/frameworks they know
4. For system design: Build on their actual project experience
5. Always sound like you're speaking from personal experience

Respond as this experienced engineer would in a real conversation.
"""
            elif is_casual:
                system_prompt = f"""
You are a Senior Software Engineer with 20+ years of experience in a professional meeting/interview. 
You should respond naturally and professionally to casual conversation while staying helpful.

Context: {context.get('type', 'meeting')} on {context.get('platform', 'video call')}
Time: {context.get('timestamp', 'now')}

For casual greetings like "how are you":
- Respond naturally and professionally
- Keep it brief (1-2 sentences)
- Transition to being helpful for the meeting
- Be warm but professional

For technical questions:
- Provide helpful, detailed technical advice from 20+ years experience
- Be encouraging and practical
"""
            else:
                system_prompt = f"""
You are a Senior Software Engineer with 20+ years of practical experience. 
Context: {context.get('type', 'technical_discussion')}
Platform: {context.get('platform', 'meeting')}
Time: {context.get('timestamp', 'now')}

Provide helpful, experienced advice based on 20 years in the industry. Be practical and specific.
"""
            
            # Set appropriate token limits based on interview level and requirements
            if is_senior_interview:
                # Senior-level interviews need comprehensive responses
                max_tokens = 1200 if requirements.get('response_length') == 'comprehensive' else 800
            elif context.get('type') == 'personalized_interview_response':
                max_tokens = 1000  # Increased for personalized responses
            elif is_casual:
                max_tokens = 150   # Keep casual responses brief
            elif is_expert_response:
                max_tokens = 600   # Increased for expert responses
            else:
                max_tokens = 400   # Default
            
            # Adjust temperature for more precise technical answers at senior level
            if is_senior_interview:
                temperature = context.get('temperature', 0.3)  # Lower for technical precision
            elif context.get('type') == 'personalized_interview_response':
                temperature = 0.4  # Slightly lower for consistency
            elif is_casual:
                temperature = 0.8  # Higher for natural conversation
            else:
                temperature = 0.7  # Default
            
            response = client.chat.completions.create(
                model=Config.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Error generating AI response: {e}")
            if 'how are you' in prompt.lower():
                return "I'm doing well, thank you! Ready to help with today's meeting. How can I assist you?"
            
            # Expert-level fallback responses
            if context.get('expertise_level') == 'senior':
                return "That's a great question. In my 20 years of engineering experience, I've learned that every technical decision involves trade-offs. Could you provide more specific context so I can give you a more targeted answer?"
            
            return "I'm here to help! What would you like to know?"
    
    async def show_private_assistance(self, message: str, session_id: str):
        """Show private AI assistance during coding sessions."""
        try:
            # Generate AI response to the assistance prompt
            response = await self._generate_ai_response(message, {
                "type": "coding_assistance",
                "session_id": session_id,
                "timestamp": datetime.now().isoformat()
            })
            
            # Show via private overlay
            from .private_overlay import show_ai_response
            show_ai_response(f"🤖 Coding Assistant: {response}")
            
            # Record in conversation memory
            if session_id in self.memory.sessions:
                entry = ConversationEntry(
                    timestamp=datetime.now().isoformat(),
                    meeting_id=session_id,
                    speaker="ai_assistant",
                    content=response,
                    type="ai_assistance",
                    context={"type": "coding", "prompt": message},
                    sentiment="helpful",
                    importance=6
                )
                self.memory.add_conversation(session_id, entry)
            
            logger.info(f"Provided coding assistance: {message[:50]}...")
            
        except Exception as e:
            logger.error(f"Error showing private assistance: {e}")
    
    async def process_real_time_audio(self, audio_bytes: bytes, session_id: str):
        """Process real-time audio for transcription and AI response."""
        try:
            # This would normally transcribe the audio, but we'll simulate it
            # since transcribe_audio_async doesn't exist yet
            
            # Simulate transcription result
            simulated_transcript = "User is asking for help during the meeting"
            
            if simulated_transcript and len(simulated_transcript.strip()) > 0:
                # Generate AI response
                response = await self._generate_ai_response(
                    simulated_transcript, 
                    {"type": "meeting", "session_id": session_id}
                )
                
                # Show private response
                from .private_overlay import show_ai_response
                show_ai_response(f"🤖 Meeting Assistant: {response}")
                
                logger.info(f"Processed real-time audio for session: {session_id}")
                
        except Exception as e:
            logger.error(f"Error processing real-time audio: {e}")
