// SFX pack v2 — softer, "product UI" sounds (the default pack of src/kit/sfx.tsx).
// Everything is synthesised here (we own it outright): tuned sines with pitch envelopes, filtered noise, a small
// stereo reverb (Freeverb-style) for space. 48 kHz / 24-bit stereo WAV, peak −1 dBFS; mix level is set in the edit.
// File names keep the v1 event groups (src/kit/sfx.tsx), plus new groups: tap, notify.
// Usage: node scripts/audio/sfx-synth-v2.mjs [OUT_DIR]   (default public/sfx/v2)
import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const SR = 48000;
const OUT = process.argv[2] ?? "public/sfx/v2";
mkdirSync(OUT, { recursive: true });

const rng = (seed) => () => ((seed = (seed * 1664525 + 1013904223) >>> 0) / 4294967296) * 2 - 1;
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const lerp = (a, b, p) => a + (b - a) * p;
const expSweep = (f0, f1, p) => f0 * Math.pow(f1 / f0, clamp(p));
const env = (t, a, d) => (t < 0 ? 0 : t < a ? Math.sin((Math.PI / 2) * (t / a)) : Math.exp(-(t - a) / d)); // smooth attack, exp decay
const TAU = Math.PI * 2;

// one-pole lowpass / highpass
const lp1 = () => { let y = 0; return (x, f) => (y += (1 - Math.exp((-TAU * f) / SR)) * (x - y)); };
const hp1 = () => { const l = lp1(); return (x, f) => x - l(x, f); };
// state-variable bandpass
const svf = () => {
  let lo = 0, bp = 0;
  return (x, f, q = 1) => {
    const F = 2 * Math.sin((Math.PI * Math.min(f, SR / 6)) / SR);
    const hp = x - lo - bp / q;
    bp += F * hp;
    lo += F * bp;
    return { lo, bp, hp };
  };
};

const render = (dur, fn) => {
  const n = Math.round(dur * SR);
  const L = new Float32Array(n), R = new Float32Array(n);
  for (let i = 0; i < n; i++) {
    const v = fn(i / SR, i);
    if (Array.isArray(v)) { L[i] = v[0]; R[i] = v[1]; } else { L[i] = v; R[i] = v; }
  }
  return [L, R];
};
const pan = (x, p) => [x * Math.cos(((p + 1) * Math.PI) / 4), x * Math.sin(((p + 1) * Math.PI) / 4)];

// Freeverb-style stereo reverb: 4 damped combs + 2 allpasses per channel.
const reverb = ([L, R], { mix = 0.18, size = 0.78, damp = 0.35, tail = 0.6 } = {}) => {
  const n = L.length + Math.round(tail * SR);
  const combsL = [1116, 1188, 1277, 1356], combsR = combsL.map((d) => d + 23);
  const aps = [556, 441];
  const run = (x, combs, spread) => {
    const out = new Float32Array(n);
    for (const d0 of combs) {
      const d = Math.round(d0 * (SR / 44100)) + spread;
      const buf = new Float32Array(d);
      let idx = 0, filt = 0;
      for (let i = 0; i < n; i++) {
        const y = buf[idx];
        filt = y * (1 - damp) + filt * damp;
        buf[idx] = (i < x.length ? x[i] : 0) * 0.015 + filt * size;
        out[i] += y;
        idx = (idx + 1) % d;
      }
    }
    for (const a0 of aps) {
      const d = Math.round(a0 * (SR / 44100)) + spread;
      const buf = new Float32Array(d);
      let idx = 0;
      for (let i = 0; i < n; i++) {
        const b = buf[idx];
        const y = -out[i] + b;
        buf[idx] = out[i] + b * 0.5;
        out[i] = y;
        idx = (idx + 1) % d;
      }
    }
    return out;
  };
  const wL = run(L, combsL, 0), wR = run(R, combsR, 0);
  const oL = new Float32Array(n), oR = new Float32Array(n);
  for (let i = 0; i < n; i++) {
    oL[i] = (i < L.length ? L[i] : 0) + wL[i] * mix * 6;
    oR[i] = (i < R.length ? R[i] : 0) + wR[i] * mix * 6;
  }
  return [oL, oR];
};

