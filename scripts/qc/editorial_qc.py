#!/usr/bin/env python3
"""Editorial QC of a rendered video — the checks a technical QC (loudness, frames) misses on a badly edited cut:

  pauses    silences in the final mix longer than --pause s (default 0.9) — dead air the viewer hears
  static    stretches where the picture hardly changes for longer than --static s (default 8) — «frozen» screen demos
  flashes   short bright spikes (dark → light → dark within 0.6 s) and single-frame luma jumps > 110 — unintended flashes
  black     black frames (luma < 10) that are not the very start or the final fade-out
  levels    loudness jumps across voice cuts (momentary loudness 0.6 s before vs after an edit point) > 4 LU

It only measures. Every finding is a candidate: an editor decides whether it is intended (a chapter card hit,
a deliberate beat) and writes the decision into the QC report. Intervals inside --ignore ranges are skipped.

Usage:
  python3 scripts/qc/editorial_qc.py exports/x.mp4 --timeline work/x/timeline.json --out work/x/qc_editorial
    --timeline   optional: edit points (voice clip joins) for the level check, insert ranges to ignore for pauses
Writes <out>.json and <out>.md; exit code 1 if any finding is not covered by --allow (a JSON list of [t0, t1, kind, reason]).
Requires ffmpeg only (no numpy).
"""
import argparse, json, re, subprocess, sys


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True).stderr


def series(path, vf):
    """per-frame YAVG of the given filter chain → [(t, v)]"""
    out = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-an", "-vf", vf + ",signalstats,metadata=print:key=lavfi.signalstats.YAVG:file=-",
                          "-f", "null", "-"], capture_output=True, text=True).stdout
    res, t = [], None
    for l in out.splitlines():
        m = re.search(r"pts_time:([\d.]+)", l)
        if m:
            t = float(m.group(1))
        m = re.search(r"YAVG=([\d.]+)", l)
        if m and t is not None:
            res.append((t, float(m.group(1))))
    return res


