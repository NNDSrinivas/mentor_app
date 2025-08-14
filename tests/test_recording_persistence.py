import sys
import json
from pathlib import Path
import importlib


def setup_module(module):
    sys.path.append(str(Path(__file__).resolve().parents[1]))


def test_get_recording_path(tmp_path, monkeypatch):
    from app import screen_record
    monkeypatch.setattr(screen_record.Config, "RECORDINGS_DIR", tmp_path)
    metadata = {
        "session_id": "s1",
        "video_path": str(tmp_path / "s1.mp4"),
        "recorded_at": "now",
    }
    (tmp_path / "s1_metadata.json").write_text(json.dumps(metadata))
    assert screen_record.get_recording_path("s1") == str(tmp_path / "s1.mp4")


def test_recording_endpoint_returns_path(tmp_path, monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "secret")
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    monkeypatch.setenv("REALTIME_DATABASE_PATH", str(tmp_path / "db.sqlite"))

    if "production_realtime" in sys.modules:
        del sys.modules["production_realtime"]
    import production_realtime
    importlib.reload(production_realtime)

    production_realtime.app.config["TESTING"] = True

    from app import screen_record as sr
    monkeypatch.setattr(sr.Config, "RECORDINGS_DIR", tmp_path)
    monkeypatch.setattr(production_realtime.screen_record.Config, "RECORDINGS_DIR", tmp_path)

    metadata = {
        "session_id": "sess1",
        "video_path": str(tmp_path / "sess1.mp4"),
        "recorded_at": "now",
    }
    (tmp_path / "sess1_metadata.json").write_text(json.dumps(metadata))

    production_realtime.session_recordings.clear()
    monkeypatch.setattr(production_realtime, "verify_token", lambda token: {"user_id": 1})

    class DummyCursor:
        def fetchone(self):
            return {"id": "sess1"}

    class DummyDB:
        def execute(self, *args, **kwargs):
            return DummyCursor()

    monkeypatch.setattr(production_realtime, "get_db", lambda: DummyDB())

    client = production_realtime.app.test_client()
    resp = client.get(
        "/api/sessions/sess1/recording",
        headers={"Authorization": "Bearer t"},
    )
    data = resp.get_json()
    assert resp.status_code == 200
    assert data["video_path"] == str(tmp_path / "sess1.mp4")


def test_meeting_summary_links_recording(tmp_path, monkeypatch):
    from app.meeting_intelligence import meeting_intelligence, MeetingContext
    from app import screen_record

    ctx = MeetingContext(
        meeting_id="sess2",
        meeting_type="standup",
        participants=[],
        action_items=[],
        decisions=[],
        agenda_items=[],
    )
    meeting_intelligence.active_meetings["sess2"] = ctx

    monkeypatch.setattr(screen_record, "get_recording_path", lambda _: str(tmp_path / "sess2.mp4"))

    summary = meeting_intelligence.get_meeting_summary("sess2")
    assert summary["recording_path"] == str(tmp_path / "sess2.mp4")
