// Chapter pieces for long videos (from a challenge-style long video): a light leak over a hard cut, an odometer clock,
// a full-screen chapter timer and a small persistent timer chip. Theme-aware (light / cine, themes.tsx).
// Rules: one light leak per chapter change, not on every cut; clock values come from the experiment's log, not made up.
import React from "react";
import { AbsoluteFill } from "remotion";
import { clamp01, ease, impulse, lerp, prog } from "./motion";
import { C, FONT, abs } from "./theme";
import { useTheme } from "./themes";

const bump = (x: number) => (Math.abs(x) >= 1 ? 0 : Math.pow(Math.cos((x * Math.PI) / 2), 2));

// ------------------------------------------------------------------ light leak ≈ 0.7 s centred on the cut at `at`
export const LEAK = 0.35;
export const leakAmount = (t: number, at: number) => bump((t - at) / LEAK);
export const LightLeak: React.FC<{ t: number; at: number; seed?: number; dark?: boolean }> = ({ t, at, seed = 0, dark }) => {
  const k = leakAmount(t, at);
  if (k <= 0) return null;
  const p = clamp01((t - at + LEAK) / (2 * LEAK));
  const dir = seed % 2 === 0 ? 1 : -1;
  const x = 50 + dir * lerp(-60, 60, p);
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <AbsoluteFill style={{ background: dark ? "#CFE0FF" : "#FFFFFF", opacity: (dark ? 0.5 : 0.78) * Math.pow(k, 1.4) }} />
      <AbsoluteFill style={{ filter: "blur(70px)", opacity: k }}>
        <div style={abs({ left: `${x - 35}%`, top: "-20%", width: "70%", height: "140%", borderRadius: "50%", background: `radial-gradient(closest-side, ${C.accent}8C, ${C.accent}00)` })} />
        <div style={abs({ left: `${100 - x - 25}%`, top: "10%", width: "50%", height: "90%", borderRadius: "50%", background: "radial-gradient(closest-side, rgba(255,214,196,0.55), rgba(255,214,196,0))" })} />
        <div style={abs({ left: `${x - 60}%`, top: "35%", width: "120%", height: "18%", transform: `rotate(${dir * -12}deg)`, background: "linear-gradient(90deg, rgba(255,255,255,0), rgba(255,255,255,0.95), rgba(255,255,255,0))" })} />
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// ------------------------------------------------------------------ odometer (hh:mm, each minute holds, then rolls)
const Digit: React.FC<{ v: number; size: number; max?: number }> = ({ v, size, max = 9 }) => {
  const col = [...Array.from({ length: max + 1 }, (_, i) => String(i)), "0"];
  return (
    <div style={{ height: size, width: size * 0.6, overflow: "hidden", position: "relative", maskImage: "linear-gradient(transparent, #000 16%, #000 84%, transparent)", WebkitMaskImage: "linear-gradient(transparent, #000 16%, #000 84%, transparent)" }}>
      <div style={abs({ left: 0, top: 0, width: "100%", transform: `translateY(${-v * size}px)` })}>
        {col.map((d, i) => <div key={i} style={{ height: size, lineHeight: `${size}px`, textAlign: "center" }}>{d}</div>)}
      </div>
    </div>
  );
};
export const Odometer: React.FC<{ minutes: number; size: number; color?: string }> = ({ minutes, size, color }) => {
  const th = useTheme();
  const raw = Math.max(0, minutes);
  const fr = raw - Math.floor(raw);
  const step = clamp01((fr - 0.65) / 0.35);
  const m = Math.floor(raw) + step * step * (3 - 2 * step);
  const u = m % 10;
  const c1 = Math.max(0, u - 9);
  const tens = Math.floor((m % 60) / 10) + c1;
  const c2 = Math.floor(m % 60) === 59 ? c1 : 0;
  const hu = (Math.floor(m / 60) % 10) + c2;
  const ht = Math.floor(m / 600);
  return (
    <div style={{ display: "flex", alignItems: "center", fontFamily: FONT, fontSize: size, fontWeight: 800, letterSpacing: "-0.04em", color: color ?? th.ink, fontVariantNumeric: "tabular-nums" }}>
      <Digit v={ht} size={size} /><Digit v={hu} size={size} />
      <div style={{ width: size * 0.32, textAlign: "center", lineHeight: `${size}px`, marginTop: -size * 0.06 }}>:</div>
      <Digit v={tens} size={size} max={5} /><Digit v={u} size={size} />
    </div>
  );
};
const fmt = (min: number) => `${String(Math.floor(min / 60)).padStart(2, "0")}:${String(Math.floor(min % 60)).padStart(2, "0")}`;

// ------------------------------------------------------------------ full-screen chapter: label, rolling clock, hairline
export const ChapterTimer: React.FC<{ t: number; label: string; from: number; to: number; rollAt?: number; rollDur?: number; caption?: string }> = ({ t, label, from, to, rollAt = 0.6, rollDur = 1.4, caption = "прошло" }) => {
  const th = useTheme();
  const enter = prog(t, 0, 0.7);
  const kick = prog(t, 0.15, 0.5);
  const roll = prog(t, rollAt, rollDur, ease.inOutCubic);
  const landed = prog(t, rollAt + rollDur, 0.5);
  const kickY = impulse(t, rollAt + rollDur, 18, 10) * -10;
  return (
    <AbsoluteFill>
      <th.Bg t={t} />
      <th.BackWord text={label.split("·").pop()!.trim()} t={t} top={320} />
      <div style={abs({ left: 0, right: 0, top: 262, textAlign: "center", fontFamily: FONT, fontSize: 34, fontWeight: 650, letterSpacing: "0.16em", color: th.muted, opacity: kick, transform: `translateY(${(1 - kick) * 14}px)` })}>{label}</div>
      <div style={abs({ left: 0, right: 0, top: 340, display: "flex", justifyContent: "center", opacity: enter, filter: `blur(${(1 - enter) * 18}px)`, transform: `translateY(${(1 - enter) * 60 + kickY}px) scale(${lerp(1.06, 1, enter)})` })}>
        <Odometer minutes={lerp(from, to, roll)} size={300} />
      </div>
      <div style={abs({ left: 760, width: 400, top: 700, height: 6, borderRadius: 3, background: th.track, opacity: kick })} />
      <div style={abs({ left: 760, width: 400 * roll, top: 700, height: 6, borderRadius: 3, background: th.accent, opacity: kick })} />
      <div style={abs({ left: 0, right: 0, top: 736, textAlign: "center", fontFamily: FONT, fontSize: 30, fontWeight: 550, color: th.muted, opacity: kick * (0.6 + 0.4 * landed) })}>{caption}</div>
    </AbsoluteFill>
  );
};

// ------------------------------------------------------------------ small persistent timer chip (top-left)
export const MiniTimer: React.FC<{ t: number; minutes: number }> = ({ t, minutes }) => {
  const th = useTheme();
  const a = prog(t, 0.1, 0.5);
  return (
    <div style={abs({ left: 110, top: 64, height: 56, padding: "0 22px 0 16px", borderRadius: 28, background: th.chip, border: `1px solid ${th.chipBorder}`, display: "flex", alignItems: "center", gap: 12, opacity: a, transform: `translateY(${(1 - a) * -16}px)` })}>
      <svg width={30} height={30} viewBox="0 0 32 32" fill="none" stroke={th.accent} strokeWidth={2.4} strokeLinecap="round"><circle cx={16} cy={18} r={11} /><path d="M16 18v-6M12 3h8" /></svg>
      <div style={{ fontFamily: FONT, fontSize: 30, fontWeight: 750, fontVariantNumeric: "tabular-nums", color: th.ink }}>{fmt(minutes)}</div>
    </div>
  );
};
