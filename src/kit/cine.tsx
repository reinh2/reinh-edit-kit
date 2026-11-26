// «Cine» look for big moments of a long video: dark navy depth (top light, vignette, grain — no grid), huge condensed
// chrome words as the back layer with objects in front, keyword stacks with a thin bracket (each word on its spoken
// beat), glowing glass panels with a slight 3D tilt, callout lines. Font: Oswald (SIL OFL 1.1, public/fonts) + Inter.
// Every piece is a pure function of local time t (s), so seeks and re-renders are deterministic.
import React from "react";
import { AbsoluteFill, continueRender, delayRender, staticFile } from "remotion";
import { loadBaseFonts } from "./fonts";
import { clamp01, ease, lerp, prog } from "./motion";
import { C, abs } from "./theme";

export const K = { bg0: "#05080F", bg1: "#0B1528", ice: "#CFE0FF", dim: "#7C8AA6", glass: "rgba(20,30,52,0.72)", red: "#FF5A5F", green: "#3DDC97" };
export const COND = "Oswald, 'Arial Narrow', sans-serif";

let oswald = false;
export const loadCineFonts = () => {
  loadBaseFonts();
  if (oswald || typeof document === "undefined") return;
  oswald = true;
  const h = delayRender("oswald");
  const CYR = "U+0301, U+0400-045F, U+0490-0491, U+04B0-04B1, U+2116";
  const LAT = "U+0000-00FF, U+0131, U+0152-0153, U+2000-206F, U+20AC, U+2122, U+2212";
  Promise.all([
    new FontFace("Oswald", `url(${staticFile("fonts/oswald-cyrillic.woff2")}) format('woff2')`, { unicodeRange: CYR, weight: "200 700" }).load(),
    new FontFace("Oswald", `url(${staticFile("fonts/oswald-latin.woff2")}) format('woff2')`, { unicodeRange: LAT, weight: "200 700" }).load(),
  ]).then((fs) => { fs.forEach((f) => document.fonts.add(f)); continueRender(h); });
};

const Grain: React.FC<{ t: number }> = ({ t }) => {
  const seed = Math.floor(t * 24) % 8;
  return (
    <svg width="100%" height="100%" style={abs({ inset: 0, opacity: 0.07, mixBlendMode: "overlay" })}>
      <filter id={`g${seed}`}><feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves={2} seed={seed} /><feColorMatrix type="saturate" values="0" /></filter>
      <rect width="100%" height="100%" filter={`url(#g${seed})`} />
    </svg>
  );
};

export const CineBg: React.FC<{ t: number; hue?: number }> = ({ t, hue = 0 }) => (
  <AbsoluteFill style={{ background: `radial-gradient(120% 90% at 50% -15%, #1A3266 0%, ${K.bg1} 42%, ${K.bg0} 100%)` }}>
    <AbsoluteFill style={{ background: `radial-gradient(60% 50% at ${50 + Math.sin(t * 0.35) * 6}% 8%, ${C.accent}${Math.round((0.22 + hue * 0.1) * 255).toString(16).padStart(2, "0")}, transparent 70%)` }} />
    <AbsoluteFill style={{ background: "radial-gradient(110% 90% at 50% 50%, transparent 55%, rgba(0,0,0,0.6) 100%)" }} />
    <Grain t={t} />
  </AbsoluteFill>
);

export const Chrome: React.FC<{ text: string; size: number; t: number; at: number; style?: React.CSSProperties; dim?: number; tone?: "chrome" | "blue" | "red" }> = ({ text, size, t, at, style, dim = 1, tone = "chrome" }) => {
  const p = prog(t, at, 0.55, ease.outExpo);
  const sheen = ((t - at) * 0.35) % 1.6;
  const fills = {
    chrome: "linear-gradient(180deg, #FFFFFF 0%, #DCE6F8 38%, #8E9DBA 52%, #E9F0FF 64%, #A9B7D3 100%)",
    blue: "linear-gradient(180deg, #E6EEFF 0%, #9DB9FF 45%, #4A72E8 60%, #B9CDFF 100%)",
    red: "linear-gradient(180deg, #FFE1E1 0%, #FF8A8A 45%, #D93A3F 60%, #FFB3B3 100%)",
  };
  return (
    <div style={{ position: "absolute", fontFamily: COND, fontWeight: 700, fontSize: size, lineHeight: 0.92, letterSpacing: "-0.01em", textTransform: "uppercase", whiteSpace: "nowrap",
      opacity: clamp01(p * 1.4) * dim, filter: `blur(${(1 - p) * 22}px)`, transform: `scaleY(${lerp(1.35, 1, p)}) translateY(${(1 - p) * 40}px)`, transformOrigin: "50% 100%", ...style }}>
      <span style={{ backgroundImage: `linear-gradient(100deg, transparent ${sheen * 100 - 30}%, rgba(255,255,255,0.55) ${sheen * 100 - 20}%, transparent ${sheen * 100 - 10}%), ${fills[tone]}`,
        WebkitBackgroundClip: "text", backgroundClip: "text", color: "transparent", filter: "drop-shadow(0 20px 40px rgba(0,0,0,0.45))" }}>{text}</span>
    </div>
  );
};

