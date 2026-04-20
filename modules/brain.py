"""
Local LLM via Ollama HTTP API (no cloud). Set PIA_LLM_MODEL to your pulled model.
"""

from __future__ import annotations

import json
import os
from typing import Any

import httpx

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
DEFAULT_MODEL = os.environ.get("PIA_LLM_MODEL", "phi3:mini")


def ask_brain(prompt: str, context: list[dict] | None = None) -> str:
    """
    Sends a prompt to the local LLM.
    context: list of {"role": "user"/"assistant", "content": str}
    Returns: plain text string response
    """
    context = context or []
    messages: list[dict[str, Any]] = []

    system = os.environ.get("PIA_SYSTEM_PROMPT")
    if system:
        messages.append({"role": "system", "content": system})

    for m in context:
        role = m.get("role")
        content = m.get("content")
        if role in ("user", "assistant") and isinstance(content, str):
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": prompt})

    model = os.environ.get("PIA_LLM_MODEL", DEFAULT_MODEL)
    payload = {"model": model, "messages": messages, "stream": False}

    with httpx.Client(timeout=120.0) as client:
        r = client.post(f"{OLLAMA_HOST}/api/chat", json=payload)
        r.raise_for_status()
        data = r.json()

    msg = data.get("message") or {}
    text = msg.get("content")
    if isinstance(text, str) and text.strip():
        return text.strip()

    if "response" in data and isinstance(data["response"], str):
        return data["response"].strip()

    return json.dumps(data)[:2000]
