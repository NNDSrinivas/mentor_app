from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Dict, List

try:
    import chromadb  # type: ignore
    from chromadb.config import Settings  # type: ignore
    from chromadb.utils.embedding_functions import (  # type: ignore
        DefaultEmbeddingFunction,
    )
except Exception:  # pragma: no cover - fallback when chromadb unavailable
    chromadb = None

    class Settings:  # type: ignore[override]
        def __init__(self, persist_directory: str | None = None):
            self.persist_directory = persist_directory

    class DefaultEmbeddingFunction:  # type: ignore[override]
        def __call__(self, texts):
            return [[float(len(text))] for text in texts]

log = logging.getLogger(__name__)


@dataclass
class VectorSearchResult:
    meeting_id: str
    document: str
    score: float


class MeetingVectorStore:
    """Thin wrapper around Chroma collections used for meeting intelligence."""

    def __init__(self, collection_name: str = "meeting_transcripts") -> None:
        persist_dir = os.getenv("MEMORY_DB_PATH", Settings().persist_directory or "./memory_db")
        self._fallback_store: Dict[str, List[str]] = {}
        if chromadb:
            try:
                self._client = chromadb.Client(Settings(persist_directory=persist_dir))
                self._collection = self._client.get_or_create_collection(
                    collection_name,
                    embedding_function=DefaultEmbeddingFunction(),
                )
            except Exception as exc:  # pragma: no cover - fallback path
                log.warning("Falling back to in-memory Chroma client: %s", exc)
                self._client = chromadb.Client(Settings())
                self._collection = self._client.get_or_create_collection(
                    collection_name,
                    embedding_function=DefaultEmbeddingFunction(),
                )
        else:
            self._client = None
            self._collection = None

    def index_chunks(self, meeting_id: str, chunks: List[str]) -> None:
        if not chunks:
            return
        if self._collection is not None:
            ids = [f"{meeting_id}_{idx}" for idx in range(len(chunks))]
            metadatas: List[Dict[str, str]] = [
                {"meeting_id": meeting_id, "chunk": str(idx)} for idx, _ in enumerate(chunks)
            ]
            self._collection.upsert(documents=chunks, metadatas=metadatas, ids=ids)
        else:
            store = self._fallback_store.setdefault(meeting_id, [])
            store.extend(chunks)

    def search(self, query: str, limit: int = 5) -> List[VectorSearchResult]:
        if not query.strip():
            return []
        if self._collection is not None:
            results = self._collection.query(query_texts=[query], n_results=limit)
            docs = results.get("documents", [[]])[0]
            metadatas = results.get("metadatas", [[]])[0]
            distances = results.get("distances", [[]])[0] or []
            formatted: List[VectorSearchResult] = []
            for doc, meta, distance in zip(docs, metadatas, distances):
                meeting_id = str(meta.get("meeting_id")) if meta else ""
                formatted.append(VectorSearchResult(meeting_id=meeting_id, document=doc, score=float(distance)))
            return formatted

        formatted: List[VectorSearchResult] = []
        for meeting_id, chunks in self._fallback_store.items():
            for chunk in chunks:
                if query.lower() in chunk.lower():
                    formatted.append(VectorSearchResult(meeting_id=meeting_id, document=chunk, score=0.0))
                    if len(formatted) >= limit:
                        return formatted
        return formatted


__all__ = ["MeetingVectorStore", "VectorSearchResult"]
