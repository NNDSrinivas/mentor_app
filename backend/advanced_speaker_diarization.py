"""
Advanced Speaker Diarization Module
AI-powered speaker identification and voice separation for enhanced meeting transcription
"""

import asyncio
import json
import logging
import sqlite3
import wave
import pickle
import threading
import queue
import time
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta

# Optional ML dependencies with graceful fallbacks
try:
    import numpy as np
    import librosa  # type: ignore[reportMissingImports]
    import torch  # type: ignore[reportMissingImports]
    import torch.nn as nn  # type: ignore[reportMissingImports]
    from sklearn.cluster import AgglomerativeClustering  # type: ignore[reportMissingImports]
    from sklearn.metrics.pairwise import cosine_similarity as _real_cosine_similarity  # type: ignore[reportMissingImports]
    from transformers import Wav2Vec2Processor, Wav2Vec2Model  # type: ignore[reportMissingImports]
    ML_AVAILABLE = True
    
    # Real numpy types for type hints
    from numpy.typing import NDArray
    from typing import Union
    ArrayType = Union[NDArray, list]  # Proper type union
    
except ImportError as e:
    logging.warning(f"Machine learning dependencies not available: {e}")
    ML_AVAILABLE = False
    
    # Create mock classes for graceful degradation
    from typing import List, Union, Any
    ArrayType = Union[List[Any], Any]  # Use proper type for annotations
    
    class MockNumpy:
        ndarray = list  # Use list as mock ndarray type
        class random:
            @staticmethod
            def randn(n): return [0.0] * n
        class _dtypes:
            float32 = float
        float32 = _dtypes.float32
        
        @staticmethod
        def array(data): return data
        @staticmethod
        def zeros(shape): return [0] * (shape if isinstance(shape, int) else shape[0])
        @staticmethod
        def mean(data): return sum(data) / len(data) if data else 0
        @staticmethod
        def vstack(arrays): return arrays
        @staticmethod
        def unique(data, return_counts=False): 
            unique_vals = list(set(data))
            if return_counts:
                counts = [data.count(val) for val in unique_vals]
                return unique_vals, counts
            return unique_vals
        @staticmethod
        def argmax(arr):
            return max(range(len(arr)), key=lambda i: arr[i]) if arr else 0
        @staticmethod
        def frombuffer(buf, dtype=float):
            return list(buf)
    
    np = MockNumpy()  # Assign the mock class
    
    # Create other mock classes
    class MockLibrosa:
        @staticmethod
        def load(file_path, sr=None): return [0] * 1000, 16000
        @staticmethod
        def to_mono(y): return y
        @staticmethod
        def resample(y, orig_sr=None, target_sr=None): return y
        class feature:
            @staticmethod
            def mfcc(y, sr, n_mfcc=13): return [[0] * 13] * 100
        
    librosa = MockLibrosa()
    
    # Mock other ML classes
    class MockTorch:
        @staticmethod
        def no_grad():
            return MockContextManager()
        
    class MockContextManager:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        
    torch = MockTorch()
    
    class MockModel:
        def __init__(self, *args, **kwargs): pass
        def __call__(self, *args, **kwargs): return MockModelOutput()
        
    class MockModelOutput:
        last_hidden_state = [[0] * 768] * 100
        
    class MockProcessor:
        def __init__(self, *args, **kwargs): pass
        def __call__(self, *args, **kwargs): return {"input_values": [[0] * 1000]}
        
    Wav2Vec2Model = MockModel
    Wav2Vec2Processor = MockProcessor
    
    class MockClustering:
        def __init__(self, *args, **kwargs): pass
        def fit_predict(self, data): return [0] * len(data)
        
    AgglomerativeClustering = MockClustering
    
    def _mock_cosine_similarity(a, b): return [[0.8]]
    _real_cosine_similarity = _mock_cosine_similarity  # type: ignore[assignment]

logger = logging.getLogger(__name__)

@dataclass
class SpeakerSegment:
    """Represents a segment of audio with identified speaker"""
    start_time: float
    end_time: float
    speaker_id: str
    speaker_name: Optional[str]
    confidence: float
    text: Optional[str] = None
    audio_features: Optional[Any] = None

@dataclass
class VoiceProfile:
    """Voice profile for speaker identification"""
    speaker_id: str
    speaker_name: Optional[str]
    voice_embedding: Any  # Array-like data structure
    sample_count: int
    last_updated: datetime
    confidence_scores: List[float]

