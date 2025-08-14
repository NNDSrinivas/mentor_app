import sys
import sqlite3
import importlib
import types
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock

import jwt
import pytest

# Ensure repository root on path
sys.path.append(str(Path(__file__).resolve().parents[1]))


def _setup_app(monkeypatch, tmp_path):
    monkeypatch.setenv("JWT_SECRET", "secret")
    db_path = tmp_path / "rt.db"
    monkeypatch.setenv("REALTIME_DATABASE_PATH", str(db_path))
    monkeypatch.setenv("OPENAI_API_KEY", "test")

    # Stub external modules before import
    monkeypatch.setitem(sys.modules, "openai", types.SimpleNamespace(OpenAI=lambda api_key=None: None))
    stub_screen = types.SimpleNamespace(
        analyze_screen_video=lambda path: [],
        record_screen=lambda *a, **k: "/tmp/video.mp4",
    )
    monkeypatch.setitem(sys.modules, "app.screen_record", stub_screen)

    if "production_realtime" in sys.modules:
        del sys.modules["production_realtime"]
    import production_realtime
    importlib.reload(production_realtime)

    production_realtime.app.config["TESTING"] = True
    production_realtime.init_db()

    conn = sqlite3.connect(production_realtime.app.config["DATABASE"])
    conn.execute("INSERT INTO sessions (id, user_id) VALUES (?, ?)", ("sess1", 1))
    conn.commit()
    conn.close()

    production_realtime.session_recordings["sess1"] = "/tmp/video.mp4"

    token = jwt.encode(
        {"user_id": 1, "exp": datetime.utcnow() + timedelta(hours=1)},
        production_realtime.app.config["SECRET_KEY"],
        algorithm="HS256",
    )
    client = production_realtime.app.test_client()
    return production_realtime, client, token


def test_download_uses_send_file(monkeypatch, tmp_path):
    pr, client, token = _setup_app(monkeypatch, tmp_path)
    send_mock = MagicMock(return_value="file")
    monkeypatch.setattr(pr, "send_file", send_mock)

    resp = client.get(
        "/api/sessions/sess1/recording?download=true",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 200
    send_mock.assert_called_once_with("/tmp/video.mp4", as_attachment=True)


def test_analyze_returns_stub(monkeypatch, tmp_path):
    pr, client, token = _setup_app(monkeypatch, tmp_path)
    stub_analysis = {"result": "ok"}
    analyze_mock = MagicMock(return_value=stub_analysis)
    monkeypatch.setattr(pr.screen_record, "analyze_screen_video", analyze_mock)

    resp = client.get(
        "/api/sessions/sess1/recording?analyze=true",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["analysis"] == stub_analysis
    analyze_mock.assert_called_once_with("/tmp/video.mp4")
