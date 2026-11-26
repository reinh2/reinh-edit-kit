// Framing of a screen recording: a virtual camera over the full-frame recording (no auto-zoom in the recorder).
// keys = [t, cx, cy, w, dur]: from local time t (s) the camera moves for `dur` s (ease in-out) to a view centred on
// (cx, cy) that shows `w` px of width — the same format as `cams` in the EDL (scripts/edit/edl_timeline.py).
// Coordinates are in the recording's own pixels (`srcW` × `srcH`). blur = privacy rects [x, y, w, h] in recording
// pixels (e-mails, keys, tokens) that move with the camera. tile = a face picture-in-picture on wide views only.
import React from "react";
import { AbsoluteFill, OffthreadVideo, useCurrentFrame, useVideoConfig } from "remotion";
import { clamp01, ease, lerp } from "./motion";

export type CamKey = [number, number, number, number, number];

export const camAt = (keys: CamKey[], t: number, srcW: number, srcH: number) => {
  const view = (k: CamKey) => ({ cx: k[1], cy: k[2], w: k[3] });
  let v = view(keys[0]);
  for (let i = 1; i < keys.length; i++) {
    const k = keys[i];
    if (t < k[0]) break;
    const p = k[4] > 0 ? ease.inOutCubic(clamp01((t - k[0]) / k[4])) : 1;
    const to = view(k);
    v = { cx: lerp(v.cx, to.cx, p), cy: lerp(v.cy, to.cy, p), w: lerp(v.w, to.w, p) };
  }
  const h = (v.w * srcH) / srcW;
  // keep the view inside the recording
  const cx = Math.min(srcW - v.w / 2, Math.max(v.w / 2, v.cx));
  const cy = Math.min(srcH - h / 2, Math.max(h / 2, v.cy));
  return { cx, cy, w: v.w, zoom: srcW / v.w };
};

export const ScreenCam: React.FC<{
  src: string; keys: CamKey[]; srcW?: number; srcH?: number; startFrom?: number;
  blur?: [number, number, number, number][]; tile?: string; radius?: number;
  /** size of the box the camera fills (default: the whole composition) */ boxW?: number; boxH?: number;
}> = ({ src, keys, srcW = 1920, srcH = 1080, startFrom = 0, blur = [], tile, radius = 0, boxW, boxH }) => {
  const frame = useCurrentFrame();
  const cfg = useVideoConfig();
  const t = frame / cfg.fps;
  const width = boxW ?? cfg.width, height = boxH ?? cfg.height;
  const cam = camAt(keys, t, srcW, srcH);
  const s = (width / srcW) * cam.zoom; // recording px → output px
  const tx = width / 2 - cam.cx * s;
  const ty = height / 2 - cam.cy * s;
  const tileOn = tile && cam.zoom < 1.05;
  return (
    <AbsoluteFill style={{ background: "#0B0D12", overflow: "hidden", borderRadius: radius }}>
      <div style={{ position: "absolute", left: 0, top: 0, width: srcW, height: srcH, transformOrigin: "0 0", transform: `translate(${tx}px, ${ty}px) scale(${s})` }}>
        <OffthreadVideo src={src} startFrom={startFrom} muted style={{ width: srcW, height: srcH }} />
        {blur.map(([x, y, w, h], i) => (
          <div key={i} style={{ position: "absolute", left: x, top: y, width: w, height: h, borderRadius: 8, backdropFilter: "blur(14px)", background: "rgba(200,205,215,0.35)" }} />
        ))}
      </div>
      {tileOn && (
        <div style={{ position: "absolute", right: width * 0.025, bottom: height * 0.04, width: width * 0.2, height: width * 0.2 * 9 / 16, borderRadius: 24, overflow: "hidden", boxShadow: "0 18px 50px rgba(0,0,0,0.35)" }}>
          <OffthreadVideo src={tile} startFrom={startFrom} muted style={{ width: "100%", height: "100%", objectFit: "cover" }} />
        </div>
      )}
    </AbsoluteFill>
  );
};
