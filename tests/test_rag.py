import os
import sys
import types

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.rag import retrieve_context_snippets


def make_stub(results, collector):
    def query_knowledge_base(query, top_k, doc_type=None):
        collector.append((query, top_k, doc_type))
        return results
    return types.SimpleNamespace(query_knowledge_base=query_knowledge_base)


def test_retrieve_context_snippets_passes_doc_type(monkeypatch):
    calls = []
    stub = make_stub([{"content": "alpha"}], calls)
    monkeypatch.setitem(sys.modules, "app.knowledge_base", stub)
    out = retrieve_context_snippets("q", top_k=1, doc_type="code")
    assert out == "alpha"
    assert calls == [("q", 1, "code")]


def test_retrieve_context_snippets_without_doc_type(monkeypatch):
    calls = []
    stub = make_stub([{"content": "beta"}], calls)
    monkeypatch.setitem(sys.modules, "app.knowledge_base", stub)
    out = retrieve_context_snippets("q", top_k=1)
    assert out == "beta"
    assert calls == [("q", 1, None)]

