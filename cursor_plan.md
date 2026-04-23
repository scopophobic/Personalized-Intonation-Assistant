# PIA — AI Vocal Coach (Project Brief for Cursor)

## What is PIA?

PIA is a modular, local-first AI vocal coach. It listens to a user sing or hum, analyzes their pitch in real time, generates vocal demonstrations across any music style, and gives specific technical feedback — all running on a MacBook M-series with 16GB RAM.

It is NOT a structured lesson app. It is a **practice partner** — the user brings a problem (a phrase they're working on, a note that keeps going flat, a style they want to explore), and PIA responds to that specific moment.

**Supported music styles:** Any — Carnatic, Hindustani, Western classical, Jazz, Pop, Folk, and more. Style knowledge lives in the Brain (LLM), not the audio pipeline.

---

## Core Architecture — 5 Modules

Every module is a standalone Python function. They do not know about each other. The orchestrator wires them together.

```
User input (text or audio)
        │
        ▼
  Intent Router          ← classifies: talk / demo / analyze
        │
   ┌────┼────────────┐
   ▼    ▼            ▼
 Brain  Voice+Persona  Ear
 (LLM) (TTS → RVC)  (pitch analysis)
   │         │            │
   └────┬────┘            │
        ▼                 │
  Response Assembler ◄────┘
        │
        ▼
  User sees text + hears audio
```

### Module 1 — Brain (NLU)
- **Job:** Understand what the user wants, generate coaching text, classify intent
- **Tool:** `llama.cpp` running `Phi-3 Mini` (3.8B params, 4-bit quantized)
- **Alternative:** `Ollama` (easier setup, same models)
- **RAM usage:** ~2–3 GB
- **Key detail:** Runs on Apple Metal via llama.cpp — fast on M-series chips
- **File:** `modules/brain.py`

### Module 2 — Voice (TTS)
- **Job:** Convert text coaching or musical notation into a sung/spoken audio demo
- **Tool:** `Kokoro TTS` (82M params, offline, fast)
- **Alternative:** `Bark` or `Coqui TTS` (more expressive, slower)
- **RAM usage:** ~500 MB
- **Key detail:** Output is raw WAV bytes. Cache aggressively — most exercise demos repeat.
- **File:** `modules/voice.py`

### Module 3 — Persona (RVC)
- **Job:** Apply a consistent voice "skin" to TTS output so PIA sounds like a real coach, not a robot
- **Tool:** `RVC v2` (Retrieval-based Voice Conversion)
- **Alternative:** `SO-VITS-SVC` (higher fidelity, heavier)
- **RAM usage:** ~1–2 GB
- **Key detail:** Runs AFTER Voice module. Takes WAV in, returns WAV out. Can be skipped in early development.
- **File:** `modules/persona.py`

### Module 4 — Ear (Analysis)
- **Job:** Analyze user's recorded audio — detect pitch, note accuracy, timing, microtonal deviation
- **Tool:** `CREPE-tiny` + `librosa`
- **Alternative:** `pYIN` or `aubio` (lighter, rule-based)
- **RAM usage:** ~100 MB
- **Key detail:** Runs in real-time or near-real-time. Returns structured data (Hz values, note names, accuracy score), NOT audio.
- **File:** `modules/ear.py`

### Module 5 — Orchestrator
- **Job:** Route user input to the right modules, run them async, assemble the response
- **Tool:** `FastAPI` + `asyncio`
- **Key detail:** Use `asyncio.to_thread()` for all blocking module calls. Never block the event loop.
- **File:** `main.py`

---

## Folder Structure

```
pia/
├── main.py                  # FastAPI app + intent router
├── modules/
│   ├── brain.py             # LLM interface
│   ├── voice.py             # TTS synthesis
│   ├── persona.py           # RVC voice conversion
│   ├── ear.py               # Pitch analysis
│   └── cache.py             # Audio cache layer
├── data/
│   ├── exercises/           # Pre-rendered demo audio clips (WAV)
│   └── knowledge/           # Music theory text files for LLM context
├── cache/                   # Runtime audio cache (auto-generated)
├── frontend/                # Next.js UI (separate folder)
│   ├── pages/
│   ├── components/
│   │   ├── ChatWindow.tsx
│   │   ├── AudioRecorder.tsx
│   │   └── PitchVisualizer.tsx
│   └── lib/
│       └── api.ts           # calls FastAPI backend
├── tests/
│   ├── test_brain.py
│   ├── test_voice.py
│   ├── test_ear.py
│   └── test_router.py
├── requirements.txt
└── README.md
```

---

## Module Interfaces (contracts)

Each module must conform to these exact function signatures. Do not change them without updating the orchestrator.

```python
# brain.py
def ask_brain(prompt: str, context: list[dict] = []) -> str:
    """
    Sends a prompt to the local LLM.
    context: list of {"role": "user"/"assistant", "content": str}
    Returns: plain text string response
    """

# voice.py
def synthesize_demo(text: str, style_hint: str = "neutral") -> bytes:
    """
    Converts text to spoken/sung audio.
    style_hint: e.g. "carnatic", "jazz", "western classical"
    Returns: raw WAV bytes
    """

# persona.py
def apply_voice(audio_bytes: bytes) -> bytes:
    """
    Applies RVC voice conversion to audio.
    Returns: processed WAV bytes
    """

# ear.py
def analyze_pitch(audio_bytes: bytes) -> dict:
    """
    Analyzes pitch and timing in user audio.
    Returns: {
        "notes": [{"time": 0.0, "hz": 261.6, "note": "C4", "confidence": 0.95}],
        "accuracy_score": 0.82,        # 0.0 to 1.0
        "sharp_notes": ["E4"],         # notes consistently sharp
        "flat_notes": [],              # notes consistently flat
        "summary": "Your D was slightly sharp throughout"
    }
    """

# cache.py
def get_cached_audio(key: str) -> bytes | None: ...
def cache_audio(key: str, audio: bytes) -> None: ...
```

---

## Intent Router Logic

```python
# in main.py

def route_intent(message: str, has_audio: bool) -> str:
    """
    Returns one of: "talk" | "demo" | "analyze"
    
    talk    → user wants conversation / explanation
    demo    → user wants to hear PIA sing/demonstrate
    analyze → user submitted audio for feedback
    """
    if has_audio:
        return "analyze"
    
    # Ask the Brain to classify
    classification_prompt = f"""
You are a routing classifier. Given a user message, output ONLY one of these labels:
- talk     (user wants explanation, conversation, or theory)
- demo     (user wants to hear an audio demonstration)
- analyze  (user wants feedback on their singing — but no audio was provided)

User message: "{message}"

Output only the label, nothing else.
"""
    return ask_brain(classification_prompt).strip().lower()
```

---

## Orchestrator (main.py skeleton)

```python
from fastapi import FastAPI, UploadFile, Form
from fastapi.responses import JSONResponse
import asyncio
from modules.brain import ask_brain
from modules.voice import synthesize_demo
from modules.persona import apply_voice
from modules.ear import analyze_pitch
from modules.cache import get_cached_audio, cache_audio
import hashlib, base64

app = FastAPI()

@app.post("/chat")
async def chat(
    message: str = Form(...),
    audio: UploadFile = None,
    history: str = Form(default="[]")  # JSON string of conversation history
):
    import json
    ctx = json.loads(history)
    audio_bytes = await audio.read() if audio else None
    intent = route_intent(message, audio_bytes is not None)

    if intent == "talk":
        text = await asyncio.to_thread(ask_brain, message, ctx)
        return {"type": "talk", "text": text}

    elif intent == "demo":
        # Check cache first
        cache_key = hashlib.md5(message.encode()).hexdigest()
        audio_out = get_cached_audio(cache_key)
        
        if not audio_out:
            text = await asyncio.to_thread(ask_brain, message, ctx)
            raw = await asyncio.to_thread(synthesize_demo, text)
            audio_out = await asyncio.to_thread(apply_voice, raw)
            cache_audio(cache_key, audio_out)
        else:
            text = await asyncio.to_thread(ask_brain, message, ctx)

        return {
            "type": "demo",
            "text": text,
            "audio": base64.b64encode(audio_out).decode()
        }

    elif intent == "analyze":
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
            "pitch_data": pitch_data
        }
```

---

## Frontend (Next.js)

The UI has three core components:

**AudioRecorder.tsx** — uses `MediaRecorder` browser API to capture mic input, sends WAV blob to `/chat` endpoint.

**ChatWindow.tsx** — standard chat UI. Renders text responses inline. For `demo` responses, renders an audio player with the base64 WAV. For `analyze` responses, shows the pitch data alongside feedback text.

**PitchVisualizer.tsx** — optional but high-value. Uses `WaveSurfer.js` to show the user's pitch curve vs the expected pitch. Makes the feedback visual and tangible.

**API call pattern (lib/api.ts):**
```typescript
export async function sendMessage(
  message: string,
  audioBlob?: Blob,
  history: Message[] = []
) {
  const form = new FormData();
  form.append("message", message);
  form.append("history", JSON.stringify(history));
  if (audioBlob) form.append("audio", audioBlob, "recording.wav");

  const res = await fetch("http://localhost:8000/chat", {
    method: "POST",
    body: form,
  });
  return res.json();
}
```

---

## Build Order (what to build first)

Build in this exact order. Do not skip ahead.

1. **`modules/ear.py`** — simplest module. Record a WAV file, run CREPE on it, print the pitch output. Confirm it works before touching anything else.

2. **`modules/brain.py`** — get Ollama running locally, send a prompt, get a response. Confirm conversation works.

3. **`modules/voice.py`** — install Kokoro TTS, synthesize a short phrase, save to WAV. Play it back and confirm quality.

4. **`main.py` (talk + demo only)** — wire Brain + Voice together with the router. Ignore Ear and Persona for now. Get a working chat endpoint.

5. **`frontend/`** — build a minimal chat UI that hits the `/chat` endpoint. Text in, text + audio out.

6. **`modules/persona.py`** — add RVC on top of Voice. This is optional until the rest is stable.

7. **`modules/cache.py`** — add caching once the pipeline works end-to-end.

8. **`analyze` intent** — wire the Ear module into the router. Add the AudioRecorder to the frontend.

---

## Key Constraints

| Constraint | Detail |
|---|---|
| Hardware target | MacBook M-series, 16GB unified memory |
| Total RAM budget | ~6 GB across all modules (leaves 10 GB headroom) |
| Quantization | All LLM models must be 4-bit quantized (GGUF format for llama.cpp) |
| Latency target | Text response < 3s, Demo audio < 8s (cached < 1s) |
| Audio format | WAV throughout the pipeline. Convert to MP3 only at the frontend edge |
| No internet required | All inference runs locally. No API calls to OpenAI or similar |
| Async everywhere | All module calls use `asyncio.to_thread()`. Never block the event loop |

---

## Dependencies

```txt
# requirements.txt

# Backend
fastapi
uvicorn
python-multipart

# Brain
llama-cpp-python          # or use ollama Python client

# Voice
kokoro-tts                # or TTS (coqui)

# Persona
# RVC v2 — install from: https://github.com/RVC-Project/Retrieval-based-Voice-Conversion-WebUI

# Ear
crepe
librosa
soundfile
numpy

# Cache
hashlib                   # stdlib
```

---

## What PIA is NOT

- Not a structured curriculum engine (lessons 1 → 2 → 3)
- Not a music transcription tool
- Not a real-time low-latency instrument tuner (use a tuner app for that)
- Not cloud-dependent — everything runs locally
- Not limited to one music style — the Brain handles theory for any tradition

---

## What makes PIA valuable

The pitch analysis (Ear) combined with the conversational coaching (Brain) creates a feedback loop no static app or YouTube video can replicate. The user sings, hears what's wrong, hears the correct version, and tries again — all in one place, with no human teacher required in the loop.

The music style knowledge lives entirely in the Brain's prompt context. To support a new style, you add text knowledge to the system prompt — you do not retrain any model.

---

## Questions to answer before writing code

1. Which music styles are the priority for v1? (affects what demo audio to pre-cache)
2. Do you want a desktop app (Electron/Tauri wrapping localhost) or a web app first?
3. Should the Persona voice be a fixed identity, or selectable (e.g. "choose your coach")?
4. What's the minimum viable demo — just text feedback, or must v1 include audio demos?