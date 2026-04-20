export type Message = { role: "user" | "assistant"; content: string };

const API_BASE = process.env.NEXT_PUBLIC_PIA_API ?? "http://127.0.0.1:8000";

export type ChatResponse =
  | { type: "talk"; text: string }
  | { type: "demo"; text: string; audio: string }
  | {
      type: "analyze";
      text: string;
      pitch_data: {
        notes: Array<{ time: number; hz: number; note: string; confidence: number }>;
        accuracy_score: number;
        sharp_notes: string[];
        flat_notes: string[];
        summary: string;
      };
    };

export async function sendMessage(
  message: string,
  audioBlob?: Blob,
  history: Message[] = []
): Promise<ChatResponse> {
  const form = new FormData();
  form.append("message", message);
  form.append("history", JSON.stringify(history));
  if (audioBlob) {
    form.append("audio", audioBlob, "recording.wav");
  }

  const res = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) {
    const t = await res.text();
    throw new Error(t || `HTTP ${res.status}`);
  }
  return res.json() as Promise<ChatResponse>;
}
