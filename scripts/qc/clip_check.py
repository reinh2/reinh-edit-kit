#!/usr/bin/env python3
"""Check every voice clip of a timeline before the render (docs/EDIT_STANDARD.md §1):
  - transcribe each clip ALONE without a prompt (slips, fragments of other takes, repeats, a cut-off last word);
  - RMS of 40 ms just outside / first / last / just after the clip: speech louder than ≈ −40 dBFS outside the edge
    means the cut is inside a word — move the edge into the nearest dip.
Usage: python3 scripts/qc/clip_check.py work/<video>/timeline.json [--public public] [--handle 0.8] [--only A1 B] [--lang ru]
Prints one line per clip to stdout; clips whose audio is a ready insert (src containing «cine») are skipped.
Language and model default to kit.config.json."""
import argparse, array, json, math, os, subprocess, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import _kit  # noqa: E402

C = _kit.cfg()

ap = argparse.ArgumentParser()
ap.add_argument("timeline"); ap.add_argument("--public", default="public"); ap.add_argument("--handle", type=float, default=0.8)
ap.add_argument("--model", default=_kit.path(C["whisperModel"])); ap.add_argument("--only", nargs="*")
ap.add_argument("--lang", default=C["language"])
a = ap.parse_args()
with open(a.timeline) as f:
    tl = json.load(f)
fps = tl["fps"]; tmp = tempfile.mkdtemp()


def rms(src, t0, d):
    if t0 < 0:
        return -99
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t0:.3f}", "-t", f"{d:.3f}", "-i", src, "-ac", "1", "-ar", "16000", "-f", "s16le", "-"],
                         capture_output=True).stdout
    x = array.array("h", pcm)
    return round(20 * math.log10(math.sqrt(sum(v * v for v in x) / max(1, len(x))) / 32768 + 1e-9)) if x else -99


for i, c in enumerate(tl["audio"]):
    if "cine" in c["src"] or (a.only and c["piece"] not in a.only):
        continue
    src = os.path.join(a.public, c["src"]); s0 = c["startFrom"] / fps; d = c["dur"] / fps
    w = f"{tmp}/c{i}"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{s0:.3f}", "-t", f"{d:.3f}", "-i", src, "-ac", "1", "-ar", "16000", "-af", "apad=pad_dur=0.6", w + ".wav"], check=True)
    subprocess.run(["whisper-cli", "-m", a.model, "-f", w + ".wav", "-l", a.lang, "-otxt", "-of", w, "-np", "-nt"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    txt = open(w + ".txt").read().strip().replace("\n", " ") if os.path.exists(w + ".txt") else ""
    e = [rms(src, s0 - 0.04, 0.04), rms(src, s0, 0.04), rms(src, s0 + d - 0.04, 0.04), rms(src, s0 + d, 0.04)]
    warn = " ⚠ edge" if e[0] > -40 or e[3] > -40 else ""
    print(f"{i:02d} {c['piece']}:{c.get('clip', 0)} @{c['from'] / fps:7.2f}s local {s0 - a.handle:.2f}–{s0 - a.handle + d:.2f} "
          f"edges[before {e[0]} | in {e[1]} … out {e[2]} | after {e[3]}]{warn} | {txt}", flush=True)
