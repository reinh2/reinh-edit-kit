// End card: a calm last screen with your contacts after the closing line (≈ 3 s, fades out). Texts, contacts and
// colours come from kit.config.json («brand», «endCard»). 9:16 — one column; 16:9 — pitch left, contacts right.
import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { loadBaseFonts } from "./fonts";
import { ease, lerp, prog } from "./motion";
import { Sfx } from "./sfx";
import { C, FONT, KIT, PAGE_BG, shadow } from "./theme";

// Lucide-style icons (ISC licence), 24 × 24, stroke. Generic glyphs only — never a platform's logo.
const ICONS: Record<string, string[]> = {
  channel: ["M14.536 21.686a.5.5 0 0 0 .937-.024l6.5-19a.496.496 0 0 0-.635-.635l-19 6.5a.5.5 0 0 0-.024.937l7.93 3.18a2 2 0 0 1 1.112 1.11z", "m21.854 2.147-10.94 10.939"],
  globe: ["M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20z", "M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20", "M2 12h20"],
  mail: ["M4 4h16a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z", "m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"],
  music: ["M9 18V5l12-2v13", "M6 15a3 3 0 1 0 0 6 3 3 0 0 0 0-6z", "M18 13a3 3 0 1 0 0 6 3 3 0 0 0 0-6z"],
  camera: ["M7 2h10a5 5 0 0 1 5 5v10a5 5 0 0 1-5 5H7a5 5 0 0 1-5-5V7a5 5 0 0 1 5-5z", "M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z", "M17.5 6.5h.01"],
  code: ["m16 18 6-6-6-6", "m8 6-6 6 6 6"],
};

const rise = (p: number, dy = 18): React.CSSProperties => ({ opacity: p, filter: `blur(${(1 - p) * 8}px)`, transform: `translateY(${(1 - p) * dy}px)` });

type Contact = { icon: string; value: string; note: string };
const Row: React.FC<{ c: Contact; p: number; k: number }> = ({ c, p, k }) => (
  <div style={{ display: "flex", alignItems: "center", gap: 22 * k, ...rise(p, 12) }}>
    <div style={{ width: 60 * k, height: 60 * k, flex: "none", borderRadius: 99, background: "#F1F3F7", display: "flex", alignItems: "center", justifyContent: "center" }}>
      <svg width={28 * k} height={28 * k} viewBox="0 0 24 24" fill="none" stroke={C.ink} strokeWidth={1.9} strokeLinecap="round" strokeLinejoin="round">
        {(ICONS[c.icon] ?? ICONS.globe).map((d) => <path key={d} d={d} />)}
      </svg>
    </div>
    <div style={{ fontFamily: FONT, fontWeight: 600, fontSize: 32 * k, color: C.ink, whiteSpace: "nowrap" }}>{c.value}</div>
    <div style={{ fontFamily: FONT, fontWeight: 500, fontSize: 24 * k, color: C.muted, whiteSpace: "nowrap" }}>{c.note}</div>
  </div>
);

const Plane: React.FC<{ s: number }> = ({ s }) => (
  <svg width={s} height={s} viewBox="0 0 24 24" style={{ flex: "none" }}>
    <circle cx="12" cy="12" r="12" fill={C.accent} />
    <path d="M5.5 11.6 17.4 7c.5-.2 1 .2.8.9l-2 9.4c-.1.6-.7.7-1.1.4l-3-2.2-1.5 1.4c-.2.2-.6.1-.6-.2l.1-2.4 5.3-4.8-6.6 4.1-2.7-.9c-.6-.2-.6-.9 0-1.1Z" fill="#fff" />
  </svg>
);

