import os
import sys
import types
from pathlib import Path

# Ensure repo root on sys.path
sys.path.append(str(Path(__file__).resolve().parents[1]))

# Stub chromadb before importing server to avoid heavy dependency
dummy_collection = type('DummyCollection', (), {'add': lambda *a, **k: None, 'query': lambda *a, **k: {}})
class DummyClient:
    def get_or_create_collection(self, name):
        return dummy_collection()
chromadb_stub = types.SimpleNamespace(Client=lambda *a, **k: DummyClient(), config=types.SimpleNamespace(Settings=lambda *a, **k: None))
sys.modules.setdefault('chromadb', chromadb_stub)
sys.modules.setdefault('chromadb.config', chromadb_stub.config)

# Stub openai client
class DummyOpenAI:
    def __init__(self, *a, **k):
        pass
    class chat:
        class completions:
            @staticmethod
            def create(*a, **k):
                class R:
                    choices = [type('C', (), {'message': type('M', (), {'content': '{}'})})]
                return R()
openai_stub = types.SimpleNamespace(OpenAI=DummyOpenAI)
sys.modules.setdefault('openai', openai_stub)
# Stub dotenv
sys.modules.setdefault('dotenv', types.SimpleNamespace(load_dotenv=lambda *a, **k: None))
# Stub stripe
class DummyStripe:
    api_key = ""
    class Price:
        @staticmethod
        def create(**kwargs):
            return {}
    class Subscription:
        @staticmethod
        def create(**kwargs):
            return {"status": "active"}
    class InvoiceItem:
        @staticmethod
        def create(**kwargs):
            return {}
    class Invoice:
        @staticmethod
        def create(**kwargs):
            return {}
    class Webhook:
        @staticmethod
        def construct_event(payload, sig, secret):
            return {}
sys.modules.setdefault('stripe', DummyStripe)

# Set secret before importing server
os.environ['GITHUB_WEBHOOK_SECRET'] = 'test-secret'

from backend import server


def test_github_webhook_rejects_bad_signature():
    client = server.app.test_client()
    res = client.post('/webhook/github', data=b'{}', headers={
        'X-Hub-Signature-256': 'sha256=bad',
        'X-GitHub-Event': 'push',
        'Content-Type': 'application/json'
    })
    assert res.status_code == 401


def test_github_pr_webhook_rejects_bad_signature():
    client = server.app.test_client()
    res = client.post('/webhook/github/pr', data=b'{}', headers={
        'X-Hub-Signature-256': 'sha256=bad',
        'X-GitHub-Event': 'pull_request',
        'Content-Type': 'application/json'
    })
    assert res.status_code == 401
