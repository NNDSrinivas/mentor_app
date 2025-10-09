"""
Production Real-time Session Service for AI Mentor
Handles live interview sessions, caption processing, and real-time AI responses
Port 8080 - Complements the Q&A service on port 8084
"""
import os
import sqlite3
import json
import jwt
import uuid
import time
import threading
import queue
from datetime import datetime, timedelta
from functools import wraps
from typing import Dict, List, Optional
from contextlib import contextmanager
from types import ModuleType, SimpleNamespace

from flask_compat import Flask, CORS, Response, g, jsonify, request

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:  # pragma: no cover - optional dependency in tests
    def load_dotenv(*_args, **_kwargs):
        """Fallback no-op when python-dotenv is unavailable."""

        return False

    if "dotenv" not in sys.modules:
        dotenv_stub = ModuleType("dotenv")
        dotenv_stub.load_dotenv = load_dotenv  # type: ignore[attr-defined]
        sys.modules["dotenv"] = dotenv_stub

try:
    from openai import OpenAI
except ModuleNotFoundError:  # pragma: no cover - optional dependency in tests
    class OpenAI:
        """Lightweight stub matching the minimal interface used in tests."""

        def __init__(self, *_, **__):
            self.chat = SimpleNamespace(
                completions=SimpleNamespace(create=self._missing_dependency)
            )

        def _missing_dependency(self, *args, **kwargs):
            raise RuntimeError("OpenAI dependency is not available")

from app import screen_record
from app.config import Config
from backend.meeting_events import MeetingEventRouter
try:
    from backend.db.base import session_scope
    from backend.db.utils import ensure_schema
    from backend.meeting_repository import add_transcript_segment, ensure_meeting
    DB_SUPPORT_AVAILABLE = True
except Exception as e:  # pragma: no cover - optional dependency
    print(f"Database integrations not available: {e}")
    DB_SUPPORT_AVAILABLE = False

    @contextmanager
    def session_scope(*_args, **_kwargs):
        yield SimpleNamespace()

    def ensure_schema(*_args, **_kwargs):
        return None

    def add_transcript_segment(*_args, **_kwargs):
        return None

    def ensure_meeting(*_args, **_kwargs):
        return None

# Import knowledge base functionality
try:
    from app.knowledge_base import KnowledgeBase, query_knowledge_base
    KNOWLEDGE_BASE_AVAILABLE = True
except ImportError as e:
    print(f"Knowledge base not available: {e}")
    KNOWLEDGE_BASE_AVAILABLE = False

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# Configuration
app.config['SECRET_KEY'] = os.getenv('JWT_SECRET', 'your-secret-key-change-this')
app.config['DATABASE'] = os.getenv('REALTIME_DATABASE_PATH', 'production_realtime.db')

# OpenAI Configuration
openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Knowledge Base Configuration
knowledge_base = None
if KNOWLEDGE_BASE_AVAILABLE:
    try:
        knowledge_base = KnowledgeBase()
        print(f"✅ Knowledge Base initialized: {knowledge_base.get_collection_info()}")
    except Exception as e:
        print(f"⚠️ Knowledge Base initialization failed: {e}")
        knowledge_base = None
else:
    print("⚠️ Knowledge Base not available - responses will use conversation context only")

# Optional advanced services
ENABLE_SPEAKER_DIARIZATION = os.getenv('ENABLE_SPEAKER_DIARIZATION', 'false').lower() == 'true'
ENABLE_MEMORY_SERVICE = os.getenv('ENABLE_MEMORY_SERVICE', 'false').lower() == 'true'

diarization_service = None
if ENABLE_SPEAKER_DIARIZATION:
    try:
        from backend.diarization_service import DiarizationService
        diarization_service = DiarizationService()
    except Exception as e:  # pragma: no cover - service optional
        print(f"⚠️ Diarization service not available: {e}")

memory_service = None
if ENABLE_MEMORY_SERVICE:
    try:
        from backend.memory_service import MemoryService
        memory_service = MemoryService()
    except Exception as e:  # pragma: no cover - service optional
        print(f"⚠️ Memory service not available: {e}")

# Session storage for real-time events
active_sessions: Dict[str, dict] = {}
session_queues: Dict[str, queue.Queue] = {}
session_recordings: Dict[str, Optional[str]] = {}
meeting_event_router = MeetingEventRouter()

ensure_schema()


class SessionStore:
    """Shared session store backed by SQLite for participant metadata"""

    def __init__(self, db_path: str):
        self.db_path = db_path

    def add_participant(self, session_id: str, user_id: int) -> None:
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            """
            INSERT OR REPLACE INTO session_participants (session_id, user_id, joined_at, left_at)
            VALUES (?, ?, CURRENT_TIMESTAMP, NULL)
            """,
            (session_id, user_id),
        )
        conn.commit()
        conn.close()

    def remove_participant(self, session_id: str, user_id: int) -> None:
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            """
            UPDATE session_participants
            SET left_at = CURRENT_TIMESTAMP
            WHERE session_id = ? AND user_id = ? AND left_at IS NULL
            """,
            (session_id, user_id),
        )
        conn.commit()
        conn.close()

    def get_participants(self, session_id: str) -> List[int]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            """
            SELECT user_id FROM session_participants
            WHERE session_id = ? AND left_at IS NULL
            """,
            (session_id,),
        )
        participants = [row[0] for row in cursor.fetchall()]
        conn.close()
        return participants


session_store = SessionStore(app.config['DATABASE'])

