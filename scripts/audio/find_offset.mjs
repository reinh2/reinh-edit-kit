// Finds where a short clip's audio sits inside a long recording (e.g. Screen Studio clip inside an OBS mic recording).
// Usage: node scripts/audio/find_offset.mjs CLIP LONG  → prints best offset (s) in LONG and a confidence score.
// Two passes: speech-envelope correlation at 200 Hz over the whole recording, then raw-sample correlation ±50 ms.
import { execFileSync } from "node:child_process";
const pcm = (f) => { const b = execFileSync("ffmpeg", ["-v", "error", "-i", f, "-vn", "-ac", "1", "-ar", "16000", "-f", "f32le", "-"], { maxBuffer: 1 << 30 }); return new Float32Array(b.buffer, b.byteOffset, b.length / 4); };
const env = (x, hop = 80) => { const n = Math.floor(x.length / hop), e = new Float32Array(n); for (let i = 0; i < n; i++) { let s = 0; for (let j = 0; j < hop; j++) s += Math.abs(x[i * hop + j]); e[i] = Math.log(1e-4 + s / hop); } let m = 0; for (const v of e) m += v; m /= n; let sd = 0; for (let i = 0; i < n; i++) { e[i] -= m; sd += e[i] * e[i]; } sd = Math.sqrt(sd / n) || 1; for (let i = 0; i < n; i++) e[i] /= sd; return e; };
const [clipF, longF] = process.argv.slice(2);
if (!clipF || !longF || clipF.startsWith("-")) {
  console.log("Usage: node scripts/audio/find_offset.mjs CLIP LONG\n  finds where the audio of CLIP sits inside LONG; prints the offset (s) and confidence as JSON");
  process.exit(clipF === "--help" || clipF === "-h" ? 0 : 2);
}
const a = pcm(clipF), b = pcm(longF);
const ea = env(a), eb = env(b);
let best = -1e9, lag = 0, second = -1e9;
const scores = new Float32Array(eb.length - ea.length);
for (let k = 0; k < eb.length - ea.length; k++) { let s = 0; for (let i = 0; i < ea.length; i++) s += ea[i] * eb[k + i]; s /= ea.length; scores[k] = s; if (s > best) { best = s; lag = k; } }
for (let k = 0; k < scores.length; k++) if (Math.abs(k - lag) > 400 && scores[k] > second) second = scores[k];
// refine on samples ±50 ms
const c0 = lag * 80; let rb = -1e9, rl = c0; const win = Math.min(a.length, 16000 * 20);
for (let d = -800; d <= 800; d++) { const o = c0 + d; if (o < 0 || o + win > b.length) continue; let s = 0, na = 0, nb = 0; for (let i = 0; i < win; i += 2) { s += a[i] * b[o + i]; na += a[i] * a[i]; nb += b[o + i] * b[o + i]; } const r = s / Math.sqrt(na * nb + 1e-12); if (r > rb) { rb = r; rl = o; } }
console.log(JSON.stringify({ clip: clipF, long: longF, offset_s: +(rl / 16000).toFixed(4), env_score: +best.toFixed(3), runner_up: +second.toFixed(3), sample_corr: +rb.toFixed(3) }));
