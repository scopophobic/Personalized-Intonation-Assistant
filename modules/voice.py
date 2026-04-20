"""
TTS for coaching demos. Prefers Kokoro (hexgrad/kokoro) when installed; falls back
to macOS `say` for a zero-dependency dev path. style_hint reserved for future prosody.
"""

from __future__ import annotations

import io
import os
import platform
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf


def _synthesize_kokoro(text: str, style_hint: str) -> bytes:
    _ = style_hint  # reserved for future style / language tags in prompts
    from kokoro import KPipeline

    lang = os.environ.get("PIA_KOKORO_LANG", "a")
    voice = os.environ.get("PIA_KOKORO_VOICE", "af_bella")
    pipeline = KPipeline(lang_code=lang)
    chunks: list[np.ndarray] = []
    sample_rate = 24000
    for result in pipeline(text, voice=voice):
        if isinstance(result, tuple) and len(result) >= 3:
            audio = result[2]
        else:
            audio = getattr(result, "audio", None)
            if audio is None:
                continue
        arr = np.asarray(audio, dtype=np.float32).reshape(-1)
        if arr.size:
            chunks.append(arr)
    if not chunks:
        raise RuntimeError("Kokoro produced no audio chunks")
    full = np.concatenate(chunks, axis=0)
    buf = io.BytesIO()
    sf.write(buf, full, sample_rate, format="WAV", subtype="PCM_16")
    return buf.getvalue()


def _synthesize_macos_say(text: str) -> bytes:
    if platform.system() != "Darwin":
        raise RuntimeError("macOS `say` fallback not available on this OS")
    clip = text.strip()[:400]
    with tempfile.NamedTemporaryFile(suffix=".aiff", delete=False) as tmp:
        path = Path(tmp.name)
    try:
        subprocess.run(
            ["say", "-o", str(path), clip],
            check=True,
            capture_output=True,
            text=True,
        )
        data, sr = sf.read(str(path), always_2d=False)
        if data.ndim > 1:
            data = np.mean(data, axis=1)
        buf = io.BytesIO()
        sf.write(buf, np.asarray(data, dtype=np.float32), int(sr), format="WAV", subtype="PCM_16")
        return buf.getvalue()
    finally:
        path.unlink(missing_ok=True)


def synthesize_demo(text: str, style_hint: str = "neutral") -> bytes:
    """
    Converts text to spoken audio (WAV bytes). Singing-quality demos need Kokoro
    or another neural TTS; `say` is a dev fallback.
    """
    _ = style_hint
    try:
        return _synthesize_kokoro(text, style_hint)
    except ImportError:
        pass
    except Exception:
        if os.environ.get("PIA_VOICE_STRICT") == "1":
            raise
    return _synthesize_macos_say(text)