def init_db():
    """Initialize the database with required tables"""
    conn = sqlite3.connect(app.config['DATABASE'])
    cursor = conn.cursor()
    
    # Sessions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            user_level TEXT DEFAULT 'IC5',
            meeting_type TEXT DEFAULT 'technical_interview',
            project_context TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ended_at TIMESTAMP NULL,
            is_active BOOLEAN DEFAULT 1,
            metadata TEXT
        )
    ''')
    
    # Captions table for live meeting data
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS captions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            text TEXT NOT NULL,
            speaker TEXT DEFAULT 'unknown',
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_question BOOLEAN DEFAULT 0,
            confidence REAL DEFAULT 1.0,
            FOREIGN KEY (session_id) REFERENCES sessions (id)
        )
    ''')
    
    # AI Responses table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ai_responses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            question_text TEXT NOT NULL,
            answer_text TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            response_time_ms INTEGER,
            tokens_used INTEGER,
            FOREIGN KEY (session_id) REFERENCES sessions (id)
        )
    ''')
    
    # Conversation Memory table for enhanced context tracking
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversation_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            interaction_type TEXT NOT NULL,  -- 'question', 'answer', 'context'
            content TEXT NOT NULL,
            speaker TEXT,
            metadata TEXT,  -- JSON string for additional context
            importance_score REAL DEFAULT 1.0,  -- For prioritizing important interactions
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES sessions (id)
        )
    ''')

    # Session participants for tracking joins/leaves
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS session_participants (
            session_id TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            left_at TIMESTAMP NULL,
            PRIMARY KEY (session_id, user_id)
        )
    ''')
    
    conn.commit()
    conn.close()

def get_db():
    """Get database connection"""
    if 'db' not in g:
        g.db = sqlite3.connect(app.config['DATABASE'])
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(error=None):
    """Close database connection"""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def verify_token(token):
    """Verify JWT token and return user data"""
    try:
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def require_auth(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': 'No token provided'}), 401
        
        if token.startswith('Bearer '):
            token = token[7:]
        
        user_data = verify_token(token)
        if not user_data:
            return jsonify({'error': 'Invalid or expired token'}), 401
        
        g.current_user = user_data
        return f(*args, **kwargs)
    
    return decorated

def token_required(f):
    """Decorator to require authentication with user_id in g"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': 'No token provided'}), 401
        
        if token.startswith('Bearer '):
            token = token[7:]
        
        user_data = verify_token(token)
        if not user_data:
            return jsonify({'error': 'Invalid or expired token'}), 401
        
        g.user_id = user_data.get('user_id')
        g.current_user = user_data
        return f(*args, **kwargs)
    
    return decorated

def detect_question(text: str) -> dict:
    """Advanced question detection with categorization and confidence scoring"""
    text_clean = text.strip().lower()
    
    # Question type patterns
    technical_patterns = [
        'implement', 'algorithm', 'complexity', 'optimize', 'architecture', 'design pattern',
        'data structure', 'big o', 'time complexity', 'space complexity', 'scale', 'database',
        'system design', 'api', 'microservices', 'distributed', 'concurrency', 'threading',
        'sql', 'nosql', 'cache', 'load balancing', 'security', 'performance', 'code review',
        'debugging', 'testing', 'deployment', 'ci/cd', 'framework', 'library', 'version control',
        'hash table', 'binary tree', 'linked list', 'array', 'sorting', 'searching',
        'recursion', 'dynamic programming', 'graph', 'tree traversal', 'heap', 'stack', 'queue'
    ]
    
    behavioral_patterns = [
        'tell me about a time', 'describe a situation', 'give me an example',
        'how do you handle', 'what would you do', 'conflict', 'team', 'leadership',
        'challenge', 'mistake', 'failure', 'success', 'achievement', 'deadline',
        'priority', 'decision', 'feedback', 'communication', 'collaboration',
        'mentor', 'learning', 'growth', 'career', 'motivation', 'weakness', 'strength',
        'tell me about', 'give an example', 'describe how you', 'walk me through a time',
        'overcome', 'difficult', 'worked with', 'managed to', 'handled a'
    ]
    
    clarification_patterns = [
        'what do you mean', 'can you clarify', 'could you explain', 'i don\'t understand',
        'could you repeat', 'what exactly', 'be more specific', 'elaborate on',
        'what are you looking for', 'what should i focus on', 'any particular',
        'clarify what', 'mean by', 'looking for in', 'more detail', 'expand on'
    ]
    
    follow_up_patterns = [
        'anything else', 'what about', 'also', 'furthermore', 'additionally',
        'follow up', 'next question', 'building on that', 'related to that',
        'speaking of', 'that reminds me', 'on a similar note'
    ]
    
    # Basic question indicators
    basic_indicators = [
        'what', 'how', 'why', 'when', 'where', 'which', 'who',
        'can you', 'could you', 'would you', 'do you', 'did you', 'have you',
        'tell me', 'explain', 'describe', 'walk me through', 'show me'
    ]
    
    # Calculate confidence score
    confidence = 0.0
    question_type = 'unknown'
    
    # Question mark is strong indicator
    if text_clean.endswith('?'):
        confidence += 0.5
    
    # Check for basic question indicators
    basic_indicator_found = False
    for indicator in basic_indicators:
        if indicator in text_clean:
            confidence += 0.4
            basic_indicator_found = True
            break
    
    # Determine question type and add type-specific confidence
    technical_score = sum(1 for pattern in technical_patterns if pattern in text_clean)
    behavioral_score = sum(1 for pattern in behavioral_patterns if pattern in text_clean)
    clarification_score = sum(1 for pattern in clarification_patterns if pattern in text_clean)
    follow_up_score = sum(1 for pattern in follow_up_patterns if pattern in text_clean)
    
    # Determine primary question type
    scores = {
        'technical': technical_score,
        'behavioral': behavioral_score,
        'clarification': clarification_score,
        'follow_up': follow_up_score
    }
    
    max_score = max(scores.values())
    if max_score > 0:
        question_type = max(scores, key=scores.get)
        confidence += min(max_score * 0.15, 0.4)  # Increased type bonus
    
    # Sentence structure analysis
    if any(text_clean.startswith(phrase) for phrase in ['how would', 'what if', 'can you', 'could you', 'tell me', 'describe', 'give me']):
        confidence += 0.2
    
    # Length analysis - very short texts are less likely to be questions
    word_count = len(text_clean.split())
    if word_count < 3:
        confidence *= 0.6
    elif word_count < 2:
        confidence *= 0.4
    
    # Complexity analysis based on question characteristics
    complexity = 'beginner'
    if any(pattern in text_clean for pattern in ['architecture', 'system design', 'distributed', 'scalability']):
        complexity = 'advanced'
    elif any(pattern in text_clean for pattern in ['algorithm', 'complexity', 'optimize', 'performance']):
        complexity = 'intermediate'
    elif question_type == 'behavioral':
        complexity = 'intermediate'  # Behavioral questions typically intermediate complexity
    
    # Cap confidence at 1.0
    confidence = min(confidence, 1.0)
    
    # Determine if this is a question (threshold of 0.3)
    is_question = confidence >= 0.3
    
    return {
        'is_question': is_question,
        'confidence': round(confidence, 3),
        'type': question_type,
        'complexity': complexity,
        'raw_scores': scores
    }

def add_to_conversation_memory(session_id: str, interaction_type: str, content: str, 
                              speaker: str = None, metadata: dict = None, importance_score: float = 1.0):
    """Add an interaction to conversation memory for enhanced context tracking"""
    try:
        db = get_db()
        metadata_json = json.dumps(metadata) if metadata else None
        
        db.execute('''
            INSERT INTO conversation_memory 
            (session_id, interaction_type, content, speaker, metadata, importance_score)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (session_id, interaction_type, content, speaker, metadata_json, importance_score))
        
        db.commit()
        
        # Keep memory manageable - remove old entries if we have too many
        cleanup_conversation_memory(session_id, max_entries=50)
        
    except Exception as e:
        print(f"Error adding to conversation memory: {e}")

