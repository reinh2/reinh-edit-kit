#!/usr/bin/env python3
"""Prepares the install guide's screenshots: window captures in work/guide/raw/*.png → public/guide/shots/<name>.png
+ public/guide/shots/sizes.json (the guide video reads the sizes).

Spec: src/guide/shots.json, {"<name>": {"from": "<raw file>", "terminal": true, "trim": true, "crop": [x, y, w, h], "blur": [[x, y, w, h]]}}
  terminal - cut the window's title and tab bar (found by the terminal's background colour): they can show the user name
  crop     - after that, keep only this area (x, y, w, h in pixels; w or h 0 = to the edge)
  trim     - drop empty terminal rows at the bottom (keeps a margin)
  blur     - blur areas (after crop) with anything personal: paths with the user name, e-mail
Capture only single windows (`screencapture -l <window id>`), never the whole screen, and look at every shot before use.
Usage: python3 scripts/example/guide_shots.py [--raw work/guide/raw]"""
import argparse, json, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def size(p):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0", p],
                         capture_output=True, text=True, check=True).stdout.strip()
    w, h = out.split(",")[:2]
    return int(w), int(h)


def gray(p, w, h):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", p, "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True, check=True).stdout
    return [raw[y * w:(y + 1) * w] for y in range(h)]


def is_bg(row, bg, x0, x1):
    return all(abs(v - bg) <= 4 for v in row[x0:x1])


def content_top(rows, w):
    """first row after the title/tab bar: a run of rows in the terminal's background colour"""
    bg = rows[-12][12]
    for y in range(20, min(200, len(rows) - 10)):
        if not is_bg(rows[y - 1], bg, 12, w - 40) and all(is_bg(rows[y + k], bg, 12, w - 40) for k in range(6)):
            return y
    return 0


def content_bottom(rows, w, top, margin=24):
    bg = rows[-12][12]
    last = top
    for y in range(top, len(rows) - 8):
        if not is_bg(rows[y], bg, 12, w - 40):
            last = y
    return min(len(rows), last + margin)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raw", default=os.path.join(ROOT, "work", "guide", "raw"))
    a = ap.parse_args()
    spec = json.load(open(os.path.join(ROOT, "src", "guide", "shots.json")))
    out = os.path.join(ROOT, "public", "guide", "shots")
    os.makedirs(out, exist_ok=True)
    sizes = {}
    for name, s in spec.items():
        if name.startswith("_"):
            continue
        src = os.path.join(a.raw, s["from"])
        if not os.path.exists(src):
            print(f"- {name}: no {s['from']} (the guide shows a placeholder)")
            continue
        w, h = size(src)
        x, y, cw, ch = 0, 0, w, h
        rows = gray(src, w, h) if s.get("terminal") or s.get("trim") else None
        if s.get("terminal"):
            y = content_top(rows, w)
            ch = h - y
        if s.get("crop"):
            dx, dy, ww, hh = s["crop"]
            x, y = x + dx, y + dy
            cw = ww or (w - x)
            ch = hh or (h - y)
        if s.get("trim"):
            ch = min(ch, content_bottom(rows, w, y) - y)
        f = f"[0]crop={cw}:{ch}:{x}:{y}[c0]"
        blurs = s.get("blur", [])
        for i, (bx, by, bw, bh) in enumerate(blurs):
            f += f";[c{i}]split[a{i}][b{i}];[b{i}]crop={bw}:{bh}:{bx}:{by},gblur=sigma=7[bl{i}];[a{i}][bl{i}]overlay={bx}:{by}[c{i + 1}]"
        f += f";[c{len(blurs)}]null"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-filter_complex", f, os.path.join(out, f"{name}.png")], check=True)
        sizes[name] = [cw, ch]
        print(f"✓ {name}: {cw}×{ch}")
    json.dump(sizes, open(os.path.join(out, "sizes.json"), "w"), indent=1)


if __name__ == "__main__":
    sys.exit(main())
