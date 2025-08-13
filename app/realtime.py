# app/realtime.py

import asyncio
import json
import logging
import queue
import threading
import uuid
from datetime import datetime
from typing import Dict, Optional, List, Any
import os
import sys
import time

from .speaker_diarization import SpeakerDiarizer

# Add the backend directory to Python path
backend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backend')
sys.path.insert(0, backend_dir)

try:
    from backend.diarization_service import DiarizationService
    from backend.memory_service import MemoryService
    ADVANCED_FEATURES = True
except ImportError:
    log = logging.getLogger(__name__)
    log.warning("Advanced features (diarization/memory) not available, using basic mode")
    ADVANCED_FEATURES = False
    DiarizationService = None  # type: ignore[assignment]
    MemoryService = None  # type: ignore[assignment]

log = logging.getLogger(__name__)

class RealtimeSessionManager:
    """
    Manages real-time AI sessions with the complete intelligence loop:
    1. Live caption capture
    2. Speaker diarization  
    3. Question boundary detection
    4. Memory context injection
    5. AI answer generation
    6. Delivery to overlay, mobile, IDE
    """

    def __init__(self):
        self.sessions: Dict[str, 'RealtimeSession'] = {}
        if ADVANCED_FEATURES:
            self.diarization = DiarizationService()  # type: ignore[operator]
            self.memory = MemoryService()  # type: ignore[operator]
        else:
            self.diarization = None
            self.memory = None
        log.info("RealtimeSessionManager initialized")

    def create_session(self, session_data: Dict) -> str:
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = RealtimeSession(
            session_id=session_id,
            diarization=self.diarization,
            memory=self.memory,
            **session_data
        )
        log.info(f"Created session {session_id}")
        return session_id

    def get_session(self, session_id: str) -> Optional['RealtimeSession']:
        return self.sessions.get(session_id)

    def end_session(self, session_id: str):
        session = self.sessions.pop(session_id, None)
        if session:
            session.cleanup()
            log.info(f"Ended session {session_id}")

    def cleanup_inactive_sessions(self):
        """Remove sessions that haven't been active for a while"""
        to_remove = []
        for session_id, session in self.sessions.items():
            if session.is_inactive():
                to_remove.append(session_id)
        
        for session_id in to_remove:
            self.end_session(session_id)


