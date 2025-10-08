from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Dict, List, Tuple

try:  # pragma: no cover - optional dependency
    import chromadb  # type: ignore
    from chromadb.config import Settings  # type: ignore
    from chromadb.utils.embedding_functions import (  # type: ignore
        DefaultEmbeddingFunction,
    )
except (ImportError, ModuleNotFoundError):  # pragma: no cover - fallback when chromadb unavailable
    chromadb = None

    class Settings:  # type: ignore[override]
        def __init__(self, persist_directory: str | None = None):
            self.persist_directory = persist_directory

    class DefaultEmbeddingFunction:  # type: ignore[override]
        def __call__(self, texts: List[str]):
            return [[float(len(text))] for text in texts]


log = logging.getLogger(__name__)


@dataclass
class JiraVectorResult:
    issue_key: str
    score: float


class JiraVectorStore:
    """Minimal vector index wrapper for Jira issue search."""

    def __init__(self, collection_name: str = "jira_issues") -> None:
        persist_dir = os.getenv("MEMORY_DB_PATH", "./memory_db")
        self._fallback_store: Dict[str, str] = {}
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

    def index_issue(self, issue_key: str, document: str, metadata: Dict[str, str]) -> None:
        if not document.strip():
            document = metadata.get("summary", "")

        if self._collection is not None:
            self._collection.upsert(
                ids=[issue_key],
                documents=[document],
                metadatas=[metadata],
            )
        else:
            combined = " ".join([document, metadata.get("summary", ""), metadata.get("status", "")])
            self._fallback_store[issue_key] = combined

    def delete_issue(self, issue_key: str) -> None:
        if self._collection is not None:
            self._collection.delete(ids=[issue_key])
        else:
            self._fallback_store.pop(issue_key, None)

    def search(self, query: str, limit: int = 10) -> List[JiraVectorResult]:
        if not query.strip():
            return []

        if self._collection is not None:
            results = self._collection.query(query_texts=[query], n_results=limit)
            ids = results.get("ids", [[]])[0]
            distances = results.get("distances", [[]])[0] or []
            return [JiraVectorResult(issue_key=_id, score=float(distance)) for _id, distance in zip(ids, distances)]

        scores: List[Tuple[str, float]] = []
        lower_query = query.lower()
        for issue_key, text in self._fallback_store.items():
            text_lower = text.lower()
            if lower_query in text_lower:
                score = float(text_lower.count(lower_query)) * -1.0
            else:
                continue
            scores.append((issue_key, score))
        scores.sort(key=lambda item: item[1])
        return [JiraVectorResult(issue_key=issue_key, score=score) for issue_key, score in scores[:limit]]


__all__ = ["JiraVectorStore", "JiraVectorResult"]
