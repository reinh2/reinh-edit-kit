#!/usr/bin/env python3
"""EDL → frame-exact timeline + editorial check.

Why: an early rough cut of a real long video laid whole takes end to end — 6 s pauses, a repeated take, 94 s of one
static screen shot — and still passed the technical QC (loudness, frames). This script is the one place that turns an
editorial EDL into output timecodes, so the same numbers drive the Remotion composition, the EDL table for a human
and the editorial check.

Layout: the EDL lives at <root>/projects/<video>/edl.json and `base` is a path relative to <root>.
Example: examples/edl/ (python3 scripts/edit/edl_timeline.py examples/edl/projects/demo/edl.json --out /tmp/tl.json).

EDL format:
  base        source info per piece id: obs (recording start clock «HH-MM-SS»), in_s (piece start in that
              recording, s), dur; optionally phone, phone_in (camera file and its offset).
              kind cine = a ready-made clip: file + audio instead of a recording
  pieces[]    {id, kind face|screen|cine, clips [[a,b,reason]], views [[t,face|screen]], cams [[t,cx,cy,w,dur]],
               punch [[t,why]], push [[a,b,z0,z1,why], …] (slow push-in z1>z0 / pull-out z1<z0 over a face run)}  — all times local to base in_s (seconds)
  gaps[]      {after, d, el}       full-screen inserts that add time (chapter cards…)
  overs[]     {piece, at, d|to, el, beats{}, overlay}  cutaways over running voice (hero cards, animated inserts),
               anchored to piece-local time; `to` = local end (output length is computed across jump cuts);
               `beats` = piece-local word times → seconds from the insert start (props.b for the component);
               `overlay` = drawn over the running shot (face stays visible) — not counted as a cut
  nolcut      piece flag: no L-cut at its joins (a cutaway that runs to the piece end would leave a 0.3 s sliver)
  panels      per piece [[t, x, y, w, h, caption, 1=no entrance]]: from t the screen is shown as a framed fragment
               (w = 0 → back to the camera view); passed through to the timeline for the composition
  gaps[].dip  dip to dark into this insert
  media       folder under public/ with <id>_{face,screen}.mp4 and <id>_voice.wav (default «media»)
  fps, handle, faceZoom [base, punched], lcut (s the screen picture overlaps the face audio at face↔screen joins)

Output: timeline JSON (video/audio/overs events in frames + seconds) and a Markdown editorial report:
  every shot (view + framing) with its length, flags for long static shots, long face runs, short flashes.

Usage:
  python3 scripts/edit/edl_timeline.py projects/<video>/edl.json --out work/<video>/timeline.json \
      --report work/<video>/editorial.md
Limits (editorial, from docs/EDIT_STANDARD.md): face shot without a change ≤ 12 s, screen framing
held ≤ 8 s (≤ 6 s for a wide, unzoomed screen), any shot ≥ 0.6 s (shorter only for deliberate inserts).
"""
import argparse, json, os, sys

LIMITS = {"face": 12.0, "screen": 8.0, "screen_wide": 6.0, "min": 0.6}


def hms(t):
    m, s = divmod(t, 60)
    return f"{int(m)}:{s:05.2f}"


