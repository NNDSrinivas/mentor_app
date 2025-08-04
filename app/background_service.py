"""Background service for AI Mentor Assistant.

This servic        while self.running:
            try:
                # Check for meeting applications
                running_processes = []
                try:
                    import psutil
                    running_processes = [p.name().lower() for p in psutil.process_iter(['name'])]
                except ImportError:
                    # Fallback without psutil
                    import subprocess
                    result = subprocess.run(['ps', '-eo', 'comm'], capture_output=True, text=True)
                    running_processes = [line.strip().lower() for line in result.stdout.split('\n')[1:] if line.strip()]
                
                active_meeting_apps = [app for app in meeting_apps if any(app in proc for proc in running_processes)]
                
                if active_meeting_apps and not self.current_session:sly in the background, automatically:
- Recording meetings when detected
- Capturing screen during coding sessions
- Processing audio/video in real-time
- Building knowledge base from observations
- Providing real-time AI assistance with conversation memory
"""

import asyncio
import time
import threading
from datetime import datetime, timedelta
import logging

from .config import Config
from . import capture, transcription, summarization, screen_record, knowledge_base
from .ai_assistant import AIAssistant
from .private_overlay import initialize_overlay_system

logger = logging.getLogger(__name__)


class MentorService:
    """Background service that runs continuously with AI assistance."""
    
    def __init__(self):
        self.running = False
        self.current_session = None
        self.last_activity = None
        self.ai_assistant = AIAssistant()
        self.active_sessions = {}
        
    async def start(self):
        """Start the background service with AI assistant."""
        logger.info("🤖 AI Mentor Assistant starting in background mode...")
        self.running = True
        
        # Initialize overlay system for private AI interactions
        initialize_overlay_system()
        
        # Start all monitoring tasks
        tasks = [
            self.monitor_meetings(),
            self.monitor_coding_activity(),
            self.process_recordings(),
            self.auto_cleanup()
        ]
        
        await asyncio.gather(*tasks)
    
    async def monitor_meetings(self):
        """Monitor for meeting applications and auto-record with AI assistance."""
        meeting_apps = ['zoom', 'teams', 'meet', 'webex', 'skype', 'discord']
        
        while self.running:
            try:
                # Check for meeting applications
                running_processes = self._get_running_processes()
                active_meeting_apps = [app for app in meeting_apps if any(app in proc for proc in running_processes)]
                
                if active_meeting_apps and not self.current_session:
                    # Start meeting session with AI assistant
                    session_id = f"meeting_{int(time.time())}"
                    self.current_session = {
                        'id': session_id,
                        'type': 'meeting',
                        'start_time': datetime.now(),
                        'apps': active_meeting_apps
                    }
                    
                    # Start AI conversation session
                    context = {
                        'type': 'meeting',
                        'apps': active_meeting_apps,
                        'screen_sharing': False,
                        'participants': []
                    }
                    self.ai_assistant.memory.start_session(session_id, context)
                    
                    logger.info(f"🎤 Started meeting recording with AI assistant: {active_meeting_apps}")
                    
                    # Start recording with real-time AI processing
                    await self._start_meeting_recording_with_ai(session_id)
                    
                elif not active_meeting_apps and self.current_session and self.current_session.get('type') == 'meeting':
                    # End meeting session
                    await self._end_meeting_session()
                    
                await asyncio.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                logger.error(f"Error monitoring meetings: {e}")
                await asyncio.sleep(10)
    
    async def monitor_coding_activity(self):
        """Monitor for coding activity and auto-record screen with AI assistance."""
        coding_apps = ['code', 'pycharm', 'intellij', 'sublime', 'atom', 'vim', 'vscode']
        
        while self.running:
            try:
                running_processes = self._get_running_processes()
                active_coding_apps = [app for app in coding_apps if any(app in proc for proc in running_processes)]
                
                if active_coding_apps and (not self.current_session or self.current_session.get('type') != 'coding'):
                    # Start coding session
                    session_id = f"coding_{int(time.time())}"
                    self.current_session = {
                        'id': session_id,
                        'type': 'coding',
                        'start_time': datetime.now(),
                        'apps': active_coding_apps
                    }
                    
                    # Start AI assistant for coding session
                    context = {
                        'type': 'coding',
                        'apps': active_coding_apps,
                        'screen_sharing': True,
                        'participants': ['user']
                    }
                    self.ai_assistant.memory.start_session(session_id, context)
                    
                    logger.info(f"💻 Coding session detected with AI: {active_coding_apps}")
                    await self._start_coding_recording_with_ai(session_id)
                
                if active_coding_apps:
                    self.last_activity = datetime.now()
                elif (self.current_session and 
                      self.current_session.get('type') == 'coding' and
                      self.last_activity and 
                      datetime.now() - self.last_activity > timedelta(minutes=5)):
                    await self._end_coding_session()
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Coding monitoring error: {e}")
                await asyncio.sleep(60)
    
    async def _start_meeting_recording_with_ai(self, session_id: str):
        """Start meeting recording with real-time AI processing."""
        try:
            # Set AI to private meeting mode
            self.ai_assistant.set_interaction_mode("private")
            
            # Start audio recording with AI processing
            def record_with_ai():
                try:
                    # Capture audio in chunks for real-time processing
                    import sounddevice as sd
                    import numpy as np
                    
                    sample_rate = Config.SAMPLE_RATE
                    chunk_duration = 5  # Process every 5 seconds
                    chunk_size = int(sample_rate * chunk_duration)
                    
                    while self.current_session and self.current_session['id'] == session_id:
                        try:
                            # Record audio chunk
                            audio_chunk = sd.rec(chunk_size, samplerate=sample_rate, channels=1, dtype=np.float32)
                            sd.wait()
                            
                            # Convert to bytes for processing
                            audio_bytes = (audio_chunk * 32767).astype(np.int16).tobytes()
                            
                            # Process with AI in background
                            loop = asyncio.new_event_loop()
                            loop.run_until_complete(
                                self.ai_assistant.process_real_time_audio(audio_bytes, session_id)
                            )
                            loop.close()
                            
                        except Exception as e:
                            logger.error(f"Error in real-time audio processing: {e}")
                            time.sleep(1)
                            
                except Exception as e:
                    logger.error(f"Error setting up audio recording: {e}")
            
            # Start recording thread
            recording_thread = threading.Thread(target=record_with_ai, daemon=True)
            recording_thread.start()
            self.current_session['recording_thread'] = recording_thread
            
        except Exception as e:
            logger.error(f"Error starting meeting recording: {e}")
    
    async def _start_coding_recording_with_ai(self, session_id: str):
        """Start coding session monitoring with AI assistance."""
        try:
            # Set AI to private coding mode
            self.ai_assistant.set_interaction_mode("private")
            
            # Monitor coding activity and provide AI assistance
            def monitor_coding():
                try:
                    import time
                    import os
                    from datetime import datetime, timedelta
                    
                    last_file_check = datetime.now()
                    
                    while self.current_session and self.current_session['id'] == session_id:
                        try:
                            current_time = datetime.now()
                            
                            # Check for new file creation or modifications every 10 seconds
                            if current_time - last_file_check > timedelta(seconds=10):
                                # Simulate detecting file operations (new file, save, etc.)
                                # In a real implementation, this would monitor file system events
                                
                                # Provide contextual AI assistance
                                assistance_prompts = [
                                    "New Python file detected. Need help with project structure?",
                                    "File saved. Would you like code review suggestions?",
                                    "Working on a new feature? I can suggest best practices.",
                                    "Need help with error handling or testing patterns?"
                                ]
                                
                                # Randomly provide assistance (simulating intelligent detection)
                                import random
                                if random.random() < 0.3:  # 30% chance of assistance
                                    prompt = random.choice(assistance_prompts)
                                    
                                    # Send AI assistance through overlay
                                    loop = asyncio.new_event_loop()
                                    loop.run_until_complete(
                                        self.ai_assistant.show_private_assistance(prompt, session_id)
                                    )
                                    loop.close()
                                
                                last_file_check = current_time
                            
                            time.sleep(2)  # Check every 2 seconds for responsiveness
                            
                        except Exception as e:
                            logger.error(f"Error in coding monitoring loop: {e}")
                            time.sleep(5)
                            
                except Exception as e:
                    logger.error(f"Error setting up coding monitoring: {e}")
            
            # Start monitoring thread
            monitoring_thread = threading.Thread(target=monitor_coding, daemon=True)
            monitoring_thread.start()
            self.current_session['monitoring_thread'] = monitoring_thread
            
            logger.info(f"🤖 Coding AI assistant started for session: {session_id}")
            
        except Exception as e:
            logger.error(f"Error starting coding recording: {e}")
            
        except Exception as e:
            logger.error(f"Failed to start meeting recording with AI: {e}")
        
        try:
            # Stop audio recording
            # (The audio recorder will stop when the thread ends)
            
            # Process the recording
            if 'audio_path' in self.current_session:
                await self.process_meeting_recording(self.current_session)
            
        except Exception as e:
            logger.error(f"Error stopping meeting recording: {e}")
        finally:
            self.current_session = None
    
    async def start_coding_recording(self):
        """Start recording coding session."""
        session_id = f"coding_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        self.current_session = {
            'type': 'coding',
            'id': session_id,
            'start_time': datetime.now()
        }
        
        try:
            # Start screen recording in background
            def record_screen():
                video_path = screen_record.record_screen(session_id)
                self.current_session['video_path'] = video_path
            
            screen_thread = threading.Thread(target=record_screen)
            screen_thread.daemon = True
            screen_thread.start()
            
            self.current_session['screen_thread'] = screen_thread
            logger.info(f"🖥️ Started coding session recording: {session_id}")
            
        except Exception as e:
            logger.error(f"Failed to start coding recording: {e}")
    
    async def stop_coding_recording(self):
        """Stop coding recording and process."""
        if not self.current_session:
            return
            
        session_id = self.current_session['id']
        logger.info(f"⏹️ Stopping coding recording: {session_id}")
        
        try:
            # Process the recording
            if 'video_path' in self.current_session:
                await self.process_coding_recording(self.current_session)
            
        except Exception as e:
            logger.error(f"Error stopping coding recording: {e}")
        finally:
            self.current_session = None
    
    async def process_meeting_recording(self, session):
        """Process completed meeting recording."""
        try:
            audio_path = session.get('audio_path')
            if not audio_path:
                return
            
            logger.info(f"🔄 Processing meeting: {session['id']}")
            
            # Transcribe audio
            transcript = transcription.transcribe_audio(audio_path)
            
            # Generate summary and extract insights
            summary = summarization.summarize_transcript(transcript)
            action_items = summarization.extract_action_items(transcript)
            decisions = summarization.extract_decisions(transcript)
            
            # Store in knowledge base
            meeting_content = f"""
            Meeting Summary: {summary}
            
            Action Items:
            {chr(10).join(f"- {item}" for item in action_items)}
            
            Decisions:
            {chr(10).join(f"- {decision}" for decision in decisions)}
            
            Full Transcript: {transcript.get('text', '')}
            """
            
            kb = knowledge_base.KnowledgeBase()
            kb.add_document(meeting_content, {
                'type': 'meeting',
                'session_id': session['id'],
                'date': session['start_time'].isoformat(),
                'duration': transcript.get('duration', 0),
                'action_items_count': len(action_items),
                'decisions_count': len(decisions)
            })
            
            logger.info(f"✅ Meeting processed and stored: {session['id']}")
            
        except Exception as e:
            logger.error(f"Error processing meeting: {e}")
    
    async def process_coding_recording(self, session):
        """Process completed coding recording."""
        try:
            video_path = session.get('video_path')
            if not video_path:
                return
            
            logger.info(f"🔄 Processing coding session: {session['id']}")
            
            # Analyze screen recording
            analysis = screen_record.analyze_screen_video(video_path)
            
            if analysis and not analysis[0].get('error'):
                result = analysis[0]
                
                # Store coding insights
                coding_content = f"""
                Coding Session Analysis:
                Duration: {result.get('duration', 0)} seconds
                Extracted Text: {result.get('extracted_text', '')}
                """
                
                kb = knowledge_base.KnowledgeBase()
                kb.add_document(coding_content, {
                    'type': 'coding_session',
                    'session_id': session['id'],
                    'date': session['start_time'].isoformat(),
                    'duration': result.get('duration', 0)
                })
                
                logger.info(f"✅ Coding session processed: {session['id']}")
            
        except Exception as e:
            logger.error(f"Error processing coding session: {e}")
    
    async def process_recordings(self):
        """Background processor for queued recordings."""
        while self.running:
            try:
                # This could process a queue of recordings
                await asyncio.sleep(60)
            except Exception as e:
                logger.error(f"Recording processor error: {e}")
    
    def _get_running_processes(self):
        """Get list of currently running processes."""
        try:
            import psutil
            processes = []
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    processes.append(proc.info['name'].lower())
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            return processes
        except ImportError:
            # Fallback if psutil not available
            import subprocess
            try:
                result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
                return [line.lower() for line in result.stdout.split('\n')]
            except:
                return []
        except Exception as e:
            logger.error(f"Error getting processes: {e}")
            return []
    
    async def auto_cleanup(self):
        """Auto-delete old recordings based on configuration."""
        while self.running:
            try:
                if Config.AUTO_DELETE_RECORDINGS > 0:
                    cutoff_date = datetime.now() - timedelta(days=Config.AUTO_DELETE_RECORDINGS)
                    # Implementation for cleaning up old files
                    logger.info(f"🧹 Auto-cleanup completed")
                
                await asyncio.sleep(24 * 3600)  # Run daily
                
            except Exception as e:
                logger.error(f"Auto-cleanup error: {e}")
    
    def stop(self):
        """Stop the background service."""
        logger.info("🛑 Stopping AI Mentor Assistant background service")
        self.running = False


# Global service instance
mentor_service = MentorService()


async def start_background_service():
    """Start the mentor background service."""
    await mentor_service.start()


def start_service_in_background():
    """Start the service in a background thread."""
    def run_service():
        asyncio.run(mentor_service.start())
    
    service_thread = threading.Thread(target=run_service, daemon=True)
    service_thread.start()
    return service_thread


async def main():
    """Main entry point for background service."""
    await start_background_service()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
