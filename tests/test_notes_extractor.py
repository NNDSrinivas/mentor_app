import os, sys
import pathlib
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from backend.notes_extractor import extract_notes


import pytest


@pytest.fixture
def sample_transcript():
    path = pathlib.Path(__file__).parent / "fixtures" / "sample_transcript.txt"
    return path.read_text()


def test_extract_notes(sample_transcript):
    notes = extract_notes(sample_transcript)
    assert any(n["type"] == "decision" for n in notes)
    actions = [n for n in notes if n["type"] == "action"]
    assert len(actions) == 2
    first = actions[0]
    assert first["owner"] == "alice"
    assert first["due"] == "2023-10-01"
    second = actions[1]
    assert second["owner"] == "bob"
    assert second["due"] == "2023-09-15"
