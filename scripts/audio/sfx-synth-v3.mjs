// SFX pack v3 — quiet, warm «product» sounds for long videos.
// Direction: quiet, warm, «product» sounds — no hard clicks, no trailer booms, no meme stings on routine beats.
// Every sound has a soft attack (≥ 3 ms), most energy below 4 kHz, a short natural room; levels are set in the edit.
// Everything is synthesised here, so the sounds are free to use (MIT, like the code).
//   in        insert opens: airy swell into a soft low bloom          out      the reverse, shorter (insert closes)
//   land      object lands (pedestal, card): rounded thud              glint    glassy two-partial bell (a highlight)
//   glint_lo  the same an octave lower                                tick     soft wood tick (list item, counter step)
//   count     accelerating soft ticks, 1.2 s (a number counts up)       tap      UI tap (a check, a field)
//   rise      gentle 1 s rise that fades instead of cutting             chapter  chapter card: low soft bloom + shimmer + quiet chord
//   spark     electric crackle (a connection fails)                    fail     two soft descending notes (error, 502)
//   success   two soft ascending marimba notes (done, accepted)        clock    fast tick-tock, 2 s (waiting / time-lapse)
//   stamp     muffled stamp: thud + paper (ВЫБЫЛ)                     whoosh   smooth wide pass (a wipe, an object flying)
// Usage: node scripts/audio/sfx-synth-v3.mjs [OUT_DIR]   (default public/sfx/v3)
import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const SR = 48000;
if (process.argv[2]?.startsWith("-")) {
  console.log("Usage: node scripts/audio/sfx-synth-v3.mjs [OUT_DIR]   (default public/sfx/v3): writes the synthesised SFX pack as WAV");
  process.exit(process.argv[2] === "--help" || process.argv[2] === "-h" ? 0 : 2);
}
const OUT = process.argv[2] ?? "public/sfx/v3";
mkdirSync(OUT, { recursive: true });
const TAU = Math.PI * 2;
const rng = (seed) => () => ((seed = (seed * 1664525 + 1013904223) >>> 0) / 4294967296) * 2 - 1;
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const svf = () => {
  let lo = 0, bp = 0;
  return (x, f, q = 1) => {
    const F = 2 * Math.sin((Math.PI * Math.min(Math.max(f, 20), SR / 6)) / SR);
    const hp = x - lo - bp / q;
    bp += F * hp;
    lo += F * bp;
    return { lo, bp, hp };
  };
};
const mix = (dur, voices) => {
  const n = Math.round(dur * SR);
  const L = new Float32Array(n), R = new Float32Array(n);
  for (const { t0 = 0, pan = 0, gain = 1, fn, len, width = 0 } of voices) {
    const a = Math.round(t0 * SR), b = Math.min(n, a + Math.round((len ?? dur) * SR));
    const fade = Math.round(0.03 * SR);
    for (let i = a; i < b; i++) {
      const t = (i - a) / SR;
      const p = clamp(pan + width * Math.sin(t * 9), -1, 1);
      const v = fn(t) * Math.min(1, (b - i) / fade) * gain;
      L[i] += v * Math.cos(((p + 1) * Math.PI) / 4); R[i] += v * Math.sin(((p + 1) * Math.PI) / 4);
    }
  }
  return [L, R];
};
const reverb = ([L, R], { wet = 0.2, size = 0.82, damp = 0.3, tail = 1.6 } = {}) => {
  const n = L.length + Math.round(tail * SR);
  const run = (x, spread) => {
    const out = new Float32Array(n);
    for (const d0 of [1116, 1188, 1277, 1356, 1422, 1491]) {
      const d = Math.round(d0 * (SR / 44100)) + spread, buf = new Float32Array(d);
      let idx = 0, filt = 0;
      for (let i = 0; i < n; i++) { const y = buf[idx]; filt = y * (1 - damp) + filt * damp; buf[idx] = (i < x.length ? x[i] : 0) * 0.015 + filt * size; out[i] += y; idx = (idx + 1) % d; }
    }
    for (const a0 of [556, 441, 341]) {
      const d = Math.round(a0 * (SR / 44100)) + spread, buf = new Float32Array(d);
      let idx = 0;
      for (let i = 0; i < n; i++) { const b = buf[idx], y = -out[i] + b; buf[idx] = out[i] + b * 0.5; out[i] = y; idx = (idx + 1) % d; }
    }
    return out;
  };
  const wL = run(L, 0), wR = run(R, 31);
  const oL = new Float32Array(n), oR = new Float32Array(n);
  for (let i = 0; i < n; i++) { oL[i] = (L[i] ?? 0) + wL[i] * wet * 5; oR[i] = (R[i] ?? 0) + wR[i] * wet * 5; }
  return [oL, oR];
};
// soft clip for weight and loudness
const sat = ([L, R], drive = 1.6) => [L.map((x) => Math.tanh(x * drive) / Math.tanh(drive)), R.map((x) => Math.tanh(x * drive) / Math.tanh(drive))];
const write = (name, [L, R]) => {
  let end = L.length;
  while (end > 1 && Math.abs(L[end - 1]) < 1e-5 && Math.abs(R[end - 1]) < 1e-5) end--;
  const f = Math.min(Math.round(0.02 * SR), end);
  for (let i = 0; i < f; i++) { const g = i / f; L[end - 1 - i] *= g; R[end - 1 - i] *= g; }
  let peak = 1e-9;
  for (let i = 0; i < end; i++) peak = Math.max(peak, Math.abs(L[i]), Math.abs(R[i]));
  const g = Math.pow(10, -1 / 20) / peak, n = end, buf = Buffer.alloc(44 + n * 6);
  buf.write("RIFF", 0); buf.writeUInt32LE(36 + n * 6, 4); buf.write("WAVE", 8); buf.write("fmt ", 12);
  buf.writeUInt32LE(16, 16); buf.writeUInt16LE(1, 20); buf.writeUInt16LE(2, 22); buf.writeUInt32LE(SR, 24);
  buf.writeUInt32LE(SR * 6, 28); buf.writeUInt16LE(6, 32); buf.writeUInt16LE(24, 34); buf.write("data", 36); buf.writeUInt32LE(n * 6, 40);
  for (let i = 0; i < n; i++) for (const [c, s] of [[0, L[i]], [1, R[i]]]) buf.writeIntLE(Math.max(-8388608, Math.min(8388607, Math.round(s * g * 8388607))), 44 + i * 6 + c * 3, 3);
  writeFileSync(join(OUT, `${name}.wav`), buf);
  console.log(name.padEnd(12), (n / SR).toFixed(2) + " s");
};

