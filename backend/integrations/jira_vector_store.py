from __future__ import annotations

import logging
import os
from typing import Dict, List, Optional

try:
    import chromadb  # type: ignore
    from chromadb.config import Settings  # type: ignore
    from chromadb.utils.embedding_functions import DefaultEmbeddingFunction  # type: ignore
    try:
        from chromadb import errors as chroma_errors  # type: ignore[attr-defined]
    except ImportError:  # pragma: no cover - optional dependency details
        chroma_errors = None  # type: ignore[assignment]
except ImportError:  # pragma: no cover - fallback for tests without chromadb
    chromadb = None
    chroma_errors = None  # type: ignore[assignment]

    class Settings:  # type: ignore[override]
        def __init__(self, persist_directory: Optional[str] = None) -> None:
            self.persist_directory = persist_directory

    class DefaultEmbeddingFunction:  # type: ignore[override]
        def __call__(self, texts: List[str]) -> List[List[float]]:
            return [[float(len(text))] for text in texts]


_CHROMA_CLIENT_EXCEPTIONS = (RuntimeError, OSError, ValueError)
if chroma_errors is not None and hasattr(chroma_errors, "ChromaError"):
    _CHROMA_CLIENT_EXCEPTIONS = (
        chroma_errors.ChromaError,
        *_CHROMA_CLIENT_EXCEPTIONS,
    )


log = logging.getLogger(__name__)


class JiraIssueVectorStore:
    """Vector index for Jira issues (summary + description + labels)."""

    def __init__(self, collection: str = "jira_issues") -> None:
        persist_dir = os.getenv("MEMORY_DB_PATH", "./memory_db")
        self._fallback: Dict[str, Dict[str, str]] = {}
        if chromadb is None:
            self._client = None
            self._collection = None
            return

        try:
            self._client = chromadb.Client(Settings(persist_directory=persist_dir))
            self._collection = self._client.get_or_create_collection(
                collection,
                embedding_function=DefaultEmbeddingFunction(),
            )
        except _CHROMA_CLIENT_EXCEPTIONS as exc:  # pragma: no cover - fallback path
            log.warning("Falling back to in-memory Chroma store: %s", exc)
            self._client = chromadb.Client(Settings())
            self._collection = self._client.get_or_create_collection(
                collection,
                embedding_function=DefaultEmbeddingFunction(),
            )

    def index_issue(self, issue_key: str, text: str, metadata: Dict[str, str]) -> None:
        if not text.strip():
            text = metadata.get("summary", "")
        if self._collection is not None:
            self._collection.upsert(
                ids=[issue_key],
                documents=[text],
                metadatas=[metadata],
            )
            return

        self._fallback[issue_key] = {"text": text, **metadata}

    def delete(self, issue_key: str) -> None:
        if self._collection is not None:
            self._collection.delete(ids=[issue_key])
            return
        self._fallback.pop(issue_key, None)

    def search(self, query: str, limit: int = 10) -> Dict[str, float]:
        if not query.strip():
            return {}
        if self._collection is not None:
            results = self._collection.query(query_texts=[query], n_results=limit)
            ids = results.get("ids", [[]])[0]
            distances = results.get("distances", [[]])[0] or []
            scores: Dict[str, float] = {}
            for issue_id, distance in zip(ids, distances):
                scores[str(issue_id)] = float(distance)
            return scores

        scores: Dict[str, float] = {}
        lowered = query.lower()
        for issue_id, payload in self._fallback.items():
            haystack = payload.get("text", "").lower()
            if lowered in haystack:
                scores[issue_id] = 0.0
                if len(scores) >= limit:
                    break
        return scores


__all__ = ["JiraIssueVectorStore"]
