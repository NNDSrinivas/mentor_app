import os
import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Optional, Any


class MemoryDB:
    """Simple SQLite-based persistence for meetings, tasks and user profiles."""

    def __init__(self, db_path: str = os.path.join("data", "memory.db")) -> None:
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init_db()

    def _init_db(self) -> None:
        cur = self.conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS meeting_summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                meeting_id TEXT,
                summary TEXT,
                timestamp TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT,
                description TEXT,
                timestamp TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS user_profiles (
                user_id TEXT PRIMARY KEY,
                profile_json TEXT,
                timestamp TEXT
            )
            """
        )
        self.conn.commit()

    # --- Meeting summaries ---
    def save_meeting_summary(self, meeting_id: str, summary: str) -> None:
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO meeting_summaries (meeting_id, summary, timestamp) VALUES (?,?,?)",
            (meeting_id, summary, datetime.now().isoformat()),
        )
        self.conn.commit()

    def get_meeting_summaries(self, limit: int = 20) -> List[Dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute(
            "SELECT meeting_id, summary, timestamp FROM meeting_summaries ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        )
        rows = cur.fetchall()
        return [
            {"meeting_id": r[0], "summary": r[1], "timestamp": r[2]} for r in rows
        ]

    # --- Tasks ---
    def save_task(self, task_id: str, description: str) -> None:
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO tasks (task_id, description, timestamp) VALUES (?,?,?)",
            (task_id, description, datetime.now().isoformat()),
        )
        self.conn.commit()

    def get_task_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute(
            "SELECT task_id, description, timestamp FROM tasks ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        )
        rows = cur.fetchall()
        return [
            {"task_id": r[0], "description": r[1], "timestamp": r[2]} for r in rows
        ]

    # --- User profiles ---
    def save_user_profile(self, user_id: str, profile: Dict[str, Any]) -> None:
        cur = self.conn.cursor()
        cur.execute(
            "REPLACE INTO user_profiles (user_id, profile_json, timestamp) VALUES (?,?,?)",
            (user_id, json.dumps(profile), datetime.now().isoformat()),
        )
        self.conn.commit()

    def load_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute(
            "SELECT profile_json FROM user_profiles WHERE user_id = ?",
            (user_id,),
        )
        row = cur.fetchone()
        if row:
            try:
                return json.loads(row[0])
            except json.JSONDecodeError:
                return None
        return None

    def close(self) -> None:
        self.conn.close()
