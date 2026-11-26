#!/usr/bin/env python3
"""Lightweight 1080p proxies of a project's face/screen media for fast draft renders.

Draft compositions (`*-Preview`, 1280x720) do not need 4K sources: decoding 4K frames is the slowest part of a
Remotion render. Proxies keep the exact fps, frame count and file names, so a composition only swaps its media
folder (`--props='{"media":"<video>/mediap"}'`). Final renders always use the full-quality folder. Originals are
never touched: only files named *_face.mp4 / *_screen.mp4 are re-encoded, everything else is hard-linked.

Encoder: Apple VideoToolbox on macOS (fast, hardware), libx264 elsewhere (or with --cpu).
Usage: python3 scripts/edit/make_proxies.py public/<video>/media public/<video>/mediap [--jobs 4] [--cpu]
"""
import argparse, concurrent.futures as cf, os, subprocess, sys
from pathlib import Path


def encoder_args(cpu: bool) -> tuple[list[str], list[str]]:
    """(input args, output codec args) for this machine."""
    if sys.platform == "darwin" and not cpu:
        return ["-hwaccel", "videotoolbox"], ["-c:v", "h264_videotoolbox", "-b:v", "14M"]
    return [], ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p"]


def proxy(src: Path, dst: Path, cpu: bool) -> str:
    if dst.exists() and dst.stat().st_mtime >= src.stat().st_mtime:
        return f"skip {dst.name}"
    tmp = dst.with_suffix(".part.mp4")
    pre, enc = encoder_args(cpu)
    cmd = ["ffmpeg", "-v", "error", "-y", *pre, "-i", str(src),
           "-map", "0:v:0", "-an", "-vf", "scale=1920:-2:flags=lanczos", "-fps_mode", "passthrough",
           *enc, "-g", "60", "-movflags", "+faststart", str(tmp)]
    subprocess.run(cmd, check=True)
    tmp.replace(dst)
    return f"done {dst.name}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("src"); ap.add_argument("dst"); ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--cpu", action="store_true", help="software x264 even on macOS")
    a = ap.parse_args()
    src, dst = Path(a.src), Path(a.dst)
    if src.resolve() == dst.resolve():
        sys.exit("src and dst must differ")
    dst.mkdir(parents=True, exist_ok=True)
    files = sorted(p for p in src.glob("*.mp4") if p.stem.endswith(("_face", "_screen")))
    # everything else (voices, ready clips) is linked as is: audio is cheap
    for p in src.iterdir():
        q = dst / p.name
        if p in files or q.exists():
            continue
        if p.is_dir():
            q.symlink_to(p.resolve(), target_is_directory=True)
        else:
            os.link(p, q)  # hard link: Remotion does not serve file symlinks
    with cf.ThreadPoolExecutor(a.jobs) as ex:
        for r in ex.map(lambda p: proxy(p, dst / p.name, a.cpu), files):
            print(r, flush=True)


if __name__ == "__main__":
    sys.exit(main())
