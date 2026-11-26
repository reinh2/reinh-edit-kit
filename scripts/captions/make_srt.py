#!/usr/bin/env python3
"""Separate .srt from the FINAL mix: whisper.cpp word timestamps → cues of ≤ 42 chars per line, 1–2 lines, 1–6 s,
a new cue on pauses ≥ 0.5 s and sentence ends; terms fixed with a glossary (glossary.json: {"fixes": [[regex, text]]}).
Usage: python3 scripts/captions/make_srt.py final.mp4 out.srt [--lang ru] [--model models/ggml-small.bin] [--glossary glossary.json]
       python3 scripts/captions/make_srt.py --words words.json out.srt   (ready word times: [{"w"|"text", "start", "end"}])
Word times from Whisper stretch over pauses — cue ends are clipped to the next cue start; read the result before delivery."""
import argparse, json, os, re, subprocess, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import _kit  # noqa: E402

LINE = 42


def transcribe(video, model, lang):
    d = tempfile.mkdtemp()
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", video, "-vn", "-ac", "1", "-ar", "16000", f"{d}/a.wav"], check=True)
    subprocess.run(["whisper-cli", "-m", model, "-f", f"{d}/a.wav", "-l", lang, "-ojf", "-ml", "1", "-sow", "-of", f"{d}/w", "-np"], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    with open(f"{d}/w.json") as f:
        return [(s["offsets"]["from"] / 1000, s["offsets"]["to"] / 1000, s["text"].strip()) for s in json.load(f)["transcription"] if s["text"].strip()]


def cues_from_words(W):
    W = [w for w in W if w[2] and not re.fullmatch(r"\[.*\]|\*.*\*", w[2])]
    cues, cur = [], []

    def flush():
        if cur:
            cues.append([cur[0][0], cur[-1][1], " ".join(w[2] for w in cur)])
            cur.clear()
    for w in W:
        n = len(" ".join(x[2] for x in cur))
        if cur and (w[0] - cur[-1][1] >= 0.5 or n + 1 + len(w[2]) > 64 or w[1] - cur[0][0] > 6 or re.search(r"[.!?]$", cur[-1][2])
                    or (n > 40 and cur[-1][2].endswith(","))):
            flush()
        cur.append(w)
    flush()
    # merge tiny tails into the previous cue when the result still fits two lines / 7 s
    merged = []
    for c in cues:
        if merged and ((c[1] - c[0]) < 1.2 or len(c[2]) < 14) and len(merged[-1][2]) + 1 + len(c[2]) <= 2 * LINE \
                and c[1] - merged[-1][0] <= 7 and c[0] - merged[-1][1] < 0.5 and not re.search(r"[.!?]$", merged[-1][2]):
            merged[-1] = [merged[-1][0], c[1], merged[-1][2] + " " + c[2]]
        else:
            merged.append(c)
    return merged


def fix(t, fixes):
    for pat, rep in fixes:
        t = re.sub(pat, rep, t, flags=re.I)
    return t


def wrap(t):
    if len(t) <= LINE:
        return t
    words, best = t.split(), None
    for i in range(1, len(words)):
        l1, l2 = " ".join(words[:i]), " ".join(words[i:])
        if len(l1) <= LINE and len(l2) <= LINE and (best is None or abs(len(l1) - len(l2)) < best[0]):
            best = (abs(len(l1) - len(l2)), l1 + "\n" + l2)
    if best:
        return best[1]
    # no split keeps both lines ≤ 42: take the most balanced one
    i = min(range(1, len(words)), key=lambda i: abs(len(" ".join(words[:i])) - len(" ".join(words[i:]))))
    return " ".join(words[:i]) + "\n" + " ".join(words[i:])


def ts(x):
    ms = int(round(x * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def srt(cues, fixes=()):
    out = []
    for i, (t0, t1, t) in enumerate(cues):
        if i + 1 < len(cues):
            t1 = min(t1, cues[i + 1][0] - 0.04)
        t1 = max(t1, t0 + 1.0)
        txt = fix(t, fixes)
        if i == 0 or re.search(r"[.!?]$", cues[i - 1][2]):  # capital letter only at a sentence start
            txt = txt[:1].upper() + txt[1:]
        out.append(f"{i + 1}\n{ts(t0)} --> {ts(t1)}\n{wrap(txt.rstrip('.'))}\n")
    return "\n".join(out)


def main():
    c = _kit.cfg()
    ap = argparse.ArgumentParser()
    ap.add_argument("video", nargs="?"); ap.add_argument("out")
    ap.add_argument("--words", help="ready word times JSON instead of transcribing")
    ap.add_argument("--model", default=_kit.path(c["whisperModel"]))
    ap.add_argument("--lang", default=c["language"])
    ap.add_argument("--glossary", default=_kit.path(c["glossary"]))
    a = ap.parse_args()
    if a.words:
        W = [(w["start"], w["end"], (w.get("w") or w.get("text", "")).strip()) for w in json.load(open(a.words))]
    elif a.video:
        W = transcribe(a.video, a.model, a.lang)
    else:
        ap.error("give a video or --words")
    fixes = json.load(open(a.glossary))["fixes"] if os.path.exists(a.glossary) else []
    cues = cues_from_words(W)
    open(a.out, "w").write(srt(cues, fixes))
    print(f"{len(cues)} cues → {a.out}")


if __name__ == "__main__":
    main()
