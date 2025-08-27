import os, sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app.asr_vad import ReadBackAligner

def test_exact_match_advances_cursor():
    answer = "The quick brown fox jumps over the lazy dog"
    aligner = ReadBackAligner(answer)
    idx = aligner.update("brown fox jumps")
    target = answer.lower().index("brown fox jumps") + len("brown fox jumps")
    assert abs(idx - target) <= 1

def test_fuzzy_match_handles_partial_words():
    answer = "Machine learning enables computers to learn from data"
    aligner = ReadBackAligner(answer)
    idx = aligner.update("learnin enables")
    assert idx > 0