def hms(t):
    m, s = divmod(t, 60)
    return f"{int(m)}:{s:05.2f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--out", required=True)
    ap.add_argument("--timeline")
    ap.add_argument("--pause", type=float, default=0.9)
    ap.add_argument("--static", type=float, default=10.0)
    ap.add_argument("--floor", type=float, default=-42.0, help="pause threshold, dBFS RMS (master at −15 LUFS)")
    ap.add_argument("--allow", help="JSON file: [[t0, t1, kind, reason], …] findings decided as intended")
    a = ap.parse_args()
    F = []  # findings: {kind, t0, t1, value, note}

    tl = json.load(open(a.timeline)) if a.timeline else None
    fps = tl["fps"] if tl else 60
    inserts = [(v["from"] / fps, (v["from"] + v["dur"]) / fps) for v in tl["video"] if v["kind"] == "insert"] if tl else []
    in_insert = lambda t0, t1: any(a0 - 0.05 <= t0 and t1 <= b0 + 0.05 for a0, b0 in inserts)

    # pauses: 20 ms RMS of the final mix (sample-peak detectors break on every click); a pause = RMS below
    # --floor dBFS for longer than --pause s, ignoring blips ≤ 60 ms (clicks, breaths' edges)
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", a.video, "-vn", "-ac", "1", "-ar", "8000", "-f", "s16le", "-"], capture_output=True).stdout
    import array, math
    x = array.array("h", pcm)
    hop = 160  # 20 ms
    rms = []
    for i in range(0, len(x) - hop, hop):
        acc = 0
        for v in x[i:i + hop]:
            acc += v * v
        rms.append(20 * math.log10(math.sqrt(acc / hop) / 32768 + 1e-9))
    quiet = [v < a.floor for v in rms]
    i, n = 0, len(quiet)
    while i < n:
        if quiet[i]:
            j, blip = i, 0
            while j < n and (quiet[j] or blip < 3):
                blip = 0 if quiet[j] else blip + 1
                j += 1
            j -= blip
            t0, t1 = i * 0.02, j * 0.02
            if t1 - t0 >= a.pause and not in_insert(t0, t1):
                F.append({"kind": "pause", "t0": round(t0, 2), "t1": round(t1, 2), "value": round(t1 - t0, 2), "note": f"RMS < {a.floor:.0f} dBFS"})
            i = j + 1
        else:
            i += 1

    # picture: luma + frame difference at 320 px
    luma = series(a.video, "scale=320:-2")
    diff = series(a.video, "scale=320:-2,tblend=all_mode=difference")
    dur = luma[-1][0] if luma else 0
    # black frames
    run_b = None
    for t, v in luma:
        if v < 10 and 0.2 < t < dur - 1.0:
            run_b = run_b or t
        elif run_b is not None:
            F.append({"kind": "black", "t0": run_b, "t1": t, "value": round(t - run_b, 3), "note": "luma < 10"})
            run_b = None
    # flashes: a bright spike that returns within 0.6 s, or a single-frame jump > 110
    L = luma
    for i in range(1, len(L)):
        t, v = L[i]
        if abs(v - L[i - 1][1]) > 110:
            F.append({"kind": "jump", "t0": L[i - 1][0], "t1": t, "value": round(v - L[i - 1][1], 1), "note": "single-frame luma jump"})
    i = 0
    while i < len(L):
        t, v = L[i]
        base = L[max(0, i - 3)][1]
        if v - base > 60:
            j = i
            while j < len(L) and L[j][0] - t < 0.6:
                j += 1
            back = [x for x in L[i:j] if x[1] - base < 25]
            if back:
                F.append({"kind": "flash", "t0": t, "t1": back[0][0], "value": round(max(x[1] for x in L[i:j]) - base, 1), "note": "dark → light → dark < 0.6 s"})
                i = j
                continue
        i += 1
    # contrast swings: dark → light plateau (+100) → dark again within 2 s (e.g. a light page between dark scenes)
    k = 0
    while k < len(L):
        t, v = L[k]
        prev = min(y[1] for y in L[max(0, k - 20):k + 1])  # darkest of the last ~0.3 s
        if v - prev > 100:
            j = k
            while j < len(L) and L[j][0] - t < 2.0 and L[j][1] - prev > 60:
                j += 1
            if j < len(L) and L[j][0] - t < 2.0 and not any(f["kind"] == "flash" and abs(f["t0"] - t) < 0.3 for f in F):
                F.append({"kind": "swing", "t0": t, "t1": L[j][0], "value": round(max(y[1] for y in L[k:j]) - prev, 1), "note": "dark → light → dark < 2 s"})
            k = j + 1
            continue
        k += 1
    # static stretches: rolling 1 s mean of frame difference below 0.35
    win = []
    st_start = None
    for t, v in diff:
        win.append((t, v))
        while win and t - win[0][0] > 1.0:
            win.pop(0)
        m = sum(x[1] for x in win) / len(win)
        if v > 8:  # a cut, punch-in or reframe ends a static stretch even if the 1 s mean stays low
            if st_start is not None and t - st_start > a.static:
                F.append({"kind": "static", "t0": st_start, "t1": t, "value": round(t - st_start, 1), "note": "picture hardly changes"})
            st_start, win = None, []
            continue
        if m < 0.35:
            st_start = st_start if st_start is not None else max(0.0, t - 1.0)
        else:
            if st_start is not None and t - st_start > a.static:
                F.append({"kind": "static", "t0": st_start, "t1": t, "value": round(t - st_start, 1), "note": "picture hardly changes"})
            st_start = None
    if st_start is not None and dur - st_start > a.static:
        F.append({"kind": "static", "t0": st_start, "t1": dur, "value": round(dur - st_start, 1), "note": "picture hardly changes"})

    # loudness steps at voice edit points
    if tl:
        mom = []
        s = run(["ffmpeg", "-v", "info", "-i", a.video, "-vn", "-af", "ebur128=framelog=verbose", "-f", "null", "-"])
        for l in s.splitlines():
            m = re.search(r"t:\s*([\d.]+)\s+TARGET.*?M:\s*(-?[\d.]+)", l)
            if m:
                mom.append((float(m.group(1)), float(m.group(2))))
        def med(t0, t1):
            xs = sorted(v for t, v in mom if t0 <= t <= t1 and v > -40)
            return xs[len(xs) // 2] if len(xs) >= 3 else None
        for c in tl["audio"][1:]:
            t = c["from"] / fps
            before, after = med(t - 0.8, t - 0.1), med(t + 0.4, t + 1.1)
            if before is not None and after is not None and abs(after - before) > 4:
                F.append({"kind": "level", "t0": t - 0.8, "t1": t + 1.1, "value": round(after - before, 1), "note": "momentary loudness step across a cut"})

    # with a timeline, a talking-head stretch is judged by the face limit (12 s, docs/EDIT_STANDARD.md §2):
    # natural speech on one framing is not «frozen» until then; screens and inserts keep --static
    if tl:
        def kind_at(t):
            for v in tl["video"]:
                if v["from"] / fps <= t < (v["from"] + v["dur"]) / fps:
                    return v["kind"]
            return None
        F = [f for f in F if not (f["kind"] == "static" and kind_at((f["t0"] + f["t1"]) / 2) == "face" and f["value"] <= 12.5)]
    allow = json.load(open(a.allow)) if a.allow else []
    def allowed(f):
        for t0, t1, kind, why in allow:
            if kind == f["kind"] and t0 - 0.2 <= f["t0"] and f["t1"] <= t1 + 0.2:
                return why
        return None
    for f in F:
        f["allowed"] = allowed(f)
    F.sort(key=lambda f: f["t0"])
    json.dump({"video": a.video, "duration": dur, "findings": F}, open(a.out + ".json", "w"), ensure_ascii=False, indent=1)
    open_f = [f for f in F if not f["allowed"]]
    md = [f"# Editorial QC - {a.video}", "", f"Duration {hms(dur)}. Findings: {len(F)}, open: {len(open_f)}.", "",
          "| time | kind | value | note | decision |", "|---|---|---|---|---|"]
    for f in F:
        md.append(f"| {hms(f['t0'])}-{hms(f['t1'])} | {f['kind']} | {f['value']} | {f['note']} | {f['allowed'] or 'OPEN'} |")
    open(a.out + ".md", "w").write("\n".join(md) + "\n")
    print("\n".join(md))
    sys.exit(1 if open_f else 0)


if __name__ == "__main__":
    main()
