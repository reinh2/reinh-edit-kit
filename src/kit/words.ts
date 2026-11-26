// Word anchors: graphics and SFX are tied to spoken words, not to seconds typed by hand, so a re-cut never breaks
// an insert. Words come from whisper.cpp (scripts/edit/short_cut.py → words.json, or make_srt --words).
export type Word = { w: string; start: number; end: number; seg?: number };

const norm = (s: string) => s.toLowerCase().replace(/ё/g, "е").replace(/[^\p{L}\p{N}]/gu, "");

// Start time (s) of the n-th (0-based) occurrence of `word` at or after `after` seconds. Throws if missing, so a
// broken anchor fails the render instead of silently landing at 0.
export const T = (words: Word[], word: string, n = 0, after = 0): number => {
  const key = norm(word);
  const hits = words.filter((x) => x.start >= after && norm(x.w).startsWith(key));
  if (!hits[n]) throw new Error(`word «${word}» #${n} not found after ${after}s`);
  return hits[n].start;
};
