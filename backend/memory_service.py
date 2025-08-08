# backend/memory_service.py

import os
import chromadb
from chromadb.config import Settings
from datetime import datetime
from typing import List, Dict, Optional, Any
import logging
import json
from cryptography.fernet import Fernet

log = logging.getLogger(__name__)

class MemoryService:
    """
    Persistent memory for meetings, tasks, and user/project context.
    Uses ChromaDB as the vector store for long-term recall.
    """

    def __init__(self):
        persist_dir = os.getenv("MEMORY_DB_PATH", "./memory_db")
        self._fernet = self._init_fernet()
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
            self.db_path = os.getenv("MENTOR_DB_PATH", "mentor_memory.db")
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._init_fallback_db()
            self.client = None

    def _init_fernet(self) -> Optional[Fernet]:
        key = os.getenv("ENCRYPTION_KEY")
        if not key:
            log.warning("ENCRYPTION_KEY not set; data will be stored unencrypted")
            return None
        try:
            return Fernet(key.encode())
        except Exception as e:
            log.error(f"Invalid ENCRYPTION_KEY: {e}")
            return None

    def _encrypt(self, text: str) -> str:
        if not self._fernet:
            return text
        return self._fernet.encrypt(text.encode()).decode()

    def _decrypt(self, text: str) -> str:
        if not self._fernet:
            return text
        try:
            return self._fernet.decrypt(text.encode()).decode()
        except Exception as e:
            log.error(f"Failed to decrypt data: {e}")
            return ""

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
                documents=[self._encrypt(text)],
                metadatas=[metadata or {}],
                ids=[doc_id]
            )
        else:
            # Fallback to SQLite
            self.store_event("meeting", {
                "meeting_id": meeting_id,
                "text": self._encrypt(text),
                **(metadata or {})
            })

    def search_meeting_context(self, query: str, n_results: int = 3):
        """Search for relevant meeting context"""
        if self.client:
            result = self.meeting_collection.query(query_texts=[query], n_results=n_results)
            docs = result.get("documents", [])
            if docs:
                result["documents"] = [[self._decrypt(d) for d in docs[0]]]
            return result
        else:
            # Fallback search
            return {"documents": [self.search_memory(category="meeting", query=query, limit=n_results)]}

    def add_task(self, task_id: str, description: str, metadata: Optional[Dict] = None):
        """Add a task to memory"""
        if self.client:
            doc_id = f"task_{task_id}"
            self.task_collection.add(
                documents=[self._encrypt(description)],
                metadatas=[metadata or {}],
                ids=[doc_id]
            )
        else:
            self.store_event("task", {
                "task_id": task_id,
                "description": self._encrypt(description),
                **(metadata or {})
            })

    def search_tasks(self, query: str, n_results: int = 3):
        """Search for relevant tasks"""
        if self.client:
            result = self.task_collection.query(query_texts=[query], n_results=n_results)
            docs = result.get("documents", [])
            if docs:
                result["documents"] = [[self._decrypt(d) for d in docs[0]]]
            return result
        else:
            return {"documents": [self.search_memory(category="task", query=query, limit=n_results)]}

    def add_code_snippet(self, file_path: str, code: str, metadata: Optional[Dict] = None):
        """Add a code snippet to memory"""
        if self.client:
            doc_id = f"code_{file_path}_{datetime.now().isoformat()}"
            self.code_collection.add(
                documents=[self._encrypt(code)],
                metadatas=[metadata or {}],
                ids=[doc_id]
            )
        else:
            self.store_event("code", {
                "file_path": file_path,
                "code": self._encrypt(code),
                **(metadata or {})
            })

    def search_code(self, query: str, n_results: int = 3):
        """Search for relevant code"""
        if self.client:
            result = self.code_collection.query(query_texts=[query], n_results=n_results)
            docs = result.get("documents", [])
            if docs:
                result["documents"] = [[self._decrypt(d) for d in docs[0]]]
            return result
        else:
            return {"documents": [self.search_memory(category="code", query=query, limit=n_results)]}

    # Fallback methods (original SQLite implementation)
    def store_event(self, category: str, data: Dict):
        """Store any event in memory with a category label (fallback)"""
        if not self.client:
            cursor = self.conn.cursor()
            payload = self._encrypt(json.dumps(data))
            cursor.execute(
                "INSERT INTO memory (category, timestamp, data) VALUES (?, ?, ?)",
                (category, datetime.now().isoformat(), payload)
            )
            self.conn.commit()

    def search_memory(self, category: Optional[str] = None, query: Optional[str] = None, limit: int = 50) -> List[Dict]:
        """Search memory by category and/or keyword (fallback)"""
        if not self.client:
            cursor = self.conn.cursor()
            sql = "SELECT category, timestamp, data FROM memory"
            params = []
            if category:
                sql += " WHERE category = ?"
                params.append(category)
            sql += " ORDER BY timestamp DESC"
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            results = []
            for r in rows:
                dec = self._decrypt(r[2])
                if query and query not in dec:
                    continue
                try:
                    data = json.loads(dec)
                except Exception:
                    data = {}
                results.append({"category": r[0], "timestamp": r[1], "data": data})
                if len(results) >= limit:
                    break
            return results
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
