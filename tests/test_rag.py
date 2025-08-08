import os
import sys

import pytest

# Ensure repository root is on the Python path so the ``app`` package can be
# imported when tests are executed in isolation.
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import app.rag as rag


def test_retrieve_context_snippets(monkeypatch):
    """retrieve_context_snippets returns joined snippet contents."""

    def fake_query_knowledge_base(query, top_k=5, doc_type=None):
        return [
            {"content": "alpha"},
            {"content": "beta"},
        ]

    # Inject a lightweight stand-in for ``app.knowledge_base`` so that the
    # function's dynamic import resolves to our fake implementation.
    fake_module = type(sys)("app.knowledge_base")
    fake_module.query_knowledge_base = fake_query_knowledge_base
    monkeypatch.setitem(sys.modules, "app.knowledge_base", fake_module)

    result = rag.retrieve_context_snippets("irrelevant", top_k=2)
    assert result == "alpha\n\nbeta"
