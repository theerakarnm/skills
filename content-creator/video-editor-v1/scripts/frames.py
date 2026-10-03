#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Eyes: pull timestamped frames and contact sheets so the agent can SEE the footage.

Usage:
  frames.py VIDEO --out DIR [--every 1.0] [--tile 180] [--per-sheet 24] [--at 3.2,7.5]

Writes DIR/f_XXXX.jpg (one per --every seconds) and DIR/sheet_N.jpg (6 columns, each tile
labelled with its time). Look at the sheets with attach_image, then note:
where the face/eyes sit (y range), where the hands move, which wall areas stay empty
(kinetic text goes there), framing problems (head cut off, too tight, low resolution).
Use --at for exact moments (e.g. checking a director note "at 0:07").
"""
import argparse
import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import SKILL_DIR, probe, run  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--out", required=True)
    ap.add_argument("--every", type=float, default=1.0)
    ap.add_argument("--tile", type=int, default=180)
    ap.add_argument("--per-sheet", type=int, default=24)
    ap.add_argument("--at", default="")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    for f in glob.glob(os.path.join(a.out, "*.jpg")):
        os.remove(f)
    font = os.path.join(SKILL_DIR, "assets", "fonts", "JetBrainsMono.ttf")
    here = os.path.dirname(os.path.abspath(__file__))
    if a.at:
        # exact moments: one full-size frame each, time in the file name
        for t in (float(x) for x in a.at.split(",")):
            run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t}", "-i", a.video, "-frames:v", "1", "-q:v", "2",
                 os.path.join(a.out, f"at_{t:07.2f}.jpg")])
        print(f"wrote {len(a.at.split(','))} frame(s) to {a.out} (named by seconds)")
        return
    run(["ffmpeg", "-v", "error", "-y", "-i", a.video, "-vf", f"fps=1/{a.every}", "-q:v", "3",
         os.path.join(a.out, "f_%04d.jpg")])
    frames = sorted(glob.glob(os.path.join(a.out, "f_*.jpg")))
    info = probe(a.video)
    # Homebrew ffmpeg often lacks drawtext (no freetype), so labels are drawn with Pillow via uv.
    out = run(["uv", "run", "--quiet", "--with", "pillow", "python", os.path.join(here, "_sheet.py"),
               a.out, str(a.every), str(a.tile), str(a.per_sheet), font])
    print(f"{len(frames)} frames ({info['width']}x{info['height']}, {info['duration']:.1f}s), "
          f"frame k is at (k-1)*{a.every}s -> {out.strip()} in {a.out}")


if __name__ == "__main__":
    main()