// trim trailing near-silence, short fade-out
const finish = ([L, R]) => {
  let end = L.length;
  while (end > 1 && Math.abs(L[end - 1]) < 1e-5 && Math.abs(R[end - 1]) < 1e-5) end--;
  const f = Math.min(Math.round(0.01 * SR), end);
  for (let i = 0; i < f; i++) { const g = i / f; L[end - 1 - i] *= g; R[end - 1 - i] *= g; }
  return [L.subarray(0, end), R.subarray(0, end)];
};

const write = (name, stereo) => {
  const [L, R] = finish(stereo);
  let peak = 1e-9;
  for (let i = 0; i < L.length; i++) peak = Math.max(peak, Math.abs(L[i]), Math.abs(R[i]));
  const g = Math.pow(10, -1 / 20) / peak;
  const n = L.length, buf = Buffer.alloc(44 + n * 6);
  buf.write("RIFF", 0); buf.writeUInt32LE(36 + n * 6, 4); buf.write("WAVE", 8); buf.write("fmt ", 12);
  buf.writeUInt32LE(16, 16); buf.writeUInt16LE(1, 20); buf.writeUInt16LE(2, 22); buf.writeUInt32LE(SR, 24);
  buf.writeUInt32LE(SR * 6, 28); buf.writeUInt16LE(6, 32); buf.writeUInt16LE(24, 34); buf.write("data", 36); buf.writeUInt32LE(n * 6, 40);
  for (let i = 0; i < n; i++) {
    for (const [c, s] of [[0, L[i]], [1, R[i]]]) {
      const v = Math.max(-8388608, Math.min(8388607, Math.round(s * g * 8388607)));
      buf.writeIntLE(v, 44 + i * 6 + c * 3, 3);
    }
  }
  writeFileSync(join(OUT, `${name}.wav`), buf);
  console.log(name.padEnd(22), (n / SR).toFixed(2) + " s");
};

// ---------- instruments ----------
// Soft bubble pop: upward chirp then a short tonal decay with one soft partial.
const bubble = (f0, f1, dur = 0.14, pos = 0) => {
  let ph = 0, ph2 = 0;
  const l = lp1();
  return reverb(render(dur, (t) => {
    const f = t < 0.028 ? expSweep(f0, f1, t / 0.028) : f1;
    ph += (TAU * f) / SR; ph2 += (TAU * f * 2.01) / SR;
    const e = env(t, 0.004, 0.045);
    return pan(l((Math.sin(ph) + 0.18 * Math.sin(ph2)) * e, 5000), pos);
  }), { mix: 0.14, tail: 0.35 });
};

// Glass tap: two bright partials, very short.
const tap = (f, pos = 0, seed = 1) => {
  const r = rng(seed); const h = hp1();
  let a = 0, b = 0;
  return reverb(render(0.18, (t) => {
    a += (TAU * f) / SR; b += (TAU * f * 1.5) / SR;
    const tone = (Math.sin(a) * env(t, 0.002, 0.05) + 0.4 * Math.sin(b) * env(t, 0.002, 0.03)) * 0.8;
    const click = h(r(), 4000) * env(t, 0.0005, 0.002) * 0.6;
    return pan(tone + click, pos);
  }), { mix: 0.2, tail: 0.4 });
};

