"""Retrieval utilities for the AI assistant.

This module provides a thin wrapper around the :class:`KnowledgeBase`
search functionality to fetch context snippets relevant to a query.  The
returned snippets can then be supplied to the language model as additional
context.
"""

from __future__ import annotations

from typing import List, Optional

import tiktoken

from .knowledge_base import KnowledgeBase


def retrieve_context_snippets(
    query: str,
    top_k: int = 5,
    *,
    max_tokens: int = 1000,
    source_filters: Optional[List[str]] = None,
    priority_order: Optional[List[str]] = None,
) -> str:
    """Retrieve relevant context snippets for a query.

    Args:
        query: Natural language query to search for.
        top_k: Number of snippets to retrieve from the knowledge base.
        max_tokens: Maximum number of tokens allowed in the returned context.
        source_filters: Optional list of metadata sources to filter results by.
        priority_order: Optional list specifying the order of sources by
            priority. Sources appearing earlier in this list will be preferred
            when assembling the final context string.

    Returns:
        A single string containing the concatenated text of the retrieved
        snippets separated by blank lines. The total token count will not
        exceed ``max_tokens``. If no snippets are found, an empty string is
        returned.
    """

    kb = KnowledgeBase()

    filter_metadata = None
    if source_filters:
        filter_metadata = {"source": {"$in": source_filters}}

    results = kb.search(query, top_k=top_k, filter_metadata=filter_metadata)

    # Apply priority ordering if provided
    if priority_order:
        order_map = {source: idx for idx, source in enumerate(priority_order)}
        results.sort(
            key=lambda r: order_map.get(r.get("metadata", {}).get("source"), len(order_map))
        )

    # Enforce strict token budget when assembling snippets
    encoding = tiktoken.get_encoding("cl100k_base")
    separator_tokens = len(encoding.encode("\n\n"))
    remaining = max_tokens
    snippets: List[str] = []

    for result in results:
        content = result.get("content", "")
        if not content:
            continue

        tokens = len(encoding.encode(content))
        needed = tokens if not snippets else tokens + separator_tokens

        if needed > remaining:
            break

        snippets.append(content)
        remaining -= needed

    return "\n\n".join(snippets)
