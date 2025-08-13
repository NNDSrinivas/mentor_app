import sys
import numpy as np
import wave
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
