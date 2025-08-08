# backend/memory_service.py

import os
import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional

class MemoryService:
    """
    Persistent memory layer for the AI mentor app.
    Stores meetings, speaker text, Jira tasks, PR comments, decisions, and code context.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or os.getenv("MENTOR_DB_PATH", "mentor_memory.db")
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._init_db()

    def _init_db(self):
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

    def store_event(self, category: str, data: Dict):
        """
        Store any event in memory with a category label.
        Categories could be: meeting, jira, pr_comment, code_decision, architecture, misc
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO memory (category, timestamp, data) VALUES (?, ?, ?)",
            (category, datetime.utcnow().isoformat(), json.dumps(data))
        )
        self.conn.commit()

    def search_memory(self, category: Optional[str] = None, query: Optional[str] = None, limit: int = 50) -> List[Dict]:
        """
        Search memory by category and/or keyword.
        Returns most recent events first.
        """
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

    def summarize_recent(self, category: Optional[str] = None, limit: int = 20) -> str:
        """
        Summarize the most recent events in a category for quick AI context injection.
        """
        events = self.search_memory(category=category, limit=limit)
        summary_lines = []
        for e in events:
            summary_lines.append(f"[{e['timestamp']}] {e['category'].upper()}: {json.dumps(e['data'])}")
        return "\n".join(summary_lines)

    def clear_memory(self, category: Optional[str] = None):
        """
        Clear all memory or specific category.
        """
        cursor = self.conn.cursor()
        if category:
            cursor.execute("DELETE FROM memory WHERE category = ?", (category,))
        else:
            cursor.execute("DELETE FROM memory")
        self.conn.commit()


if __name__ == "__main__":
    # Example usage
    mem = MemoryService()

    # Store a meeting transcript
    mem.store_event("meeting", {
        "speaker": "SPEAKER_1",
        "text": "We need to refactor the payment service by Friday.",
        "project": "ReImagine"
    })

    # Store a Jira update
    mem.store_event("jira", {
        "ticket": "LAB-123",
        "status": "In Progress",
        "summary": "Implement ALVA dual write"
    })

    # Retrieve & summarize
    print("=== Recent Meetings ===")
    print(mem.summarize_recent("meeting"))

    print("=== Search for 'payment' ===")
    print(mem.search_memory(query="payment"))
