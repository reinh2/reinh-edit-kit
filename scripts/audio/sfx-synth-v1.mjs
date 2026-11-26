// SFX pack v1: synthesised from scratch (noise, oscillators, filters), so we own every sound outright.
// Deterministic (seeded), 48 kHz / 24-bit stereo WAV, peak-normalised to −1 dBFS; mix level is set in the edit.
// Usage: node scripts/audio/sfx-synth-v1.mjs [OUT_DIR]   (default public/sfx/v1)
import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const SR = 48000;
const OUT = process.argv[2] ?? "public/sfx/v1";
mkdirSync(OUT, { recursive: true });

// ---------- building blocks ----------
const rng = (seed) => () => ((seed = (seed * 1664525 + 1013904223) >>> 0) / 4294967296) * 2 - 1;
const lerp = (a, b, p) => a + (b - a) * p;
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const expEnv = (t, a, d) => (t < a ? t / a : Math.exp(-(t - a) / d)); // attack then exponential decay
const bell = (p) => Math.sin(Math.PI * clamp(p)) ** 2; // smooth hump over 0..1
const expSweep = (f0, f1, p) => f0 * Math.pow(f1 / f0, clamp(p));

// State-variable filter (Chamberlin), returns {lp, bp, hp} per sample.
const svf = () => {
  let lp = 0, bp = 0;
  return (x, f, q = 0.7) => {
    const F = 2 * Math.sin((Math.PI * Math.min(f, SR / 6)) / SR);
    const hp = x - lp - bp / q;
    bp += F * hp;
    lp += F * bp;
    return { lp, bp, hp };
  };
};

// Render `dur` seconds; fn(t, i) returns [L, R] or a mono number.
const render = (dur, fn) => {
  const n = Math.round(dur * SR);
  const L = new Float32Array(n), R = new Float32Array(n);
  for (let i = 0; i < n; i++) {
    const v = fn(i / SR, i);
    if (Array.isArray(v)) { L[i] = v[0]; R[i] = v[1]; } else { L[i] = v; R[i] = v; }
  }
  return [L, R];
};
const pan = (x, p) => [x * Math.cos(((p + 1) * Math.PI) / 4), x * Math.sin(((p + 1) * Math.PI) / 4)]; // p −1..1, equal power

// Short room so dry synths do not sound "in a vacuum": a few early reflections, quiet.
const room = ([L, R], mix = 0.12) => {
  const taps = [[0.011, 0.5], [0.019, 0.35], [0.027, 0.25], [0.041, 0.15]];
  const tail = Math.round(0.08 * SR);
  const n = L.length + tail;
  const oL = new Float32Array(n), oR = new Float32Array(n);
  for (let i = 0; i < L.length; i++) { oL[i] += L[i]; oR[i] += R[i]; }
  for (const [d, g] of taps) {
    const k = Math.round(d * SR);
    for (let i = 0; i < L.length; i++) { oL[i + k] += R[i] * g * mix; oR[i + k + 7] = (oR[i + k + 7] ?? 0) + L[i] * g * mix; }
  }
  return [oL, oR.subarray(0, n)];
};

const write = (name, [L, R]) => {
  let peak = 1e-9;
  for (let i = 0; i < L.length; i++) peak = Math.max(peak, Math.abs(L[i]), Math.abs(R[i]));
  const g = Math.pow(10, -1 / 20) / peak;
  // 10 ms fade-out guard against clicks at the end.
  const fo = Math.min(L.length, Math.round(0.01 * SR));
  const n = L.length, bytes = 3, ch = 2;
  const buf = Buffer.alloc(44 + n * ch * bytes);
  buf.write("RIFF", 0); buf.writeUInt32LE(36 + n * ch * bytes, 4); buf.write("WAVE", 8);
  buf.write("fmt ", 12); buf.writeUInt32LE(16, 16); buf.writeUInt16LE(1, 20); buf.writeUInt16LE(ch, 22);
  buf.writeUInt32LE(SR, 24); buf.writeUInt32LE(SR * ch * bytes, 28); buf.writeUInt16LE(ch * bytes, 32); buf.writeUInt16LE(24, 34);
  buf.write("data", 36); buf.writeUInt32LE(n * ch * bytes, 40);
  let o = 44;
  for (let i = 0; i < n; i++) {
    const f = i >= n - fo ? (n - i) / fo : 1;
    for (const s of [L[i], R[i]]) {
      const v = Math.round(clamp(s * g * f, -1, 1) * 8388607);
      buf.writeIntLE(v, o, 3);
      o += 3;
    }
  }
  writeFileSync(join(OUT, `${name}.wav`), buf);
  console.log(`${name}.wav  ${(n / SR).toFixed(2)} s`);
};

