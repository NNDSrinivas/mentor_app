import importlib
import os
import sys

# Ensure repository root is on the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def _create_assistant():
    """Reload configuration and create a fresh AIAssistant instance."""
    # Reload modules so that environment variable changes are picked up.
    import app.config as config
    importlib.reload(config)
    import app.knowledge_base as knowledge_base
    importlib.reload(knowledge_base)
    import app.ai_assistant as ai_assistant
    importlib.reload(ai_assistant)
    return ai_assistant.AIAssistant()


def test_assistant_starts_with_api_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    assistant = _create_assistant()
    assert assistant.mock_mode is False
    assert assistant.memory.kb is not None


def test_assistant_starts_without_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assistant = _create_assistant()
    assert assistant.mock_mode is True
    assert assistant.memory.kb is not None