// Air whoosh: noise through a moving band, asymmetric swell, stereo travel.
const air = (seed, dur, f0, fmid, f1, p0, p1, q = 1.1, peakAt = 0.6) => {
  const r = rng(seed); const bL = svf(), bR = svf(); const l1 = lp1(), l2 = lp1();
  let pink = 0;
  return reverb(render(dur, (t) => {
    const p = t / dur;
    const f = p < peakAt ? expSweep(f0, fmid, p / peakAt) : expSweep(fmid, f1, (p - peakAt) / (1 - peakAt));
    const a = p < peakAt ? Math.sin((Math.PI / 2) * (p / peakAt)) ** 2 : Math.cos((Math.PI / 2) * ((p - peakAt) / (1 - peakAt))) ** 1.5;
    pink = pink * 0.86 + r() * 0.14;
    const xL = bL(pink + r() * 0.05, f, q).bp, xR = bR(pink + r() * 0.05, f * 1.03, q).bp;
    const pp = lerp(p0, p1, p);
    const [gL, gR] = pan(1, pp);
    return [l1(xL * a * gL, 7000) * 2.2, l2(xR * a * gR, 7000) * 2.2];
  }), { mix: 0.16, tail: 0.5 });
};

// Soft thud: low sine drop + felt-like noise.
const thud = (seed, dur, f0, f1, body = 0.09, noise = 0.25) => {
  const r = rng(seed); const l = lp1();
  let ph = 0;
  return reverb(render(dur, (t) => {
    ph += (TAU * expSweep(f0, f1, t / 0.12)) / SR;
    const s = Math.sin(ph) * env(t, 0.003, body);
    const n = l(r(), 900) * env(t, 0.001, 0.025) * noise * 4;
    return s + n;
  }), { mix: 0.18, tail: 0.6, damp: 0.5 });
};

// Mallet note (marimba-ish): fundamental + 4th harmonic + a little 10th, quick decay.
const mallet = (f, t0, dec = 0.18) => (t) => {
  const u = t - t0;
  if (u < 0) return 0;
  const e = env(u, 0.002, dec);
  return (Math.sin(TAU * f * u) + 0.25 * Math.sin(TAU * f * 3.98 * u) * Math.exp(-u / 0.04) + 0.08 * Math.sin(TAU * f * 9.9 * u) * Math.exp(-u / 0.015)) * e;
};
const melody = (notes, dur, mixRev = 0.24, pos = 0) => {
  const voices = notes.map(([f, at, d]) => mallet(f, at, d));
  return reverb(render(dur, (t) => pan(voices.reduce((a, v) => a + v(t), 0) * 0.5, pos)), { mix: mixRev, tail: 0.8 });
};

// Soft bell for notifications (inharmonic partials, gentle).
const bell = (f, dur = 0.9) => {
  const parts = [[1, 1, 0.5], [2.01, 0.35, 0.3], [2.76, 0.25, 0.22], [5.4, 0.08, 0.1]];
  return reverb(render(dur, (t) => parts.reduce((a, [k, g, d]) => a + g * Math.sin(TAU * f * k * t) * env(t, 0.003, d), 0) * 0.5), { mix: 0.22, tail: 0.9 });
};

// Tiny tick for counters and keys.
const tick = (seed, f, len = 0.006, tone = 0.4) => {
  const r = rng(seed); const b = svf();
  return reverb(render(0.06, (t) => (b(r(), f, 2.5).bp * env(t, 0.0004, len) * 2 + Math.sin(TAU * f * 1.2 * t) * env(t, 0.0005, len * 1.5) * tone)), { mix: 0.1, tail: 0.2 });
};

// UI click: low "thock" + short high click.
const click = (seed, f) => {
  const r = rng(seed); const h = hp1();
  return reverb(render(0.09, (t) => Math.sin(TAU * f * t) * env(t, 0.001, 0.018) * 0.9 + h(r(), 3500) * env(t, 0.0003, 0.003) * 0.7), { mix: 0.12, tail: 0.25 });
};

// Riser: filtered noise opening up + sine glide, ending softly.
const riser = (seed, dur, f0, f1) => {
  const r = rng(seed); const b = svf(); const l = lp1();
  let ph = 0;
  return reverb(render(dur, (t) => {
    const p = t / dur;
    ph += (TAU * expSweep(f0, f1, p)) / SR;
    const a = Math.pow(p, 1.8) * (p > 0.94 ? (1 - p) / 0.06 : 1);
    return pan(l(b(r(), expSweep(300, 4000, p), 1.4).bp * 1.6 + Math.sin(ph) * 0.25, 8000) * a, lerp(-0.3, 0.3, p));
  }), { mix: 0.2, tail: 0.6 });
};

