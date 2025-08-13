from __future__ import annotations
"""Simple code generation utilities for review comment automation."""
from typing import Dict, Any, Optional, List


def extract_patch_from_comment(body: str) -> Optional[str]:
    """Extract a unified diff patch from a comment body if present."""
    in_patch = False
    patch_lines: List[str] = []
    for line in body.splitlines():
        if line.strip().startswith("```patch") or line.strip().startswith("```diff"):
            in_patch = True
            continue
        if line.strip().startswith("```") and in_patch:
            break
        if in_patch:
            patch_lines.append(line)
    return "\n".join(patch_lines) if patch_lines else None


def generate_patch(comment: Dict[str, Any]) -> Optional[str]:
    """Generate a patch for an actionable review comment.

    This stub tries to read a patch directly embedded in the comment. In a real
    deployment this would call an external code generation service.
    """
    body = comment.get("body", "")
    patch = extract_patch_from_comment(body)
    if patch:
        return patch
    # Placeholder for AI-based generation
    return None
