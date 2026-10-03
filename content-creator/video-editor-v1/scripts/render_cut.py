#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Render the A-roll from an EDL: frame-exact video + matching voice track.

Usage:
  render_cut.py edl.json --dir PROJECT/assets/aroll [--width 1080 --height 1920] [--pip 480]

Writes into --dir:
  aroll.mp4  picture only, scaled (and center-cropped to 9:16 if needed), sharpened, GOP 15 for fast seeking
  voice.wav  48 kHz mono, each piece with 6-8 ms fades so cuts never click
  pip.mp4    small copy for the round face picture-in-picture (decodes much faster than the full frame)

Cuts use frame numbers for video and the matching sample numbers for audio, so
sync holds even across 35+ cuts. Re-transcribe voice.wav afterwards
(transcribe.py) and diff the text against the plan to prove no word was clipped.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import load_json, probe, run  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("edl")
    ap.add_argument("--dir", required=True)
    ap.add_argument("--width", type=int, default=1080)
    ap.add_argument("--height", type=int, default=1920)
    ap.add_argument("--pip", type=int, default=480, help="pip.mp4 width (0 = skip)")
    ap.add_argument("--crf", default="18")
    a = ap.parse_args()
    edl = load_json(a.edl)
    src = edl["source"]
    info = probe(src)
    fps, sr = edl["fps"], info.get("sample_rate", 48000)
    os.makedirs(a.dir, exist_ok=True)
    fv, fa, cat = [], [], []
    for n, (s, e, _) in enumerate(edl["keep"]):
        f0, f1 = int(round(s * fps)), int(round(e * fps))
        d = (f1 - f0) / fps
        fv.append(f"[0:v]trim=start_frame={f0}:end_frame={f1},setpts=PTS-STARTPTS[v{n}]")
        fa.append(f"[0:a]atrim=start_sample={round(f0 * sr / fps)}:end_sample={round(f1 * sr / fps)},"
                  f"asetpts=PTS-STARTPTS,afade=t=in:d=0.006,afade=t=out:st={max(d - 0.008, 0):.4f}:d=0.008[a{n}]")
        cat.append(f"[v{n}][a{n}]")
    W, H = a.width, a.height
    vf = (f"scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,crop={W}:{H},"
          f"unsharp=5:5:0.5,format=yuv420p")
    fc = ";\n".join(fv + fa) + ";\n" + "".join(cat) + f"concat=n={len(cat)}:v=1:a=1[vc][ac];\n[vc]{vf}[vo];\n" \
        "[ac]aresample=48000,pan=mono|c0=0.5*c0+0.5*c1[ao]"
    script = os.path.join(a.dir, "cut.ffscript")
    open(script, "w").write(fc)
    av, wav = os.path.join(a.dir, "aroll.mp4"), os.path.join(a.dir, "voice.wav")
    run(["ffmpeg", "-v", "error", "-y", "-i", src, "-filter_complex_script", script,
         "-map", "[vo]", "-c:v", "libx264", "-crf", a.crf, "-preset", "medium", "-g", "15",
         "-r", edl["fps_str"], "-an", av, "-map", "[ao]", "-c:a", "pcm_s16le", wav])
    if a.pip:
        ph = int(round(a.pip * H / W / 2) * 2)
        run(["ffmpeg", "-v", "error", "-y", "-i", av, "-vf", f"scale={a.pip}:{ph}:flags=lanczos",
             "-c:v", "libx264", "-crf", "20", "-g", "15", "-an", os.path.join(a.dir, "pip.mp4")])
    dv, da = probe(av)["duration"], probe(wav)["duration"]
    print(f"aroll.mp4 {dv:.3f}s, voice.wav {da:.3f}s, EDL {edl['duration']:.3f}s")
    if abs(dv - da) > 0.05 or abs(dv - edl["duration"]) > 0.1:
        print("WARNING: durations disagree, check the EDL")


if __name__ == "__main__":
    main()
