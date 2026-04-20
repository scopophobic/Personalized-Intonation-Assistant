"""
Pitch analysis (Ear). Uses librosa pYIN (plan alternative to CREPE) for broad
compatibility; optional CREPE path can be added when tensorflow is available.
"""

from __future__ import annotations

import io
import math
import re
from collections import defaultdict

import librosa
import numpy as np
import soundfile as sf


def _hz_to_note_safe(hz: float) -> str:
    if hz <= 0 or not math.isfinite(hz):
        return "?"
    return librosa.hz_to_note(float(hz), cents=False)


def analyze_pitch(audio_bytes: bytes) -> dict:
    """
    Analyzes pitch and timing in user audio (WAV or other formats soundfile understands).

    Returns the contract shape from cursor_plan.md.
    """
    y, sr = sf.read(io.BytesIO(audio_bytes), always_2d=False)
    if y.ndim > 1:
        y = np.mean(y, axis=1)
    y = np.asarray(y, dtype=np.float32)
    if y.size == 0:
        return {
            "notes": [],
            "accuracy_score": 0.0,
            "sharp_notes": [],
            "flat_notes": [],
            "summary": "No audio energy detected — try recording a bit louder.",
        }

    fmin = librosa.note_to_hz("C2")
    fmax = librosa.note_to_hz("C7")
    hop_length = 512
    f0, voiced_flag, voiced_probs = librosa.pyin(
        y, fmin=fmin, fmax=fmax, sr=sr, hop_length=hop_length
    )
    times = librosa.frames_to_time(np.arange(len(f0)), sr=sr, hop_length=hop_length)

    notes: list[dict] = []
    cents_by_label: defaultdict[str, list[float]] = defaultdict(list)

    for t, hz, vflag, vprob in zip(times, f0, voiced_flag, voiced_probs):
        if not bool(vflag) or hz is None or not math.isfinite(float(hz)):
            continue
        hz_f = float(hz)
        label = _hz_to_note_safe(hz_f)
        midi = librosa.hz_to_midi(hz_f)
        et_hz = librosa.midi_to_hz(round(float(midi)))
        cents = 1200.0 * math.log2(hz_f / et_hz) if et_hz > 0 else 0.0
        cents_by_label[label].append(cents)

        conf = float(vprob) if vprob is not None and math.isfinite(float(vprob)) else 0.5
        notes.append(
            {
                "time": round(float(t), 3),
                "hz": round(hz_f, 2),
                "note": label,
                "confidence": round(min(max(conf, 0.0), 1.0), 3),
            }
        )

    sharp_notes: list[str] = []
    flat_notes: list[str] = []
    all_cents: list[float] = []

    for label, cents_list in cents_by_label.items():
        mean_c = float(np.mean(cents_list))
        all_cents.extend(cents_list)
        if mean_c > 18.0:
            sharp_notes.append(label)
        elif mean_c < -18.0:
            flat_notes.append(label)

    if all_cents:
        mean_abs = float(np.mean(np.abs(all_cents)))
        accuracy_score = float(max(0.0, min(1.0, 1.0 - mean_abs / 45.0)))
    else:
        accuracy_score = 0.0

    summary = _build_summary(sharp_notes, flat_notes, accuracy_score, len(notes))

    return {
        "notes": notes[:500],
        "accuracy_score": round(accuracy_score, 3),
        "sharp_notes": sorted(set(sharp_notes)),
        "flat_notes": sorted(set(flat_notes)),
        "summary": summary,
    }


def _build_summary(
    sharp: list[str], flat: list[str], accuracy: float, n_frames: int
) -> str:
    if n_frames == 0:
        return "Could not track pitch reliably — hum or sing a clearer sustained tone."
    parts: list[str] = []
    if sharp:
        parts.append(f"Sharp tendency on: {', '.join(sharp[:5])}")
    if flat:
        parts.append(f"Flat tendency on: {', '.join(flat[:5])}")
    if not parts:
        parts.append("Pitch centers look fairly stable relative to equal temperament.")
    parts.append(f"Overall steadiness score: {accuracy:.0%}.")
    text = " ".join(parts)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:240]
