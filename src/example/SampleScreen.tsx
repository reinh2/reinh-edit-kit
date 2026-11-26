// A synthetic «screen recording» for the example (so the kit needs no one's footage): a terminal where an agent cuts a
// video, next to a timeline. Rendered once by `npm run sample` into public/example/screen.mp4 (1920×1080, 30 fps).
import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { loadBaseFonts } from "../kit/fonts";
import { clamp01, typed } from "../kit/motion";
import { C, FONT, MONO } from "../kit/theme";

const LINES: [number, string, string?][] = [
  [0.4, "$ python3 scripts/edit/edl_timeline.py edl.json --report editorial.md"],
  [2.2, "total 0:35.60, 10 shots, 0 flags", C.green],
  [3.4, "$ python3 scripts/audio/voice_master.py voice raw.wav voice.wav --preset usb-condenser"],
  [5.6, "voice: −17.0 LUFS · TP −1.9 dBTP · ok", C.green],
  [6.8, "$ python3 scripts/qc/editorial_qc.py draft.mp4 --timeline timeline.json --out qc"],
  [9.0, "pauses 0 · static 0 · flashes 0 · open findings: 0", C.green],
];

export const SampleScreen: React.FC = () => {
  loadBaseFonts();
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  return (
    <AbsoluteFill style={{ background: "#1B1E25", fontFamily: FONT }}>
      {/* terminal */}
      <div style={{ position: "absolute", left: 60, top: 60, width: 1150, height: 960, borderRadius: 18, background: "#0E1016", boxShadow: "0 20px 60px rgba(0,0,0,0.5)", overflow: "hidden" }}>
        <div style={{ height: 52, background: "#171A22", display: "flex", alignItems: "center", gap: 10, padding: "0 20px" }}>
          {["#FF5F57", "#FEBC2E", "#28C840"].map((c) => <div key={c} style={{ width: 14, height: 14, borderRadius: 99, background: c }} />)}
          <div style={{ marginLeft: 20, color: "#8A8F98", fontSize: 20 }}>agent · edit-kit</div>
        </div>
        <div style={{ padding: "34px 36px", fontFamily: MONO, fontSize: 25, lineHeight: 1.7 }}>
          {LINES.map(([at, text, color], i) => {
            const n = color ? (t >= at ? text.length : 0) : typed(t, at, text, 34, i + 1);
            return <div key={i} style={{ color: color ?? "#E6E9EF", whiteSpace: "pre-wrap", minHeight: 42 }}>{text.slice(0, n)}{!color && n > 0 && n < text.length ? "▍" : ""}</div>;
          })}
        </div>
      </div>
      {/* timeline */}
      <div style={{ position: "absolute", left: 1250, top: 60, width: 610, height: 960, borderRadius: 18, background: "#F5F6F8", padding: 36 }}>
        <div style={{ fontSize: 28, fontWeight: 750, color: C.ink }}>Таймлайн</div>
        {["лицо", "экран", "вставки", "голос", "музыка"].map((row, r) => (
          <div key={row} style={{ marginTop: 44 }}>
            <div style={{ fontSize: 20, color: C.muted, marginBottom: 10 }}>{row}</div>
            <div style={{ position: "relative", height: 46, borderRadius: 10, background: "#E6E9EF", overflow: "hidden" }}>
              {[0, 1, 2, 3].map((k) => {
                const x = (k * 0.26 + r * 0.07) % 0.9;
                const grow = clamp01((t - 0.5 - k * 0.6 - r * 0.3) / 0.5);
                return <div key={k} style={{ position: "absolute", left: `${x * 100}%`, width: `${18 * grow}%`, top: 6, bottom: 6, borderRadius: 7, background: r === 3 ? C.green : r === 2 ? "#F5A524" : C.accent, opacity: 0.85 }} />;
              })}
            </div>
          </div>
        ))}
        <div style={{ position: "absolute", left: 36 + ((t * 40) % 540), top: 120, width: 3, height: 780, background: C.red }} />
      </div>
    </AbsoluteFill>
  );
};
