from __future__ import annotations

"""Simple heuristics for extracting meeting notes from transcripts.

This module detects decisions and action items from a block of
transcribed text. The extractor looks for keywords such as
``DECISION:`` or ``ACTION:`` and attempts to parse optional owners
(``@alice``) and deadlines (``2023-10-01``).

Returned notes are dictionaries with the following keys:
    * ``type`` – either ``decision`` or ``action``
    * ``text`` – the free form note text
    * ``owner`` – owner username if detected
    * ``due`` – ISO date string if detected

These structures can be fed directly into :mod:`backend.memory_indexer`
for long-term storage.
"""

import re
from typing import Dict, List

# Regular expression patterns
_DECISION_RE = re.compile(r"(?i)\bdecision\s*:\s*(?P<text>.+)")
_ACTION_RE = re.compile(r"(?i)\baction(?:\s*item)?\s*:\s*(?P<text>.+)")
_OWNER_RE = re.compile(r"@(?P<owner>[\w.-]+)")
_DATE_RE = re.compile(r"(?P<due>\d{4}-\d{2}-\d{2})")


def extract_notes(transcript: str) -> List[Dict[str, str]]:
    """Extract structured notes from a transcript string.

    Parameters
    ----------
    transcript: str
        The raw transcript text to analyse.

    Returns
    -------
    List[Dict[str, str]]
        A list of extracted notes. Each note contains at least ``type`` and
        ``text`` keys. ``owner`` and ``due`` are included when detected.
    """

    notes: List[Dict[str, str]] = []
    for line in transcript.splitlines():
        line = line.strip()
        if not line:
            continue

        # Decision lines -------------------------------------------------
        m = _DECISION_RE.search(line)
        if m:
            notes.append({"type": "decision", "text": m.group("text").strip()})
            continue

        # Action lines ---------------------------------------------------
        m = _ACTION_RE.search(line)
        if m:
            text = m.group("text").strip()
            owner_match = _OWNER_RE.search(text)
            due_match = _DATE_RE.search(text)
            owner = owner_match.group("owner") if owner_match else None
            due = due_match.group("due") if due_match else None

            # Clean text by removing owner and due fragments
            if owner_match:
                text = text.replace(owner_match.group(0), "").strip()
            if due_match:
                # Remove the due date and any preceding 'due' token
                text = re.sub(r"\b(due\s*)?" + re.escape(due_match.group("due")), "", text, flags=re.IGNORECASE).strip()

            note = {"type": "action", "text": text}
            if owner:
                note["owner"] = owner
            if due:
                note["due"] = due
            notes.append(note)

    return notes
