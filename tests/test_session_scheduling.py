import os
import sys
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
import importlib


def setup_module(module):
    # Ensure repository root on path
    sys.path.append(str(Path(__file__).resolve().parents[1]))


def test_schedule_session(tmp_path, monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "testsecret")
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_PATH", str(db_path))
    monkeypatch.setenv("OPENAI_API_KEY", "test")

    if "production_backend" in sys.modules:
        del sys.modules["production_backend"]
    import production_backend
    importlib.reload(production_backend)

    production_backend.app.config["TESTING"] = True
    production_backend.init_db()

    # Create a dummy user
    conn = sqlite3.connect(production_backend.app.config["DATABASE"])
    cur = conn.cursor()
    user_id = "user1"
    cur.execute(
        "INSERT INTO users (id, email, password_hash) VALUES (?, ?, ?)",
        (user_id, "u@example.com", production_backend.hash_password("pw")),
    )
    conn.commit()
    conn.close()

    token = production_backend.generate_token(user_id)

    client = production_backend.app.test_client()
    start = datetime.now()
    end = start + timedelta(hours=1)
    resp = client.post(
        "/api/sessions",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": "Test Meeting",
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
            "attendees": ["a@example.com"],
            "platform": "zoom",
        },
    )

    assert resp.status_code == 201
    data = resp.get_json()
    assert data["meeting_url"].startswith("https://")

    # Verify session stored in database
    conn = sqlite3.connect(production_backend.app.config["DATABASE"])
    cur = conn.cursor()
    cur.execute("SELECT title FROM sessions WHERE id=?", (data["session_id"],))
    row = cur.fetchone()
    conn.close()
    assert row[0] == "Test Meeting"