// Glitch: gated, pitched bursts.
const glitch = (seed, dur) => {
  const r = rng(seed); const h = (x) => { x = Math.imul(x ^ (x >>> 15), 2246822507); x = Math.imul(x ^ (x >>> 13), 3266489909); return ((x ^ (x >>> 16)) >>> 0) / 4294967296; };
  return render(dur, (t, i) => {
    const seg = Math.floor(t / 0.022);
    const on = h(seed * 997 + seg) > 0.45;
    const f = 200 + h(seed * 131 + seg) * 1800;
    return on ? (Math.sign(Math.sin(TAU * f * t)) * 0.35 + r() * 0.25) * Math.exp(-t / dur * 1.5) : 0;
  });
};

// ---------- the pack ----------
write("pop_01", bubble(420, 760, 0.16, -0.1));
write("pop_02", bubble(480, 860, 0.16, 0.1));
write("pop_03", bubble(380, 690, 0.16, 0));
write("tap_01", tap(1760, -0.15, 1));
write("tap_02", tap(1975.5, 0.15, 2));
write("tap_03", tap(1568, 0, 3));
write("whoosh_soft_01", air(11, 0.48, 280, 1900, 700, -0.5, 0.5));
write("whoosh_soft_02", air(12, 0.44, 320, 2200, 800, 0.5, -0.5));
write("whoosh_soft_03", air(13, 0.52, 250, 1700, 650, -0.3, 0.6));
write("swipe_fast_01", air(21, 0.24, 700, 4200, 2200, -0.6, 0.6, 1.4, 0.55));
write("swipe_fast_02", air(22, 0.22, 800, 4600, 2400, 0.6, -0.6, 1.4, 0.55));
write("swoosh_long_01", air(31, 1.0, 180, 2600, 500, -0.8, 0.8, 1.0, 0.55));
write("whoosh_reverse_01", air(41, 0.4, 2000, 900, 260, 0.4, -0.4, 1.1, 0.35));
write("riser_short_01", riser(51, 1.1, 180, 720));
write("riser_long_01", riser(52, 2.3, 120, 880));
write("blip_packet_01", tap(2349, -0.3, 4));
write("blip_packet_02", tap(2637, 0.3, 5));
write("tick_01", tick(61, 2600));
write("tick_02", tick(62, 2900));
write("tick_03", tick(63, 2400));
write("click_ui_01", click(71, 230));
write("click_ui_02", click(72, 210));
write("click_ui_03", click(73, 250));
write("land_square_01", thud(81, 0.4, 150, 75, 0.08, 0.22));
write("land_square_02", thud(82, 0.4, 165, 82, 0.075, 0.22));
write("impact_soft_01", thud(91, 0.9, 95, 42, 0.2, 0.3));
write("impact_soft_02", thud(92, 0.9, 85, 40, 0.22, 0.28));
write("confirm_01", melody([[880, 0, 0.16], [1318.5, 0.085, 0.22]], 0.55));
write("confirm_02", melody([[783.99, 0, 0.16], [1174.66, 0.085, 0.22]], 0.55));
write("reveal_sparkle_01", melody([[1318.5, 0, 0.12], [1568, 0.06, 0.12], [1975.5, 0.12, 0.14], [2637, 0.18, 0.2]], 0.8, 0.3));
write("deny_01", melody([[523.25, 0, 0.12], [440, 0.1, 0.18]], 0.5, 0.18));
write("notify_01", bell(1318.5));
write("notify_02", bell(1174.66));
for (let k = 1; k <= 6; k++) write(`key_0${k}`, tick(200 + k, 1900 + k * 140, 0.009, 0.15));
write("glitch_01", glitch(101, 0.3));
write("glitch_02", glitch(102, 0.22));
