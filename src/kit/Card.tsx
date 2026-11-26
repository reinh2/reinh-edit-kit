// Basic overlay graphics: a white card over the shot, a pill with 1–2 words, a bar with a number.
// Inserts are animations tied to what is said, not lines of text: names, numbers and one label at most.
import React from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";
import { clamp01, ease, lerp, prog } from "./motion";
import { C, FONT, shadow } from "./theme";

export const useT = () => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  return f / fps;
};

// fade + rise + un-blur in 0.28 s: the entrance of every overlay
export const rise = (p: number, dy = 18): React.CSSProperties => ({ opacity: p, filter: `blur(${(1 - p) * 8}px)`, transform: `translateY(${(1 - p) * dy}px)` });

export const OverlayCard: React.FC<{ at?: number; until?: number; style?: React.CSSProperties; children: React.ReactNode }> = ({ at = 0, until = 1e9, style, children }) => {
  const t = useT();
  const p = prog(t, at, 0.28, ease.outCubic) * (1 - prog(t, until - 0.2, 0.2, ease.inCubic));
  return (
    <div style={{ position: "absolute", background: "rgba(255,255,255,0.95)", borderRadius: 30, boxShadow: shadow, padding: "28px 34px", fontFamily: FONT, color: C.ink, ...rise(p), ...style }}>
      {children}
    </div>
  );
};

export const Pill: React.FC<{ text: string; at: number; hot?: boolean; dark?: boolean; size?: number }> = ({ text, at, hot, dark, size = 36 }) => {
  const t = useT();
  const p = prog(t, at, 0.4, ease.outBack);
  return (
    <div style={{ display: "inline-flex", alignItems: "center", padding: `${size * 0.36}px ${size * 0.78}px`, borderRadius: 999, background: dark ? C.ink : hot ? C.accent : "#fff",
      border: hot || dark ? "none" : "2px solid #E3E7EF", color: hot || dark ? "#fff" : C.ink, fontFamily: FONT, fontWeight: 750, fontSize: size, whiteSpace: "nowrap",
      opacity: clamp01(p * 2), transform: `scale(${lerp(0.75, 1, p)})` }}>{text}</div>
  );
};

export const Bar: React.FC<{ label: string; value: number; max: number; at: number; unit?: string; color?: string; width?: number }> = ({ label, value, max, at, unit = "", color = C.accent, width = 620 }) => {
  const t = useT();
  const p = prog(t, at, 0.9, ease.inOutCubic);
  return (
    <div style={{ fontFamily: FONT, width }}>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 30, fontWeight: 700, color: C.ink, marginBottom: 12 }}>
        <span>{label}</span><span style={{ color }}>{Math.round(value * p)}{unit}</span>
      </div>
      <div style={{ height: 20, borderRadius: 99, background: C.track, overflow: "hidden" }}>
        <div style={{ height: "100%", width: `${(value / max) * 100 * p}%`, borderRadius: 99, background: color }} />
      </div>
    </div>
  );
};