// ---------- sounds ----------
// Whoosh: band-passed noise sweeping in pitch, smooth hump envelope, panned across.
const whoosh = (seed, dur, f0, f1, panFrom, panTo, q = 1.2, air = 0.25) => {
  const r = rng(seed), f = svf(), g = svf();
  return room(render(dur, (t) => {
    const p = t / dur;
    const e = bell(Math.pow(p, 0.8));
    const n = r();
    const body = f(n, expSweep(f0, f1, p), q).bp;
    const hiss = g(n, expSweep(f0 * 4, f1 * 3, p), 0.8).hp * air;
    return pan((body + hiss) * e, lerp(panFrom, panTo, p));
  }), 0.18);
};

// Pitched blip: sine with pitch glide and a hint of 2nd harmonic.
const blip = (dur, f0, f1, a = 0.002, d = 0.05, h2 = 0.15) => {
  let ph = 0;
  return room(render(dur, (t) => {
    const fr = expSweep(f0, f1, t / dur);
    ph += (2 * Math.PI * fr) / SR;
    return (Math.sin(ph) + h2 * Math.sin(2 * ph)) * expEnv(t, a, d);
  }));
};

// Click: very short filtered noise transient + tiny tonal body.
const click = (seed, fBody, fNoise, d = 0.012) => {
  const r = rng(seed), f = svf();
  let ph = 0;
  return room(render(0.08, (t) => {
    ph += (2 * Math.PI * fBody) / SR;
    const tr = f(r(), fNoise, 1.5).bp * expEnv(t, 0.0005, d * 0.5);
    return tr * 1.2 + Math.sin(ph) * expEnv(t, 0.001, d) * 0.5;
  }), 0.08);
};

// Low thump for landings and soft impacts: falling sine + a little noise.
const thump = (seed, dur, f0, f1, d, noise = 0.15) => {
  const r = rng(seed), f = svf();
  let ph = 0;
  return room(render(dur, (t) => {
    ph += (2 * Math.PI * expSweep(f0, f1, t / 0.12)) / SR;
    return Math.sin(ph) * expEnv(t, 0.002, d) + f(r(), 900, 0.8).lp * expEnv(t, 0.001, 0.02) * noise;
  }), 0.15);
};

// Chime: soft bell (sine partials) with gentle attack.
const chime = (notes, step, d = 0.35) => {
  const dur = step * (notes.length - 1) + d * 4;
  return room(render(dur, (t) => {
    let s = 0;
    notes.forEach((fr, k) => {
      const tt = t - k * step;
      if (tt < 0) return;
      const e = expEnv(tt, 0.004, d);
      s += (Math.sin(2 * Math.PI * fr * tt) + 0.25 * Math.sin(2 * Math.PI * fr * 2.01 * tt) * Math.exp(-tt / (d * 0.4))) * e;
    });
    return s;
  }), 0.2);
};

// Riser: noise band and a sine both gliding up, swelling to the end.
const riser = (seed, dur, f0, f1) => {
  const r = rng(seed), f = svf();
  let ph = 0;
  return room(render(dur, (t) => {
    const p = t / dur;
    const e = Math.pow(p, 2.2) * (1 - clamp((p - 0.97) / 0.03));
    ph += (2 * Math.PI * expSweep(f0, f1, p)) / SR;
    return pan(f(r(), expSweep(f0 * 3, f1 * 4, p), 2).bp * e * 0.9 + Math.sin(ph) * e * 0.35, Math.sin(p * 6) * 0.15);
  }), 0.2);
};

