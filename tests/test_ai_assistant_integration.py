"""Integration tests for the knowledge base REST endpoints."""

import importlib
import sys
import types
from datetime import datetime, timedelta
from pathlib import Path

import jwt
import pytest

# Ensure repository root is on the Python path
sys.path.append(str(Path(__file__).resolve().parents[1]))


def _get_client(monkeypatch, tmp_path):
    """Create a test client for the production realtime service."""

    class SimpleKB:
        def __init__(self):
            self.docs = []

        def add_document(self, content, metadata):
            self.docs.append({"content": content, "metadata": metadata})
            return f"doc_{len(self.docs)}"

        def query_knowledge_base(self, query, top_k=5, doc_type=None):
            results = []
            for doc in self.docs:
                if query.lower() in doc["content"].lower():
                    results.append({
                        "content": doc["content"],
                        "metadata": doc["metadata"],
                        "similarity_score": 1.0,
                    })
            return results[:top_k]

        def get_collection_info(self):
            return {"document_count": len(self.docs), "collection_name": "test"}

    # Provide dummy implementations and environment
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    monkeypatch.setitem(sys.modules, "app.knowledge_base", types.SimpleNamespace(KnowledgeBase=SimpleKB))

    # Reload configuration and service to pick up environment changes
    import app.config as config
    importlib.reload(config)
    import production_realtime
    importlib.reload(production_realtime)

    return production_realtime.app.test_client(), production_realtime


def _auth_header(app_module, user_id=1):
    token = jwt.encode(
        {"user_id": user_id, "exp": datetime.utcnow() + timedelta(hours=1)},
        app_module.app.config["SECRET_KEY"],
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


def test_knowledge_base_add_and_search(monkeypatch, tmp_path):
    """Ensure documents can be added and retrieved via the REST API."""

    client, module = _get_client(monkeypatch, tmp_path)
    headers = _auth_header(module)

    # Add a document
    resp = client.post(
        "/api/knowledge/add",
        json={"content": "Python testing tricks", "metadata": {"type": "note"}},
        headers=headers,
    )
    assert resp.status_code == 201

    # Search for the document
    resp = client.post(
        "/api/knowledge/search",
        json={"query": "Python"},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["total_results"] >= 1
    assert any("Python testing tricks" in r["content"] for r in data["results"])

    # Stats endpoint should reflect at least one document
    resp = client.get("/api/knowledge/stats", headers=headers)
    assert resp.status_code == 200
    stats = resp.get_json()
    assert stats.get("document_count", 0) >= 1

