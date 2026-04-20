"use client";

import { useCallback, useRef, useState } from "react";

type Props = {
  onRecording: (blob: Blob) => void;
};

export function AudioRecorder({ onRecording }: Props) {
  const [recording, setRecording] = useState(false);
  const chunks = useRef<BlobPart[]>([]);
  const mediaRecorder = useRef<MediaRecorder | null>(null);
  const stream = useRef<MediaStream | null>(null);

  const stop = useCallback(() => {
    mediaRecorder.current?.stop();
    setRecording(false);
    stream.current?.getTracks().forEach((t) => t.stop());
    stream.current = null;
  }, []);

  const start = useCallback(async () => {
    chunks.current = [];
    const s = await navigator.mediaDevices.getUserMedia({ audio: true });
    stream.current = s;
    const mr = new MediaRecorder(s, { mimeType: "audio/webm" });
    mediaRecorder.current = mr;
    mr.ondataavailable = (e) => {
      if (e.data.size > 0) chunks.current.push(e.data);
    };
    mr.onstop = () => {
      const blob = new Blob(chunks.current, { type: mr.mimeType || "audio/webm" });
      onRecording(blob);
    };
    mr.start();
    setRecording(true);
  }, [onRecording]);

  return (
    <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
      {!recording ? (
        <button type="button" onClick={start}>
          Record
        </button>
      ) : (
        <button type="button" onClick={stop}>
          Stop
        </button>
      )}
      <span style={{ opacity: 0.7, fontSize: 13 }}>
        WebM from the mic; send with your message for analysis.
      </span>
    </div>
  );
}
