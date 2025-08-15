from __future__ import annotations
import os, time, json, sqlite3

from backend.memory_service import MemoryService

def _days(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except Exception:
        return default

RAW_DAYS = _days("RETENTION_RAW_VIDEO_DAYS", 7)
TXT_DAYS = _days("RETENTION_TRANSCRIPT_DAYS", 30)
VEC_DAYS = _days("RETENTION_VECTOR_DAYS", 180)

DOCUMENT_DB = os.getenv("DOCUMENTATION_DB_PATH", "./data/documentation.db")

def prune_path(path: str, older_than_days: int):
    if not os.path.exists(path): return
    cutoff = time.time() - older_than_days*86400
    for root, _, files in os.walk(path):
        for fn in files:
            p = os.path.join(root, fn)
            try:
                if os.path.getmtime(p) < cutoff:
                    os.remove(p)
            except Exception:
                pass

def run_once():
    prune_path("./data/recordings", RAW_DAYS)
    prune_path("./data/transcripts", TXT_DAYS)
    prune_path("./data/chroma_db", VEC_DAYS)
    index_meeting_summaries()
    compact_documentation_db()


def index_meeting_summaries():
    if not os.path.exists(DOCUMENT_DB):
        return
    conn = sqlite3.connect(DOCUMENT_DB)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT id, meeting_id, summary, metadata FROM summaries WHERE indexed = 0")
    rows = cur.fetchall()
    if rows:
        mem = MemoryService()
        for row in rows:
            meta = json.loads(row["metadata"]) if row["metadata"] else {}
            mem.add_meeting_entry(row["meeting_id"], row["summary"], meta, persist=False)
            cur.execute("UPDATE summaries SET indexed = 1 WHERE id = ?", (row["id"],))
        conn.commit()
    conn.close()


def compact_documentation_db():
    if not os.path.exists(DOCUMENT_DB):
        return
    conn = sqlite3.connect(DOCUMENT_DB)
    try:
        conn.execute("VACUUM")
    finally:
        conn.close()


def run_periodically(interval_hours: int = 24):
    while True:
        run_once()
        time.sleep(interval_hours * 3600)

if __name__ == "__main__":
    interval = int(os.getenv("RETENTION_JOB_INTERVAL_HOURS", "24"))
    run_periodically(interval)
