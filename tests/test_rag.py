import pytest

from app.rag import retrieve_context_snippets


def test_retrieve_context_snippets_returns_string():
    result = retrieve_context_snippets("test")
    assert isinstance(result, str)
