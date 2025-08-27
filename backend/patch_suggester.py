from __future__ import annotations
import re


def suggest_patch(log: str) -> str:
    """Generate a minimal patch suggestion from a CI log.

    Supports two simple heuristics:
    - Missing Python dependency (ModuleNotFoundError) -> add to requirements.txt
    - Failing assertion in tests -> replace expected value with actual value
    """
    # Dependency missing
    m = re.search(r"ModuleNotFoundError: No module named '([^']+)'", log)
    if m:
        pkg = m.group(1)
        return (
            "--- a/requirements.txt\n"
            "+++ b/requirements.txt\n"
            "@@\n"
            f" {pkg}\n"
        )

    # Simple pytest assertion mismatch
    m = re.search(
        r">[^\n]*assert ([^\n]+)\nE\s+AssertionError: assert ([^\n]+)\n\n([^:]+\.py):", log
    )
    if m:
        expected_expr = m.group(1).strip()
        actual_expr = m.group(2).strip()
        file_path = m.group(3).strip()
        return (
            f"--- a/{file_path}\n"
            f"+++ b/{file_path}\n"
            "@@\n"
            f"-assert {expected_expr}\n"
            f"+assert {actual_expr}\n"
        )

    return ""


def suggest_patch_from_url(url: str, timeout: int = 10) -> str:
    """Fetch logs from ``url`` and run :func:`suggest_patch`.

    This imports :mod:`requests` lazily to keep the dependency optional.
    Returns empty string if the logs cannot be fetched or no patch is found.
    """
    try:
        import requests  # type: ignore

        r = requests.get(url, timeout=timeout)
        r.raise_for_status()
        return suggest_patch(r.text)
    except Exception:
        return ""
