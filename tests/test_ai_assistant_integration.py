import sys
import asyncio
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

from app.ai_assistant import AIAssistant


async def _run_segments(assistant: AIAssistant):
    await assistant.process_interview_speech("Can you tell me about your experience?", {})
    await assistant.process_interview_speech("Sure, I have worked on many projects.", {})


@pytest.mark.asyncio
async def test_ai_assistant_records_segments(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    monkeypatch.setattr("app.ai_assistant.KnowledgeBase", DummyKB)
    monkeypatch.setattr("app.ai_assistant.TranscriptionService", DummyTS)
    monkeypatch.setattr("app.ai_assistant.SummarizationService", DummySumm)

    assistant = AIAssistant()
    assistant.mock_mode = True

    await _run_segments(assistant)

    session = assistant.memory.sessions.get("interview_session")
    assert session is not None
    assert len(session.conversations) == 2
    first, second = session.conversations
    assert first.context["is_interviewer"] is True
    assert first.context["is_question"] is True
    assert second.context["is_interviewer"] is False
