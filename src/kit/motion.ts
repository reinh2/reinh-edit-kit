// Motion helpers: easing, tweens, splines, damped impulses, seeded random. Pure functions of time,
// so every frame renders the same after any seek. Times are in seconds.

export const clamp01 = (x: number) => Math.min(1, Math.max(0, x));
export const lerp = (a: number, b: number, p: number) => a + (b - a) * p;

export const ease = {
  linear: (t: number) => t,
  // Entrances: fast start, long soft settle (≈ cubic-bezier(0.16, 1, 0.3, 1)).
  outExpo: (t: number) => (t >= 1 ? 1 : 1 - Math.pow(2, -10 * t)),
  outCubic: (t: number) => 1 - Math.pow(1 - t, 3),
  // Exits.
  inCubic: (t: number) => t * t * t,
  // Camera moves and morphs.
  inOutCubic: (t: number) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2),
  // Gentle overshoot (~3 %), within the style guide's 4 % limit.
  outBack: (t: number) => {
    const c1 = 0.9;
    const c3 = c1 + 1;
    return 1 + c3 * Math.pow(t - 1, 3) + c1 * Math.pow(t - 1, 2);
  },
};

// Eased progress of a tween that starts at `start` and lasts `dur` seconds.
export const prog = (t: number, start: number, dur: number, fn: (x: number) => number = ease.outExpo) => fn(clamp01((t - start) / dur));

// Damped oscillation after an event: 0 before `at`, peaks right after, decays in ~0.4 s.
export const impulse = (t: number, at: number, freq = 16, decay = 9) => {
  const u = t - at;
  if (u < 0) return 0;
  return Math.exp(-decay * u) * Math.cos(freq * u);
};

// Damped settle towards a target: value(t) after a step at `at` from `from` to `to` (spring-like, no overshoot > 6 %).
export const settle = (t: number, at: number, from: number, to: number, freq = 9, decay = 5.5) => {
  const u = t - at;
  if (u <= 0) return from;
  return to + (from - to) * Math.exp(-decay * u) * Math.cos(freq * u);
};

// Deterministic pseudo-random in [0, 1) from an integer seed.
export const rnd = (seed: number) => {
  const x = Math.sin(seed * 127.1 + 311.7) * 43758.5453;
  return x - Math.floor(x);
};

// Typewriter: number of characters visible at time t, with seeded jitter (≈ cps chars/second).
export const typed = (t: number, at: number, text: string, cps = 26, seed = 1) => {
  if (t < at) return 0;
  let acc = at;
  for (let i = 0; i < text.length; i++) {
    acc += (1 / cps) * (0.7 + 0.6 * rnd(seed * 1000 + i)) * (text[i] === " " ? 0.6 : 1);
    if (acc > t) return i;
  }
  return text.length;
};
