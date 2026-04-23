import io

import numpy as np
import soundfile as sf

from modules.ear import analyze_pitch


def _tone_wav(freq: float = 440.0, seconds: float = 2.0, sr: int = 44100) -> bytes:
    t = np.linspace(0.0, seconds, int(sr * seconds), endpoint=False, dtype=np.float32)
    y = 0.35 * np.sin(2.0 * np.pi * freq * t)
    buf = io.BytesIO()
    sf.write(buf, y, sr, format="WAV", subtype="PCM_16")
    return buf.getvalue()


def test_analyze_pitch_returns_contract():
    raw = _tone_wav(440.0)
    out = analyze_pitch(raw)
    assert "notes" in out
    assert "accuracy_score" in out
    assert "sharp_notes" in out
    assert "flat_notes" in out
    assert "summary" in out
    assert isinstance(out["notes"], list)
    assert len(out["notes"]) > 0
