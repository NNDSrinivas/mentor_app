"""Utilities for chunking GitHub file contents into semantic blocks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List


@dataclass(frozen=True)
class CodeChunk:
    path: str
    start_line: int
    end_line: int
    text: str


def chunk_source(
    path: str,
    content: str,
    chunk_size: int = 160,
    overlap: int = 20,
) -> List[CodeChunk]:
    """Split text content into ~``chunk_size`` line chunks with overlap.

    The function keeps chunk boundaries aligned with line numbers which allows us
    to build GitHub permalinks easily.  Overlap is used so that contextual lines
    around boundaries remain searchable.
    """

    lines = content.splitlines()
    if not lines:
        return []

    chunks: List[CodeChunk] = []
    start = 0
    total_lines = len(lines)
    step = max(chunk_size - overlap, 1)

    while start < total_lines:
        end = min(start + chunk_size, total_lines)
        snippet_lines = lines[start:end]
        if snippet_lines:
            joined_text = "\n".join(snippet_lines)
            chunk = CodeChunk(
                path=path,
                start_line=start + 1,
                end_line=end,
                text=joined_text.strip() or joined_text,
            )
            chunks.append(chunk)
        if end == total_lines:
            break
        start = min(end, total_lines)
        if overlap and start > overlap:
            start -= overlap
    return chunks


def iter_language_from_path(path: str) -> Iterable[str]:
    """Yield language heuristics based on file extension."""

    lower = path.lower()
    if lower.endswith(".py"):
        yield "Python"
    elif lower.endswith(".ts") or lower.endswith(".tsx"):
        yield "TypeScript"
    elif lower.endswith(".js") or lower.endswith(".jsx"):
        yield "JavaScript"
    elif lower.endswith(".go"):
        yield "Go"
    elif lower.endswith(".rs"):
        yield "Rust"
    elif lower.endswith(".java"):
        yield "Java"
    elif lower.endswith(".cs"):
        yield "C#"
    elif lower.endswith(".rb"):
        yield "Ruby"
    elif lower.endswith(".php"):
        yield "PHP"
    elif lower.endswith(".swift"):
        yield "Swift"
    elif lower.endswith(".kt") or lower.endswith(".kts"):
        yield "Kotlin"
    elif lower.endswith(".cpp") or lower.endswith(".cc") or lower.endswith(".cxx"):
        yield "C++"
    elif lower.endswith(".c"):
        yield "C"
    elif lower.endswith(".scala"):
        yield "Scala"
    elif lower.endswith(".md"):
        yield "Markdown"
    elif lower.endswith(".json"):
        yield "JSON"
    elif lower.endswith(".yaml") or lower.endswith(".yml"):
        yield "YAML"
    elif lower.endswith(".sql"):
        yield "SQL"


__all__ = ["CodeChunk", "chunk_source", "iter_language_from_path"]

