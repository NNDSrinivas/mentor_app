# backend/memory_service.py

import os
import chromadb
from chromadb.config import Settings
from datetime import datetime
from typing import List, Dict, Optional, Any
import logging

log = logging.getLogger(__name__)

class MemoryService:
    """
    Persistent memory for meetings, tasks, and user/project context.
    Uses ChromaDB as the vector store for long-term recall.
    """

    def __init__(self):
        persist_dir = os.getenv("MEMORY_DB_PATH", "./memory_db")
        try:
            self.client = chromadb.Client(
                Settings(persist_directory=persist_dir)
            )
            # Create collections for different contexts
            self.meeting_collection = self.client.get_or_create_collection("meetings")
            self.task_collection = self.client.get_or_create_collection("tasks")
            self.code_collection = self.client.get_or_create_collection("code")
            log.info("ChromaDB collections initialized successfully")
        except Exception as e:
            log.warning(f"ChromaDB not available, falling back to simple storage: {e}")
            # Fallback to the original SQLite-based system
            import sqlite3
            import json
            self.db_path = os.getenv("MENTOR_DB_PATH", "mentor_memory.db")
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._init_fallback_db()
            self.client = None

    def _init_fallback_db(self):
        cursor = self.conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT,
            timestamp TEXT,
            data TEXT
        )
        """)
        self.conn.commit()

    def add_meeting_entry(self, meeting_id: str, text: str, metadata: Optional[Dict] = None):
        """Add a meeting entry to memory"""
        if self.client:
            doc_id = f"meeting_{meeting_id}_{datetime.now().isoformat()}"
            self.meeting_collection.add(
                documents=[text],
                metadatas=[metadata or {}],
                ids=[doc_id]
            )
        else:
            # Fallback to SQLite
            self.store_event("meeting", {
                "meeting_id": meeting_id,
                "text": text,
                **(metadata or {})
            })

    def search_meeting_context(self, query: str, n_results: int = 3):
        """Search for relevant meeting context"""
        if self.client:
            return self.meeting_collection.query(query_texts=[query], n_results=n_results)
        else:
            # Fallback search
            return {"documents": [self.search_memory(category="meeting", query=query, limit=n_results)]}

    def add_task(self, task_id: str, description: str, metadata: Optional[Dict] = None):
        """Add a task to memory"""
        if self.client:
            doc_id = f"task_{task_id}"
            self.task_collection.add(
                documents=[description],
                metadatas=[metadata or {}],
                ids=[doc_id]
            )
        else:
            self.store_event("task", {
                "task_id": task_id,
                "description": description,
                **(metadata or {})
            })

    def search_tasks(self, query: str, n_results: int = 3):
        """Search for relevant tasks"""
        if self.client:
            return self.task_collection.query(query_texts=[query], n_results=n_results)
        else:
            return {"documents": [self.search_memory(category="task", query=query, limit=n_results)]}

    def add_code_snippet(self, file_path: str, code: str, metadata: Optional[Dict] = None):
        """Add a code snippet to memory"""
        if self.client:
            doc_id = f"code_{file_path}_{datetime.now().isoformat()}"
            self.code_collection.add(
                documents=[code],
                metadatas=[metadata or {}],
                ids=[doc_id]
            )
        else:
            self.store_event("code", {
                "file_path": file_path,
                "code": code,
                **(metadata or {})
            })

    def search_code(self, query: str, n_results: int = 3):
        """Search for relevant code"""
        if self.client:
            return self.code_collection.query(query_texts=[query], n_results=n_results)
        else:
            return {"documents": [self.search_memory(category="code", query=query, limit=n_results)]}

    # Fallback methods (original SQLite implementation)
    def store_event(self, category: str, data: Dict):
        """Store any event in memory with a category label (fallback)"""
        if not self.client:
            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT INTO memory (category, timestamp, data) VALUES (?, ?, ?)",
                (category, datetime.now().isoformat(), json.dumps(data))
            )
            self.conn.commit()

    def search_memory(self, category: Optional[str] = None, query: Optional[str] = None, limit: int = 50) -> List[Dict]:
        """Search memory by category and/or keyword (fallback)"""
        if not self.client:
            cursor = self.conn.cursor()
            sql = "SELECT category, timestamp, data FROM memory"
            params = []
            if category or query:
                sql += " WHERE "
                conditions = []
                if category:
                    conditions.append("category = ?")
                    params.append(category)
                if query:
                    conditions.append("data LIKE ?")
                    params.append(f"%{query}%")
                sql += " AND ".join(conditions)
            sql += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            return [{"category": r[0], "timestamp": r[1], "data": json.loads(r[2])} for r in rows]
        return []


if __name__ == "__main__":
    # Example usage
    mem = MemoryService()

    # Store a meeting transcript
    mem.add_meeting_entry("meeting_123", "We need to refactor the payment service by Friday.", 
                         {"speaker": "tech_lead", "project": "ReImagine"})

    # Store a task
    mem.add_task("LAB-123", "Implement ALVA dual write", {"status": "In Progress"})

    # Search for context
    print("=== Meeting Context Search ===")
    context = mem.search_meeting_context("payment service")
    print(context)

    print("=== Task Search ===")
    tasks = mem.search_tasks("ALVA")
    print(tasks)