def build(edl_path):
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(edl_path))))
    with open(edl_path) as f:
        E = json.load(f)
    with open(os.path.join(root, E["base"])) as f:
        base = {s["id"]: s for s in json.load(f)["segments"]}
    fps, H, (Z0, Z1), L = E["fps"], E["handle"], E["faceZoom"], E.get("lcut", 0.0)
    media = E.get("media", "media")
    hh, mm, ss = map(int, E.get("clockStart", "0:0:0").split(":"))
    START = hh * 3600 + mm * 60 + ss
    F = lambda x: int(round(x * fps))

    def clock(pid, local):
        b = base[pid]
        h, m, s = map(int, b["obs"].split("-"))
        return round((h * 3600 + m * 60 + s + b["in_s"] + local - START) / 60, 3)

    video, audio, overs, clipmap, gaps_out = [], [], [], {}, []
    pos = 0  # frames
    zi = 0
    prev_face_src = None  # (src id, end source time) of the last face frame shown
    prev_kind = None
    gaps = {}
    for g in E["gaps"]:
        gaps.setdefault(g["after"], []).append(g)
    for p in E["pieces"]:
        pid, kind = p["id"], p["kind"]
        if kind == "cine":
            n = F(p["dur"])
            video.append({"from": pos, "dur": n, "kind": "cine", "piece": pid, "src": p["file"]})
            audio.append({"from": pos, "dur": n, "src": p["audio"], "startFrom": 0, "fadeIn": 0, "fadeOut": 0, "piece": pid, "gainDb": p.get("audioGainDb", 0)})
            pos += n
            prev_face_src, prev_kind = None, "cine"
        else:
            b = base[pid]
            src = (b["obs"], round(b["in_s"], 3))
            views = p.get("views") or [[p["clips"][0][0], "face" if kind == "face" else "screen"]]
            punches = [x[0] for x in p.get("punch", [])]
            clipmap[pid] = []
            for ci, (a, bb, *_r) in enumerate(p["clips"]):
                opt = next((x for x in _r if isinstance(x, dict)), {})  # per-clip options: fadeIn / fadeOut (frames)
                n = F(bb - a)
                clipmap[pid].append((a, bb, pos))
                contiguous_next = False
                audio.append({"from": pos, "dur": n, "src": f"{media}/{pid}_voice.wav", "startFrom": F(a + H), "fadeIn": opt.get("fadeIn", 2), "fadeOut": opt.get("fadeOut", 2),
                              "piece": pid, "clip": ci, "srcIn": round(b["in_s"] + a, 3), "srcOut": round(b["in_s"] + bb, 3), "obs": b["obs"]})
                # split the clip by view changes and punches
                pushes_ = p.get("push") or []
                if pushes_ and not isinstance(pushes_[0], list):
                    pushes_ = [pushes_]
                push_marks = {x for q in pushes_ for x in q[:2]}
                marks = sorted({a, bb} | {t for t, _ in views if a < t < bb} | {t for t in punches if a < t < bb} | {t for t in push_marks if a < t < bb})
                for k in range(len(marks) - 1):
                    t0, t1 = marks[k], marks[k + 1]
                    view = [v for t, v in views if t <= t0 + 1e-6]
                    view = view[-1] if view else views[0][1]
                    f0 = pos + F(t0 - a)
                    f1 = pos + F(t1 - a)
                    ev = {"from": f0, "dur": f1 - f0, "kind": view, "piece": pid, "local": round(t0, 4), "obs": b["obs"], "in_s": b["in_s"]}
                    if view == "face":
                        src_t = b["in_s"] + t0
                        cont = prev_face_src is not None and prev_face_src[0] == b["obs"] and abs(prev_face_src[1] - src_t) < 0.05
                        if prev_kind == "face" and not cont:
                            zi ^= 1  # jump cut between face shots → change the framing
                        if t0 in punches:
                            zi ^= 1
                        z = Z1 if zi else Z0
                        ev["zoom"] = z
                        ev["zoom1"] = z
                        pushes = p.get("push") or []
                        if pushes and not isinstance(pushes[0], list):
                            pushes = [pushes]  # v2 format: one [a, b, z0, z1]
                        for pa, pb, z0, z1, *_why in pushes:  # long slow push-in / pull-out on a talking face
                            if pa <= t0 < pb:
                                ev["zoom"] = round(z * (z0 + (z1 - z0) * (t0 - pa) / (pb - pa)), 4)
                                ev["zoom1"] = round(z * (z0 + (z1 - z0) * (min(t1, pb) - pa) / (pb - pa)), 4)
                        prev_face_src = (b["obs"], b["in_s"] + t1)
                    prev_kind = view
                    video.append(ev)
                pos += n
        for g in gaps.get(pid, []):
            n = F(g["d"])
            el = g["el"]
            props = {}
            if "clock" in el:
                pass
            video.append({"from": pos, "dur": n, "kind": "insert", "el": el, "props": props, **({"dip": True} if g.get("dip") else {})})
            gaps_out.append({"from": pos, "dur": n, "el": el})
            pos += n
            prev_face_src, prev_kind, zi = None, "insert", 0
    # the film ends on a fade: the last voice clip fades with the picture (E["endFade"] s, cut it in room tone)
    if audio and E.get("endFade") and E.get("endFadeVoice", True):  # endFadeVoice false: an end card follows, the last line must not fade
        audio[-1]["fadeOut"] = F(E["endFade"])
    # overs (cutaways over voice)
    def out_frame(pid, local):
        """output frame of a piece-local time (a time inside a removed gap maps to the next kept clip)"""
        for a, bb, f in clipmap[pid]:
            if local < a:
                return f
            if a <= local <= bb:
                return f + F(local - a)
        a, bb, f = clipmap[pid][-1]
        return f + F(bb - a)

    for o in E["overs"]:
        if not any(a <= o["at"] < bb for a, bb, _ in clipmap[o["piece"]]):
            raise SystemExit(f"over {o} outside clips")
        f0 = out_frame(o["piece"], o["at"])
        n = out_frame(o["piece"], o["to"]) - f0 if "to" in o else F(o["d"])
        ev = {"from": f0, "dur": n, "el": o["el"], "piece": o["piece"]}
        if o.get("beats"):
            ev["props"] = {"b": {k: round((out_frame(o["piece"], v) - f0) / fps, 3) for k, v in o["beats"].items()}}
        if o.get("overlay"):
            ev["overlay"] = True
        if o.get("fadeOut"):
            ev["fadeOut"] = o["fadeOut"]
        overs.append(ev)
    # L-cuts: at a join of two different pieces (no insert in between) where face meets screen,
    # the screen picture takes over L s earlier / keeps L s longer (lips are never shown out of sync)
    if L:
        n = F(L)
        nol = {p["id"] for p in E["pieces"] if p.get("nolcut")}  # pieces whose joins stay hard cuts (e.g. a cutaway runs to the end)
        for i in range(len(video) - 1):
            x, y = video[i], video[i + 1]
            if x["from"] + x["dur"] != y["from"] or x.get("piece") == y.get("piece") or x.get("piece") in nol or y.get("piece") in nol:
                continue
            if x["kind"] == "face" and y["kind"] == "screen" and x["dur"] > n * 3:
                x["dur"] -= n; y["from"] -= n; y["dur"] += n; y["local"] = round(y["local"] - L, 4); y["lcut"] = True
            elif x["kind"] == "screen" and y["kind"] == "face" and y["dur"] > n * 3:
                x["dur"] += n; y["from"] += n; y["dur"] -= n; y["local"] = round(y["local"] + L, 4); y["lcut"] = True
    # chapter clocks (minutes since the experiment start) — the clock rolls from the end of the previous piece to the next
    order = [p["id"] for p in E["pieces"]]
    first = {p["id"]: p["clips"][0][0] for p in E["pieces"] if p["kind"] != "cine"}
    last = {p["id"]: p["clips"][-1][1] for p in E["pieces"] if p["kind"] != "cine"}
    for ev in video:
        if ev["kind"] == "insert":
            g = next(g for g in E["gaps"] if g["el"] == ev["el"])
            i = order.index(g["after"])
            if i + 1 < len(order) and order[i + 1] in first and g["after"] in last:
                ev["props"] = {"from": clock(g["after"], last[g["after"]]), "to": clock(order[i + 1], first[order[i + 1]])}
    return {"fps": fps, "total": pos, "endFade": E.get("endFade", 0), "totalSec": round(pos / fps, 3), "faceZoom": E["faceZoom"],
            "faceFrame": {k: v for k, v in E.get("faceFrame", {}).items() if not k.startswith("_")}, "blur": E.get("blur"),
            "cams": {p["id"]: p.get("cams", []) for p in E["pieces"]},
            "panels": {p["id"]: p["panels"] for p in E["pieces"] if p.get("panels")}, "video": video, "audio": audio, "overs": overs,
            "clockStart": START, "media": media}, E


