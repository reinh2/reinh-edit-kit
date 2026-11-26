#!/usr/bin/env python3
"""Short cut from processed media pieces: voice back to back + a timeline + word times for captions.

EDL (projects/<short>/edl.json): pieces of processed media (public/<src>_voice.wav, plus _face.mp4 / _screen.mp4 for
the composition, one shared timebase per piece), each with source in/out `a`/`b` (s, measured cut points), the exact
spoken `text` and an optional `gap` (s of silence after the piece).
Output:
  <out>/voice_cut.wav   the pieces back to back, 6 ms edge fades, frame-exact (fps) lengths;
  <out>/timeline.json   per piece: t0/t1 in the Short, source a/b (also copied next to the EDL as <edl>_tl.json);
  <out>/words.json      whisper.cpp word times on the cut, words replaced by the EDL text (difflib alignment),
                        `seg` = piece index (also next to the EDL as <edl>_words.json).
Usage: python3 scripts/edit/short_cut.py projects/<short>/edl.json work/<short>/cut [--fps 30] [--lang ru] [--model …]
Language and model default to kit.config.json («language», «whisperModel»).
"""
import argparse, difflib, json, os, re, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import _kit  # noqa: E402

NOISE = re.compile(r"\[.*\]|\*.*\*|[.,!?…-]+")


def norm(s):
    return re.sub(r"[^\wё]", "", s.lower().replace("ё", "е"))


def plan(pieces, fps):
    """frame-exact piece placement: [{…piece, seg, t0, t1, dur}], total seconds"""
    t, tl = 0.0, []
    for i, p in enumerate(pieces):
        d = round((p["b"] - p["a"]) * fps) / fps
        gap = round(p.get("gap", 0) * fps) / fps
        tl.append({**p, "seg": i, "t0": round(t, 4), "t1": round(t + d, 4), "dur": d, "gap": gap})
        t += d + gap
    return tl, round(t * fps) / fps


def align(tl, W):
    """Words of the EDL text with times from the recogniser words W = [(start, end, text)] of the cut.
    One-to-one matches keep their own time; words whisper missed are spread between the neighbours."""
    W = [w for w in W if w[2] and not NOISE.fullmatch(w[2])]
    words = []
    for p in tl:
        ws = [w for w in W if p["t0"] - 0.15 <= (w[0] + w[1]) / 2 < p["t1"] + 0.1]
        toks = p["text"].split()
        sm = difflib.SequenceMatcher(a=[norm(w[2]) for w in ws], b=[norm(x) for x in toks], autojunk=False)
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if j2 == j1:
                continue
            if i2 - i1 == j2 - j1:  # one to one (equal or same-length replace): keep each word's own time
                for k in range(j2 - j1):
                    words.append({"w": toks[j1 + k], "start": round(max(p["t0"], ws[i1 + k][0]), 3),
                                  "end": round(min(p["t1"], ws[i1 + k][1]), 3), "seg": p["seg"]})
                continue
            if i2 > i1:
                s0, s1 = ws[i1][0], ws[i2 - 1][1]
            else:  # whisper missed these words: squeeze them between neighbours
                s0 = ws[i1 - 1][1] if i1 > 0 else p["t0"]
                s1 = ws[i1][0] if i1 < len(ws) else p["t1"]
            n = j2 - j1
            for k in range(n):
                words.append({"w": toks[j1 + k], "start": round(max(p["t0"], s0 + (s1 - s0) * k / n), 3),
                              "end": round(min(p["t1"], s0 + (s1 - s0) * (k + 1) / n), 3), "seg": p["seg"]})
    return words


def ff(*args):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args], check=True)


def main():
    c = _kit.cfg()
    ap = argparse.ArgumentParser()
    ap.add_argument("edl"); ap.add_argument("out"); ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--public", default="public")
    ap.add_argument("--model", default=_kit.path(c["whisperModel"]))
    ap.add_argument("--lang", default=c["language"])
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    E = json.load(open(a.edl))
    tl, total = plan(E["pieces"], a.fps)
    parts = []
    for p in tl:
        w = f"{a.out}/p{p['seg']:02d}.wav"
        d = p["dur"]
        ff("-ss", f"{p['a']:.4f}", "-t", f"{d:.4f}", "-i", f"{a.public}/{p['src']}_voice.wav",
           "-af", f"afade=t=in:d=0.006,afade=t=out:st={d - 0.006:.4f}:d=0.006,apad=whole_dur={d + p['gap']:.4f}",
           "-ar", "48000", "-ac", "1", "-c:a", "pcm_s24le", w)
        parts.append(w)
    with open(f"{a.out}/list.txt", "w") as f:
        f.writelines(f"file '{os.path.abspath(p)}'\n" for p in parts)
    ff("-f", "concat", "-safe", "0", "-i", f"{a.out}/list.txt", "-ar", "48000", "-ac", "1", "-c:a", "pcm_s24le", f"{a.out}/voice_cut.wav")
    out_tl = {"fps": a.fps, "total": total, "pieces": tl}
    for path in (f"{a.out}/timeline.json", a.edl.replace(".json", "_tl.json")):
        json.dump(out_tl, open(path, "w"), ensure_ascii=False, indent=1)
    ff("-i", f"{a.out}/voice_cut.wav", "-ac", "1", "-ar", "16000", f"{a.out}/a16.wav")
    subprocess.run(["whisper-cli", "-m", a.model, "-f", f"{a.out}/a16.wav", "-l", a.lang, "-ojf", "-ml", "1", "-sow", "-of", f"{a.out}/w", "-np"],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    W = [(s["offsets"]["from"] / 1000, s["offsets"]["to"] / 1000, s["text"].strip()) for s in json.load(open(f"{a.out}/w.json"))["transcription"]]
    words = align(tl, W)
    for path in (f"{a.out}/words.json", a.edl.replace(".json", "_words.json")):
        json.dump(words, open(path, "w"), ensure_ascii=False, indent=0)
    for p in tl:
        print(f"{p['seg']:2} {p['id']:8} {p['t0']:6.2f}-{p['t1']:6.2f}  " + " ".join(f"{w['w']}@{w['start']:.2f}" for w in words if w["seg"] == p["seg"]))
    print("total", total)


if __name__ == "__main__":
    main()
