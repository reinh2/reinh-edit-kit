#!/usr/bin/env python3
"""Lay one music bed under a whole long video.

Rules (docs/MUSIC_AND_SFX.md): one calm bed for the whole film, under speech 16–20 dB below the
voice, +4…6 dB in pauses and on chapter cards, 1–1.5 s fades; a bed shorter than the film is looped on a bar boundary.

How:
  1. bar length: tempo from the autocorrelation of the low-band (kick/bass) envelope, × 4 beats;
  2. loop: the longest whole number of bars that ends ≥ 3 s before the track's own outro, repeated with a 0.25 s
     equal-power crossfade at each join (joins stay on the beat grid), 1.5 s fade-in, 3 s fade-out at the film's end;
  3. level: the bed is set so that, unducked, it sits `--pause-db` below the voice stem; a sidechain compressor keyed by the
     film's own mix (voice dominates it) pulls it down a further ~6 dB under speech → ≈ `--pause-db` − 6 below the voice;
  4. sum with the film's mix (no normalisation) → PCM in an MKV with the untouched video; then run
     scripts/audio/voice_master.py master --video for the −15 LUFS / −1.5 dBTP delivery master.
Pure Python + ffmpeg (no numpy).
Usage: python3 scripts/audio/mix_bed.py film.mp4 bed.mp3 out_mixed.mkv [--voice-lufs -17] [--pause-db 13] [--json report.json]
"""
import argparse, array, json, math, re, subprocess, sys


def ff(*a, capture=True):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", *a], capture_output=capture, text=False)
    if r.returncode:
        sys.exit(r.stderr.decode(errors="ignore")[-3000:])
    return r


def dur(p):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p], capture_output=True, text=True).stdout)


def lufs(p, af=""):
    e = ff("-i", p, "-af", (af + "," if af else "") + "ebur128", "-f", "null", "-").stderr.decode(errors="ignore")
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", e)[-1])


def mean_db(p, ss, t):
    e = subprocess.run(["ffmpeg", "-hide_banner", "-ss", f"{ss:.3f}", "-t", f"{t:.3f}", "-i", p, "-af", "volumedetect", "-f", "null", "-"], capture_output=True, text=True).stderr
    return float(re.findall(r"mean_volume: (-?[\d.]+)", e)[-1])


