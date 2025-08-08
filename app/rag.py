from __future__ import annotations

import logging
from typing import Any, Dict, List

try:  # pragma: no cover - exercised when optional deps missing
    from .knowledge_base import query_knowledge_base
except Exception:  # Module may rely on optional chromadb dependency
    query_knowledge_base = None  # type: ignore[assignment]

log = logging.getLogger(__name__)


def retrieve_context_snippets(query: str, top_k: int = 5) -> str:
    """Fetch context snippets from the knowledge base.

    This helper wraps :func:`query_knowledge_base` so tests can easily
    monkeypatch the lower level call.  Any exceptions are logged and an empty
    string is returned so callers don't have to handle errors themselves.
    """

    try:
        if query_knowledge_base is None:
            raise RuntimeError("Knowledge base unavailable")

        results: List[Dict[str, Any]] = query_knowledge_base(query, top_k=top_k)
        snippets = [r.get("content", "") for r in results if r.get("content")]
        return "\n\n".join(snippets)
    except Exception as e:  # pragma: no cover - exercised in tests
        log.error("Failed to retrieve context snippets: %s", e)
        return ""
