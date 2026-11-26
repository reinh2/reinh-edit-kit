#!/usr/bin/env python3
"""Find «phantom frames» in a render (a human reviewer once found ten of them by eye in one long draft).

A phantom frame is picture content that is on screen for only a few frames between two cuts: A → B (≤ --max frames) → C,
where B differs strongly from both A and C. Typical causes: a dissolve that reveals a shot hidden under an insert, a panel
that changes right after a card, a shot sliver left by an L-cut. Gradual dissolves are not flagged (each frame differs
only a little from the previous one).

Every frame is reduced to a 48×27 grey thumbnail (ffmpeg → raw bytes, pure Python). A «cut» is a frame-to-frame mean
absolute difference above --cut. Two cuts closer than --max frames, with the picture after the second cut not simply
returning to the one before the first, are reported with the time and a strip of thumbnails for checking.
Usage: python3 scripts/qc/ghost_frames.py film.mp4 [--max 10] [--cut 18] [--out work/x/ghosts]
"""
import argparse, json, os, subprocess

W, Hh = 48, 27


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video"); ap.add_argument("--max", type=int, default=10); ap.add_argument("--cut", type=float, default=12.0)
    ap.add_argument("--out")
    a = ap.parse_args()
    fps = eval(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate", "-of", "csv=p=0", a.video], capture_output=True, text=True).stdout.strip())
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", a.video, "-vf", f"scale={W}:{Hh}:flags=area,format=gray", "-f", "rawvideo", "-"], capture_output=True).stdout
    n = W * Hh
    fr = [raw[i:i + n] for i in range(0, len(raw) - n + 1, n)]
    d = lambda x, y: sum(abs(p - q) for p, q in zip(x, y)) / n
    diffs = [0.0] + [d(fr[i - 1], fr[i]) for i in range(1, len(fr))]
    # A frame B is «foreign» when it is far from both the picture K frames earlier (A) and K frames later (C) by more than
    # a blend of the two could be: d(A,B) + d(B,C) clearly above d(A,C). A dissolve from A to C stays on the line between
    # them (sum ≈ d(A,C)); a phantom frame — a shot glimpsed under a fading card — is off that line.
    K = a.max
    score = [0.0] * len(fr)
    for i in range(K, len(fr) - K):
        A, B, C = fr[i - K], fr[i], fr[i + K]
        dab, dbc, dac = d(A, B), d(B, C), d(A, C)
        if dab > a.cut and dbc > a.cut:
            score[i] = dab + dbc - 1.4 * dac
    cuts = [i for i, v in enumerate(diffs) if v > a.cut]
    found, i = [], 0
    while i < len(fr):
        if score[i] > a.cut:
            j = i
            while j + 1 < len(fr) and score[j + 1] > a.cut:
                j += 1
            k = max(range(i, j + 1), key=lambda q: score[q])
            found.append({"t": round(k / fps, 3), "frames": j - i + 1, "kind": "foreign", "d_in": round(score[k], 1), "d_out": 0})
            i = j + 1
        else:
            i += 1
    print(f"{len(fr)} frames, {len(cuts)} cuts, {len(found)} phantom candidates")
    for f in found:
        m, s = divmod(f["t"], 60)
        print(f"  {int(m)}:{s:05.2f}  {f['kind']:6} {f['frames']:2d} fr  in {f['d_in']} out {f['d_out']}")
    if a.out:
        os.makedirs(a.out, exist_ok=True)
        json.dump(found, open(f"{a.out}/ghosts.json", "w"), indent=1)
        for f in found[:60]:
            t0 = max(0, f["t"] - 3 / fps)
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t0:.3f}", "-i", a.video, "-vf", "scale=240:-2,tile=16x1", "-frames:v", "1", f"{a.out}/g_{f['t']:08.3f}.jpg"])


if __name__ == "__main__":
    main()
