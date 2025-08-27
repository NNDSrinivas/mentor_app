import os, sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app.question_detector import QuestionDetector


def test_punctuation_triggers_boundary():
    det = QuestionDetector(silence_ms=800)
    ts = 0
    text = "What is your name?"
    q = det.add_chunk("other", text, ts)
    assert q == text


def test_silence_gap_triggers_boundary():
    det = QuestionDetector(silence_ms=800)
    ts = 0
    det.add_chunk("other", "Tell me about yourself", ts)
    ts += 900
    q = det.add_chunk("other", "", ts)
    assert q.startswith("Tell me")


def test_classifier_score_triggers_boundary():
    det = QuestionDetector(silence_ms=800, threshold=0.6)
    ts = 0
    q = det.add_chunk("other", "Please explain", ts, score=0.7)
    assert q == "Please explain"


def test_user_speaker_does_not_trigger():
    det = QuestionDetector(silence_ms=800)
    ts = 0
    q = det.add_chunk("user", "Should not trigger?", ts)
    assert q is None