def cleanup_conversation_memory(session_id: str, max_entries: int = 50):
    """Clean up old conversation memory entries, keeping the most recent and important ones"""
    try:
        db = get_db()
        
        # Count current entries
        count_cursor = db.execute(
            'SELECT COUNT(*) FROM conversation_memory WHERE session_id = ?', 
            (session_id,)
        )
        entry_count = count_cursor.fetchone()[0]
        
        if entry_count > max_entries:
            # Keep the most recent entries and high-importance entries
            db.execute('''
                DELETE FROM conversation_memory 
                WHERE session_id = ? AND id NOT IN (
                    SELECT id FROM conversation_memory 
                    WHERE session_id = ? 
                    ORDER BY 
                        CASE 
                            WHEN importance_score > 2.0 THEN 1 
                            ELSE 2 
                        END,
                        timestamp DESC 
                    LIMIT ?
                )
            ''', (session_id, session_id, max_entries))
            
            db.commit()
            
    except Exception as e:
        print(f"Error cleaning up conversation memory: {e}")

def get_conversation_context(session_id: str, max_interactions: int = 10) -> str:
    """Get conversation context from memory with intelligent selection"""
    try:
        db = get_db()
        
        # Get recent and important interactions
        cursor = db.execute('''
            SELECT interaction_type, content, speaker, importance_score, timestamp
            FROM conversation_memory 
            WHERE session_id = ? 
            ORDER BY 
                CASE 
                    WHEN importance_score > 2.0 THEN 1 
                    ELSE 2 
                END,
                timestamp DESC
            LIMIT ?
        ''', (session_id, max_interactions))
        
        interactions = cursor.fetchall()
        
        if not interactions:
            return ""
        
        context_parts = ["\n=== Conversation Context ==="]
        
        # Group interactions by type for better organization
        questions = []
        answers = []
        other_context = []
        
        for interaction in reversed(interactions):  # Reverse for chronological order
            content = interaction['content']
            interaction_type = interaction['interaction_type']
            speaker = interaction['speaker'] or 'unknown'
            
            if interaction_type == 'question':
                questions.append(f"Q: {content}")
            elif interaction_type == 'answer':
                answers.append(f"A: {content}")
            else:
                other_context.append(f"{speaker}: {content}")
        
        # Build context with recent Q&A pairs
        if questions or answers:
            context_parts.append("\nRecent Q&A:")
            # Pair questions and answers
            for i in range(max(len(questions), len(answers))):
                if i < len(questions):
                    context_parts.append(questions[i])
                if i < len(answers):
                    context_parts.append(answers[i])
        
        if other_context:
            context_parts.append("\nOther Context:")
            context_parts.extend(other_context[-5:])  # Last 5 other interactions
        
        return "\n".join(context_parts) + "\n=== End Context ===\n"
        
    except Exception as e:
        print(f"Error getting conversation context: {e}")
        return ""

def analyze_conversation_importance(content: str, interaction_type: str) -> float:
    """Analyze the importance of a conversation interaction for memory prioritization"""
    importance_score = 1.0
    
    # Technical keywords that indicate important content
    technical_keywords = [
        'algorithm', 'architecture', 'design pattern', 'scalability', 'performance',
        'database', 'api', 'microservices', 'system design', 'optimization',
        'security', 'authentication', 'encryption', 'framework', 'library'
    ]
    
    # Interview-specific important phrases
    interview_keywords = [
        'experience', 'project', 'challenge', 'leadership', 'team',
        'accomplishment', 'failure', 'learning', 'growth', 'goal'
    ]
    
    content_lower = content.lower()
    
    # Boost importance for technical discussions
    for keyword in technical_keywords:
        if keyword in content_lower:
            importance_score += 0.3
    
    # Boost importance for interview-relevant content
    for keyword in interview_keywords:
        if keyword in content_lower:
            importance_score += 0.2
    
    # Question-answer pairs are generally more important
    if interaction_type in ['question', 'answer']:
        importance_score += 0.5
    
    # Long, detailed content is often more important
    if len(content) > 200:
        importance_score += 0.3
    
    # Cap the importance score
    return min(importance_score, 3.0)

