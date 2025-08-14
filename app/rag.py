"""Retrieval utilities for the AI assistant.

This module provides a thin wrapper around the :class:`KnowledgeBase`
search functionality to fetch context snippets relevant to a query.  The
returned snippets can then be supplied to the language model as additional
context.
"""

from __future__ import annotations

from typing import List

from .knowledge_base import KnowledgeBase


def retrieve_context_snippets(query: str, top_k: int = 5) -> str:
    """Retrieve relevant context snippets for a query.

    Args:
        query: Natural language query to search for.
        top_k: Number of snippets to retrieve.

    Returns:
        A single string containing the concatenated text of the retrieved
        snippets separated by blank lines. If no snippets are found, an
        empty string is returned.
    """

    kb = KnowledgeBase()
    results = kb.search(query, top_k=top_k)
    snippets: List[str] = [r.get("content", "") for r in results if r.get("content")]
    return "\n\n".join(snippets)
