// Install guide for Reinh Edit Kit (16:9, 2560×1440, 30 fps): real screenshots of every step, few animations.
// Each scene of src/guide/script.json is either a screenshot (shot) or a plain card (card):
//   shot  - public/guide/shots/<name>.png (prepared by `npm run guide:shots` from window captures), drawn in a neutral
//           window frame; `focus` [x, y, w, h] in screenshot pixels: a slow push-in to that area + an accent outline;
//   card  - a title, a few lines, optional commands (Windows/WSL, what you need, where to ask);
//   cmd   - the command of the step, under the screenshot, readable and copyable from the screen.
// Scene length = max(min, voice + 0.5 s), voice from 0.2 s. Voice: public/guide/vo_<id>.wav (scratch: `npm run guide:vo`; the final voice-over
// is recorded by a person). Without screenshots a scene shows a grey placeholder with the shot name: the video still renders.
import React from "react";
import { AbsoluteFill, Audio, Img, Sequence, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { loadBaseFonts } from "../kit/fonts";
import { clamp01, ease, lerp, prog } from "../kit/motion";
import script from "./script.json";

export const GUIDE_FPS = 30;
const W = 1920, H = 1080;
const ACCENT = "#5B8CFF", INK = "#111318", SUB = "#5B6170";
const FONT = "Inter, Arial, sans-serif", MONO = "'JetBrains Mono', Menlo, monospace";
const abs = (s: React.CSSProperties): React.CSSProperties => ({ position: "absolute", boxSizing: "border-box", ...s });

type Rect = [number, number, number, number];
type Shot = { name: string; frame?: "terminal" | "browser" | "window"; title?: string; focus?: Rect; zoom?: number };
type Card = { title: string; lines?: string[]; code?: string[] };
type GuideScene = { id: string; chapter: string; vo: string; min: number; shot?: Shot; card?: Card; cmd?: string };
export type ShotSizes = Record<string, [number, number]>;
export type GuideProps = { vo: Record<string, number> | null; sizes: ShotSizes | null };

const SCENES = script.scenes as unknown as GuideScene[];
const CHAPTERS = Array.from(new Set(SCENES.map((s) => s.chapter)));
export const guideDurations = (vo: GuideProps["vo"]) => SCENES.map((s) => Math.max(s.min, vo?.[s.id] ? vo[s.id] + 0.5 : 0));
export const guideFrames = (vo: GuideProps["vo"]) => Math.round(guideDurations(vo).reduce((a, b) => a + b, 0) * GUIDE_FPS);

const Fit: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { width } = useVideoConfig();
  return (
    <AbsoluteFill style={{ overflow: "hidden" }}>
      <div style={abs({ left: 0, top: 0, width: W, height: H, transformOrigin: "0 0", transform: `scale(${width / W})`, overflow: "hidden" })}>{children}</div>
    </AbsoluteFill>
  );
};

const Bg: React.FC = () => <AbsoluteFill style={{ background: "linear-gradient(180deg, #F4F6FA 0%, #E9EDF4 100%)" }} />;

// chapter label (top left) and chapter progress dots (top right)
const Header: React.FC<{ chapter: string }> = ({ chapter }) => {
  const n = CHAPTERS.indexOf(chapter);
  return (
    <>
      <div style={abs({ left: 90, top: 52, display: "flex", alignItems: "center", gap: 16 })}>
        <div style={{ minWidth: 52, height: 52, padding: "0 14px", borderRadius: 16, background: ACCENT, color: "#fff", fontFamily: FONT, fontWeight: 800, fontSize: 28, display: "flex", alignItems: "center", justifyContent: "center" }}>{n + 1}</div>
        <div style={{ fontFamily: FONT, fontWeight: 750, fontSize: 36, color: INK, letterSpacing: "-0.02em" }}>{chapter}</div>
      </div>
      <div style={abs({ right: 90, top: 72, display: "flex", gap: 10 })}>
        {CHAPTERS.map((c, i) => <div key={c} style={{ width: i === n ? 34 : 12, height: 12, borderRadius: 99, background: i <= n ? ACCENT : "#C9D0DC" }} />)}
      </div>
    </>
  );
};

