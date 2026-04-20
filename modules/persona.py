"""
RVC persona skin — passthrough until RVC weights and runtime are wired.
"""


def apply_voice(audio_bytes: bytes) -> bytes:
    """
    Applies RVC voice conversion to audio.
    Returns: processed WAV bytes
    """
    return audio_bytes