def bar_length(p):
    """seconds per bar (4 beats) from the low-band envelope autocorrelation, 70–140 bpm folded"""
    raw = ff("-i", p, "-t", "90", "-ac", "1", "-af", "lowpass=f=160,aresample=8000", "-f", "s16le", "-").stdout
    x = array.array("h", raw)
    hop = 80  # 100 Hz envelope
    env = [math.sqrt(sum(v * v for v in x[i:i + hop]) / hop) for i in range(0, len(x) - hop, hop)]
    d = [max(0.0, env[i] - env[i - 1]) for i in range(1, len(env))]  # onset strength
    m = sum(d) / len(d)
    d = [v - m for v in d]
    best, lag = -1e18, 0
    for L in range(int(100 * 60 / 140), int(100 * 60 / 70) + 1):
        s = sum(d[i] * d[i + L] for i in range(len(d) - L))
        if s > best:
            best, lag = s, L
    beat = lag / 100
    return 4 * beat, 60 / beat


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("film"); ap.add_argument("bed"); ap.add_argument("out")
    ap.add_argument("--voice-lufs", type=float, default=-17.0, help="loudness of the film's voice stem")
    ap.add_argument("--pause-db", type=float, default=13.0, help="unducked bed this many dB below the voice (pauses, chapters)")
    ap.add_argument("--duck-db", type=float, default=6.0, help="extra reduction under speech")
    ap.add_argument("--no-intro", action="store_true", help="start on the body, not the quiet intro (a film that opens on a teaser)")
    ap.add_argument("--fade-in", type=float, default=1.5, help="bed fade-in at the film start, s")
    ap.add_argument("--json")
    a = ap.parse_args()
    D = dur(a.film)
    Tb = dur(a.bed)
    bar, bpm = bar_length(a.bed)
    # a quiet intro (e.g. 4 bars ≈ 13 dB under the beat) plays once at the film's start; the repeats loop the
    # body only, so the bed never «drops out» every lap. Intro = leading bars more than 6 dB under the track's median bar.
    lv = [mean_db(a.bed, k * bar, bar) for k in range(int(Tb // bar))]
    med = sorted(lv)[len(lv) // 2]
    k0 = 0
    while k0 < len(lv) // 3 and lv[k0] < med - 6:
        k0 += 1
    lf = k0 * bar
    # body end: the last bar before the outro (a bar more than 6 dB under the median, or 3 s before the end)
    k1 = int((Tb - 3.0) // bar)
    while k1 > k0 + 4 and lv[k1 - 1] < med - 6:
        k1 -= 1
    nb = k1 - k0
    seg = nb * bar
    reps = math.ceil((D + 3 - lf) / (seg - 0.25)) + 1
    # the looped bed: [0, lf + seg] once, then copies of [lf, lf + seg], joined by 0.25 s equal-power crossfades on the bar grid
    # a film that opens on a teaser: the quiet intro + 1.5 s fade would leave its first second silent
    # (editorial_qc «pause» at 0:00.9) — --no-intro starts on the beat with a short fade
    inputs = ["-ss", f"{lf:.4f}", "-t", f"{seg:.4f}", "-i", a.bed] if a.no_intro else ["-t", f"{lf + seg:.4f}", "-i", a.bed]
    chain = []
    for i in range(1, reps):
        inputs += ["-ss", f"{lf:.4f}", "-t", f"{seg:.4f}", "-i", a.bed]
    prev = "[0:a]"
    for i in range(1, reps):
        o = f"[x{i}]"
        chain.append(f"{prev}[{i}:a]acrossfade=d=0.25:c1=qsin:c2=qsin{o}")
        prev = o
    bed_lufs = lufs(a.bed)
    gain = (a.voice_lufs - a.pause_db) - bed_lufs
    chain.append(f"{prev}atrim=0:{D:.3f},volume={gain:.2f}dB,afade=t=in:d={a.fade_in:.2f},afade=t=out:st={D - 3:.3f}:d=3,aresample=48000,aformat=channel_layouts=stereo[bed]")
    loop = a.out + ".bed.wav"
    ff(*inputs, "-filter_complex", ";".join(chain), "-map", "[bed]", "-c:a", "pcm_s24le", "-y", loop)
    # duck under the film's own mix, then sum
    ratio = 2.2  # threshold −32 dBFS, ratio 2.2: speech at ≈ −20 dBFS pulls the bed down ≈ 6 dB (4.0 / −36 dB took ≈ 16 dB — bed inaudible)
    fc = (f"[1:a]aformat=channel_layouts=stereo,asplit=2[key][dry];"
          f"[2:a][key]sidechaincompress=threshold=0.025:ratio={ratio}:attack=60:release=900:knee=6:makeup=1[duck];"
          f"[dry][duck]amix=inputs=2:normalize=0:duration=first[mix]")
    ff("-i", a.film, "-i", a.film, "-i", loop, "-filter_complex", fc, "-map", "0:v:0", "-map", "[mix]", "-c:v", "copy", "-c:a", "pcm_s24le", "-y", a.out)
    rep = {"film": a.film, "bed": a.bed, "film_s": round(D, 2), "bed_s": round(Tb, 2), "bpm": round(bpm, 1), "bar_s": round(bar, 3),
           "intro_bars": 0 if a.no_intro else k0, "loop_from_s": round(lf, 2), "loop_bars": nb, "loop_s": round(seg, 2), "copies": reps, "bed_lufs": bed_lufs, "bed_gain_db": round(gain, 2),
           "bed_unducked_vs_voice_db": -a.pause_db, "bed_under_speech_vs_voice_db": round(-a.pause_db - a.duck_db, 1), "bed_file": loop}
    print(json.dumps(rep, ensure_ascii=False))
    if a.json:
        json.dump(rep, open(a.json, "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
