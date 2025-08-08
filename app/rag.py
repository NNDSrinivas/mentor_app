"""Lightweight retrieval helper used by the AI assistant.

This module provides a very small abstraction over the more feature rich
``knowledge_base`` module.  The original repository shipped with a stub
implementation that always returned an empty string which meant the assistant
never had any additional context to augment its responses with.  For the
initial step of building out the application we wire this function up to the
existing knowledge base search helpers.

`retrieve_context_snippets` now queries the knowledge base and returns the
top matching document contents joined together as a single string.  The
function is intentionally resilient: any errors from the knowledge base layer
are caught and logged and an empty string is returned so callers can continue
gracefully even when the vector store is unavailable.
"""

from __future__ import annotations

import logging
from typing import List


logger = logging.getLogger(__name__)


def retrieve_context_snippets(query: str, top_k: int = 5) -> str:
    """Return relevant context snippets for a query.

    The knowledge base returns a list of dictionaries containing a ``content``
    field.  We extract the content from each result and join them with blank
    lines so the caller can feed the text to the language model.

    If the knowledge base cannot be queried (for example when the OpenAI API
    key is not configured) the function will simply return an empty string.

    Args:
        query: Natural language query describing the context you are looking
            for.
        top_k: Maximum number of snippets to return.

    Returns:
        A string containing the top matching snippets separated by two newlines.
    """

    try:
        # Import here to avoid importing heavy optional dependencies when the
        # knowledge base is not used.  This also makes unit testing easier
        # because the function can be exercised without the chromadb package
        # installed.
        from .knowledge_base import query_knowledge_base

        results = query_knowledge_base(query, top_k=top_k)
    except Exception as exc:  # pragma: no cover - defensive programming
        logger.error("Knowledge base query failed: %s", exc)
        return ""

    snippets: List[str] = []
    for result in results:
        content = result.get("content") if isinstance(result, dict) else None
        if content:
            snippets.append(str(content).strip())

    return "\n\n".join(snippets)