def shots(tl):
    """Shots as the viewer sees them: a new shot starts at every cut, view change, punch or snapped camera move;
    a held camera inside a screen view is one shot until the camera moves."""
    fps = tl["fps"]
    out = []
    for ev in tl["video"]:
        t0, t1 = ev["from"] / fps, (ev["from"] + ev["dur"]) / fps
        if ev["kind"] == "screen" and out and out[-1]["kind"] == "screen" and out[-1].get("src") == (ev["obs"], round(ev["in_s"] + ev["local"], 2)) \
                and abs(out[-1]["t"] + out[-1]["d"] - t0) < 1e-6:
            out[-1]["d"] += t1 - t0  # the next piece continues the same recording without a cut (e.g. G1 → G2)
            out[-1]["src"] = (ev["obs"], round(ev["in_s"] + ev["local"] + t1 - t0, 2))
            continue
        if ev["kind"] == "screen":
            # panels are framings too: each one starts a new held «shot» (a 0.45 s dissolve, counted like a move)
            cams = sorted([c for c in tl["cams"].get(ev["piece"], [])] + [[q[0], 0, 0, q[3] or 1920, 0.45] for q in tl.get("panels", {}).get(ev["piece"], [])], key=lambda c: c[0])
            loc0 = ev["local"]
            loc1 = loc0 + (t1 - t0)
            # camera keys inside this event split it
            cur = [c for c in cams if c[0] <= loc0 + 1e-6] or cams[:1]  # before the first key the first key holds
            keys = [c for c in cams if loc0 + 1e-6 < c[0] < loc1 - 1e-6 and c is not (cur[0] if cur else None)]
            w = cur[-1][3] if cur else 1920
            moving = bool(cur and cur[-1][4] > 1.5)  # slow push counts as motion
            start = t0
            for c in keys:
                tt = t0 + (c[0] - loc0)
                if tt - start < 0.25:  # snap immediately followed by a move = one shot
                    w, moving = c[3], moving or c[4] > 1.5
                    continue
                # a camera move is a visual change (ends a held framing) but not a cut: no «short shot» flag
                out.append({"t": start, "d": tt - start, "kind": "screen", "w": w, "moving": moving, "piece": ev["piece"], "endMove": c[4] > 0})
                start, w, moving = tt, c[3], c[4] > 1.5
            out.append({"t": start, "d": t1 - start, "kind": "screen", "w": w, "moving": moving, "piece": ev["piece"],
                        "src": (ev["obs"], round(ev["in_s"] + loc1, 2))})
        else:
            out.append({"t": t0, "d": t1 - t0, "kind": ev["kind"], "piece": ev.get("piece") or ev.get("el"),
                        "moving": ev.get("zoom") != ev.get("zoom1")})
    # overs cut the underlying shot
    for o in tl["overs"]:
        if o.get("overlay"):
            continue  # drawn over the running shot: the face stays in frame
        a, b = o["from"] / fps, (o["from"] + o["dur"]) / fps
        res = []
        for s in out:
            s0, s1 = s["t"], s["t"] + s["d"]
            if s1 <= a or s0 >= b:
                res.append(s)
                continue
            if s0 < a:
                res.append({**s, "d": a - s0})
            if s1 > b:
                res.append({**s, "t": b, "d": s1 - b})
        res.append({"t": a, "d": b - a, "kind": "over", "piece": o["el"], "moving": True})
        out = sorted(res, key=lambda s: s["t"])
    return out


