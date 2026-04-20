"use client";

import { FormEvent, useMemo, useState } from "react";
import type { ChatResponse, Message } from "../lib/api";
import { sendMessage } from "../lib/api";
import { AudioRecorder } from "./AudioRecorder";
import { PitchVisualizer } from "./PitchVisualizer";

type ChatMessage = Message & { meta?: ChatResponse };

export function ChatWindow() {
  const [input, setInput] = useState("");
  const [pendingBlob, setPendingBlob] = useState<Blob | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const history = useMemo(
    () => messages.map((m) => ({ role: m.role, content: m.content })),
    [messages]
  );

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!input.trim() && !pendingBlob) return;
    setError(null);
    setLoading(true);
    const userText = input.trim() || "(audio only)";
    setMessages((m) => [...m, { role: "user", content: userText }]);
    setInput("");
    try {
      const res = await sendMessage(
        userText,
        pendingBlob ?? undefined,
        history
      );
      setPendingBlob(null);
      let assistant = "";
      if (res.type === "talk") {
        assistant = res.text;
      } else if (res.type === "demo") {
        assistant = res.text;
      } else {
        assistant = `${res.text}\n\nPitch summary: ${res.pitch_data.summary}`;
      }
      setMessages((m) => [
        ...m,
        { role: "assistant", content: assistant, meta: res },
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ maxWidth: 720, margin: "0 auto", padding: 24 }}>
      <h1 style={{ fontSize: 22, marginBottom: 8 }}>PIA</h1>
      <p style={{ opacity: 0.75, marginBottom: 16 }}>
        Local vocal coach — text the backend; attach a recording for pitch feedback.
      </p>

      <div
        style={{
          border: "1px solid #333",
          borderRadius: 8,
          padding: 12,
          minHeight: 280,
          marginBottom: 12,
          background: "#0a0a0a",
        }}
      >
        {messages.map((m, i) => (
          <div key={i} style={{ marginBottom: 12 }}>
            <div style={{ fontSize: 12, opacity: 0.6 }}>{m.role}</div>
            <div style={{ whiteSpace: "pre-wrap" }}>{m.content}</div>
            {m.meta?.type === "demo" && (
              <audio
                controls
                src={`data:audio/wav;base64,${m.meta.audio}`}
                style={{ width: "100%", marginTop: 8 }}
              />
            )}
            {m.meta?.type === "analyze" && (
              <div style={{ marginTop: 8 }}>
                <PitchVisualizer notes={m.meta.pitch_data.notes} />
              </div>
            )}
          </div>
        ))}
      </div>

      {error && <p style={{ color: "#f87171", marginBottom: 8 }}>{error}</p>}

      <AudioRecorder onRecording={setPendingBlob} />
      {pendingBlob && (
        <p style={{ fontSize: 13, marginTop: 8 }}>
          Ready to send recording with next message.
        </p>
      )}

      <form onSubmit={onSubmit} style={{ marginTop: 12, display: "flex", gap: 8 }}>
        <input
          style={{
            flex: 1,
            padding: 8,
            borderRadius: 6,
            border: "1px solid #444",
            background: "#111",
            color: "#eee",
          }}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask for theory, a demo, or feedback…"
        />
        <button type="submit" disabled={loading}>
          {loading ? "…" : "Send"}
        </button>
      </form>
    </div>
  );
}
