from __future__ import annotations

import importlib
import logging
from typing import List, Optional


logger = logging.getLogger(__name__)


def retrieve_context_snippets(
    query: str, top_k: int = 5, doc_type: Optional[str] = None
) -> str:
    """Retrieve relevant context snippets from the knowledge base.

    This function dynamically imports the knowledge base module at runtime so
    the application can run even when the optional dependency is missing.

    Args:
        query: The search query to retrieve context for.
        top_k: Maximum number of snippets to return.
        doc_type: Optional document type filter used when querying the knowledge
            base. Only documents matching this type will be retrieved when
            provided.

    Returns:
        A string containing the concatenated contents of the retrieved snippets
        or an empty string if the knowledge base is unavailable.
    """

    try:
        kb_module = importlib.import_module("app.knowledge_base")
        query_fn = getattr(kb_module, "query_knowledge_base")
        results = query_fn(query, top_k, doc_type)
        snippets: List[str] = [
            item.get("content", "") for item in results if isinstance(item, dict)
        ]
        return "\n".join(s for s in snippets if s).strip()
    except Exception as exc:  # pragma: no cover - logging path
        logger.debug("Knowledge base unavailable: %s", exc)
        return ""