// keyword stack with a thin bracket; items[].at = the spoken word's time (from words.json, not typed by hand)
export const Stack: React.FC<{ t: number; items: { w: string; at: number }[]; x: number; y: number; size?: number; hot?: number; color?: string }> = ({ t, items, x, y, size = 64, hot = -1, color = "#FFFFFF" }) => {
  const first = items[0].at, last = items[items.length - 1].at;
  const h = prog(t, first - 0.2, last - first + 0.5, ease.outCubic);
  const step = size * 1.22;
  const H = step * items.length + 10;
  const line = color === "#FFFFFF" ? "rgba(220,232,255,0.85)" : "rgba(17,19,24,0.5)";
  return (
    <>
      <div style={abs({ left: x, top: y - 8, width: 3, height: H * h, background: line })} />
      <div style={abs({ left: x, top: y - 8, width: 22, height: 3, background: line, opacity: clamp01(h * 5) })} />
      <div style={abs({ left: x, top: y - 8 + H * h - 3, width: 22, height: 3, background: line, opacity: clamp01(h * 5) })} />
      {items.map((it, i) => {
        const p = prog(t, it.at, 0.4);
        const next = items[i + 1] ? prog(t, items[i + 1].at, 0.4) : 0;
        return <div key={it.w} style={abs({ left: x + 42, top: y + i * step, fontFamily: "Inter", fontWeight: 760, fontSize: size, letterSpacing: "-0.03em", color: i === hot ? C.accent : color,
          opacity: p * lerp(1, 0.55, next), filter: `blur(${(1 - p) * 8}px)`, transform: `translateY(${(1 - p) * 18}px)`, whiteSpace: "nowrap" })}>{it.w}</div>;
      })}
    </>
  );
};

export const Glass: React.FC<{ children: React.ReactNode; style: React.CSSProperties; p?: number; tilt?: number; glow?: number }> = ({ children, style, p = 1, tilt = 0, glow = 1 }) => (
  <div style={abs({ borderRadius: 34, background: K.glass, border: "1px solid rgba(170,200,255,0.28)",
    boxShadow: `0 40px 120px rgba(0,0,0,0.55), 0 0 ${80 * glow}px ${C.accent}47, inset 0 1px 0 rgba(255,255,255,0.18)`, backdropFilter: "blur(10px)",
    opacity: clamp01(p * 1.5), transform: `perspective(1800px) rotateY(${tilt}deg) translateY(${(1 - p) * 50}px) scale(${lerp(0.94, 1, p)})`, overflow: "hidden", ...style })}>{children}</div>
);

export const Callout: React.FC<{ t: number; at: number; from: [number, number]; to: [number, number]; label: React.ReactNode; side?: "left" | "right"; W?: number; H?: number }> = ({ t, at, from, to, label, side = "right", W = 1920, H = 1080 }) => {
  const d = prog(t, at, 0.45, ease.inOutCubic);
  const l = prog(t, at + 0.3, 0.4);
  const mid: [number, number] = [lerp(from[0], to[0], 0.55), to[1]];
  return (
    <>
      <svg width={W} height={H} style={abs({ inset: 0, pointerEvents: "none" })}>
        <path d={`M${from[0]} ${from[1]} L${mid[0]} ${mid[1]} L${to[0]} ${to[1]}`} fill="none" stroke="rgba(220,232,255,0.8)" strokeWidth={2.5} pathLength={1} strokeDasharray={1} strokeDashoffset={1 - d} />
        <circle cx={from[0]} cy={from[1]} r={7 * clamp01(d * 4)} fill={K.ice} />
      </svg>
      <div style={abs({ left: side === "right" ? to[0] + 22 : undefined, right: side === "left" ? W - to[0] + 22 : undefined, top: to[1] - 36, opacity: l, transform: `translateX(${(side === "right" ? -1 : 1) * (1 - l) * 20}px)` })}>{label}</div>
    </>
  );
};
