"""Utility helpers used within the demo repository."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List


def fibonacci(depth: int) -> List[int]:
    """Return ``depth`` elements of the fibonacci sequence."""

    if depth <= 0:
        return []
    sequence = [0, 1]
    while len(sequence) < depth:
        sequence.append(sequence[-1] + sequence[-2])
    return sequence[:depth]


def read_config(path: str) -> Dict[str, object]:
    """Read a JSON config file; return defaults when missing."""

    config_path = Path(path)
    if not config_path.exists():
        return {"depth": 5, "author": "fixtures"}
    return json.loads(config_path.read_text())
