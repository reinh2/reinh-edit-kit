// Word-by-word captions for vertical videos: pages of up to N words (kit.config.json «captions»), a new page after
// punctuation or a new EDL piece (`seg`), the current word in the accent colour, hidden during full-screen inserts.
// Long videos: do not burn captions in — deliver a separate .srt (scripts/captions/make_srt.py).
import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { C, FONT, KIT } from "./theme";
import type { Word } from "./words";

export const pages = (words: Word[], maxWords = KIT.captions.maxWords) => {
  const out: Word[][] = [];
  let cur: Word[] = [];
  words.forEach((w, i) => {
    const prev = words[i - 1];
    if (cur.length && (cur.length >= maxWords || /[.!?,:;…]$/.test(prev.w) || prev.seg !== w.seg || w.start - prev.end > 0.6)) {
      out.push(cur);
      cur = [];
    }
    cur.push(w);
  });
  if (cur.length) out.push(cur);
  return out;
};

export const Captions: React.FC<{ words: Word[]; hide?: [number, number][]; top?: number; size?: number }> = ({ words, hide = [], top, size }) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const t = frame / fps;
  if (hide.some(([a, b]) => t >= a && t < b)) return null;
  const k = height / 1920;
  const page = pages(words).find((p, i, all) => t >= p[0].start - 0.05 && t < (all[i + 1]?.[0].start ?? p[p.length - 1].end + 0.6));
  if (!page) return null;
  return (
    <AbsoluteFill>
      <div
        style={{
          position: "absolute", top: (top ?? KIT.captions.top) * k, left: width * 0.08, right: width * 0.08,
          display: "flex", flexWrap: "wrap", justifyContent: "center", gap: `0 ${18 * k}px`,
          fontFamily: FONT, fontWeight: 800, fontSize: (size ?? KIT.captions.fontSize) * k, lineHeight: 1.12, letterSpacing: "-0.02em",
          textShadow: "0 4px 18px rgba(0,0,0,0.55), 0 1px 3px rgba(0,0,0,0.6)",
        }}
      >
        {page.map((w, i) => (
          <span key={i} style={{ color: t >= w.start && t < w.end + 0.08 ? C.accent : C.white }}>{w.w.replace(/[.,]$/, "")}</span>
        ))}
      </div>
    </AbsoluteFill>
  );
};