def generate_ai_response(session_id: str, question: str, question_analysis: dict = None) -> str:
    """Generate AI response for a question in session context with question type awareness"""
    try:
        db = get_db()
        
        # Get session context
        session_cursor = db.execute('SELECT * FROM sessions WHERE id = ?', (session_id,))
        session = session_cursor.fetchone()
        
        if not session:
            return "I couldn't find the session context for this question."
        
        # Analyze question if not provided
        if question_analysis is None:
            question_analysis = detect_question(question)
        
        # Add the current question to conversation memory with enhanced metadata
        question_importance = analyze_conversation_importance(question, 'question')
        add_to_conversation_memory(
            session_id, 
            'question', 
            question, 
            'interviewer',
            {
                'question_length': len(question),
                'question_type': question_analysis.get('type', 'unknown'),
                'confidence': question_analysis.get('confidence', 0.0),
                'complexity': question_analysis.get('complexity', 'beginner')
            },
            question_importance
        )
        
        # Get enhanced conversation context from memory
        conversation_context = get_conversation_context(session_id, max_interactions=15)

        # Retrieve additional context from external memory service
        memory_context = ""
        if memory_service:
            try:
                context_parts = []
                meeting_context = memory_service.search_meeting_context(question, n_results=3)
                if meeting_context and meeting_context.get('documents'):
                    context_parts.append("Previous meeting context:")
                    for doc in meeting_context['documents'][0][:2]:
                        context_parts.append(f"- {doc}")
                code_context = memory_service.search_code(question, n_results=2)
                if code_context and code_context.get('documents'):
                    context_parts.append("Code context:")
                    for doc in code_context['documents'][0][:2]:
                        context_parts.append(f"- {doc}")
                task_context = memory_service.search_tasks(question, n_results=2)
                if task_context and task_context.get('documents'):
                    context_parts.append("Related tasks:")
                    for doc in task_context['documents'][0][:2]:
                        context_parts.append(f"- {doc}")
                memory_context = "\n".join(context_parts)
            except Exception as e:  # pragma: no cover - optional feature
                print(f"Memory service search failed: {e}")

        # Get knowledge base context for enhanced responses
        knowledge_context = ""
        if knowledge_base:
            try:
                # Search knowledge base for relevant information
                kb_results = knowledge_base.search(question, top_k=3)
                
                if kb_results:
                    knowledge_context = "\n=== Relevant Knowledge ===\n"
                    for i, result in enumerate(kb_results, 1):
                        if result.get('similarity_score', 0) > 0.7:  # Only include high-relevance results
                            knowledge_context += f"\nKnowledge {i}:\n{result['content'][:300]}...\n"
                            metadata = result.get('metadata', {})
                            if metadata.get('title'):
                                knowledge_context += f"Source: {metadata['title']}\n"
                    knowledge_context += "=== End Knowledge ===\n"
                    
                    # Add knowledge retrieval to conversation memory
                    if len(kb_results) > 0:
                        knowledge_summary = f"Retrieved {len(kb_results)} knowledge items for: {question[:50]}..."
                        add_to_conversation_memory(
                            session_id,
                            'context',
                            knowledge_summary,
                            'knowledge_base',
                            {'knowledge_count': len(kb_results), 'query': question[:100]},
                            2.0  # High importance for knowledge retrieval
                        )
            except Exception as e:
                print(f"Knowledge base search failed: {e}")
        
        # Get user's resume context (from the Q&A service database)
        resume_context = ""
        try:
            # Connect to the Q&A service database to get resume
            qa_db = sqlite3.connect('production_mentor.db')
            qa_cursor = qa_db.execute('SELECT resume_text FROM user_data WHERE user_id = ?', (session['user_id'],))
            resume_result = qa_cursor.fetchone()
            if resume_result and resume_result[0]:
                resume_context = f"\n\nUser's Background:\n{resume_result[0][:1000]}..."  # First 1000 chars
            qa_db.close()
        except Exception as e:
            print(f"Could not fetch resume context: {e}")
        
        # Build type-specific response guidance
        question_type = question_analysis.get('type', 'unknown')
        complexity = question_analysis.get('complexity', 'beginner')
        confidence = question_analysis.get('confidence', 0.0)
        
        type_guidance = ""
        if question_type == 'technical':
            type_guidance = """
TECHNICAL QUESTION GUIDANCE:
- Provide clear, step-by-step explanations
- Include relevant algorithms, data structures, or system design concepts
- Consider time/space complexity when applicable
- Use concrete examples or code snippets if helpful
- Address scalability and performance considerations"""
        elif question_type == 'behavioral':
            type_guidance = """
BEHAVIORAL QUESTION GUIDANCE:
- Structure response using STAR method (Situation, Task, Action, Result)
- Focus on specific examples and measurable outcomes
- Highlight leadership, teamwork, and problem-solving skills
- Show growth mindset and learning from challenges
- Connect experience to the role requirements"""
        elif question_type == 'clarification':
            type_guidance = """
CLARIFICATION REQUEST:
- Provide clear, direct explanations
- Break down complex concepts into simpler terms
- Offer multiple perspectives or approaches
- Check understanding and invite follow-up questions"""
        elif question_type == 'follow_up':
            type_guidance = """
FOLLOW-UP QUESTION:
- Build directly on previous conversation context
- Reference earlier discussions when relevant
- Provide additional depth or alternative approaches
- Connect to broader interview themes"""
        
        complexity_guidance = ""
        if complexity == 'advanced':
            complexity_guidance = "Provide in-depth, comprehensive analysis appropriate for senior-level candidates."
        elif complexity == 'intermediate':
            complexity_guidance = "Balance detail with clarity, suitable for mid-level professionals."
        else:
            complexity_guidance = "Focus on fundamental concepts with clear explanations."

        # Build enhanced system prompt with memory-based conversation context
        system_prompt = f"""You are an AI mentor helping a candidate during a {session['meeting_type']} interview.

Session Context:
- User Level: {session['user_level']}
- Meeting Type: {session['meeting_type']}
- Project Context: {session['project_context'] or 'General interview'}

Question Analysis:
- Type: {question_type}
- Complexity: {complexity}
- Detection Confidence: {confidence:.2f}

{type_guidance}

Complexity Level: {complexity_guidance}

{resume_context}

{conversation_context}

{memory_context}

{knowledge_context}

Current Question: {question}

Please provide a helpful, contextual response that:
1. Directly answers the question using the type-specific guidance above
2. Builds on previous conversation context when relevant
3. Uses relevant memory or knowledge base information when available
4. Considers the user's background and experience level
5. Is appropriate for a {session['meeting_type']} context and {complexity} complexity level
6. Helps the candidate succeed in their interview

Keep responses under 300 words and be practical and actionable. If this question relates to previous discussions or available knowledge, acknowledge that context and provide more comprehensive guidance."""

        # Call OpenAI API
        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful AI mentor providing intelligent interview assistance with conversation awareness."},
                {"role": "user", "content": system_prompt}
            ],
            max_tokens=400,
            temperature=0.7
        )
        
        ai_answer = response.choices[0].message.content
        
        # Add the AI response to conversation memory
        answer_importance = analyze_conversation_importance(ai_answer, 'answer')
        add_to_conversation_memory(
            session_id,
            'answer',
            ai_answer,
            'ai_mentor',
            {
                'response_length': len(ai_answer),
                'question': question[:100] + '...' if len(question) > 100 else question
            },
            answer_importance
        )

        # Store Q&A pair in external memory service
        if memory_service:
            try:
                memory_service.add_meeting_entry(
                    session_id,
                    f"Q: {question}\nA: {ai_answer}",
                    {
                        'type': 'qa_pair',
                        'user_level': session['user_level'],
                        'timestamp': datetime.utcnow().isoformat()
                    }
                )
            except Exception as e:  # pragma: no cover - optional feature
                print(f"Memory service store failed: {e}")

        return ai_answer
        
    except Exception as e:
        print(f"Error generating AI response: {e}")
        return f"I encountered an error while processing your question: {str(e)}"