class RealtimeSession:
    """
    Individual session managing the complete AI interview loop for one meeting.
    """

    def __init__(self, session_id: str, diarization=None, memory=None, **kwargs):
        self.session_id = session_id
        self.memory = memory
        self.diarization = diarization  # kept for backward compatibility
        self.speaker_diarizer = SpeakerDiarizer()
        self.last_activity = datetime.now()
        
        # Session configuration
        self.user_level = kwargs.get('user_level', 'IC5')
        self.user_name = kwargs.get('user_name', 'candidate')
        self.meeting_type = kwargs.get('meeting_type', 'technical_interview')
        self.project_context = kwargs.get('project_context', '')
        
        # State management
        self.caption_buffer = []
        self.current_question = None
        self.answers_generated = []
        self.client_queues: Dict[str, queue.Queue] = {}
        self.background_task = None
        self.last_processed_index = 0
        
        # Start the processing loop
        self._start_background_processing()
        
        log.info(f"RealtimeSession {session_id} initialized for {self.user_name}")

    def _start_background_processing(self):
        """Start the background thread for processing captions"""
        self.background_task = threading.Thread(
            target=self._process_captions_loop,
            daemon=True
        )
        self.background_task.start()

    def _process_captions_loop(self):
        """Background loop that processes captions and generates answers"""
        while True:
            try:
                if len(self.caption_buffer) > self.last_processed_index:
                    new_captions = self.caption_buffer[self.last_processed_index:]
                    self.last_processed_index = len(self.caption_buffer)

                    for caption in new_captions:
                        segment = caption.get('segment')
                        if not segment:
                            continue

                        if segment.is_interviewer and segment.is_question:
                            self.speaker_diarizer.start_new_question(segment)

                        if self.speaker_diarizer.should_generate_response(segment):
                            potential_question = self.speaker_diarizer.get_complete_question()

                            if potential_question and potential_question != self.current_question:
                                self.current_question = potential_question
                                log.info(
                                    f"New question detected: {potential_question[:100]}..."
                                )
                                speakers = {caption['id']: caption.get('speaker', 'unknown')}
                                self._generate_answer_with_context(
                                    potential_question, speakers
                                )

                # Sleep briefly before next iteration
                time.sleep(2.0)

            except Exception as e:
                log.error(f"Error in caption processing loop: {e}")
                time.sleep(5.0)

    def add_caption(self, caption_data: Dict):
        """Add a new caption to the buffer"""
        self.last_activity = datetime.now()

        # Add timestamp if not present
        if 'timestamp' not in caption_data:
            caption_data['timestamp'] = datetime.now().isoformat()

        # Use speaker diarizer to assign speaker role and track question segments
        if self.speaker_diarizer:
            segment = self.speaker_diarizer.process_transcript_with_speakers(
                caption_data.get('text', ''), {}
            )
            caption_data['speaker'] = (
                'interviewer' if segment.is_interviewer else 'candidate'
            )
            caption_data['segment'] = segment
            self.speaker_diarizer.current_segments.append(segment)
        self.caption_buffer.append(caption_data)
        
        # Keep buffer at reasonable size
        if len(self.caption_buffer) > 100:
            self.caption_buffer = self.caption_buffer[-50:]
        
        # Store in memory if available
        if self.memory:
            self.memory.add_meeting_entry(
                self.session_id,
                caption_data.get('text', ''),
                {
                    'speaker': caption_data.get('speaker', 'unknown'),
                    'timestamp': caption_data['timestamp'],
                    'meeting_type': self.meeting_type
                }
            )

    def _generate_answer_with_context(self, question: str, speakers: Dict):
        """Generate an AI answer with memory context injection"""
        try:
            memory_context = ""
            
            # Search for relevant context from memory if available
            if self.memory:
                meeting_context = self.memory.search_meeting_context(question, n_results=3)
                code_context = self.memory.search_code(question, n_results=2)
                task_context = self.memory.search_tasks(question, n_results=2)
                
                # Build context string
                context_parts = []
                
                if meeting_context and meeting_context.get('documents'):
                    context_parts.append("Previous meeting context:")
                    for doc in meeting_context['documents'][0][:2]:  # Top 2 results
                        context_parts.append(f"- {doc}")
                
                if code_context and code_context.get('documents'):
                    context_parts.append("Relevant code context:")
                    for doc in code_context['documents'][0][:2]:
                        context_parts.append(f"- {doc}")
                
                if task_context and task_context.get('documents'):
                    context_parts.append("Related tasks:")
                    for doc in task_context['documents'][0][:2]:
                        context_parts.append(f"- {doc}")
                
                memory_context = "\n".join(context_parts) if context_parts else "No specific context found."
            else:
                memory_context = self._build_simple_context()
            
            # Import LLM service for answer generation
            try:
                # Use lightweight LLM wrapper
                from app.llm import generate_answer as _gen_answer
                prompt = f"Level: {self.user_level}\nContext: {memory_context}\nQuestion: {question}\nAnswer:"
                answer = _gen_answer(prompt)
            except ImportError:
                # Fallback to basic answer generation
                answer = f"[{self.user_level}] For this question: '{question[:100]}...', consider the system design patterns, scalability concerns, and implementation details appropriate for your level."
            
            # Store the Q&A pair
            qa_entry = {
                'question': question,
                'answer': answer,
                'timestamp': datetime.now().isoformat(),
                'user_level': self.user_level,
                'memory_context_used': bool(self.memory)
            }
            
            self.answers_generated.append(qa_entry)
            
            # Store in memory for future context if available
            if self.memory:
                self.memory.add_meeting_entry(
                    self.session_id,
                    f"Q: {question}\nA: {answer}",
                    {
                        'type': 'qa_pair',
                        'user_level': self.user_level,
                        'timestamp': qa_entry['timestamp']
                    }
                )
            
            # Send to all connected clients
            self._broadcast_answer(qa_entry)
            
            log.info(f"Generated answer for question: {question[:50]}...")
            
        except Exception as e:
            log.error(f"Error generating answer: {e}")

    def _build_simple_context(self) -> str:
        """Build simple context from recent captions"""
        recent_chunks = self.caption_buffer[-20:]  # Last 20 chunks
        return " ".join([chunk.get('text', '') for chunk in recent_chunks])

    def _broadcast_answer(self, qa_entry: Dict):
        """Broadcast answer to all connected clients (overlay, mobile, IDE)"""
        message = {
            'type': 'new_answer',
            'session_id': self.session_id,
            'data': qa_entry
        }
        
        # Send to all client queues
        for client_id, client_queue in self.client_queues.items():
            try:
                client_queue.put(json.dumps(message))
            except Exception as e:
                log.error(f"Failed to send to client {client_id}: {e}")

    def add_client_queue(self, client_id: str) -> queue.Queue:
        """Add a client queue for real-time updates"""
        client_queue = queue.Queue()
        self.client_queues[client_id] = client_queue
        return client_queue

    def remove_client_queue(self, client_id: str):
        """Remove a client queue"""
        self.client_queues.pop(client_id, None)

    def get_recent_answers(self, limit: int = 5) -> List[Dict]:
        """Get recent answers for new clients"""
        return self.answers_generated[-limit:] if self.answers_generated else []

    def is_inactive(self) -> bool:
        """Check if session has been inactive for too long"""
        from datetime import timedelta
        return (datetime.now() - self.last_activity) > timedelta(hours=2)

    def cleanup(self):
        """Clean up session resources"""
        # Close all client queues
        for client_queue in self.client_queues.values():
            try:
                client_queue.put(json.dumps({'type': 'session_ended'}))
            except:
                pass
        self.client_queues.clear()
        
        # Stop background processing
        # (The daemon thread will exit when main thread exits)
        
        log.info(f"Session {self.session_id} cleaned up")


