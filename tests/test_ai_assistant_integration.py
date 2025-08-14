import sys
from typing import Any
from pathlib import Path
import types

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))


class DummyKB:
    def add_document(self, *args, **kwargs):
        pass

    def search(self, *args, **kwargs):
        return []


class DummyTS:
    def __init__(self):
        pass


class DummySumm:
    def __init__(self):
        pass


sys.modules['app.knowledge_base'] = types.SimpleNamespace(KnowledgeBase=DummyKB)
sys.modules['app.transcription'] = types.SimpleNamespace(TranscriptionService=DummyTS)
sys.modules['app.summarization'] = types.SimpleNamespace(SummarizationService=DummySumm)
sys.modules['openai'] = types.SimpleNamespace(OpenAI=object)
sys.modules['dotenv'] = types.SimpleNamespace(load_dotenv=lambda: None)

from app.ai_assistant import AIAssistant
from app.rag import retrieve_context_snippets


def _run_segments(assistant: AIAssistant):
    Segment = types.SimpleNamespace
    assistant._handle_new_segment(
        Segment(
            speaker_id="interviewer",
            transcript="Can you tell me about your experience?",
            is_question=True,
            is_interviewer=True,
        )
    )
    assistant._handle_new_segment(
        Segment(
            speaker_id="candidate",
            transcript="Sure, I have worked on many projects.",
            is_question=False,
            is_interviewer=False,
        )
    )


def test_ai_assistant_records_segments(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    monkeypatch.setattr("app.ai_assistant.KnowledgeBase", DummyKB)
    monkeypatch.setattr("app.ai_assistant.TranscriptionService", DummyTS)
    monkeypatch.setattr("app.ai_assistant.SummarizationService", DummySumm)

    assistant = AIAssistant()
    assistant.mock_mode = True

    _run_segments(assistant)

    session = assistant.memory.sessions.get("interview_session")
    assert session is not None
    assert len(session.conversations) == 2
    first, second = session.conversations
    assert first.context["is_interviewer"] is True
    assert first.context["is_question"] is True
    assert second.context["is_interviewer"] is False


def test_retrieve_context_snippets_returns_snippets(monkeypatch):
    class FakeKB:
        def search(self, query: str, top_k: int = 5, filter_metadata: Any | None = None):
            assert query == "python"
            assert top_k == 2
            return [
                {"content": "Python is a versatile language."},
                {"content": "It emphasizes readability."},
                {"content": "Extra snippet"},
            ][:top_k]

    # Patch KnowledgeBase used inside retrieve_context_snippets
    monkeypatch.setattr("app.rag.KnowledgeBase", FakeKB)

    result = retrieve_context_snippets("python", top_k=2)
    assert "Python is a versatile language." in result
    assert "It emphasizes readability." in result
    assert "Extra snippet" not in result


def test_retrieve_context_snippets_empty(monkeypatch):
    class EmptyKB:
        def search(self, query: str, top_k: int = 5, filter_metadata: Any | None = None):
            return []

    monkeypatch.setattr("app.rag.KnowledgeBase", EmptyKB)
    assert retrieve_context_snippets("unknown") == ""