class VoiceEmbeddingExtractor:
    """Extract voice embeddings using Wav2Vec2 model"""
    
    def __init__(self):
        if not ML_AVAILABLE:
            logger.warning("ML dependencies not available, using mock embedding extractor")
            self.processor = None
            self.model = None
            return
            
        try:
            from transformers import Wav2Vec2Processor, Wav2Vec2Model
            self.processor = Wav2Vec2Processor.from_pretrained("facebook/wav2vec2-base-960h")
            self.model = Wav2Vec2Model.from_pretrained("facebook/wav2vec2-base-960h")
            self.model.eval()
        except Exception as e:
            logger.error(f"Failed to load Wav2Vec2 model: {e}")
            self.processor = None
            self.model = None
    
    def extract_embedding(self, audio_segment, sample_rate: int = 16000):
        """Extract voice embedding from audio segment"""
        if not ML_AVAILABLE or self.model is None or self.processor is None:
            # Return mock embedding
            return np.zeros(768)
            
        try:
            # Resample if necessary
            if hasattr(audio_segment, 'shape') and len(audio_segment.shape) > 1:
                audio_segment = librosa.to_mono(audio_segment.T)
            
            if sample_rate != 16000:
                audio_segment = librosa.resample(audio_segment, orig_sr=sample_rate, target_sr=16000)
            
            # Process with Wav2Vec2
            inputs = self.processor(audio_segment, sampling_rate=16000, return_tensors="pt", padding=True)
            
            with torch.no_grad():
                outputs = self.model(**inputs)
                # Use mean pooling of last hidden states
                embedding = outputs.last_hidden_state.mean(dim=1).squeeze().numpy()
            
            return embedding
            
        except Exception as e:
            logger.error(f"Error extracting voice embedding: {e}")
            return np.zeros(768)  # Default embedding size for wav2vec2-base

class SpeakerClustering:
    """Clustering algorithm for speaker separation"""
    
    def __init__(self, distance_threshold: float = 0.7):
        self.distance_threshold = distance_threshold
        self.clustering_model = None
    
    def cluster_speakers(self, embeddings: List, 
                        time_segments: List[Tuple[float, float]]) -> List[int]:
        """Cluster embeddings into speaker groups"""
        if not ML_AVAILABLE:
            # Return simple sequential speaker IDs when ML is not available
            return list(range(len(embeddings)))
            
        if len(embeddings) < 2:
            return [0] * len(embeddings)
        
        try:
            # Convert to numpy array
            embedding_matrix = np.vstack(embeddings)
            
            # Use Agglomerative Clustering with cosine distance
            from sklearn.cluster import AgglomerativeClustering
            clustering = AgglomerativeClustering(
                n_clusters=None,
                distance_threshold=self.distance_threshold,
                linkage='average',
                metric='cosine'
            )
            
            speaker_labels = clustering.fit_predict(embedding_matrix)
            
            # Post-process to handle temporal consistency
            speaker_labels = self._temporal_smoothing(speaker_labels, time_segments)
            
            return speaker_labels.tolist()
        except Exception as e:
            logger.error(f"Error in speaker clustering: {e}")
            return list(range(len(embeddings)))
    
    def _temporal_smoothing(self, labels: Any, 
                           time_segments: List[Tuple[float, float]],
                           window_size: float = 2.0) -> Any:
        """Apply temporal smoothing to reduce speaker switching noise"""
        smoothed_labels = labels.copy()
        
        for i in range(len(labels)):
            if i == 0 or i == len(labels) - 1:
                continue
                
            current_time = time_segments[i][0]
            
            # Find neighboring segments within window
            neighbors = []
            for j in range(len(labels)):
                if abs(time_segments[j][0] - current_time) <= window_size:
                    neighbors.append(labels[j])
            
            # Use majority vote
            if len(neighbors) > 1:
                unique, counts = np.unique(neighbors, return_counts=True)
                majority_label = unique[np.argmax(counts)]
                smoothed_labels[i] = majority_label
        
        return smoothed_labels

