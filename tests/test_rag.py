import logging
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
from app import rag


def test_retrieve_context_snippets_logs_error(monkeypatch, caplog):
    def boom(query: str, top_k: int = 5):
        raise RuntimeError("boom")

    monkeypatch.setattr(rag, "query_knowledge_base", boom)

    with caplog.at_level(logging.ERROR):
        result = rag.retrieve_context_snippets("question")

    assert result == ""
    assert "Failed to retrieve context snippets" in caplog.text
