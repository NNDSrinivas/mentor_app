# backend/memory_service.py

import os
import json
import sqlite3
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
            self.db_path = os.getenv("MENTOR_DB_PATH", "mentor_memory.db")
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._init_fallback_db()
            self.client = None

        # Documentation database for summaries and tasks
        self.doc_db_path = os.getenv("DOCUMENTATION_DB_PATH", "data/documentation.db")
        self.doc_conn = sqlite3.connect(self.doc_db_path, check_same_thread=False)
        self._init_documentation_db()

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

    def _init_documentation_db(self):
        """Initialize tables for summaries and tasks in documentation DB."""
        cursor = self.doc_conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                meeting_id TEXT,
                summary TEXT,
                metadata TEXT,
                created_at TEXT,
                indexed BOOLEAN DEFAULT 0
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT,
                description TEXT,
                metadata TEXT,
                created_at TEXT
            )
            """
        )
        self.doc_conn.commit()

    def add_meeting_entry(self, meeting_id: str, text: str, metadata: Optional[Dict] = None, persist: bool = True):
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

        # Persist meeting summaries to documentation DB
        if persist:
            self._save_summary(meeting_id, text, metadata)

    def search_meeting_context(self, query: str, n_results: int = 3):
        """Search for relevant meeting context"""
        if self.client:
            return self.meeting_collection.query(query_texts=[query], n_results=n_results)
        else:
            # Fallback search
            return {"documents": [self.search_memory(category="meeting", query=query, limit=n_results)]}

    def get_meeting_notes(self, meeting_id: str) -> List[Dict[str, Any]]:
        """Retrieve stored meeting summaries for a specific meeting."""
        cursor = self.doc_conn.cursor()
        cursor.execute(
            "SELECT summary, metadata, created_at FROM summaries WHERE meeting_id = ? ORDER BY created_at DESC",
            (meeting_id,),
        )
        rows = cursor.fetchall()
        notes = []
        for summary, metadata, created_at in rows:
            try:
                meta = json.loads(metadata) if metadata else {}
            except Exception:
                meta = {}
            notes.append({"summary": summary, "metadata": meta, "created_at": created_at})
        return notes

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

        # Persist task metadata to documentation DB
        self._save_task_metadata(task_id, description, metadata)

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

    # Documentation database helper methods
    def _save_summary(self, meeting_id: str, summary: str, metadata: Optional[Dict] = None):
        cursor = self.doc_conn.cursor()
        cursor.execute(
            "INSERT INTO summaries (meeting_id, summary, metadata, created_at) VALUES (?, ?, ?, ?)",
            (
                meeting_id,
                summary,
                json.dumps(metadata or {}),
                datetime.now().isoformat(),
            ),
        )
        self.doc_conn.commit()

    def _save_task_metadata(self, task_id: str, description: str, metadata: Optional[Dict] = None):
        cursor = self.doc_conn.cursor()
        cursor.execute(
            "INSERT INTO tasks (task_id, description, metadata, created_at) VALUES (?, ?, ?, ?)",
            (
                task_id,
                description,
                json.dumps(metadata or {}),
                datetime.now().isoformat(),
            ),
        )
        self.doc_conn.commit()


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