export const EndCard: React.FC<{ dur?: number; sound?: boolean }> = ({ dur = 3, sound = true }) => {
  loadBaseFonts();
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const t = frame / fps;
  const vertical = height > width;
  const k = (vertical ? 1 : 1.05) * Math.min(width, height) / (vertical ? 1080 : 1080);
  const up = (at: number, d = 0.32) => prog(t, at, d, ease.outCubic);
  const out = prog(t, dur - 0.6, 0.6, ease.inCubic);
  const card = up(0, 0.36);
  const E = KIT.endCard;

  const pitch = (
    <div style={{ display: "flex", flexDirection: "column", alignItems: vertical ? "center" : "flex-start", textAlign: vertical ? "center" : "left" }}>
      <div style={{ display: "inline-flex", alignItems: "center", gap: 14 * k, padding: `${12 * k}px ${24 * k}px`, borderRadius: 999, background: "#F1F3F7", fontFamily: FONT, fontWeight: 650, fontSize: 28 * k, color: C.ink, ...rise(up(0.12)) }}>
        <span style={{ width: 11 * k, height: 11 * k, borderRadius: 99, background: C.accent, boxShadow: `0 0 12px ${C.accent}` }} />
        {KIT.brand.name}
      </div>
      <div style={{ marginTop: 36 * k }}>
        {E.headline.map((w, i) => (
          <div key={w} style={{ fontFamily: FONT, fontWeight: 800, fontSize: 84 * k, lineHeight: 1.04, letterSpacing: "-0.035em", color: C.ink, ...rise(up(0.22 + i * 0.1), 22) }}>{w}</div>
        ))}
      </div>
      <div style={{ fontFamily: FONT, fontWeight: 500, fontSize: 34 * k, color: C.muted, marginTop: 22 * k, ...rise(up(0.42)) }}>{KIT.brand.tagline}</div>
      <div style={{ display: "inline-flex", alignItems: "center", gap: 20 * k, marginTop: 44 * k, padding: `${20 * k}px ${38 * k}px ${20 * k}px ${22 * k}px`, borderRadius: 999,
        background: "rgba(17,19,24,0.92)", boxShadow: shadow, opacity: up(0.55), transform: `translateY(${(1 - up(0.55)) * 20}px) scale(${lerp(0.94, 1, prog(t, 0.55, 0.4, ease.outBack))})` }}>
        <Plane s={62 * k} />
        <div style={{ textAlign: "left" }}>
          <div style={{ fontFamily: FONT, fontWeight: 700, fontSize: 38 * k, color: "#FFFFFF", whiteSpace: "nowrap" }}>{E.cta}</div>
          <div style={{ fontFamily: FONT, fontWeight: 500, fontSize: 26 * k, color: "rgba(255,255,255,0.65)", marginTop: 2 }}>{E.ctaHandle}</div>
        </div>
      </div>
    </div>
  );

  return (
    <AbsoluteFill style={{ background: PAGE_BG, alignItems: "center", justifyContent: "center", paddingBottom: vertical ? 160 * k : 0 }}>
      <div style={{ background: "rgba(255,255,255,0.96)", borderRadius: 44 * k, boxShadow: shadow, padding: vertical ? `${64 * k}px ${60 * k}px` : `${80 * k}px ${90 * k}px`,
        width: vertical ? 920 * k : undefined, display: "flex", flexDirection: vertical ? "column" : "row", alignItems: "center", gap: (vertical ? 56 : 110) * k,
        opacity: card * (1 - out), filter: `blur(${(1 - card) * 8 + out * 6}px)`, transform: `translateY(${(1 - card) * 30 + out * 14}px) scale(${lerp(0.96, 1, card) * lerp(1, 0.985, out)})` }}>
        {pitch}
        {vertical && <div style={{ width: "100%", height: 1, background: "#E6E9EF", opacity: up(0.7) }} />}
        <div style={{ display: "flex", flexDirection: "column", gap: 24 * k, alignItems: "flex-start" }}>
          {E.contacts.map((c, i) => <Row key={c.value} c={c} p={up(0.75 + i * 0.07)} k={k} />)}
        </div>
      </div>
      {sound && (<><Sfx at={0} ev="scene-in" gainDb={-6} /><Sfx at={0.55} ev="notify" /></>)}
    </AbsoluteFill>
  );
};
