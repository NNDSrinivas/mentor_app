import os
import sys
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from backend.context_builder import ContextBuilder
from backend.prompt_builder import PromptBuilder


class MockChroma:
    def __init__(self, docs):
        self.docs = docs

    def query(self, user_id, doc_type, top_k):
        matched = [d for d in self.docs if d["user_id"] == user_id and d["doc_type"] == doc_type]
        return matched[:top_k]


def make_doc(user_id, doc_type, text, days_ago, metadata=None):
    return {
        "user_id": user_id,
        "doc_type": doc_type,
        "text": text,
        "created_at": datetime.utcnow() - timedelta(days=days_ago),
        "metadata": metadata or {},
    }


def test_context_ordering_and_budget():
    docs = [
        make_doc("u1", "profile", "senior summary", 100, {"level": "IC7"}),
        make_doc("u1", "jira", "jira one item", 1),
        make_doc("u1", "jira", "jira two item", 2),
        make_doc("u1", "meeting", "meeting one", 1),
        make_doc("u1", "repo", "repo one", 2),
        make_doc("u1", "repo", "repo two", 1),
    ]
    chroma = MockChroma(docs)
    builder = ContextBuilder(chroma, token_budget=12)
    context = builder.build("u1")

    assert context["jira"] == ["jira one item", "jira two item"]
    assert context["meetings"] == ["meeting one"]
    assert context["repo"] == ["repo two"]  # oldest repo doc trimmed
    assert context["token_count"] <= 12


def test_context_priority_drops_lowest():
    docs = [
        make_doc("u1", "profile", "senior summary", 100, {"level": "IC6"}),
        make_doc("u1", "jira", "jira one item", 1),
        make_doc("u1", "jira", "jira two item", 2),
        make_doc("u1", "meeting", "meeting one", 1),
        make_doc("u1", "repo", "repo one", 1),
    ]
    chroma = MockChroma(docs)
    builder = ContextBuilder(chroma, token_budget=8)
    context = builder.build("u1")

    assert context["jira"] == ["jira one item", "jira two item"]
    assert context["meetings"] == []
    assert context["repo"] == []
    assert context["token_count"] <= 8


def test_prompt_builder_voice_block():
    docs = [
        make_doc("u1", "profile", "senior summary", 100, {"level": "IC7"}),
        make_doc("u1", "jira", "jira issue", 1),
        make_doc("u1", "meeting", "meeting notes", 1),
        make_doc("u1", "repo", "repo summary", 1),
    ]
    chroma = MockChroma(docs)
    context = ContextBuilder(chroma, token_budget=50).build("u1")

    pb = PromptBuilder(max_tokens=50)
    prompt = pb.build("How do we scale?", context)

    assert "IC7" in prompt
    assert "What we know:" in prompt
    assert "Resume: senior summary" in prompt
    assert "Jira: jira issue" in prompt
    assert "Meetings: meeting notes" in prompt
    assert "Repo: repo summary" in prompt
