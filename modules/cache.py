"""
File-backed WAV cache for demo audio.
"""

from __future__ import annotations

from pathlib import Path

_CACHE_ROOT = Path(__file__).resolve().parent.parent / "cache"


def _path(key: str) -> Path:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in key)[:200]
    _CACHE_ROOT.mkdir(parents=True, exist_ok=True)
    return _CACHE_ROOT / f"{safe}.wav"


def get_cached_audio(key: str) -> bytes | None:
    p = _path(key)
    if p.is_file():
        return p.read_bytes()
    return None


def cache_audio(key: str, audio: bytes) -> None:
    p = _path(key)
    p.write_bytes(audio)