class VoiceProfileManager:
    """Manage speaker voice profiles and identification"""
    
    def __init__(self, db_path: str = "data/voice_profiles.db"):
        self.db_path = db_path
        self.profiles: Dict[str, VoiceProfile] = {}
        self._init_database()
        self._load_profiles()
    
    def _init_database(self):
        """Initialize voice profiles database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS voice_profiles (
                    speaker_id TEXT PRIMARY KEY,
                    speaker_name TEXT,
                    voice_embedding BLOB,
                    sample_count INTEGER,
                    last_updated TEXT,
                    confidence_scores TEXT
                )
            ''')
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error initializing voice profiles database: {e}")
    
    def _load_profiles(self):
        """Load voice profiles from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM voice_profiles')
            rows = cursor.fetchall()
            
            for row in rows:
                speaker_id, speaker_name, embedding_blob, sample_count, last_updated, confidence_scores = row
                
                voice_embedding = pickle.loads(embedding_blob)
                confidence_scores = json.loads(confidence_scores)
                last_updated = datetime.fromisoformat(last_updated)
                
                profile = VoiceProfile(
                    speaker_id=speaker_id,
                    speaker_name=speaker_name,
                    voice_embedding=voice_embedding,
                    sample_count=sample_count,
                    last_updated=last_updated,
                    confidence_scores=confidence_scores
                )
                
                self.profiles[speaker_id] = profile
            
            conn.close()
            logger.info(f"Loaded {len(self.profiles)} voice profiles")
            
        except Exception as e:
            logger.error(f"Error loading voice profiles: {e}")
    
    def save_profile(self, profile: VoiceProfile):
        """Save voice profile to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            embedding_blob = pickle.dumps(profile.voice_embedding)
            confidence_scores_json = json.dumps(profile.confidence_scores)
            
            cursor.execute('''
                INSERT OR REPLACE INTO voice_profiles 
                (speaker_id, speaker_name, voice_embedding, sample_count, last_updated, confidence_scores)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                profile.speaker_id,
                profile.speaker_name,
                embedding_blob,
                profile.sample_count,
                profile.last_updated.isoformat(),
                confidence_scores_json
            ))
            
            conn.commit()
            conn.close()
            
            self.profiles[profile.speaker_id] = profile
            
        except Exception as e:
            logger.error(f"Error saving voice profile: {e}")
    
    def identify_speaker(self, embedding: Any, 
                        threshold: float = 0.8) -> Tuple[Optional[str], float]:
        """Identify speaker from voice embedding"""
        if not self.profiles:
            return None, 0.0
        
        best_match = None
        best_similarity = 0.0
        
        for speaker_id, profile in self.profiles.items():
            similarity = _real_cosine_similarity(
                embedding.reshape(1, -1),
                profile.voice_embedding.reshape(1, -1)
            )[0][0]
            
            if similarity > best_similarity:
                best_similarity = similarity
                best_match = speaker_id
        
        if best_similarity >= threshold:
            return best_match, best_similarity
        
        return None, best_similarity
    
    def update_profile(self, speaker_id: str, new_embedding: Any, confidence: float):
        """Update existing voice profile with new sample"""
        if speaker_id in self.profiles:
            profile = self.profiles[speaker_id]
            
            # Exponential moving average for embedding update
            alpha = 0.3  # Learning rate
            profile.voice_embedding = (
                alpha * new_embedding + 
                (1 - alpha) * profile.voice_embedding
            )
            
            profile.sample_count += 1
            profile.last_updated = datetime.now()
            profile.confidence_scores.append(confidence)
            
            # Keep only last 100 confidence scores
            if len(profile.confidence_scores) > 100:
                profile.confidence_scores = profile.confidence_scores[-100:]
            
            self.save_profile(profile)
    
    def create_new_profile(self, embedding: Any, 
                          speaker_name: Optional[str] = None) -> str:
        """Create new voice profile for unknown speaker"""
        speaker_id = f"speaker_{len(self.profiles) + 1}_{int(time.time())}"
        
        profile = VoiceProfile(
            speaker_id=speaker_id,
            speaker_name=speaker_name,
            voice_embedding=embedding,
            sample_count=1,
            last_updated=datetime.now(),
            confidence_scores=[1.0]
        )
        
        self.save_profile(profile)
        return speaker_id

class RealTimeSpeakerDiarization:
    """Real-time speaker diarization system"""
    
    def __init__(self, segment_duration: float = 2.0, overlap: float = 0.5):
        self.segment_duration = segment_duration
        self.overlap = overlap
        self.embedding_extractor = VoiceEmbeddingExtractor()
        self.clustering = SpeakerClustering()
        self.profile_manager = VoiceProfileManager()
        
        self.audio_buffer = queue.Queue()
        self.result_queue = queue.Queue()
        self.is_processing = False
        self.processing_thread = None
    
    def start_processing(self):
        """Start real-time processing thread"""
        if not self.is_processing:
            self.is_processing = True
            self.processing_thread = threading.Thread(target=self._processing_loop)
            self.processing_thread.daemon = True
            self.processing_thread.start()
            logger.info("Started real-time speaker diarization")
    
    def stop_processing(self):
        """Stop real-time processing"""
        self.is_processing = False
        if self.processing_thread:
            self.processing_thread.join()
        logger.info("Stopped real-time speaker diarization")
    
    def add_audio_chunk(self, audio_chunk: Any, timestamp: float):
        """Add audio chunk for processing"""
        self.audio_buffer.put((audio_chunk, timestamp))
    
    def get_latest_results(self) -> List[SpeakerSegment]:
        """Get latest diarization results"""
        results = []
        while not self.result_queue.empty():
            try:
                result = self.result_queue.get_nowait()
                results.append(result)
            except queue.Empty:
                break
        return results
    
    def _processing_loop(self):
        """Main processing loop for real-time diarization"""
        audio_segments = []
        
        while self.is_processing:
            try:
                # Collect audio segments
                try:
                    audio_chunk, timestamp = self.audio_buffer.get(timeout=0.1)
                    audio_segments.append((audio_chunk, timestamp))
                except queue.Empty:
                    continue
                
                # Process when we have enough segments
                if len(audio_segments) >= 3:  # Process in batches
                    self._process_audio_batch(audio_segments)
                    # Keep some overlap
                    audio_segments = audio_segments[-1:]
                
            except Exception as e:
                logger.error(f"Error in processing loop: {e}")
                time.sleep(0.1)
    
    def _process_audio_batch(self, audio_segments: List[Tuple[Any, float]]):
        """Process batch of audio segments"""
        try:
            segments = []
            embeddings = []
            time_ranges = []
            
            for audio_chunk, timestamp in audio_segments:
                if len(audio_chunk) > 0:
                    # Extract embedding
                    embedding = self.embedding_extractor.extract_embedding(audio_chunk)
                    
                    # Identify or cluster speaker
                    speaker_id, confidence = self.profile_manager.identify_speaker(embedding)
                    
                    if speaker_id is None:
                        # Create new speaker profile
                        speaker_id = self.profile_manager.create_new_profile(embedding)
                        confidence = 0.5  # Medium confidence for new speaker
                    else:
                        # Update existing profile
                        self.profile_manager.update_profile(speaker_id, embedding, confidence)
                    
                    # Create speaker segment
                    segment = SpeakerSegment(
                        start_time=timestamp,
                        end_time=timestamp + self.segment_duration,
                        speaker_id=speaker_id,
                        speaker_name=self.profile_manager.profiles[speaker_id].speaker_name,
                        confidence=confidence,
                        audio_features=embedding
                    )
                    
                    segments.append(segment)
                    self.result_queue.put(segment)
            
        except Exception as e:
            logger.error(f"Error processing audio batch: {e}")

class AdvancedSpeakerDiarization:
    """Main speaker diarization service"""
    
    def __init__(self):
        self.realtime_diarization = RealTimeSpeakerDiarization()
        self.meeting_sessions: Dict[str, List[SpeakerSegment]] = {}
        self.active_session_id: Optional[str] = None
    
    async def start_meeting_diarization(self, session_id: str) -> bool:
        """Start speaker diarization for a meeting session"""
        try:
            self.active_session_id = session_id
            self.meeting_sessions[session_id] = []
            self.realtime_diarization.start_processing()
            
            logger.info(f"Started speaker diarization for session: {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error starting meeting diarization: {e}")
            return False
    
    async def stop_meeting_diarization(self) -> Dict[str, Any]:
        """Stop speaker diarization and return session summary"""
        try:
            if self.active_session_id:
                self.realtime_diarization.stop_processing()
                
                # Get final results
                results = self.realtime_diarization.get_latest_results()
                self.meeting_sessions[self.active_session_id].extend(results)
                
                # Generate summary
                summary = self._generate_session_summary(self.active_session_id)
                
                logger.info(f"Stopped speaker diarization for session: {self.active_session_id}")
                self.active_session_id = None
                
                return summary
            
            return {"error": "No active diarization session"}
            
        except Exception as e:
            logger.error(f"Error stopping meeting diarization: {e}")
            return {"error": str(e)}
    
    async def process_audio_stream(self, audio_data: bytes, timestamp: float) -> List[SpeakerSegment]:
        """Process incoming audio stream"""
        try:
            # Convert bytes to numpy array
            # Use a basic dtype for mock numpy to satisfy type checkers
            dtype = getattr(np, 'float32', float)
            audio_array = np.frombuffer(audio_data, dtype=dtype)
            
            # Add to real-time processor
            self.realtime_diarization.add_audio_chunk(audio_array, timestamp)
            
            # Get latest results
            results = self.realtime_diarization.get_latest_results()
            
            if self.active_session_id and results:
                self.meeting_sessions[self.active_session_id].extend(results)
            
            return results
            
        except Exception as e:
            logger.error(f"Error processing audio stream: {e}")
            return []
    
    def _generate_session_summary(self, session_id: str) -> Dict[str, Any]:
        """Generate summary of diarization session"""
        if session_id not in self.meeting_sessions:
            return {"error": "Session not found"}
        
        segments = self.meeting_sessions[session_id]
        
        # Calculate speaker statistics
        speaker_stats = {}
        total_duration = 0
        
        for segment in segments:
            speaker_id = segment.speaker_id
            duration = segment.end_time - segment.start_time
            
            if speaker_id not in speaker_stats:
                speaker_stats[speaker_id] = {
                    "speaker_id": speaker_id,
                    "speaker_name": segment.speaker_name or f"Speaker {speaker_id}",
                    "total_time": 0,
                    "segment_count": 0,
                    "avg_confidence": 0,
                    "confidence_scores": []
                }
            
            speaker_stats[speaker_id]["total_time"] += duration
            speaker_stats[speaker_id]["segment_count"] += 1
            speaker_stats[speaker_id]["confidence_scores"].append(segment.confidence)
            total_duration += duration
        
        # Calculate averages and percentages
        for speaker_id, stats in speaker_stats.items():
            stats["avg_confidence"] = np.mean(stats["confidence_scores"])
            stats["time_percentage"] = (stats["total_time"] / total_duration * 100) if total_duration > 0 else 0
            del stats["confidence_scores"]  # Remove raw scores from summary
        
        return {
            "session_id": session_id,
            "total_duration": total_duration,
            "total_segments": len(segments),
            "unique_speakers": len(speaker_stats),
            "speaker_statistics": list(speaker_stats.values()),
            "segments": [
                {
                    "start_time": seg.start_time,
                    "end_time": seg.end_time,
                    "speaker_id": seg.speaker_id,
                    "speaker_name": seg.speaker_name,
                    "confidence": seg.confidence
                }
                for seg in segments
            ]
        }
    
    async def get_speaker_profiles(self) -> List[Dict[str, Any]]:
        """Get all speaker profiles"""
        try:
            profiles = []
            for speaker_id, profile in self.realtime_diarization.profile_manager.profiles.items():
                profiles.append({
                    "speaker_id": speaker_id,
                    "speaker_name": profile.speaker_name,
                    "sample_count": profile.sample_count,
                    "last_updated": profile.last_updated.isoformat(),
                    "avg_confidence": np.mean(profile.confidence_scores) if profile.confidence_scores else 0
                })
            
            return profiles
            
        except Exception as e:
            logger.error(f"Error getting speaker profiles: {e}")
            return []
    
    async def update_speaker_name(self, speaker_id: str, speaker_name: str) -> bool:
        """Update speaker name in profile"""
        try:
            profile_manager = self.realtime_diarization.profile_manager
            if speaker_id in profile_manager.profiles:
                profile = profile_manager.profiles[speaker_id]
                profile.speaker_name = speaker_name
                profile_manager.save_profile(profile)
                
                logger.info(f"Updated speaker name: {speaker_id} -> {speaker_name}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error updating speaker name: {e}")
            return False

# Initialize global diarization service
diarization_service = AdvancedSpeakerDiarization()

if __name__ == "__main__":
    # Test the diarization system
    async def test_diarization():
        service = AdvancedSpeakerDiarization()
        
        # Start diarization
        await service.start_meeting_diarization("test_session")
        
        # Simulate audio processing
        for i in range(10):
            fake_audio = np.random.randn(16000).astype(np.float32)  # 1 second of fake audio
            results = await service.process_audio_stream(fake_audio.tobytes(), i * 1.0)
            print(f"Processed chunk {i}, found {len(results)} segments")
            await asyncio.sleep(0.1)
        
        # Stop and get summary
        summary = await service.stop_meeting_diarization()
        print(f"Session summary: {json.dumps(summary, indent=2)}")
        
        # Get speaker profiles
        profiles = await service.get_speaker_profiles()
        print(f"Speaker profiles: {json.dumps(profiles, indent=2)}")
    
    # Run test
    asyncio.run(test_diarization())
