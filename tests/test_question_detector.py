import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
import app.question_detector as qd
from app.config import Config


class FakeTime:
    def __init__(self):
        self.t = 0.0

    def advance(self, ms: int) -> None:
        self.t += ms / 1000.0

    def time(self) -> float:
        return self.t


def test_punctuation_boundary():
    det = qd.QuestionBoundaryDetector()
    out = det.add_token("How are you?")
    assert out == "How are you?"


def test_silence_boundary(monkeypatch):
    fake = FakeTime()
    monkeypatch.setattr(qd.time, "time", fake.time)
    det = qd.QuestionBoundaryDetector()
    assert det.add_token("Hello") is None
    fake.advance(Config.QUESTION_SILENCE_MS_MIN + 50)
    out = det.add_token(" there")
    assert out == "Hello there"
