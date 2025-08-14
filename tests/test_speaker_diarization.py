import sys
import os
import numpy as np
import wave
import importlib
import jwt
from datetime import datetime, timedelta
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
from app.speaker_diarization import SpeakerDiarizer


def _generate_test_wav(path: Path) -> Path:
    sr = 16000
    t = np.linspace(0, 0.5, int(sr * 0.5), endpoint=False)
    s1 = 0.5 * np.sin(2 * np.pi * 220 * t)
    s2 = 0.5 * np.sin(2 * np.pi * 330 * t)
    silence = np.zeros(int(sr * 0.2))
    audio = np.concatenate([s1, silence, s2])
    pcm = (audio * 32767).astype("<i2")
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())
    return path


def test_diarizer_detects_multiple_speakers(tmp_path):
    audio_path = _generate_test_wav(tmp_path / "two_speakers.wav")
    diarizer = SpeakerDiarizer()
    segments = diarizer.identify_speakers(str(audio_path))
    assert len(segments) == 2
    assert segments[0].speaker_id != segments[1].speaker_id
    assert segments[0].end_time <= segments[1].start_time


def test_diarization_service_enabled(monkeypatch, tmp_path):
    monkeypatch.setenv("ENABLE_SPEAKER_DIARIZATION", "true")
    monkeypatch.setenv("ENABLE_MEMORY_SERVICE", "false")
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    monkeypatch.setenv("REALTIME_DATABASE_PATH", str(tmp_path / "rt.db"))

    if "production_realtime" in sys.modules:
        del sys.modules["production_realtime"]
    import production_realtime  # type: ignore
    assert production_realtime.diarization_service is not None


def test_add_caption_assigns_speaker(monkeypatch, tmp_path):
    monkeypatch.setenv("ENABLE_SPEAKER_DIARIZATION", "true")
    monkeypatch.setenv("ENABLE_MEMORY_SERVICE", "false")
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    monkeypatch.setenv("REALTIME_DATABASE_PATH", str(tmp_path / "rt2.db"))

    if "production_realtime" in sys.modules:
        del sys.modules["production_realtime"]
    import production_realtime  # type: ignore
    production_realtime.diarization_service.assign_speaker_to_text = lambda text, context=None: "interviewer"
    production_realtime.generate_ai_response = lambda *args, **kwargs: "ok"

    app = production_realtime.app
    client = app.test_client()
    token = jwt.encode(
        {"user_id": 1, "exp": datetime.utcnow() + timedelta(hours=1)},
        app.config["SECRET_KEY"],
        algorithm="HS256",
    )

    res = client.post("/api/sessions", json={}, headers={"Authorization": f"Bearer {token}"})
    session_id = res.get_json()["session_id"]
    res = client.post(
        f"/api/sessions/{session_id}/captions",
        json={"text": "Can you explain?"},
        headers={"Authorization": f"Bearer {token}"},
    )
    data = res.get_json()
    assert data["speaker"] == "interviewer"