# API Endpoints

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'realtime',
        'port': 8080,
        'timestamp': datetime.utcnow().isoformat(),
        'active_sessions': len(active_sessions)
    }), 200


@app.route('/api/meeting-events', methods=['POST'])
def realtime_meeting_events():
    """Accept meeting intelligence events from capture clients."""

    payload = request.get_json(silent=True) or {}
    try:
        result = meeting_event_router.handle_event(payload)
    except ValueError as exc:
        return jsonify({'ok': False, 'error': str(exc)}), 400
    return jsonify({'ok': True, 'result': result})

@app.route('/api/sessions', methods=['POST'])
@require_auth
def create_session():
    """Create a new interview session"""
    try:
        data = request.get_json() or {}
        user_id = g.current_user['user_id']
        
        # Generate session ID
        session_id = str(uuid.uuid4())
        
        # Session configuration
        user_level = data.get('user_level', 'IC5')
        meeting_type = data.get('meeting_type', 'technical_interview')
        project_context = data.get('project_context', '')
        
        # Store in database
        db = get_db()
        db.execute('''
            INSERT INTO sessions (id, user_id, user_level, meeting_type, project_context, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (session_id, user_id, user_level, meeting_type, project_context, json.dumps(data)))

        db.commit()

        # Initialize session metadata
        active_sessions[session_id] = {
            'user_id': user_id,
            'created_at': datetime.utcnow().isoformat(),
            'user_level': user_level,
            'meeting_type': meeting_type,
            'project_context': project_context
        }
        session_store.add_participant(session_id, user_id)

        try:
            with session_scope() as knowledge_session:
                ensure_meeting(
                    knowledge_session,
                    session_id=uuid.UUID(session_id),
                    title=data.get('title') or meeting_type,
                    provider='realtime',
                    started_at=datetime.utcnow(),
                    participants=data.get('participants') or [str(user_id)],
                )
        except Exception as exc:  # pragma: no cover - defensive log
            print(f"⚠️ Failed to mirror meeting in knowledge store: {exc}")

        # Initialize event queue for this session
        session_queues[session_id] = queue.Queue()
        session_recordings[session_id] = None

        if Config.SCREEN_RECORDING_ENABLED:
            def _record_screen() -> None:
                video_path = screen_record.record_screen(
                    session_id, Config.SCREEN_RECORDING_DURATION
                )
                session_recordings[session_id] = video_path

            threading.Thread(target=_record_screen, daemon=True).start()

        # Broadcast session creation (for monitoring/admin purposes)
        session_queues[session_id].put({
            'type': 'session_created',
            'data': {
                'session_id': session_id,
                'user_level': user_level,
                'meeting_type': meeting_type,
                'project_context': project_context
            },
            'timestamp': datetime.utcnow().isoformat()
        })
        
        return jsonify({
            'session_id': session_id,
            'user_level': user_level,
            'meeting_type': meeting_type,
            'status': 'created'
        }), 201
        
    except Exception as e:
        return jsonify({'error': f'Session creation failed: {str(e)}'}), 500

@app.route('/api/sessions/<session_id>', methods=['GET'])
@require_auth
def get_session(session_id):
    """Get session information"""
    try:
        user_id = g.current_user['user_id']
        db = get_db()
        
        # Verify user owns this session
        cursor = db.execute('SELECT * FROM sessions WHERE id = ? AND user_id = ?', (session_id, user_id))
        session = cursor.fetchone()
        
        if not session:
            return jsonify({'error': 'Session not found or access denied'}), 404
        
        # Get session statistics
        captions_cursor = db.execute('SELECT COUNT(*) as count FROM captions WHERE session_id = ?', (session_id,))
        captions_count = captions_cursor.fetchone()['count']
        
        responses_cursor = db.execute('SELECT COUNT(*) as count FROM ai_responses WHERE session_id = ?', (session_id,))
        responses_count = responses_cursor.fetchone()['count']
        
        return jsonify({
            'session_id': session['id'],
            'user_level': session['user_level'],
            'meeting_type': session['meeting_type'],
            'project_context': session['project_context'],
            'created_at': session['created_at'],
            'ended_at': session['ended_at'],
            'is_active': bool(session['is_active']),
            'captions_count': captions_count,
            'responses_count': responses_count
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to get session: {str(e)}'}), 500

@app.route('/api/sessions/<session_id>', methods=['DELETE'])
@require_auth
def end_session(session_id):
    """End/delete a session"""
    try:
        user_id = g.current_user['user_id']
        db = get_db()
        
        # Verify user owns this session
        cursor = db.execute('SELECT * FROM sessions WHERE id = ? AND user_id = ?', (session_id, user_id))
        session = cursor.fetchone()
        
        if not session:
            return jsonify({'error': 'Session not found or access denied'}), 404
        
        # Mark session as ended
        db.execute('''
            UPDATE sessions
            SET ended_at = CURRENT_TIMESTAMP, is_active = 0
            WHERE id = ? AND user_id = ?
        ''', (session_id, user_id))

        db.execute(
            "UPDATE session_participants SET left_at = CURRENT_TIMESTAMP WHERE session_id = ? AND left_at IS NULL",
            (session_id,),
        )

        db.commit()
        
        # Broadcast session end to connected clients
        if session_id in session_queues:
            session_queues[session_id].put({
                'type': 'session_ended',
                'data': {
                    'session_id': session_id,
                    'message': 'Session has been ended'
                },
                'timestamp': datetime.utcnow().isoformat()
            })
        
        # Clean up memory
        active_sessions.pop(session_id, None)
        session_queues.pop(session_id, None)
        
        return jsonify({
            'message': 'Session ended successfully',
            'session_id': session_id
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to end session: {str(e)}'}), 500


@app.route('/api/sessions/<session_id>/join', methods=['POST'])
@require_auth
def join_session(session_id):
    """Join a session and broadcast presence"""
    try:
        user_id = g.current_user['user_id']
        session_store.add_participant(session_id, user_id)
        participants = session_store.get_participants(session_id)

        if session_id in session_queues:
            session_queues[session_id].put({
                'type': 'participant_joined',
                'data': {
                    'user_id': user_id,
                    'participants': participants
                },
                'timestamp': datetime.utcnow().isoformat()
            })

        return jsonify({'message': 'joined', 'participants': participants}), 200
    except Exception as e:
        return jsonify({'error': f'Failed to join session: {str(e)}'}), 500


@app.route('/api/sessions/<session_id>/leave', methods=['POST'])
@require_auth
def leave_session(session_id):
    """Leave a session and broadcast presence"""
    try:
        user_id = g.current_user['user_id']
        session_store.remove_participant(session_id, user_id)
        participants = session_store.get_participants(session_id)

        if session_id in session_queues:
            session_queues[session_id].put({
                'type': 'participant_left',
                'data': {
                    'user_id': user_id,
                    'participants': participants
                },
                'timestamp': datetime.utcnow().isoformat()
            })

        return jsonify({'message': 'left', 'participants': participants}), 200
    except Exception as e:
        return jsonify({'error': f'Failed to leave session: {str(e)}'}), 500

@app.route('/api/sessions/<session_id>/captions', methods=['POST'])
@require_auth
def add_caption(session_id):
    """Add a caption/speech input to the session"""
    try:
        user_id = g.current_user['user_id']
        data = request.get_json()
        
        if not data or 'text' not in data:
            return jsonify({'error': 'Caption text is required'}), 400
        
        text = data['text'].strip()
        speaker = data.get('speaker', 'unknown')

        # Use diarization service to assign speaker if not provided
        if speaker == 'unknown' and diarization_service:
            try:
                detected_speaker = diarization_service.assign_speaker_to_text(text)
                if detected_speaker:
                    speaker = detected_speaker
            except Exception as e:  # pragma: no cover - optional feature
                print(f"⚠️ Diarization failed: {e}")
        
        if not text:
            return jsonify({'error': 'Caption text cannot be empty'}), 400
        
        db = get_db()
        
        # Verify session exists and user owns it
        cursor = db.execute('SELECT * FROM sessions WHERE id = ? AND user_id = ? AND is_active = 1', (session_id, user_id))
        session = cursor.fetchone()
        
        if not session:
            return jsonify({'error': 'Session not found, ended, or access denied'}), 404
        
        # Detect if this is a question with advanced analysis
        question_analysis = detect_question(text)
        is_question = question_analysis['is_question']
        
        # Store caption with enhanced question metadata
        db.execute('''
            INSERT INTO captions (session_id, text, speaker, is_question)
            VALUES (?, ?, ?, ?)
        ''', (session_id, text, speaker, is_question))

        db.commit()

        ts_start_ms = int(data.get('ts_start_ms') or data.get('timestamp_ms') or int(time.time() * 1000))
        ts_end_ms = int(data.get('ts_end_ms') or ts_start_ms)
        try:
            with session_scope() as knowledge_session:
                add_transcript_segment(
                    knowledge_session,
                    session_id=uuid.UUID(session_id),
                    text=text,
                    speaker=speaker,
                    ts_start_ms=ts_start_ms,
                    ts_end_ms=ts_end_ms,
                )
        except Exception as exc:  # pragma: no cover - defensive log
            print(f"⚠️ Failed to store transcript segment: {exc}")

        # Store caption in external memory service if available
        if memory_service:
            try:
                memory_service.add_meeting_entry(
                    session_id,
                    text,
                    {
                        'speaker': speaker,
                        'timestamp': datetime.utcnow().isoformat(),
                        'meeting_type': session['meeting_type']
                    }
                )
            except Exception as e:  # pragma: no cover - optional feature
                print(f"⚠️ Memory service store failed: {e}")
        
        # Add caption to conversation memory for enhanced context tracking
        caption_importance = analyze_conversation_importance(text, 'question' if is_question else 'context')
        add_to_conversation_memory(
            session_id,
            'question' if is_question else 'context',
            text,
            speaker,
            {
                'is_question': is_question,
                'question_type': question_analysis.get('type', 'unknown'),
                'confidence': question_analysis.get('confidence', 0.0),
                'complexity': question_analysis.get('complexity', 'beginner'),
                'text_length': len(text),
                'speaker': speaker
            },
            caption_importance
        )
        
        # Broadcast caption to connected SSE clients with enhanced question analysis
        if session_id in session_queues:
            session_queues[session_id].put({
                'type': 'new_caption',
                'data': {
                    'text': text,
                    'speaker': speaker,
                    'is_question': is_question,
                    'question_analysis': question_analysis if is_question else None,
                    'session_id': session_id
                },
                'timestamp': datetime.utcnow().isoformat()
            })
        
        response_data = {
            'message': 'Caption added successfully',
            'session_id': session_id,
            'is_question': is_question,
            'speaker': speaker
        }
        
        # If it's a question from interviewer, generate AI response
        if is_question and speaker.lower() in ['interviewer', 'unknown']:
            try:
                start_time = time.time()
                ai_answer = generate_ai_response(session_id, text, question_analysis)
                response_time_ms = int((time.time() - start_time) * 1000)
                
                # Store AI response
                db.execute('''
                    INSERT INTO ai_responses (session_id, question_text, answer_text, response_time_ms)
                    VALUES (?, ?, ?, ?)
                ''', (session_id, text, ai_answer, response_time_ms))
                
                db.commit()
                
                response_data['ai_response'] = {
                    'answer': ai_answer,
                    'response_time_ms': response_time_ms
                }
                
                # Add to session queue for real-time updates (future SSE implementation)
                if session_id in session_queues:
                    session_queues[session_id].put({
                        'type': 'new_answer',
                        'data': response_data['ai_response'],
                        'timestamp': datetime.utcnow().isoformat()
                    })
                
            except Exception as e:
                print(f"Error generating AI response: {e}")
                response_data['ai_response_error'] = str(e)
        
        return jsonify(response_data), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to add caption: {str(e)}'}), 500

@app.route('/api/sessions/<session_id>/answers', methods=['GET'])
@require_auth
def get_session_answers(session_id):
    """Get recent AI answers for a session"""
    try:
        user_id = g.current_user['user_id']
        db = get_db()
        
        # Verify session exists and user owns it
        cursor = db.execute('SELECT * FROM sessions WHERE id = ? AND user_id = ?', (session_id, user_id))
        session = cursor.fetchone()
        
        if not session:
            return jsonify({'error': 'Session not found or access denied'}), 404
        
        # Get recent answers (last 10)
        limit = request.args.get('limit', 10, type=int)
        limit = min(limit, 50)  # Cap at 50
        
        answers_cursor = db.execute('''
            SELECT question_text, answer_text, timestamp, response_time_ms, tokens_used
            FROM ai_responses 
            WHERE session_id = ? 
            ORDER BY timestamp DESC 
            LIMIT ?
        ''', (session_id, limit))
        
        answers = []
        for row in answers_cursor.fetchall():
            answers.append({
                'question': row['question_text'],
                'answer': row['answer_text'],
                'timestamp': row['timestamp'],
                'response_time_ms': row['response_time_ms'],
                'tokens_used': row['tokens_used']
            })
        
        return jsonify({
            'session_id': session_id,
            'answers': answers,
            'count': len(answers)
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to get answers: {str(e)}'}), 500

@app.route('/api/sessions/<session_id>/memory', methods=['GET'])
@require_auth
def get_conversation_memory(session_id):
    """Get conversation memory for a session (for debugging and monitoring)"""
    try:
        user_id = g.current_user['user_id']
        db = get_db()
        
        # Verify session exists and user owns it
        cursor = db.execute('SELECT * FROM sessions WHERE id = ? AND user_id = ?', (session_id, user_id))
        session = cursor.fetchone()
        
        if not session:
            return jsonify({'error': 'Session not found or access denied'}), 404
        
        # Get conversation memory
        limit = request.args.get('limit', 20, type=int)
        limit = min(limit, 100)  # Cap at 100
        
        memory_cursor = db.execute('''
            SELECT interaction_type, content, speaker, metadata, importance_score, timestamp
            FROM conversation_memory 
            WHERE session_id = ? 
            ORDER BY timestamp DESC 
            LIMIT ?
        ''', (session_id, limit))
        
        memory_items = []
        for row in memory_cursor.fetchall():
            metadata = None
            if row['metadata']:
                try:
                    metadata = json.loads(row['metadata'])
                except:
                    metadata = {}
            
            memory_items.append({
                'type': row['interaction_type'],
                'content': row['content'][:200] + '...' if len(row['content']) > 200 else row['content'],
                'speaker': row['speaker'],
                'importance_score': row['importance_score'],
                'timestamp': row['timestamp'],
                'metadata': metadata
            })
        
        # Get conversation context preview
        context_preview = get_conversation_context(session_id, max_interactions=8)
        
        return jsonify({
            'session_id': session_id,
            'memory_items': memory_items,
            'total_items': len(memory_items),
            'context_preview': context_preview.strip()
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to get conversation memory: {str(e)}'}), 500


@app.route('/api/sessions/<session_id>/recording', methods=['GET'])
@require_auth
def get_screen_recording(session_id):
    """Get screen recording path or analysis for a session."""
    try:
        user_id = g.current_user['user_id']
        db = get_db()

        cursor = db.execute('SELECT id FROM sessions WHERE id = ? AND user_id = ?', (session_id, user_id))
        if not cursor.fetchone():
            return jsonify({'error': 'Session not found or access denied'}), 404

        video_path = session_recordings.get(session_id)
        if not video_path:
            return jsonify({'message': 'Recording in progress or unavailable'}), 202

        if not os.path.exists(video_path):
            return jsonify({'error': 'Recording file not found'}), 404

        if request.args.get('analyze') == 'true':
            analysis = screen_record.analyze_screen_video(video_path)
            return jsonify({'video_path': video_path, 'analysis': analysis}), 200

        return jsonify({'video_path': video_path}), 200

    except Exception as e:
        return jsonify({'error': f'Failed to get recording: {str(e)}'}), 500

@app.route('/api/knowledge/search', methods=['POST'])
@require_auth
def search_knowledge_base():
    """Search the knowledge base for relevant information"""
    try:
        if not knowledge_base:
            return jsonify({'error': 'Knowledge base not available'}), 503
        
        data = request.get_json()
        if not data or 'query' not in data:
            return jsonify({'error': 'Query is required'}), 400
        
        query = data['query'].strip()
        top_k = data.get('top_k', 5)
        doc_type = data.get('doc_type')  # Optional filter
        
        if not query:
            return jsonify({'error': 'Query cannot be empty'}), 400
        
        # Search knowledge base
        results = knowledge_base.search(query, top_k, {'type': doc_type} if doc_type else None)
        
        # Format results for response
        formatted_results = []
        for result in results:
            formatted_results.append({
                'content': result['content'][:500] + '...' if len(result['content']) > 500 else result['content'],
                'similarity_score': result.get('similarity_score', 0),
                'metadata': result.get('metadata', {}),
                'relevance': 'high' if result.get('similarity_score', 0) > 0.8 else 'medium' if result.get('similarity_score', 0) > 0.6 else 'low'
            })
        
        return jsonify({
            'query': query,
            'results': formatted_results,
            'total_results': len(formatted_results),
            'knowledge_base_available': True
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Knowledge base search failed: {str(e)}'}), 500

@app.route('/api/knowledge/stats', methods=['GET'])
@require_auth
def get_knowledge_base_stats():
    """Get knowledge base statistics"""
    try:
        if not knowledge_base:
            return jsonify({'error': 'Knowledge base not available', 'available': False}), 503
        
        stats = knowledge_base.get_collection_info()
        stats['available'] = True
        stats['status'] = 'operational'
        
        return jsonify(stats), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to get knowledge base stats: {str(e)}', 'available': False}), 500

@app.route('/api/knowledge/add', methods=['POST'])
@require_auth
def add_knowledge_document():
    """Add a document to the knowledge base"""
    try:
        if not knowledge_base:
            return jsonify({'error': 'Knowledge base not available'}), 503
        
        data = request.get_json()
        if not data or 'content' not in data:
            return jsonify({'error': 'Content is required'}), 400
        
        content = data['content'].strip()
        if not content:
            return jsonify({'error': 'Content cannot be empty'}), 400
        
        # Prepare metadata
        metadata = data.get('metadata', {})
        metadata.update({
            'added_by_user': g.current_user.get('user_id'),
            'added_via': 'api',
            'type': data.get('type', 'manual'),
            'title': data.get('title', f'Document added via API'),
            'source': 'user_upload'
        })
        
        # Add to knowledge base
        doc_id = knowledge_base.add_document(content, metadata)
        
        return jsonify({
            'message': 'Document added successfully',
            'document_id': doc_id,
            'content_length': len(content),
            'metadata': metadata
        }), 201
        
    except Exception as e:
        return jsonify({'error': f'Failed to add document: {str(e)}'}), 500

@app.route('/api/sessions/<session_id>/stream', methods=['GET'])
def stream_session_events(session_id):
    """
    Server-Sent Events endpoint for real-time session updates
    Streams events like new answers, captions, and session changes
    
    Authentication can be provided via:
    1. Authorization header (for server-to-server)
    2. token query parameter (for browser EventSource)
    """
    try:
        # Get token from header or query parameter
        token = request.headers.get('Authorization')
        if token and token.startswith('Bearer '):
            token = token[7:]
        else:
            token = request.args.get('token')
        
        if not token:
            return jsonify({'error': 'No token provided'}), 401
        
        # Verify token
        user_data = verify_token(token)
        if not user_data:
            return jsonify({'error': 'Invalid or expired token'}), 401
        
        user_id = user_data.get('user_id')
        
        # Verify session exists and user has access
        conn = get_db()
        cursor = conn.cursor()
        
        # Get session and verify ownership
        cursor.execute('''
            SELECT s.*, u.email, u.subscription_tier 
            FROM sessions s
            JOIN users u ON s.user_id = u.id 
            WHERE s.id = ? AND s.user_id = ?
        ''', (session_id, user_id))
        
        session = cursor.fetchone()
        if not session:
            return jsonify({'error': 'Session not found or access denied'}), 404
        
        def event_stream():
            """Generator function for SSE events"""
            # Send initial connection event
            initial_event = json.dumps({
                'type': 'connected',
                'session_id': session_id,
                'timestamp': datetime.utcnow().isoformat(),
                'message': 'Connected to real-time stream',
                'participants': session_store.get_participants(session_id)
            })
            yield f"data: {initial_event}\\n\\n"
            
            # Create a queue for this client if session doesn't exist
            if session_id not in session_queues:
                session_queues[session_id] = queue.Queue()
            
            client_queue = session_queues[session_id]

            try:
                while True:
                    try:
                        # Wait for an event (with timeout)
                        event = client_queue.get(timeout=30)
                        yield f"data: {json.dumps(event)}\\n\\n"
                    except queue.Empty:
                        # Send heartbeat to keep connection alive
                        heartbeat = json.dumps({
                            'type': 'heartbeat',
                            'timestamp': datetime.utcnow().isoformat()
                        })
                        yield f"data: {heartbeat}\\n\\n"
                    except Exception as e:
                        # Send error event and break
                        error_event = json.dumps({
                            'type': 'error',
                            'message': str(e),
                            'timestamp': datetime.utcnow().isoformat()
                        })
                        yield f"data: {error_event}\\n\\n"
                        break
            except GeneratorExit:
                # Client disconnected
                pass
        
        # Return SSE response
        return Response(
            event_stream(),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Cache-Control'
            }
        )
        
    except Exception as e:
        return jsonify({'error': f'Failed to start stream: {str(e)}'}), 500

# Error Handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

# Cleanup
@app.teardown_appcontext
def close_db_connection(error):
    close_db(error)

# Initialize database on startup
with app.app_context():
    init_db()

if __name__ == '__main__':
    port = int(os.getenv('REALTIME_PORT', 8080))
    debug = os.getenv('FLASK_ENV') == 'development'
    
    print(f"🚀 AI Mentor Realtime Service starting on port {port}")
    print(f"🔑 OpenAI API Key: {'✅ Configured' if os.getenv('OPENAI_API_KEY') else '❌ Missing'}")
    print(f"💾 Database: {app.config['DATABASE']}")
    print(f"🔄 Active Sessions: {len(active_sessions)}")
    
    app.run(host='0.0.0.0', port=port, debug=debug)
