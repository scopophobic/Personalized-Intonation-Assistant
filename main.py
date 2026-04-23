"""
PIA orchestrator: FastAPI + intent router. Blocking module calls run in threads.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import re
from typing import Any, Optional

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from modules.brain import ask_brain
from modules.cache import cache_audio, get_cached_audio
from modules.ear import analyze_pitch
from modules.persona import apply_voice
from modules.voice import synthesize_demo

app = FastAPI(title="PIA", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:3000",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def route_intent(message: str, has_audio: bool) -> str:
    """
    Returns one of: "talk" | "demo" | "analyze"
    """
    if has_audio:
        return "analyze"

    classification_prompt = f"""
You are a routing classifier. Given a user message, output ONLY one of these labels:
- talk     (user wants explanation, conversation, or theory)
- demo     (user wants to hear an audio demonstration)
- analyze  (user wants feedback on their singing — but no audio was provided)

User message: "{message}"

Output only the label, nothing else.
"""
    raw = ask_brain(classification_prompt, []).strip().lower()
    m = re.search(r"\b(talk|demo|analyze)\b", raw)
    if m:
        return m.group(1)
    first = raw.split()[0] if raw.split() else "talk"
    first = re.sub(r"[^a-z]", "", first)
    if first in ("talk", "demo", "analyze"):
        return first
    return "talk"


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/chat")
async def chat(
    message: str = Form(...),
    audio: Optional[UploadFile] = File(None),
    history: str = Form(default="[]"),
) -> dict[str, Any]:
    try:
        ctx: list[dict] = json.loads(history)
        if not isinstance(ctx, list):
            ctx = []
    except json.JSONDecodeError:
        ctx = []

    audio_bytes: bytes | None = None
    if audio is not None:
        audio_bytes = await audio.read()
        if not audio_bytes:
            audio_bytes = None

    intent = route_intent(message, audio_bytes is not None)

    if intent == "talk":
        text = await asyncio.to_thread(ask_brain, message, ctx)
        return {"type": "talk", "text": text}

    if intent == "demo":
        cache_key = hashlib.md5(message.encode(), usedforsecurity=False).hexdigest()
        audio_out = get_cached_audio(cache_key)

        text = await asyncio.to_thread(ask_brain, message, ctx)
        if not audio_out:
            raw = await asyncio.to_thread(synthesize_demo, text)
            audio_out = await asyncio.to_thread(apply_voice, raw)
            cache_audio(cache_key, audio_out)

        return {
            "type": "demo",
            "text": text,
            "audio": base64.b64encode(audio_out).decode("ascii"),
        }

    # analyze
    assert audio_bytes is not None
    pitch_data = await asyncio.to_thread(analyze_pitch, audio_bytes)
    feedback_prompt = f"""
The user just sang a phrase. Here is the pitch analysis:
{pitch_data}

Give specific, encouraging feedback. Mention which notes were off and by how much.
Suggest one concrete thing to fix. Keep it under 4 sentences.
"""
    feedback = await asyncio.to_thread(ask_brain, feedback_prompt, ctx)
    return {
        "type": "analyze",
        "text": feedback,
        "pitch_data": pitch_data,
    }
