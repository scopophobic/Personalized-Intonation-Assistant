"use client";

type Note = { time: number; hz: number; note: string; confidence: number };

type Props = {
  notes: Note[];
};

export function PitchVisualizer({ notes }: Props) {
  if (!notes.length) {
    return <p style={{ opacity: 0.7 }}>No pitch frames to plot.</p>;
  }

  const maxT = Math.max(...notes.map((n) => n.time));
  const minHz = Math.min(...notes.map((n) => n.hz));
  const maxHz = Math.max(...notes.map((n) => n.hz));
  const pad = 24;
  const w = 560;
  const h = 200;

  const path = notes
    .map((n) => {
      const x = pad + (n.time / (maxT || 1)) * (w - pad * 2);
      const y =
        h -
        pad -
        ((n.hz - minHz) / (maxHz - minHz || 1)) * (h - pad * 2);
      return `${x},${y}`;
    })
    .join(" ");

  return (
    <div>
      <svg width={w} height={h} style={{ background: "#111", borderRadius: 8 }}>
        <polyline
          fill="none"
          stroke="#7dd3fc"
          strokeWidth={2}
          points={path}
        />
      </svg>
      <p style={{ fontSize: 12, opacity: 0.75, marginTop: 6 }}>
        Pitch (Hz) over time — quick preview; swap for WaveSurfer when you want
        waveform + pitch lanes.
      </p>
    </div>
  );
}
