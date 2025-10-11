from __future__ import annotations

"""Utilities for storing transcripts and notes in a persistent vector DB.

The :class:`MemoryIndexer` class wraps access to ChromaDB while providing a
light-weight fallback implementation when the dependency is not available.
This makes the module usable in test environments without requiring the full
vector database stack.
"""

import uuid
from typing import Dict, List, Optional

try:  # pragma: no cover - optional dependency
    import chromadb  # type: ignore
    from chromadb.config import Settings  # type: ignore
except Exception:  # pragma: no cover - library optional
    chromadb = None  # type: ignore
    Settings = None  # type: ignore


class MemoryIndexer:
    """Index meeting artefacts into a vector store."""

    def __init__(self, persist_dir: str = "./data/memory", metadata: Optional[Dict[str, str]] = None) -> None:
        self.metadata_defaults = metadata or {}
        if chromadb:
            self.client = chromadb.Client(Settings(persist_directory=persist_dir))
            self.transcript_collection = self.client.get_or_create_collection("transcripts")
            self.notes_collection = self.client.get_or_create_collection("notes")
        else:
            # Fallback containers used in tests
            self.client = None
            self._transcripts: List[Dict] = []
            self._notes: List[Dict] = []

    # ------------------------------------------------------------------
    def _merge_metadata(self, extra: Optional[Dict[str, str]]) -> Dict[str, str]:
        meta = dict(self.metadata_defaults)
        if extra:
            meta.update(extra)
        return meta

    # ------------------------------------------------------------------
    def upsert_transcript(self, meeting_id: str, text: str, metadata: Optional[Dict[str, str]] = None) -> str:
        """Store a transcript chunk and return its identifier."""
        meta = self._merge_metadata(metadata)
        meta["meeting_id"] = meeting_id
        doc_id = f"{meeting_id}_t_{uuid.uuid4()}"
        if self.client:
            self.transcript_collection.add(documents=[text], metadatas=[meta], ids=[doc_id])
        else:
            self._transcripts.append({"id": doc_id, "text": text, "metadata": meta})
        return doc_id

    def upsert_notes(self, meeting_id: str, notes: List[Dict[str, str]], metadata: Optional[Dict[str, str]] = None) -> List[str]:
        """Store extracted notes."""
        meta = self._merge_metadata(metadata)
        ids = []
        for note in notes:
            note_meta = dict(meta)
            note_meta.update(note)
            note_meta["meeting_id"] = meeting_id
            doc_id = f"{meeting_id}_n_{uuid.uuid4()}"
            text = note.get("text", "")
            if self.client:
                self.notes_collection.add(documents=[text], metadatas=[note_meta], ids=[doc_id])
            else:
                self._notes.append({"id": doc_id, "note": note, "metadata": note_meta})
            ids.append(doc_id)
        return ids

    # Accessors used in tests -------------------------------------------
    @property
    def stored_transcripts(self) -> List[Dict]:
        if self.client:
            raise RuntimeError("stored_transcripts only available without ChromaDB")
        return self._transcripts

    @property
    def stored_notes(self) -> List[Dict]:
        if self.client:
            raise RuntimeError("stored_notes only available without ChromaDB")
        return self._notes
