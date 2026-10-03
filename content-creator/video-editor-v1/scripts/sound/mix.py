"""Final mixer: processed voice + ducked BGM + SFX cues -> loudness-normalized master.

Usage: python mix.py --voice VOICE.wav --bgm BGM.wav --cues CUES.json --out MASTER.wav
       [--sfx-dir sfx/] [--lufs -14] [--ceiling -1] [--gap-db 20] [--duck-db 12]
"""
import argparse
import json
import os

import numpy as np
import pyloudnorm as pyln
import soundfile as sf
from scipy import signal

from dsp import SR, butter, follower, lookahead_limiter, peaking, undb

HERE = os.path.dirname(os.path.abspath(__file__))
HOP = 48  # 1 ms control rate


def load(path, mono=False):
    x, sr = sf.read(path, always_2d=True)
    if sr != SR:
        g = np.gcd(sr, SR)
        x = signal.resample_poly(x, SR // g, sr // g, axis=0)
    if mono:
        return x.mean(axis=1)
    if x.shape[1] == 1:
        x = np.repeat(x, 2, axis=1)
    return x[:, :2]


def frame_rms(x, win):
    """RMS over a centered window, sampled every HOP samples."""
    c = np.concatenate([[0.0], np.cumsum(x.astype(np.float64) ** 2)])
    centers = np.arange(0, len(x), HOP)
    a = np.clip(centers - win // 2, 0, len(x))
    b = np.clip(centers + win // 2, 0, len(x))
    return np.sqrt(np.maximum(c[b] - c[a], 0) / np.maximum(b - a, 1))


def ctrl_to_samples(g, n):
    return np.interp(np.arange(n), np.arange(len(g)) * HOP, g)


def process_voice(v):
    v = v - np.mean(v)
    v = butter(v, 80, "high", 4)
    v = peaking(v, 4000, 2.0, q=0.7)  # gentle presence lift 3-5 kHz
    meter = pyln.Meter(SR)
    v *= undb(-20 - meter.integrated_loudness(v))
    # compressor: 3:1 above threshold, RMS detector, attack 10 ms / release 120 ms
    lvl = 20 * np.log10(frame_rms(v, int(0.01 * SR)) + 1e-9)
    thr, ratio = -24.0, 3.0
    gr = np.maximum(lvl - thr, 0) * (1 - 1 / ratio)
    gr = follower(gr, 0.010, 0.120, SR / HOP)
    v = v * ctrl_to_samples(undb(-gr), len(v))
    v *= undb(-18 - meter.integrated_loudness(v))  # makeup to -18 LUFS before the mix
    # de-clip safety: soft-saturate anything approaching full scale
    v = np.where(np.abs(v) > 0.9, np.sign(v) * (0.9 + 0.1 * np.tanh((np.abs(v) - 0.9) / 0.1)), v)
    return v


def duck_curve(v, duck_db, n):
    """Voice activity -> BGM gain. RMS 20 ms window, attack 30 ms, release 250 ms."""
    env = frame_rms(v, int(0.02 * SR))
    env = follower(env, 0.030, 0.250, SR / HOP)
    edb = 20 * np.log10(env + 1e-9)
    active = edb > np.percentile(edb, 30)
    speech = np.percentile(edb[active], 80) if active.any() else -20
    lo, hi = speech - 20, speech - 10
    a = np.clip((edb - lo) / (hi - lo), 0, 1)
    a = a * a * (3 - 2 * a)  # smoothstep
    a = ctrl_to_samples(a, n)
    return a


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--voice", required=True)
    ap.add_argument("--bgm", required=True)
    ap.add_argument("--cues", required=True, help='JSON file: [{"sfx":"pop","t":12.34,"gain_db":-6,"pan":0}]')
    ap.add_argument("--out", required=True)
    ap.add_argument("--sfx-dir", default=os.path.join(HERE, "sfx"))
    ap.add_argument("--lufs", type=float, default=-14.0)
    ap.add_argument("--ceiling", type=float, default=-1.0, help="limiter ceiling in dBFS (4x oversampled peak)")
    ap.add_argument("--gap-db", type=float, default=20.0, help="BGM loudness below voice in speech gaps")
    ap.add_argument("--duck-db", type=float, default=12.0, help="extra BGM reduction while voice is active")
    ap.add_argument("--sfx-base-db", type=float, default=-6.0, help="SFX bus level before per-cue gain_db")
    a = ap.parse_args()

    meter = pyln.Meter(SR)
    v = process_voice(load(a.voice, mono=True))
    voice_lufs = meter.integrated_loudness(v)
    cues = json.load(open(a.cues))
    sfx = {}
    end = len(v)
    for c in cues:
        if c["sfx"] not in sfx:
            sfx[c["sfx"]] = load(os.path.join(a.sfx_dir, c["sfx"] + ".wav"), mono=True)
        end = max(end, int(c["t"] * SR) + len(sfx[c["sfx"]]))
    n = end

    # BGM: set its integrated loudness gap-db under the voice, fit to length
    b = load(a.bgm)
    b *= undb(voice_lufs - a.gap_db - meter.integrated_loudness(b))
    if len(b) >= n:
        b = b[:n].copy()
        fo = min(int(1.5 * SR), n)
        b[-fo:] *= (np.cos(np.linspace(0, np.pi / 2, fo)) ** 2)[:, None]
    else:
        b = np.pad(b, ((0, n - len(b)), (0, 0)))
    vv = np.pad(v, (0, n - len(v)))

    # ducking + sidechain-style EQ dip (extra -4 dB at 1-4 kHz while speaking)
    act = duck_curve(vv, a.duck_db, n)
    g = undb(-a.duck_db * act)[:, None]
    band = butter(b, [1000, 4000], "band", 2)
    b = b * g + band * g * (undb(-4.0 * act)[:, None] - 1)

    bus = np.zeros((n, 2))
    for c in cues:
        s = sfx[c["sfx"]] * undb(a.sfx_base_db + c.get("gain_db", 0.0))
        pan = float(c.get("pan", 0.0))
        i = int(round(c["t"] * SR))
        m = min(len(s), n - i)
        if m <= 0:
            continue
        bus[i:i + m, 0] += s[:m] * np.cos((pan + 1) * np.pi / 4) * np.sqrt(2)
        bus[i:i + m, 1] += s[:m] * np.sin((pan + 1) * np.pi / 4) * np.sqrt(2)

    mixd = vv[:, None] * np.ones((1, 2)) + b + bus
    assert np.all(np.isfinite(mixd))
    # loudness normalize + limit, iterate so the limiter does not leave us short
    gain = a.lufs - meter.integrated_loudness(mixd)
    for _ in range(3):
        out = lookahead_limiter(mixd * undb(gain), a.ceiling)
        L = meter.integrated_loudness(out)
        if abs(L - a.lufs) < 0.1:
            break
        gain += a.lufs - L
    sf.write(a.out, out.astype(np.float32), SR, subtype="FLOAT")
    peak = 20 * np.log10(np.max(np.abs(out)))
    tp = 20 * np.log10(np.max(np.abs(signal.resample_poly(out, 4, 1, axis=0))))
    vact = act > 0.5
    print(f"voice {voice_lufs:.2f} LUFS | BGM gap level {voice_lufs - a.gap_db:.2f} LUFS ({a.gap_db:.0f} dB under voice), "
          f"ducked -{a.duck_db:.0f} dB while speaking | voice active {100 * vact.mean():.0f}% of time | cues {len(cues)}")
    print(f"MASTER {a.out}: {n / SR:.2f}s  integrated {L:.2f} LUFS  sample peak {peak:.2f} dBFS  true peak ~{tp:.2f} dBTP")


if __name__ == "__main__":
    main()
