import os
import sys
import sqlite3
import importlib
import jwt
import types
from pathlib import Path


def setup_module(module):
    # Ensure repository root on path
    sys.path.append(str(Path(__file__).resolve().parents[1]))


def test_get_screen_recording_missing_file(tmp_path, monkeypatch):
    # Environment setup
    monkeypatch.setenv("JWT_SECRET", "testsecret")
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    db_path = tmp_path / "realtime.db"
    monkeypatch.setenv("REALTIME_DATABASE_PATH", str(db_path))

    # Mock openai module used in production_realtime
    class DummyOpenAI:
        def __init__(self, api_key=None):
            pass
    monkeypatch.setitem(sys.modules, "openai", types.SimpleNamespace(OpenAI=DummyOpenAI))

    # Import and initialize application
    if "production_realtime" in sys.modules:
        del sys.modules["production_realtime"]
    import production_realtime
    importlib.reload(production_realtime)

    production_realtime.app.config["TESTING"] = True
    production_realtime.init_db()

    # Create session for user
    conn = sqlite3.connect(production_realtime.app.config["DATABASE"])
    cur = conn.cursor()
    session_id = "sess1"
    user_id = 1
    cur.execute("INSERT INTO sessions (id, user_id) VALUES (?, ?)", (session_id, user_id))
    conn.commit()
    conn.close()

    # Recording path that does not exist
    production_realtime.session_recordings[session_id] = str(tmp_path / "missing.mp4")

    # Ensure path check fails regardless of file system
    monkeypatch.setattr(os.path, "exists", lambda path: False)

    token = jwt.encode({"user_id": user_id}, "testsecret", algorithm="HS256")
    client = production_realtime.app.test_client()
    resp = client.get(
        f"/api/sessions/{session_id}/recording",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 404
    assert resp.get_json()["error"] == "Recording file not found"