// window frame: terminal (dark bar, «Терминал»), browser (light bar with an address pill), window (the app's own bar is in the shot)
const BAR = 40;
const Frame: React.FC<{ shot: Shot; w: number; h: number; children: React.ReactNode }> = ({ shot, w, h, children }) => {
  const kind = shot.frame ?? "terminal";
  const bar = kind === "window" ? 0 : BAR;
  const dark = kind === "terminal";
  return (
    <div style={{ width: w, height: h + bar, borderRadius: 14, overflow: "hidden", background: dark ? "#1E1E1E" : "#fff", boxShadow: "0 30px 80px rgba(17,19,24,0.22), 0 0 0 1px rgba(17,19,24,0.08)" }}>
      {bar > 0 && (
        <div style={{ height: bar, display: "flex", alignItems: "center", padding: "0 16px", gap: 8, background: dark ? "#2A2A2C" : "#ECEEF2", borderBottom: `1px solid ${dark ? "#111" : "#D8DCE3"}`, position: "relative" }}>
          {["#FF5F57", "#FEBC2E", "#28C840"].map((c) => <div key={c} style={{ width: 13, height: 13, borderRadius: 99, background: c }} />)}
          <div style={abs({ left: 0, right: 0, top: 0, height: bar, display: "flex", alignItems: "center", justifyContent: "center", fontFamily: FONT, fontWeight: 600, fontSize: 15, color: dark ? "#A8ABB3" : SUB })}>
            {kind === "browser" ? <div style={{ padding: "4px 18px", borderRadius: 8, background: "#fff", border: "1px solid #D8DCE3" }}>{shot.title ?? ""}</div> : shot.title ?? "Терминал"}
          </div>
        </div>
      )}
      {children}
    </div>
  );
};

// the stage: the whole window fits, then a slow push-in to `focus` and an outline around it
const STAGE: Rect = [110, 150, 1700, 740];
type View = { z: number; cx: number; cy: number };
// the camera on a window: the whole window, or zoomed to `focus` (the view centre is clamped so the zoomed window still
// covers the stage where it can)
const viewOf = (shot: Shot, fw: number, fh: number, bar: number, sw: number, sh: number): View => {
  const s0 = Math.min(sw / fw, sh / fh, 2.4);
  const f = shot.focus;
  if (!f) return { z: s0, cx: fw / 2, cy: fh / 2 };
  const s1 = Math.max(s0, Math.min(sw * 0.94 / f[2], sh * 0.9 / f[3], s0 * (shot.zoom ?? 1.6)));
  const fx = f[0] + f[2] / 2, fy = f[1] + f[3] / 2 + bar;
  const halfW = sw / 2 / s1, halfH = sh / 2 / s1;
  return {
    z: s1,
    cx: fw * s1 > sw ? Math.min(Math.max(fx, halfW), fw - halfW) : fw / 2,
    cy: fh * s1 > sh ? Math.min(Math.max(fy, halfH), fh - halfH) : fh / 2,
  };
};
const PUSH = 0.035;  // a barely visible slow push over the scene: a held screenshot never looks frozen

// `prev`: the previous scene shows the same screenshot → the camera moves on from where it was instead of cutting back
// to the whole window
const ShotView: React.FC<{ shot: Shot; prev?: Shot; size: [number, number] | null; t: number; dur: number; hasCmd: boolean }> = ({ shot, prev, size, t, dur, hasCmd }) => {
  const [sx, sy, sw, sh0] = STAGE;
  const sh = hasCmd ? sh0 : sh0 + 110;
  const [iw, ih] = size ?? [1600, 900];
  const bar = (shot.frame ?? "terminal") === "window" ? 0 : BAR;
  const fw = iw, fh = ih + bar;
  const f = shot.focus;
  const end = viewOf(shot, fw, fh, bar, sw, sh);
  const from = prev ? viewOf(prev, fw, fh, bar, sw, sh) : viewOf({ ...shot, focus: undefined }, fw, fh, bar, sw, sh);
  if (prev) from.z *= 1 + PUSH;
  else if (f && (fw * from.z) * (fh * from.z) < 0.6 * sw * sh) {
    // a small whole window after a zoomed dark one reads as a flash: start part of the way in
    from.z = lerp(from.z, end.z, 0.55); from.cx = lerp(from.cx, end.cx, 0.55); from.cy = lerp(from.cy, end.cy, 0.55);
  }
  const p = ease.inOutCubic(prev ? prog(t, 0.15, 1.1) : prog(t, 0.5, 1.3));
  const z = lerp(from.z, end.z, p) * (1 + PUSH * clamp01(t / dur));
  const cx = lerp(from.cx, end.cx, p), cy = lerp(from.cy, end.cy, p);
  const outline = f ? clamp01((t - 1.5) / 0.4) : 0;
  return (
    <div style={abs({ left: sx - 30, top: sy - 20, width: sw + 60, height: sh + 40, overflow: "hidden", borderRadius: 18 })}>
      <div style={abs({ left: 30, top: 20, width: sw, height: sh })}>
      <div style={abs({ left: sw / 2, top: sh / 2, width: fw, height: fh, transformOrigin: "0 0", transform: `scale(${z}) translate(${-cx}px, ${-cy}px)` })}>
        <Frame shot={shot} w={fw} h={ih}>
          {size ? <Img src={staticFile(`guide/shots/${shot.name}.png`)} style={{ display: "block", width: iw, height: ih }} />
            : <div style={{ width: iw, height: ih, display: "flex", alignItems: "center", justifyContent: "center", background: "#D9DEE7", color: SUB, fontFamily: MONO, fontSize: 40 }}>{shot.name}</div>}
        </Frame>
        {f && outline > 0 && (
          <div style={abs({ left: f[0] - 6, top: f[1] + bar - 6, width: f[2] + 12, height: f[3] + 12, borderRadius: 10, border: `${3 / z}px solid ${ACCENT}`,
            boxShadow: `0 0 0 ${6 / z}px rgba(91,140,255,0.22)`, opacity: outline })} />
        )}
      </div>
      </div>
    </div>
  );
};

