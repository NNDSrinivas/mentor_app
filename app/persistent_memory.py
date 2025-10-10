"""
Advanced Persistent Memory System
Inspired by how Cluely and Firefly maintain context across sessions.

This system remembers EVERYTHING:
- Meeting discussions and decisions
- Task assignments and progress
- Code changes and patterns
- Team dynamics and relationships
- Project evolution over time
"""
import asyncio
import json
import logging
import sqlite3
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
import numpy as np

# Vector database for semantic search
try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    chromadb = None

# Graph database for relationships (optional)
try:
    from py2neo import Graph, Node, Relationship
    GRAPH_DB_AVAILABLE = True
except ImportError:
    GRAPH_DB_AVAILABLE = False
    Graph = None

logger = logging.getLogger(__name__)

@dataclass
class MemoryEntry:
    """Base class for all memory entries"""
    entry_id: str
    entry_type: str
    content: Dict[str, Any]
    metadata: Dict[str, Any]
    timestamp: str
    context_hash: str
    importance_score: float
    
@dataclass
class Relationship:
    """Represents a relationship between entities"""
    from_entity: str
    to_entity: str
    relationship_type: str
    strength: float
    context: Dict[str, Any]
    created_at: str

class PersistentMemory:
    """
    Advanced Memory System that remembers everything across sessions
    
    Architecture:
    - SQLite: Structured data (meetings, tasks, users, projects)
    - ChromaDB: Vector embeddings for semantic search
    - Graph DB: Relationships and entity connections
    - File Storage: Large files (recordings, documents)
    """
    
    def __init__(self, db_path: str = "data/ai_memory.db"):
        self.db_path = db_path
        self.vector_db = None
        self.graph_db = None
        
        # Initialize SQLite database
        self._init_sqlite_db()
        
        # Initialize vector database
        if CHROMADB_AVAILABLE:
            self._init_vector_db()
        else:
            logger.warning("⚠️ ChromaDB not available - semantic search disabled")
        
        # Initialize graph database (optional)
        if GRAPH_DB_AVAILABLE:
            self._init_graph_db()
        else:
            logger.warning("⚠️ Graph DB not available - relationship mapping limited")
        
        logger.info("🧠 Persistent Memory System initialized")
    
    def _init_sqlite_db(self):
        """Initialize SQLite database with comprehensive schema"""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        
        # Create tables
        cursor = self.conn.cursor()
        
        # Core memory entries
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memory_entries (
                entry_id TEXT PRIMARY KEY,
                entry_type TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                context_hash TEXT NOT NULL,
                importance_score REAL DEFAULT 0.5,
                embedding_vector TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Meeting records
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS meetings (
                meeting_id TEXT PRIMARY KEY,
                title TEXT,
                participants TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT,
                platform TEXT,
                transcript TEXT,
                summary TEXT,
                action_items TEXT,
                decisions TEXT,
                recording_path TEXT,
                meeting_type TEXT,
                project_id TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Task records
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                task_id TEXT PRIMARY KEY,
                external_id TEXT,
                title TEXT NOT NULL,
                description TEXT,
                status TEXT,
                priority TEXT,
                assignee TEXT,
                project_id TEXT,
                epic_id TEXT,
                story_points INTEGER,
                requirements TEXT,
                acceptance_criteria TEXT,
                related_meetings TEXT,
                implementation_notes TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Code/PR records
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS code_changes (
                change_id TEXT PRIMARY KEY,
                repository TEXT,
                branch TEXT,
                commit_hash TEXT,
                pr_number TEXT,
                files_changed TEXT,
                diff_summary TEXT,
                description TEXT,
                author TEXT,
                reviewers TEXT,
                related_tasks TEXT,
                build_status TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Team members and relationships
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS team_members (
                member_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT,
                role TEXT,
                expertise_areas TEXT,
                communication_style TEXT,
                projects TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Projects
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                project_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                status TEXT,
                team_members TEXT,
                repositories TEXT,
                architecture_notes TEXT,
                documentation_links TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # AI decisions and feedback
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ai_decisions (
                decision_id TEXT PRIMARY KEY,
                decision_type TEXT NOT NULL,
                context TEXT NOT NULL,
                reasoning TEXT,
                confidence REAL,
                user_approved BOOLEAN,
                user_feedback TEXT,
                outcome TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # User feedback for learning
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_feedback (
                feedback_id TEXT PRIMARY KEY,
                category TEXT,
                rating INTEGER,
                comments TEXT,
                context TEXT,
                improvement_suggestions TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Relationships between entities
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS entity_relationships (
                relationship_id TEXT PRIMARY KEY,
                from_entity_type TEXT NOT NULL,
                from_entity_id TEXT NOT NULL,
                to_entity_type TEXT NOT NULL,
                to_entity_id TEXT NOT NULL,
                relationship_type TEXT NOT NULL,
                strength REAL DEFAULT 1.0,
                context TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes for better performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_memory_type ON memory_entries(entry_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_memory_timestamp ON memory_entries(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_meeting_participants ON meetings(participants)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_task_assignee ON tasks(assignee)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_task_project ON tasks(project_id)")
        
        self.conn.commit()
        logger.info("✅ SQLite database initialized with comprehensive schema")
    
    def _init_vector_db(self):
        """Initialize ChromaDB for semantic search"""
        try:
            self.chroma_client = chromadb.PersistentClient(path="data/chroma_memory")
            
            # Create collections
            self.collections = {
                'meetings': self.chroma_client.get_or_create_collection("meetings"),
                'tasks': self.chroma_client.get_or_create_collection("tasks"),
                'code': self.chroma_client.get_or_create_collection("code"),
                'decisions': self.chroma_client.get_or_create_collection("decisions"),
                'general': self.chroma_client.get_or_create_collection("general")
            }
            
            logger.info("✅ ChromaDB vector database initialized")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize ChromaDB: {e}")
            self.vector_db = None
    
    def _init_graph_db(self):
        """Initialize graph database for relationships"""
        try:
            # For now, we'll use SQLite for relationships
            # In production, consider Neo4j or similar
            logger.info("✅ Using SQLite for relationship storage")
        except Exception as e:
            logger.error(f"❌ Graph DB initialization failed: {e}")
    
    async def store_context(self, context_type, data: Dict[str, Any]) -> str:
        """Store context in the memory system"""
        
        # Generate unique entry ID
        entry_id = f"{context_type.value}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hashlib.md5(str(data).encode()).hexdigest()[:8]}"
        
        # Calculate context hash for deduplication
        context_hash = hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
        
        # Calculate importance score
        importance_score = self._calculate_importance(context_type, data)
        
        # Store in SQLite
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO memory_entries 
            (entry_id, entry_type, content, metadata, timestamp, context_hash, importance_score)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            entry_id,
            context_type.value,
            json.dumps(data),
            json.dumps({'source': 'ai_brain', 'processed': True}),
            datetime.now().isoformat(),
            context_hash,
            importance_score
        ))
        self.conn.commit()
        
        # Store in vector database for semantic search
        if self.vector_db and context_type.value in self.collections:
            await self._store_in_vector_db(context_type.value, entry_id, data)
        
        # Store specific entity types in specialized tables
        await self._store_specialized_entity(context_type, entry_id, data)
        
        logger.info(f"💾 Stored {context_type.value} context: {entry_id}")
        return entry_id
    
    async def _store_in_vector_db(self, collection_name: str, entry_id: str, data: Dict[str, Any]):
        """Store data in vector database for semantic search"""
        try:
            # Extract text content for embedding
            text_content = self._extract_text_content(data)
            
            if text_content:
                self.collections[collection_name].add(
                    documents=[text_content],
                    metadatas=[{
                        'entry_id': entry_id,
                        'timestamp': datetime.now().isoformat(),
                        'data_type': collection_name
                    }],
                    ids=[entry_id]
                )
        except Exception as e:
            logger.error(f"❌ Failed to store in vector DB: {e}")
    
    def _extract_text_content(self, data: Dict[str, Any]) -> str:
        """Extract meaningful text content from data for embedding"""
        text_parts = []
        
        # Common text fields
        for field in ['content', 'description', 'title', 'summary', 'transcript', 'message']:
            if field in data and data[field]:
                text_parts.append(str(data[field]))
        
        # Recursively extract from nested structures
        for key, value in data.items():
            if isinstance(value, dict):
                nested_text = self._extract_text_content(value)
                if nested_text:
                    text_parts.append(nested_text)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        nested_text = self._extract_text_content(item)
                        if nested_text:
                            text_parts.append(nested_text)
                    elif isinstance(item, str):
                        text_parts.append(item)
        
        return ' '.join(text_parts)
    
    async def _store_specialized_entity(self, context_type, entry_id: str, data: Dict[str, Any]):
        """Store entities in specialized tables"""
        
        cursor = self.conn.cursor()
        
        if context_type.value == 'meeting':
            cursor.execute("""
                INSERT OR REPLACE INTO meetings 
                (meeting_id, title, participants, start_time, end_time, platform, 
                 transcript, summary, action_items, decisions, meeting_type, project_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                entry_id,
                data.get('title', ''),
                json.dumps(data.get('participants', [])),
                data.get('start_time', datetime.now().isoformat()),
                data.get('end_time', ''),
                data.get('platform', ''),
                data.get('transcript', ''),
                data.get('summary', ''),
                json.dumps(data.get('action_items', [])),
                json.dumps(data.get('decisions', [])),
                data.get('meeting_type', ''),
                data.get('project_id', '')
            ))
            
        elif context_type.value == 'task':
            cursor.execute("""
                INSERT OR REPLACE INTO tasks 
                (task_id, external_id, title, description, status, priority, assignee, 
                 project_id, requirements, acceptance_criteria, related_meetings)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                entry_id,
                data.get('external_id', ''),
                data.get('title', ''),
                data.get('description', ''),
                data.get('status', ''),
                data.get('priority', ''),
                data.get('assignee', ''),
                data.get('project_id', ''),
                data.get('requirements', ''),
                data.get('acceptance_criteria', ''),
                json.dumps(data.get('related_meetings', []))
            ))
            
        elif context_type.value == 'code':
            cursor.execute("""
                INSERT OR REPLACE INTO code_changes 
                (change_id, repository, branch, commit_hash, pr_number, 
                 files_changed, diff_summary, description, author, related_tasks)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                entry_id,
                data.get('repository', ''),
                data.get('branch', ''),
                data.get('commit_hash', ''),
                data.get('pr_number', ''),
                json.dumps(data.get('files_changed', [])),
                data.get('diff_summary', ''),
                data.get('description', ''),
                data.get('author', ''),
                json.dumps(data.get('related_tasks', []))
            ))
        
        self.conn.commit()
    
    def _calculate_importance(self, context_type, data: Dict[str, Any]) -> float:
        """Calculate importance score for memory entry"""
        base_score = 0.5
        
        # Meeting importance factors
        if context_type.value == 'meeting':
            if data.get('decisions'):
                base_score += 0.3
            if data.get('action_items'):
                base_score += 0.2
            if len(data.get('participants', [])) > 5:
                base_score += 0.1
        
        # Task importance factors
        elif context_type.value == 'task':
            priority = data.get('priority', '').lower()
            if priority in ['high', 'critical']:
                base_score += 0.3
            elif priority == 'medium':
                base_score += 0.1
        
        # Code importance factors
        elif context_type.value == 'code':
            if data.get('pr_number'):
                base_score += 0.2
            if data.get('files_changed', 0) > 10:
                base_score += 0.1
        
        return min(base_score, 1.0)
    
    async def get_related_context(self, context_type, data: Dict[str, Any], limit: int = 5) -> List[Dict[str, Any]]:
        """Get related context using semantic search"""
        
        if not self.collections or context_type.value not in self.collections:
            return await self._get_related_context_sql(context_type, data, limit)
        
        try:
            # Extract query text
            query_text = self._extract_text_content(data)
            
            if not query_text:
                return []
            
            # Search in vector database
            results = self.collections[context_type.value].query(
                query_texts=[query_text],
                n_results=limit
            )
            
            # Get full context from SQLite
            related_contexts = []
            for doc_id in results['ids'][0]:
                context = await self._get_context_by_id(doc_id)
                if context:
                    related_contexts.append(context)
            
            return related_contexts
            
        except Exception as e:
            logger.error(f"❌ Error in semantic search: {e}")
            return await self._get_related_context_sql(context_type, data, limit)
    
    async def _get_related_context_sql(self, context_type, data: Dict[str, Any], limit: int) -> List[Dict[str, Any]]:
        """Fallback to SQL-based context search"""
        
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM memory_entries 
            WHERE entry_type = ? 
            ORDER BY importance_score DESC, timestamp DESC 
            LIMIT ?
        """, (context_type.value, limit))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'entry_id': row['entry_id'],
                'content': json.loads(row['content']),
                'metadata': json.loads(row['metadata']),
                'timestamp': row['timestamp'],
                'importance_score': row['importance_score']
            })
        
        return results
    
    async def _get_context_by_id(self, entry_id: str) -> Optional[Dict[str, Any]]:
        """Get context by entry ID"""
        
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM memory_entries WHERE entry_id = ?", (entry_id,))
        row = cursor.fetchone()
        
        if row:
            return {
                'entry_id': row['entry_id'],
                'entry_type': row['entry_type'],
                'content': json.loads(row['content']),
                'metadata': json.loads(row['metadata']),
                'timestamp': row['timestamp'],
                'importance_score': row['importance_score']
            }
        
        return None
    
    async def find_related_meetings(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find meetings related to current context"""
        
        # Extract key terms for search
        search_terms = []
        if 'title' in data:
            search_terms.extend(data['title'].split())
        if 'description' in data:
            search_terms.extend(data['description'].split()[:10])  # First 10 words
        
        if not search_terms:
            return []
        
        cursor = self.conn.cursor()
        # Simple keyword search in meeting transcripts and summaries
        query = """
            SELECT * FROM meetings 
            WHERE (transcript LIKE ? OR summary LIKE ? OR title LIKE ?)
            ORDER BY start_time DESC 
            LIMIT 3
        """
        
        search_pattern = f"%{' '.join(search_terms[:3])}%"  # Use first 3 terms
        cursor.execute(query, (search_pattern, search_pattern, search_pattern))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'meeting_id': row['meeting_id'],
                'title': row['title'],
                'participants': json.loads(row['participants']) if row['participants'] else [],
                'start_time': row['start_time'],
                'summary': row['summary'],
                'relevance_type': 'keyword_match'
            })
        
        return results
    
    async def find_related_tasks(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find tasks related to current context"""
        
        cursor = self.conn.cursor()
        query = """
            SELECT * FROM tasks 
            WHERE (title LIKE ? OR description LIKE ?)
            ORDER BY updated_at DESC 
            LIMIT 3
        """
        
        search_text = data.get('title', data.get('description', ''))
        if not search_text:
            return []
        
        search_pattern = f"%{search_text[:50]}%"
        cursor.execute(query, (search_pattern, search_pattern))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'task_id': row['task_id'],
                'title': row['title'],
                'status': row['status'],
                'assignee': row['assignee'],
                'relevance_type': 'keyword_match'
            })
        
        return results
    
    async def find_related_code(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find code changes related to current context"""
        
        cursor = self.conn.cursor()
        query = """
            SELECT * FROM code_changes 
            WHERE (description LIKE ? OR diff_summary LIKE ?)
            ORDER BY created_at DESC 
            LIMIT 3
        """
        
        search_text = data.get('description', data.get('title', ''))
        if not search_text:
            return []
        
        search_pattern = f"%{search_text[:50]}%"
        cursor.execute(query, (search_pattern, search_pattern))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'change_id': row['change_id'],
                'repository': row['repository'],
                'description': row['description'],
                'author': row['author'],
                'relevance_type': 'keyword_match'
            })
        
        return results
    
    async def store_decision(self, decision) -> str:
        """Store AI decision in memory"""
        
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO ai_decisions 
            (decision_id, decision_type, context, reasoning, confidence, user_approved)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            decision.decision_id,
            decision.decision_type,
            json.dumps(decision.context),
            decision.reasoning,
            decision.confidence,
            None  # Will be updated when user responds
        ))
        self.conn.commit()
        
        return decision.decision_id
    
    async def store_action_execution(self, action_plan, results: List[Dict[str, Any]]):
        """Store action plan execution results"""
        
        # Store as a specialized memory entry
        await self.store_context(
            context_type=type('ContextType', (), {'value': 'action_execution'})(),
            data={
                'plan_id': action_plan.plan_id,
                'title': action_plan.title,
                'steps': action_plan.steps,
                'results': results,
                'success_rate': len([r for r in results if r.get('status') == 'completed']) / len(results)
            }
        )
    
    async def store_feedback(self, feedback: Dict[str, Any]):
        """Store user feedback for learning"""
        
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO user_feedback 
            (feedback_id, category, rating, comments, context, improvement_suggestions)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            f"feedback_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            feedback.get('category', 'general'),
            feedback.get('rating', 0),
            feedback.get('comments', ''),
            json.dumps(feedback.get('context', {})),
            feedback.get('improvement_suggestions', '')
        ))
        self.conn.commit()
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get memory system statistics"""
        
        cursor = self.conn.cursor()
        
        # Count entries by type
        cursor.execute("SELECT entry_type, COUNT(*) as count FROM memory_entries GROUP BY entry_type")
        entry_counts = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Total entries
        cursor.execute("SELECT COUNT(*) FROM memory_entries")
        total_entries = cursor.fetchone()[0]
        
        # Recent activity (last 7 days)
        week_ago = (datetime.now() - timedelta(days=7)).isoformat()
        cursor.execute("SELECT COUNT(*) FROM memory_entries WHERE timestamp > ?", (week_ago,))
        recent_entries = cursor.fetchone()[0]
        
        return {
            'total_entries': total_entries,
            'recent_entries_7d': recent_entries,
            'entries_by_type': entry_counts,
            'vector_db_available': CHROMADB_AVAILABLE,
            'collections': list(self.collections.keys()) if self.collections else [],
            'last_updated': datetime.now().isoformat()
        }
    
    def close(self):
        """Close database connections"""
        if self.conn:
            self.conn.close()
        logger.info("🔒 Memory system closed")
