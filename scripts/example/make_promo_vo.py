#!/usr/bin/env python3
"""Scratch voice-over for the promo (src/promo/script.json): one synthetic line per scene (macOS `say`, else espeak-ng),
processed with voice_master (preset neutral) → public/promo/vo_<id>.wav + public/promo/vo.json (durations).
Only for pacing the draft: the final voice-over is recorded by a person. Files stay local (public/promo is ignored)."""
import json, os, shutil, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "public", "promo")


def dur(p):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p], capture_output=True, text=True).stdout)


def main():
    os.makedirs(OUT, exist_ok=True)
    S = json.load(open(os.path.join(ROOT, "src", "promo", "script.json")))["scenes"]
    tmp = tempfile.mkdtemp()
    meta = {}
    for s in S:
        raw = f"{tmp}/{s['id']}.wav"
        if shutil.which("say"):
            subprocess.run(["say", "-v", "Milena", "-r", "185", "-o", raw + ".aiff", s["vo"].replace(" - ", ", ")], check=True)
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", raw + ".aiff", "-ar", "48000", "-ac", "1", raw], check=True)
        elif shutil.which("espeak-ng"):
            subprocess.run(["espeak-ng", "-v", "ru", "-s", "160", "-w", raw, s["vo"]], check=True)
        else:
            sys.exit("no speech engine (macOS say or espeak-ng): the promo renders silent without vo.json")
        out = os.path.join(OUT, f"vo_{s['id']}.wav")
        subprocess.run([sys.executable, os.path.join(ROOT, "scripts/audio/voice_master.py"), "voice", raw, out, "--preset", "neutral"],
                       check=True, capture_output=True)
        meta[s["id"]] = round(dur(out), 3)
        print(f"{s['id']:9} {meta[s['id']]:5.2f} s")
    json.dump(meta, open(os.path.join(OUT, "vo.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
