"""Numeric checks for every rendered file: duration, peak, RMS, spectral centroid, NaN and clipping.

Usage: python verify.py [extra.wav ...]   (defaults: sfx/*.wav, tmp/bgm_demo.wav, demo_mix.wav)
"""
import glob
import os
import sys

import numpy as np
import soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
EXPECT = {"whoosh_short": 0.35, "whoosh_long": 0.8, "swoosh_down": 0.5, "pop": 0.12, "pop_soft": 0.12, "click": 0.05,
          "key_typing": 1.5, "key_enter": 0.09, "ding": 0.6, "success_chime": 0.9, "error_buzz": 0.4, "riser": 2.0,
          "riser_short": 1.0, "impact": 0.8, "impact_soft": 0.8, "glitch": 0.3, "deploy_launch": 1.2,
          "notification_stack": 0.5}


def stats(path):
    x, sr = sf.read(path, always_2d=True)
    m = x.mean(axis=1)
    peak = 20 * np.log10(np.abs(x).max() + 1e-12)
    rms = 20 * np.log10(np.sqrt(np.mean(m ** 2)) + 1e-12)
    spec = np.abs(np.fft.rfft(m * np.hanning(len(m))))
    f = np.fft.rfftfreq(len(m), 1 / sr)
    cent = float((f * spec).sum() / (spec.sum() + 1e-12))
    return dict(sr=sr, dur=len(x) / sr, peak=peak, rms=rms, cent=cent,
                nan=bool(~np.isfinite(x).all()), clip=bool((np.abs(x) >= 0.999).any()),
                edge=max(abs(m[0]), abs(m[-1])))


def main():
    files = sorted(glob.glob(os.path.join(HERE, "sfx", "*.wav")))
    files += [p for p in (os.path.join(HERE, "tmp", "bgm_demo.wav"), os.path.join(HERE, "demo_mix.wav")) if os.path.exists(p)]
    files += sys.argv[1:]
    fails = []
    print(f"{'name':20s} {'dur s':>7s} {'peak dBFS':>9s} {'RMS dBFS':>9s} {'centroid Hz':>11s}  flags")
    rows = {}
    for p in files:
        name = os.path.splitext(os.path.basename(p))[0]
        s = stats(p)
        rows[name] = s
        flags = []
        if s["sr"] != 48000:
            flags.append("SR")
        if s["nan"]:
            flags.append("NaN")
        if s["clip"]:
            flags.append("CLIP")
        if s["edge"] > 0.01:
            flags.append("EDGE-CLICK")
        if name in EXPECT and abs(s["dur"] - EXPECT[name]) > 0.05:
            flags.append(f"DUR!={EXPECT[name]}")
        if name in EXPECT and not -40 < s["rms"] < -3:
            flags.append("RMS?")
        fails += [f"{name}:{f}" for f in flags]
        print(f"{name:20s} {s['dur']:7.3f} {s['peak']:9.2f} {s['rms']:9.2f} {s['cent']:11.0f}  {' '.join(flags) or 'ok'}")
    # spectral sanity: whooshes must be much brighter than impacts
    if "whoosh_long" in rows and "impact" in rows:
        ok = rows["whoosh_long"]["cent"] > 4 * rows["impact"]["cent"]
        print(f"centroid check whoosh_long ({rows['whoosh_long']['cent']:.0f} Hz) > 4x impact ({rows['impact']['cent']:.0f} Hz): {'ok' if ok else 'FAIL'}")
        if not ok:
            fails.append("centroid")
    print("ALL OK" if not fails else f"FAILURES: {fails}")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