# Global session manager instance
session_manager = RealtimeSessionManager()


def get_session_manager() -> RealtimeSessionManager:
    """Get the global session manager instance"""
    return session_manager


# Backward compatibility functions for existing API
def get_or_create_session(meeting_id: str, ic_level: str = "IC6"):
    """Backward compatibility: create session using new manager"""
    session_data = {
        'user_level': ic_level,
        'user_name': f'user_{meeting_id}',
        'meeting_type': 'technical_interview'
    }
    session_id = session_manager.create_session(session_data)
    return session_manager.get_session(session_id)

def push_caption(meeting_id: str, text: str, speaker: Optional[str] = None):
    """Backward compatibility: add caption to session"""
    session = get_or_create_session(meeting_id)
    if session:
        caption_data = {
            'text': text,
            'speaker': speaker or 'unknown',
            'id': f"{meeting_id}_{len(session.caption_buffer)}"
        }
        session.add_caption(caption_data)

def pop_event_generator(meeting_id: str):
    """Backward compatibility: SSE event generator"""
    session = get_or_create_session(meeting_id)
    if session:
        client_id = f"sse_{meeting_id}"
        client_queue = session.add_client_queue(client_id)
        
        try:
            while True:
                try:
                    data = client_queue.get(timeout=30)  # 30 second timeout
                    yield f"data: {data}\n\n"
                except queue.Empty:
                    # Send keepalive
                    yield f"data: {json.dumps({'type': 'keepalive'})}\n\n"
                except GeneratorExit:
                    break
        finally:
            session.remove_client_queue(client_id)


if __name__ == "__main__":
    # Test the realtime system
    manager = RealtimeSessionManager()
    
    # Create a test session
    session_id = manager.create_session({
        'user_level': 'IC6',
        'user_name': 'test_user',
        'meeting_type': 'system_design_interview'
    })
    
    session = manager.get_session(session_id)
    
    # Simulate some captions
    test_captions = [
        {'id': '1', 'text': 'Hello, thanks for joining today.', 'speaker': 'interviewer'},
        {'id': '2', 'text': 'Thanks for having me.', 'speaker': 'candidate'},
        {'id': '3', 'text': 'Can you describe how you would design a URL shortening service like bit.ly?', 'speaker': 'interviewer'},
    ]
    
    for caption in test_captions:
        if session:
            session.add_caption(caption)
        time.sleep(1)
    
    # Wait a bit for processing
    time.sleep(5)
    
    # Check results
    print("Recent answers:")
    if session:
        for answer in session.get_recent_answers():
            print(f"Q: {answer['question']}")
            print(f"A: {answer['answer'][:100]}...")
            print()
    
    manager.end_session(session_id)