def check(tl):
    rows, flags = [], []
    for s in shots(tl):
        k = s["kind"]
        lim = LIMITS["face"] if k == "face" else (LIMITS["screen_wide"] if k == "screen" and s.get("w", 0) >= 1700 else LIMITS["screen"]) if k == "screen" else None
        flag = ""
        if lim and s["d"] > lim and not s.get("moving"):
            flag = f"held {s['d']:.1f} s > {lim:.0f} s"
        elif lim and s["d"] > lim * 1.6:
            flag = f"long even with motion ({s['d']:.1f} s)"
        if s["d"] < LIMITS["min"] and k in ("face", "screen") and not s.get("endMove"):
            flag = f"short {s['d']:.2f} s"
        rows.append((s, flag))
        if flag:
            flags.append((s, flag))
    return rows, flags


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("edl")
    ap.add_argument("--out", required=True)
    ap.add_argument("--report")
    a = ap.parse_args()
    tl, E = build(a.edl)
    json.dump(tl, open(a.out, "w"), ensure_ascii=False, indent=1)
    rows, flags = check(tl)
    print(f"total {hms(tl['totalSec'])} ({tl['totalSec']} s), {len(tl['video'])} video events, {len(rows)} shots, {len(flags)} flags")
    for s, f in flags:
        print(f"  FLAG {hms(s['t'])} {s['kind']:6} {s['piece']}: {f}")
    if a.report:
        L = [f"# Editorial check - {os.path.basename(a.edl)}", "", f"Total {hms(tl['totalSec'])}. Shots: {len(rows)}, flags: {len(flags)}.",
             f"Limits: face ≤ {LIMITS['face']:.0f} s, screen framing ≤ {LIMITS['screen']:.0f} s (wide ≤ {LIMITS['screen_wide']:.0f} s), shot ≥ {LIMITS['min']} s; slow push counts as motion.", "",
             "| # | out | len | shot | piece | flag |", "|---|---|---|---|---|---|"]
        for i, (s, f) in enumerate(rows):
            kind = s["kind"] + (f" w{s['w']}" if s["kind"] == "screen" else "") + (" ↗" if s.get("moving") else "")
            L.append(f"| {i+1} | {hms(s['t'])} | {s['d']:.1f} | {kind} | {s['piece']} | {f} |")
        # clips table (source → output)
        fps = tl["fps"]
        L += ["", "## Clips (source → output)", "", "| out in | out out | piece | source (recording @ s) | len |", "|---|---|---|---|---|"]
        for c in tl["audio"]:
            L.append(f"| {hms(c['from']/fps)} | {hms((c['from']+c['dur'])/fps)} | {c['piece']} | {c.get('obs','cine')} @ {c.get('srcIn','')}-{c.get('srcOut','')} | {c['dur']/fps:.2f} |")
        open(a.report, "w").write("\n".join(L) + "\n")
    sys.exit(0)


if __name__ == "__main__":
    main()