const Cmd: React.FC<{ text: string }> = ({ text }) => (
  <div style={abs({ left: 0, width: W, top: 930, display: "flex", justifyContent: "center" })}>
    <div style={{ maxWidth: 1700, padding: "18px 34px", borderRadius: 18, background: "#111318", color: "#fff", fontFamily: MONO, fontSize: text.length > 70 ? 26 : 32, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", boxShadow: "0 14px 40px rgba(17,19,24,0.25)" }}>
      <span style={{ color: "#8FB0FF" }}>$ </span>{text}
    </div>
  </div>
);

const CardView: React.FC<{ card: Card }> = ({ card }) => (
  <div style={abs({ left: 260, top: 170, width: 1400, padding: "64px 80px", borderRadius: 34, background: "#fff", boxShadow: "0 30px 80px rgba(17,19,24,0.12), 0 0 0 1px rgba(17,19,24,0.05)" })}>
    <div style={{ fontFamily: FONT, fontWeight: 850, fontSize: 64, letterSpacing: "-0.035em", color: INK, marginBottom: 30 }}>{card.title}</div>
    {(card.lines ?? []).map((l) => (
      <div key={l} style={{ display: "flex", gap: 22, alignItems: "baseline", fontFamily: FONT, fontWeight: 550, fontSize: 36, color: INK, lineHeight: 1.35, marginBottom: 16 }}>
        <div style={{ width: 14, height: 14, borderRadius: 99, background: ACCENT, flex: "none", transform: "translateY(-6px)" }} />{l}
      </div>
    ))}
    {(card.code ?? []).map((c) => (
      <div key={c} style={{ marginTop: 18, padding: "16px 28px", borderRadius: 14, background: "#111318", color: "#fff", fontFamily: MONO, fontSize: 30 }}><span style={{ color: "#8FB0FF" }}>$ </span>{c}</div>
    ))}
  </div>
);

const SceneView: React.FC<{ s: GuideScene; prev?: GuideScene; dur: number; sizes: ShotSizes | null }> = ({ s, prev, dur, sizes }) => {
  const t = useCurrentFrame() / GUIDE_FPS;
  // plain cuts between scenes: a fade through the light background flashes the dark windows
  return (
    <AbsoluteFill>
      <Bg />
      <Header chapter={s.chapter} />
      {s.shot && <ShotView shot={s.shot} prev={prev?.shot?.name === s.shot.name && !!prev.cmd === !!s.cmd ? prev.shot : undefined} size={sizes?.[s.shot.name] ?? null} t={t} dur={dur} hasCmd={!!s.cmd} />}
      {s.card && <CardView card={s.card} />}
      {s.cmd && <Cmd text={s.cmd} />}
    </AbsoluteFill>
  );
};

export const Guide: React.FC<GuideProps> = ({ vo, sizes }) => {
  loadBaseFonts();
  const durs = guideDurations(vo);
  const starts = durs.map((_, i) => durs.slice(0, i).reduce((a, b) => a + b, 0));
  return (
    <AbsoluteFill style={{ background: "#E9EDF4" }}>
      {SCENES.map((s, i) => (
        <Sequence key={s.id} from={Math.round(starts[i] * GUIDE_FPS)} durationInFrames={Math.round((starts[i] + durs[i]) * GUIDE_FPS) - Math.round(starts[i] * GUIDE_FPS)} name={`${i + 1} · ${s.id}`}>
          <Fit><SceneView s={s} prev={SCENES[i - 1]} dur={durs[i]} sizes={sizes} /></Fit>
          {vo?.[s.id] ? <Sequence from={Math.round(0.2 * GUIDE_FPS)} layout="none"><Audio src={staticFile(`guide/vo_${s.id}.wav`)} /></Sequence> : null}
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};
