#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Render, then put the designed master mix back in and verify the deliverable.

Usage:
  finalize.py PROJECT [--name NAME] [--quality delivery] [--skip-render]

Steps:
  1. npx hyperframes render -q <quality> -o renders/<name>.mp4   (~2.5x realtime on this Mac)
  2. The renderer re-mixes audio (measured -16.4 LUFS for a -14 LUFS master), so remux
     assets/audio/master.wav onto the rendered picture (video stream copied, not re-encoded),
     with a gain trim so the AAC true peak stays under -1 dBFS.
  3. Verify duration, size, loudness, and write renders/<name>_sheet.jpg (a frame every ~9 s)
     for a last visual check with attach_image.
Long-running: launch it with bash() in the background and continue when it completes.
"""
import argparse
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import die, probe, run  # noqa: E402


def loud(path):
    p = subprocess.run(["ffmpeg", "-hide_banner", "-i", path, "-af", "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True)
    i = re.findall(r"I:\s+(-?[\d.]+) LUFS", p.stderr)
    pk = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", p.stderr)
    return float(i[-1]), float(pk[-1])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project")
    ap.add_argument("--name")
    ap.add_argument("--quality", default="delivery")
    ap.add_argument("--skip-render", action="store_true")
    a = ap.parse_args()
    P = os.path.abspath(a.project)
    name = a.name or os.path.basename(P)
    raw = os.path.join(P, "renders", f"{name}.mp4")
    fin = os.path.join(P, "renders", f"{name}_final.mp4")
    if not a.skip_render:
        p = subprocess.run(["npx", "hyperframes", "render", "-q", a.quality, "-o", raw], cwd=P, capture_output=True, text=True)
        print("\n".join(p.stdout.strip().splitlines()[-4:]))
        if p.returncode:
            die(p.stderr[-3000:])
    master = os.path.join(P, "assets", "audio", "master.wav")
    gain = 0.0
    for _ in range(3):
        run(["ffmpeg", "-v", "error", "-y", "-i", raw, "-i", master, "-map", "0:v", "-map", "1:a", "-c:v", "copy",
             "-af", f"volume={gain}dB", "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-shortest",
             "-movflags", "+faststart", fin])
        lu, pk = loud(fin)
        if pk <= -1.0:
            break
        gain -= pk + 1.0 + 0.1
    info = probe(fin)
    d = info["duration"]
    run(["ffmpeg", "-v", "error", "-y", "-i", fin, "-vf", f"fps=1/{max(d / 16, 1):.2f},scale=216:-1,tile=8x2",
         "-frames:v", "1", os.path.join(P, "renders", f"{name}_sheet.jpg")])
    print(f"FINAL {fin}\n  {info['width']}x{info['height']} {info['fps_str']} fps, {d:.2f}s, "
          f"{os.path.getsize(fin) / 1e6:.1f} MB, {lu:.1f} LUFS, peak {pk:.1f} dBFS (trim {gain:.1f} dB)")


if __name__ == "__main__":
    main()
