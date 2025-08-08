from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional


logger = logging.getLogger(__name__)


def retrieve_context_snippets(
    query: str,
    top_k: int = 5,
    results: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """Retrieve context snippets for a query.

    Parameters
    ----------
    query:
        The query string used for retrieval.
    top_k:
        Maximum number of snippets to return.
    results:
        Optional list of pre-fetched results. Each result is expected to have a
        non-empty ``content`` field.

    Returns
    -------
    str
        The concatenated context snippets separated by newlines.

    Raises
    ------
    ValueError
        If no valid snippets remain after validation.
    """

    # TODO: plug your Chroma/pgvector retrieval here
    if results is None:
        results = []

    valid_snippets: List[str] = []
    for idx, item in enumerate(results):
        content = item.get("content") if isinstance(item, dict) else None
        if not content:
            logger.warning("Malformed result at index %s: %s", idx, item)
            continue
        valid_snippets.append(content)

    if not valid_snippets:
        message = f"No valid context snippets found for query: {query!r}"
        logger.warning(message)
        raise ValueError(message)

    return "\n".join(valid_snippets[:top_k])
