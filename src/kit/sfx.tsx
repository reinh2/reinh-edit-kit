// Sound map for Remotion: motion events → SFX files. The packs are synthesised by scripts/audio/sfx-synth-v*.mjs into
// public/sfx/<pack> (`npm run sfx`), so every sound is ours and free to use. Rules: docs/MUSIC_AND_SFX.md.
// Variants rotate deterministically, so the same sample never plays twice in a row.
import React from "react";
import { Audio, Sequence, staticFile, useVideoConfig } from "remotion";

export type SfxEvent =
  | "scene-in" // full-screen insert enters, an element opens into a card/panel
  | "swipe" // chart/slide swap inside an insert
  | "theme-wipe" // light ↔ dark theme, chapter
  | "collapse" // element shrinks back / leaves
  | "build-short" // 1 s lead-in to a reveal
  | "build-long" // the one big build of a video
  | "pop" // badge, chip, icon appears
  | "packet" // packet on a flow graph, cursor dot
  | "tick" // counter steps, clock hand
  | "click" // cursor click, button, toggle
  | "land" // an accent element lands with a settle
  | "impact" // big number / conclusion (≤ 2 per video)
  | "confirm" // success
  | "sparkle" // beautiful result revealed
  | "deny" // error, fail, strike-through
  | "glitch" // agent breaks, bug
  | "key" // typing, rotate per keystroke
  | "tap" // a chip or tag appears
  | "notify"; // CTA, notification card

const FILES: Record<SfxEvent, string[]> = {
  "scene-in": ["whoosh_soft_01", "whoosh_soft_02", "whoosh_soft_03"],
  swipe: ["swipe_fast_01", "swipe_fast_02"],
  "theme-wipe": ["swoosh_long_01"],
  collapse: ["whoosh_reverse_01"],
  "build-short": ["riser_short_01"],
  "build-long": ["riser_long_01"],
  pop: ["pop_01", "pop_02", "pop_03"],
  packet: ["blip_packet_01", "blip_packet_02"],
  tick: ["tick_01", "tick_02", "tick_03"],
  click: ["click_ui_01", "click_ui_02", "click_ui_03"],
  land: ["land_square_01", "land_square_02"],
  impact: ["impact_soft_01", "impact_soft_02"],
  confirm: ["confirm_01", "confirm_02"],
  sparkle: ["reveal_sparkle_01"],
  deny: ["deny_01"],
  glitch: ["glitch_01", "glitch_02"],
  key: ["key_01", "key_02", "key_03", "key_04", "key_05", "key_06"],
  tap: ["tap_01", "tap_02", "tap_03"],
  notify: ["notify_01", "notify_02"],
};

// Default mix gain (dB, relative to the −1 dBFS-normalised file) so SFX sit 6–10 dB under the voice.
export const SFX_GAIN_DB: Record<SfxEvent, number> = {
  "scene-in": -14, swipe: -15, "theme-wipe": -13, collapse: -15, "build-short": -14, "build-long": -12,
  pop: -16, packet: -20, tick: -22, click: -16, land: -12, impact: -10, confirm: -14, sparkle: -16,
  deny: -14, glitch: -16, key: -24, tap: -18, notify: -16,
};

export const PACK = "v2";
export const dbToGain = (db: number) => Math.pow(10, db / 20);

// `n` = index of this occurrence of the event in the video (0, 1, 2…), so consecutive uses rotate variants.
export const sfx = (event: SfxEvent, n = 0) => {
  const list = FILES[event];
  return { src: staticFile(`sfx/${PACK}/${list[n % list.length]}.wav`), volume: dbToGain(SFX_GAIN_DB[event]) };
};

// Audio leads the visual peak by 2 frames: start = visualFrame − SFX_LEAD_FRAMES.
export const SFX_LEAD_FRAMES = 2;

export const Sfx: React.FC<{ at: number; ev: SfxEvent; n?: number; gainDb?: number }> = ({ at, ev, n = 0, gainDb = 0 }) => {
  const { fps } = useVideoConfig();
  const s = sfx(ev, n);
  const from = Math.max(0, Math.round(at * fps) - SFX_LEAD_FRAMES);
  return (
    <Sequence from={from} layout="none" name={`sfx:${ev}`}>
      <Audio src={s.src} volume={s.volume * dbToGain(gainDb)} />
    </Sequence>
  );
};
