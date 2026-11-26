// A 3D hero in Remotion: plays a transparent PNG sequence rendered by Blender (scripts/blender/*.py → public/<dir>/0001.png …
// + meta.json) over any background, at the sequence's own fps (30 fps in a 60 fps film = each frame twice). Without
// frames (Blender not installed or not rendered yet) it shows a soft glow placeholder, so the film still renders.
// loop: repeat (turntables); otherwise the last frame holds. Load meta.json with loadHeroMeta() in calculateMetadata.
import React from "react";
import { Img, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { clamp01, ease, lerp, prog } from "./motion";

export type HeroMeta = { frames: number; fps: number; width: number; height: number };

export const loadHeroMeta = async (dir: string): Promise<HeroMeta | null> => {
  const r = await fetch(staticFile(`${dir}/meta.json`)).catch(() => null);
  return r && r.ok ? ((await r.json()) as HeroMeta) : null;
};

export const Hero3D: React.FC<{ dir: string; meta: HeroMeta | null; style: React.CSSProperties; loop?: boolean; delay?: number; fadeIn?: number; glow?: string }> = ({ dir, meta, style, loop, delay = 0, fadeIn = 0.25, glow = "rgba(160,190,255,0.45)" }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps - delay;
  const p = prog(t, 0, fadeIn, ease.outCubic);
  if (t < 0) return null;
  const box: React.CSSProperties = { position: "absolute", pointerEvents: "none", opacity: clamp01(p * 1.2), filter: "drop-shadow(0 50px 70px rgba(0,0,0,0.45))", ...style };
  if (!meta || meta.frames <= 0) {
    return <div style={{ ...box, transform: `scale(${lerp(0.9, 1, p)})` }}><div style={{ width: "100%", height: "100%", borderRadius: "50%", background: `radial-gradient(circle, ${glow}, transparent 62%)` }} /></div>;
  }
  const n = Math.floor(t * meta.fps);
  const i = loop ? (n % meta.frames) + 1 : Math.min(meta.frames, n + 1);
  return (
    <div style={box}>
      <Img src={staticFile(`${dir}/${String(i).padStart(4, "0")}.png`)} style={{ width: "100%", height: "100%", objectFit: "contain" }} />
    </div>
  );
};
