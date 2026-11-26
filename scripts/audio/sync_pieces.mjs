// Piecewise sync of an edited clip (e.g. a Screen Studio export cut from several takes) to a long mic recording.
// Usage: node scripts/audio/sync_pieces.mjs CLIP LONG OUT.wav OFF1 OFF2 ...
//   OFFn — candidate offsets (s) of clip time 0 in LONG, found with find_offset.mjs on pieces of the clip.
// For every 0.1 s of the clip it scores each candidate (±40 ms refine, 1 s window), keeps the best, merges runs into
// segments, writes OUT.json (segments: clip t0–t1 → long offset) and OUT.wav: the LONG audio laid on the clip timeline
// (48 kHz, original channels), with 10 ms crossfades at the joins.
import { execFileSync } from "node:child_process";
import { writeFileSync } from "node:fs";
const pcm = (f, sr = 16000) => { const b = execFileSync("ffmpeg", ["-v", "error", "-i", f, "-vn", "-ac", "1", "-ar", String(sr), "-f", "f32le", "-"], { maxBuffer: 1 << 30 }); return new Float32Array(b.buffer, b.byteOffset, b.length / 4); };
const [clipF, longF, outF, ...offs] = process.argv.slice(2);
const cands = offs.map(Number);
const a = pcm(clipF), b = pcm(longF), SR = 16000;
const corr = (ca, cb, n) => { let s = 0, x = 0, y = 0; for (let i = 0; i < n; i += 2) { s += a[ca + i] * b[cb + i]; x += a[ca + i] ** 2; y += b[cb + i] ** 2; } return x < 1e-6 ? 0 : s / Math.sqrt(x * y + 1e-12); };
const W = SR, H = SR / 10, dur = a.length / SR, picks = [];
for (let c = 0; c + W <= a.length; c += H) {
  let best = { r: -1, off: null };
  for (const o of cands) for (let d = -640; d <= 640; d += 16) { const cb = c + Math.round(o * SR) + d; if (cb < 0 || cb + W > b.length) continue; const r = corr(c, cb, W); if (r > best.r) best = { r, off: o + d / SR }; }
  picks.push({ t: c / SR, ...best });
}
// assign each pick to its candidate group, then median-filter labels (window 5) to drop flickers
const lab = picks.map((p) => cands.reduce((bi, o, i) => (Math.abs(p.off - o) < Math.abs(p.off - cands[bi]) ? i : bi), 0));
const sm = lab.map((_, i) => { const w = lab.slice(Math.max(0, i - 2), i + 3); const cnt = {}; w.forEach((v) => (cnt[v] = (cnt[v] || 0) + 1)); return +Object.entries(cnt).sort((x, y) => y[1] - x[1])[0][0]; });
const segs = [];
sm.forEach((g, i) => { const t = picks[i].t; if (!segs.length || segs.at(-1).g !== g) segs.push({ g, t0: t, rs: [] }); segs.at(-1).rs.push(picks[i]); });
segs.forEach((s, i) => { s.t1 = i + 1 < segs.length ? segs[i + 1].t0 + 0.5 : dur; if (i) s.t0 += 0.5; const good = s.rs.filter((p) => p.r > 0.2).map((p) => p.off).sort((x, y) => x - y); s.offset = good.length ? good[good.length >> 1] : cands[s.g]; s.mean_r = +(s.rs.reduce((q, p) => q + p.r, 0) / s.rs.length).toFixed(3); delete s.rs; delete s.g; });
segs[0].t0 = 0;
writeFileSync(outF.replace(/\.wav$/, ".json"), JSON.stringify({ clip: clipF, long: longF, segments: segs }, null, 1));
// build: each segment = LONG[t0+offset, t1+offset], placed at t0, 10 ms fades
const parts = [], filt = [];
segs.forEach((s, i) => { parts.push("-ss", (s.t0 + s.offset).toFixed(4), "-t", (s.t1 - s.t0).toFixed(4), "-i", longF); filt.push(`[${i}:a]aresample=48000,afade=t=in:d=0.01,afade=t=out:st=${(s.t1 - s.t0 - 0.01).toFixed(4)}:d=0.01[s${i}]`); });
execFileSync("ffmpeg", ["-v", "error", "-y", ...parts, "-filter_complex", `${filt.join(";")};${segs.map((_, i) => `[s${i}]`).join("")}concat=n=${segs.length}:v=0:a=1[o]`, "-map", "[o]", "-c:a", "pcm_s24le", outF]);
console.log(JSON.stringify(segs));
