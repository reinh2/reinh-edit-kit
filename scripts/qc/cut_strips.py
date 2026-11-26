#!/usr/bin/env python3
"""Dense strips around every cut of a timeline (kit-qc «плёнки на переходах»): for each video event boundary,
frames at −0.20, −0.10, −0.03, +0.03, +0.10, +0.20 s, one row per cut, sheets of N rows with the time printed
in the file list (cuts.txt), so it works with FFmpeg builds without drawtext.
Usage: python3 scripts/qc/cut_strips.py render.mp4 timeline.json out_dir [--rows 12] [--width 320]"""
import argparse, json, os, subprocess

ap = argparse.ArgumentParser()
ap.add_argument("video"); ap.add_argument("timeline"); ap.add_argument("out")
ap.add_argument("--rows", type=int, default=12); ap.add_argument("--width", type=int, default=320)
a = ap.parse_args()
os.makedirs(a.out, exist_ok=True)
with open(a.timeline) as f:
    tl = json.load(f)
fps = tl["fps"]
cuts = sorted({v["from"] for v in tl["video"] if v["from"] > 0} | {o["from"] for o in tl["overs"]} | {o["from"] + o["dur"] for o in tl["overs"]})
offs = [-0.20, -0.10, -0.03, 0.03, 0.10, 0.20]
listing = []
for si in range(0, len(cuts), a.rows):
    chunk = cuts[si:si + a.rows]
    frames = []
    for c in chunk:
        t = c / fps
        listing.append(f"sheet {si // a.rows + 1:02d} row {len(frames) // len(offs) + 1:02d}: cut at {int(t // 60)}:{t % 60:05.2f}")
        for o in offs:
            p = f"{a.out}/_f{len(frames):03d}.png"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{max(0, t + o):.3f}", "-i", a.video, "-frames:v", "1", "-vf", f"scale={a.width}:-2", p], check=True)
            frames.append(p)
    n = len(frames)
    h = int(a.width * 9 / 16)
    lay = "|".join(f"{(k % len(offs)) * a.width}_{(k // len(offs)) * h}" for k in range(n))
    args = sum([["-i", p] for p in frames], [])
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args, "-filter_complex", "".join(f"[{k}]" for k in range(n)) + f"xstack=inputs={n}:layout={lay}",
                    f"{a.out}/cuts_{si // a.rows + 1:02d}.jpg"], check=True)
    for p in frames:
        os.remove(p)
open(f"{a.out}/cuts.txt", "w").write("\n".join(listing) + "\n")
print(f"{len(cuts)} cuts → {a.out}")
