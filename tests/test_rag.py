import logging
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.rag import retrieve_context_snippets


def test_retrieve_context_snippets_filters_invalid(caplog):
    results = [
        {"content": "valid1"},
        {"no_content": "oops"},
        {"content": ""},
        {"content": "valid2"},
    ]
    with caplog.at_level(logging.WARNING):
        context = retrieve_context_snippets("query", results=results)
    assert context == "valid1\nvalid2"
    assert "Malformed result at index 1" in caplog.text
    assert "Malformed result at index 2" in caplog.text


def test_retrieve_context_snippets_raises_with_only_invalid(caplog):
    results = [
        {"content": ""},
        {"no_content": "oops"},
    ]
    with caplog.at_level(logging.WARNING):
        with pytest.raises(ValueError):
            retrieve_context_snippets("query", results=results)
    assert "No valid context snippets found" in caplog.text


def test_retrieve_context_snippets_raises_with_empty_results(caplog):
    with caplog.at_level(logging.WARNING):
        with pytest.raises(ValueError):
            retrieve_context_snippets("query", results=[])
    assert "No valid context snippets found" in caplog.text