// ---------------------------------------------------------------- building blocks
// sub drop: sine sweeping f0 → f1, punchy attack
const sub = (f0, f1, dec, sweep = 0.06) => { let p = 0; return (t) => { p += (TAU * (f1 + (f0 - f1) * Math.exp(-t / sweep))) / SR; return Math.sin(p) * Math.exp(-t / dec) * Math.min(1, t / 0.0015); }; };
// filtered noise with a moving centre frequency fc(t)
const air = (seed, fc, q, env) => { const r = rng(seed), f = svf(); return (t) => f(r(), fc(t), q).bp * env(t); };
const click = (seed, f = 5000, dec = 0.004) => { const r = rng(seed), h = svf(); return (t) => h(r(), f, 0.7).hp * Math.exp(-t / dec); };
// short inharmonic metal ring
const ring = (f0, dec, seed = 1) => {
  const ratios = [1, 2.76, 5.4, 8.93, 11.3], r = rng(seed), ph = ratios.map(() => r() * TAU);
  return (t) => ratios.reduce((s, k, i) => s + Math.sin(TAU * f0 * k * t + ph[i]) * Math.exp(-t / (dec / (1 + i * 0.7))) / (1 + i), 0);
};
const saw = (f) => { let p = 0; return (t, ff = f) => { p += ff / SR; p -= Math.floor(p); return 2 * p - 1; }; };
const sine = (f, ph = 0) => (t) => Math.sin(TAU * f * t + ph);
const env = (a, d) => (t) => Math.min(1, t / a) * Math.exp(-Math.max(0, t - a) / d);
const lowpass = ([L, R], f) => { const a = svf(), b = svf(); return [L.map((x) => a(x, f, 0.7).lo), R.map((x) => b(x, f, 0.7).lo)]; };
const tri = (f) => (t) => { const p = (f * t) % 1; return 4 * Math.abs(p - 0.5) - 1; };
// soft bell: two partials + a quiet inharmonic shimmer
const bell = (f, dec = 0.9) => (t) => env(0.004, dec)(t) * (sine(f)(t) + 0.45 * sine(f * 1.5, 0.3)(t) + 0.12 * sine(f * 2.76, 1.1)(t) * Math.exp(-t / 0.15));
const wood = (f, seed) => { const n = air(seed, () => f * 1.6, 3.5, env(0.0015, 0.012)); return (t) => 0.7 * sine(f)(t) * env(0.002, 0.02)(t) + 0.5 * n(t); };
const marimba = (f) => (t) => env(0.003, 0.35)(t) * (sine(f)(t) + 0.35 * sine(f * 4, 0.5)(t) * Math.exp(-t / 0.05));

