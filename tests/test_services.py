import importlib
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def _reset_module(module_name: str) -> None:
    """Remove a module from sys.modules if present to force a clean import."""
    if module_name in sys.modules:
        del sys.modules[module_name]


def _mock_chat_completion(content: str):
    """Create a lightweight object that mimics OpenAI's chat completion response."""
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
    )


def _install_stub_dependencies() -> None:
    """Install lightweight stubs for optional heavy dependencies."""
    class _StubDiarizationService:
        def __init__(self, *args, **kwargs):
            pass

        def resolve_speaker(self, speaker_id):
            return speaker_id

        def assign_speaker_to_text(self, text):
            return None

    class _StubMeetingIntelligence:
        def __init__(self, *args, **kwargs):
            pass

        def analyze(self, *args, **kwargs):
            return None

    sys.modules.pop("backend.diarization_service", None)
    sys.modules.setdefault(
        "backend.diarization_service",
        SimpleNamespace(DiarizationService=_StubDiarizationService),
    )
    sys.modules.pop("app.meeting_intelligence", None)
    sys.modules.setdefault(
        "app.meeting_intelligence",
        SimpleNamespace(MeetingIntelligence=_StubMeetingIntelligence),
    )
def test_backend_register_login_and_resume_flow(tmp_path, monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    backend_db = tmp_path / "backend.db"
    monkeypatch.setenv("DATABASE_PATH", str(backend_db))
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    _install_stub_dependencies()
    _reset_module("production_backend")
    backend = importlib.import_module("production_backend")

    with backend.app.app_context():
        backend.init_db()

    monkeypatch.setattr(
        backend.openai_client.chat.completions,
        "create",
        lambda *args, **kwargs: _mock_chat_completion("Mock backend answer"),
    )

    client = backend.app.test_client()

    register_response = client.post(
        "/api/register",
        json={"email": "test@example.com", "password": "secret123"},
    )
    assert register_response.status_code == 201

    login_response = client.post(
        "/api/login",
        json={"email": "test@example.com", "password": "secret123"},
    )
    assert login_response.status_code == 200
    token = login_response.get_json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    ask_response = client.post(
        "/api/ask",
        json={"question": "Explain CAP theorem", "interview_mode": True},
        headers=headers,
    )
    assert ask_response.status_code == 200
    assert ask_response.get_json()["response"] == "Mock backend answer"

    resume_text = (
        "Experienced engineer with 10+ years in software development, specializing in backend systems, "
        "cloud infrastructure, and team leadership. Proven track record in delivering scalable solutions "
        "and mentoring junior engineers."
    )
    upload_response = client.post(
        "/api/resume",
        json={"resume_text": resume_text},
        headers=headers,
    )
    assert upload_response.status_code == 200
    assert upload_response.get_json()["length"] == len(resume_text)

    fetch_response = client.get("/api/resume", headers=headers)
    assert fetch_response.status_code == 200
    assert fetch_response.get_json()["resume_text"] == resume_text


def test_realtime_session_flow(tmp_path, monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    backend_db = tmp_path / "backend.db"
    realtime_db = tmp_path / "realtime.db"
    monkeypatch.setenv("DATABASE_PATH", str(backend_db))
    monkeypatch.setenv("REALTIME_DATABASE_PATH", str(realtime_db))
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    _install_stub_dependencies()
    _reset_module("production_backend")
    backend = importlib.import_module("production_backend")
    with backend.app.app_context():
        backend.init_db()

    monkeypatch.setattr(
        backend.openai_client.chat.completions,
        "create",
        lambda *args, **kwargs: _mock_chat_completion("Mock backend answer"),
    )

    backend_client = backend.app.test_client()
    backend_client.post(
        "/api/register",
        json={"email": "session@example.com", "password": "secret123"},
    )
    login_response = backend_client.post(
        "/api/login",
        json={"email": "session@example.com", "password": "secret123"},
    )
    token = login_response.get_json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    _reset_module("production_realtime")
    realtime = importlib.import_module("production_realtime")
    with realtime.app.app_context():
        realtime.init_db()

    monkeypatch.setattr(
        realtime,
        "generate_ai_response",
        lambda *args, **kwargs: "Mock real-time answer",
    )

    realtime_client = realtime.app.test_client()

    session_response = realtime_client.post(
        "/api/sessions",
        json={"user_level": "IC6", "meeting_type": "technical_interview"},
        headers=headers,
    )
    assert session_response.status_code == 201
    session_id = session_response.get_json()["session_id"]

    caption_response = realtime_client.post(
        f"/api/sessions/{session_id}/captions",
        json={
            "text": "How would you design a scalable cache?",
            "speaker": "interviewer",
        },
        headers=headers,
    )
    assert caption_response.status_code == 200
    assert caption_response.get_json()["ai_response"]["answer"] == "Mock real-time answer"

    answers_response = realtime_client.get(
        f"/api/sessions/{session_id}/answers",
        headers=headers,
    )
    assert answers_response.status_code == 200
    answers = answers_response.get_json()["answers"]
    assert len(answers) == 1
    assert answers[0]["answer"] == "Mock real-time answer"
    assert "scalable cache" in answers[0]["question"]
