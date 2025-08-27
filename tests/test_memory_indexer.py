import os, sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from backend import memory_indexer as mi
from backend.memory_indexer import MemoryIndexer


def test_upsert_transcript_and_notes(monkeypatch):
    # Force fallback mode by disabling chromadb
    monkeypatch.setattr(mi, "chromadb", None)

    indexer = MemoryIndexer(metadata={
        "team": "core",
        "repo": "mentor_app",
        "jira": "MAPP",
        "date": "2023-09-01",
    })

    tid = indexer.upsert_transcript("meeting1", "hello world")
    assert indexer.stored_transcripts[0]["id"] == tid
    meta = indexer.stored_transcripts[0]["metadata"]
    assert meta["team"] == "core"
    assert meta["meeting_id"] == "meeting1"

    notes = [{"type": "action", "text": "do thing", "owner": "alice"}]
    ids = indexer.upsert_notes("meeting1", notes)
    assert len(ids) == 1
    nmeta = indexer.stored_notes[0]["metadata"]
    assert nmeta["owner"] == "alice"
    assert nmeta["meeting_id"] == "meeting1"
    assert nmeta["team"] == "core"