write("in", reverb(lowpass(mix(0.9, [
  { len: 0.5, fn: air(101, (t) => 250 + 1500 * (t / 0.5) ** 2, 1.2, (t) => (t / 0.5) ** 2), gain: 0.8, width: 0.6 },
  { t0: 0.42, fn: (t) => sine(78)(t) * env(0.025, 0.28)(t), gain: 0.9 },
  { t0: 0.42, fn: air(103, () => 900, 0.8, env(0.01, 0.08)), gain: 0.25 },
]), 5000), { wet: 0.16, tail: 0.8 }));

write("out", reverb(lowpass(mix(0.45, [
  { len: 0.4, fn: air(107, (t) => 1600 - 1300 * (t / 0.4), 1.2, (t) => Math.sin(Math.PI * Math.min(1, t / 0.4)) ** 1.5), gain: 0.8, width: 0.6 },
]), 4500), { wet: 0.12, tail: 0.5 }));

write("land", reverb(lowpass(mix(0.5, [
  { fn: sub(105, 52, 0.16, 0.03), gain: 1.0 },
  { fn: air(111, () => 600, 0.9, env(0.002, 0.03)), gain: 0.45 },
]), 2500), { wet: 0.1, tail: 0.5 }));

write("glint", reverb(lowpass(mix(1.2, [{ fn: bell(1046.5), gain: 0.9, pan: -0.1 }, { t0: 0.012, fn: bell(1568, 0.6), gain: 0.35, pan: 0.2 }]), 6000), { wet: 0.22, tail: 1.2 }));
write("glint_lo", reverb(lowpass(mix(1.4, [{ fn: bell(523.25, 1.1), gain: 0.9 }, { t0: 0.01, fn: bell(784, 0.7), gain: 0.3, pan: 0.2 }]), 5000), { wet: 0.22, tail: 1.2 }));
write("tick", reverb(lowpass(mix(0.12, [{ fn: wood(1300, 121), gain: 0.9 }]), 5000), { wet: 0.06, tail: 0.25 }));
{
  const v = []; let t = 0, k = 0;
  while (t < 1.15) { const iv = 0.11 * Math.pow(0.82, k) + 0.025; v.push({ t0: t, len: 0.1, fn: wood(1100 + 25 * k, 130 + k), gain: 0.55 + 0.35 * (t / 1.15), pan: k % 2 ? 0.15 : -0.15 }); t += iv; k++; }
  write("count", reverb(lowpass(mix(1.3, v), 5000), { wet: 0.08, tail: 0.3 }));
}
write("tap", reverb(lowpass(mix(0.12, [{ fn: (t) => Math.sin(TAU * (620 - 1800 * t) * t) * env(0.002, 0.025)(t), gain: 0.8 }, { fn: air(141, () => 2200, 1.5, env(0.001, 0.006)), gain: 0.2 }]), 5000), { wet: 0.06, tail: 0.25 }));
{
  let ph = 0;
  write("rise", reverb(lowpass(mix(1.15, [
    { len: 1.1, fn: air(151, (t) => 300 * Math.pow(9, t / 1.1), 1.3, (t) => Math.pow(t / 1.1, 1.8) * (1 - Math.max(0, (t - 0.95) / 0.15))), gain: 0.7, width: 0.5 },
    { len: 1.1, fn: (t) => { ph += TAU * (180 + 200 * (t / 1.1) ** 2) / SR; return Math.sin(ph) * Math.pow(t / 1.1, 2) * (1 - Math.max(0, (t - 0.95) / 0.15)); }, gain: 0.35 },
  ]), 5500), { wet: 0.14, tail: 0.6 }));
}
write("chapter", reverb(lowpass(mix(2.2, [
  { fn: (t) => sine(55)(t) * env(0.03, 0.9)(t), gain: 1.0 },
  { fn: air(161, () => 140, 0.7, env(0.02, 0.4)), gain: 0.35 },
  { len: 1.4, fn: air(163, () => 5200, 1.5, (t) => Math.min(1, t / 0.25) * Math.exp(-t / 0.5)), gain: 0.12, width: 0.8 },
  { t0: 0.04, fn: bell(523.25, 1.3), gain: 0.16, pan: -0.3 },
  { t0: 0.06, fn: bell(659.25, 1.2), gain: 0.12, pan: 0.3 },
  { t0: 0.08, fn: bell(783.99, 1.1), gain: 0.1 },
]), 6000), { wet: 0.26, size: 0.86, tail: 1.8 }));
{
  const r = rng(171), v = [];
  for (let i = 0; i < 16; i++) v.push({ t0: Math.abs(r()) * 0.32, len: 0.04, fn: air(172 + i, () => 2500 + Math.abs(r()) * 2500, 1.2, env(0.0008, 0.006 + Math.abs(r()) * 0.008)), gain: 0.4 + Math.abs(r()) * 0.5, pan: r() * 0.6 });
  v.push({ fn: sub(160, 60, 0.12, 0.02), gain: 0.6 });
  write("spark", reverb(lowpass(mix(0.5, v), 7000), { wet: 0.12, tail: 0.5 }));
}
{
  const n1 = (t) => (tri(329.6)(t) + 0.6 * tri(331.2)(t)) * env(0.008, 0.22)(t), n2 = (t) => (tri(261.6)(t) + 0.6 * tri(262.9)(t)) * env(0.008, 0.4)(t);
  write("fail", reverb(lowpass(mix(1.0, [{ fn: n1, gain: 0.5 }, { t0: 0.17, fn: n2, gain: 0.55 }, { t0: 0.17, fn: sub(90, 55, 0.2, 0.03), gain: 0.4 }]), 2200), { wet: 0.18, tail: 0.8 }));
}
write("success", reverb(lowpass(mix(1.0, [{ fn: marimba(784), gain: 0.7, pan: -0.15 }, { t0: 0.11, fn: marimba(1174.7), gain: 0.65, pan: 0.15 }]), 6000), { wet: 0.18, tail: 0.8 }));
{
  const v = [];
  for (let i = 0; i < 8; i++) v.push({ t0: i * 0.25, len: 0.1, fn: wood(i % 2 ? 1050 : 1400, 181 + i), gain: 0.7, pan: i % 2 ? 0.2 : -0.2 });
  write("clock", reverb(lowpass(mix(2.1, v), 5000), { wet: 0.08, tail: 0.3 }));
}
write("stamp", reverb(lowpass(mix(0.6, [
  { fn: sub(120, 60, 0.12, 0.02), gain: 1.0 },
  { fn: air(191, () => 1800, 0.7, env(0.002, 0.05)), gain: 0.4, width: 0.3 },
]), 3500), { wet: 0.12, tail: 0.5 }));
write("whoosh", reverb(lowpass(mix(0.7, [
  { len: 0.6, fn: air(201, (t) => 400 + 2200 * Math.sin(Math.PI * Math.min(1, t / 0.6)), 1.6, (t) => Math.sin(Math.PI * Math.min(1, t / 0.6)) ** 2), gain: 0.9, width: 0.9 },
]), 5500), { wet: 0.14, tail: 0.6 }));