// Glitch: short bursts of bit-crushed, sample-held noise and tone.
const glitch = (seed, dur) => {
  const r = rng(seed);
  let hold = 0, held = 0, ph = 0;
  return render(dur, (t, i) => {
    const seg = Math.floor(t / 0.035);
    const on = (Math.imul(seg + seed, 2654435761) >>> 0) % 5 !== 0; // hashed: ~4 of 5 segments sound
    if (i % (6 + (seg % 5) * 4) === 0) held = r();
    ph += (2 * Math.PI * (300 + (seg % 7) * 180)) / SR;
    const tone = Math.sign(Math.sin(ph)) * 0.4;
    const s = on ? Math.round((held * 0.8 + tone) * 6) / 6 : 0;
    hold = s;
    return pan(hold * expEnv(t, 0.002, dur * 0.6), (seg % 3) - 1);
  });
};

// Key press: tiny noise burst with random brightness (several variants for rotation).
const key = (seed) => {
  const r = rng(seed), f = svf();
  const fc = 2200 + (rng(seed * 7)() + 1) * 1400;
  return room(render(0.06, (t) => f(r(), fc, 1.8).bp * expEnv(t, 0.0004, 0.008) + f(r(), 400, 1).lp * expEnv(t, 0.001, 0.006) * 0.4), 0.06);
};

// ---------- the pack ----------
// Transitions
write("whoosh_soft_01", whoosh(11, 0.55, 350, 2400, -0.6, 0.6));
write("whoosh_soft_02", whoosh(12, 0.5, 300, 2000, 0.5, -0.5));
write("whoosh_soft_03", whoosh(13, 0.6, 420, 2800, -0.3, 0.7));
write("swipe_fast_01", whoosh(21, 0.24, 900, 5200, -0.7, 0.7, 1.6, 0.35));
write("swipe_fast_02", whoosh(22, 0.22, 1100, 6000, 0.7, -0.7, 1.6, 0.35));
write("swoosh_long_01", whoosh(31, 1.1, 180, 3200, -0.8, 0.8, 1.0, 0.2));
write("whoosh_reverse_01", whoosh(41, 0.7, 2600, 300, 0.4, -0.4));
write("riser_short_01", riser(51, 1.2, 180, 900));
write("riser_long_01", riser(52, 2.4, 120, 1100));
// Morphs / UI motion
write("pop_01", blip(0.12, 720, 380, 0.002, 0.04));
write("pop_02", blip(0.12, 820, 420, 0.002, 0.035));
write("pop_03", blip(0.12, 640, 330, 0.002, 0.045));
write("blip_packet_01", blip(0.09, 1650, 1550, 0.003, 0.025, 0.05));
write("blip_packet_02", blip(0.09, 1850, 1750, 0.003, 0.022, 0.05));
write("tick_01", click(61, 2400, 6000, 0.01));
write("tick_02", click(62, 2200, 5500, 0.01));
write("tick_03", click(63, 2600, 6500, 0.009));
write("click_ui_01", click(71, 1200, 3500, 0.018));
write("click_ui_02", click(72, 1050, 3200, 0.02));
write("click_ui_03", click(73, 1350, 3800, 0.016));
write("land_square_01", thump(81, 0.45, 160, 70, 0.09, 0.2));
write("land_square_02", thump(82, 0.45, 180, 80, 0.08, 0.2));
write("impact_soft_01", thump(91, 0.9, 110, 42, 0.22, 0.35));
write("impact_soft_02", thump(92, 0.9, 95, 38, 0.26, 0.3));
// Results and states
write("confirm_01", chime([1318.5, 1975.5], 0.09));
write("confirm_02", chime([1046.5, 1568], 0.08));
write("reveal_sparkle_01", chime([1568, 2093, 2637, 3136], 0.045, 0.18));
write("deny_01", chime([392, 311.1], 0.11, 0.18));
write("glitch_01", glitch(101, 0.3));
write("glitch_02", glitch(102, 0.22));
// Typing (rotate variants per keystroke)
for (let k = 1; k <= 6; k++) write(`key_0${k}`, key(200 + k * 13));
