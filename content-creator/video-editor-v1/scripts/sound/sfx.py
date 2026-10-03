"""Synthesize the SFX kit. Usage: python sfx.py [--out sfx/]"""
import argparse
import os

import numpy as np
import soundfile as sf

from dsp import (SR, adsr, bandpass_sweep, bl_square, blit_saw, butter, exp_env, fade,
                 peak_normalize, phase_from_freq, reverb, svf, t_axis)


def rng(seed):
    return np.random.default_rng(seed)


def whoosh(dur, f0, f1, seed, q=1.6):
    n = int(dur * SR)
    noise = rng(seed).standard_normal(n)
    # sweep in log frequency with a smooth bell-shaped amplitude
    x = bandpass_sweep(noise, f0, f1, q=q)
    x2 = bandpass_sweep(rng(seed + 1).standard_normal(n), f0 * 1.5, f1 * 1.5, q=q * 1.5)
    t = np.linspace(0, 1, n)
    peak = 0.62 if f1 > f0 else 0.38
    env = np.where(t < peak, (t / peak) ** 2, ((1 - t) / (1 - peak)) ** 1.6)
    y = (x + 0.5 * x2) * env
    return reverb(y, wet=0.18, dur=0.5, decay=0.12, seed=seed)


def pop(dur=0.12, f_hi=1400, f_lo=380, seed=0):
    t = t_axis(dur)
    f = f_lo + (f_hi - f_lo) * np.exp(-t / 0.018)
    ph = phase_from_freq(f)
    body = np.sin(ph) + 0.25 * np.sin(2 * ph)
    env = adsr(len(t), 0.002, 0.03, 0.35, dur - 0.04) * exp_env(len(t), 0.05)
    click = rng(seed).standard_normal(len(t)) * exp_env(len(t), 0.0015)
    click = butter(click, 3000, "high")
    return body * env + 0.15 * click


def key_click(seed, heavy=False):
    r = rng(seed)
    dur = 0.09 if heavy else 0.05
    n = int(dur * SR)
    t = np.arange(n) / SR
    # two transients: switch "click" and bottom-out "thock"
    hi = butter(r.standard_normal(n), [2500, 9000] if not heavy else [1500, 6000], "band") * exp_env(n, 0.003)
    f_body = r.uniform(180, 260) if heavy else r.uniform(350, 600)
    body = np.sin(2 * np.pi * f_body * t) * exp_env(n, 0.012 if heavy else 0.006)
    d = int(r.uniform(0.006, 0.012) * SR)
    thock = np.zeros(n)
    thock[d:] = butter(r.standard_normal(n - d), 900 if heavy else 1800, "low") * exp_env(n - d, 0.006 if heavy else 0.004)
    y = 0.8 * hi + (1.0 if heavy else 0.5) * body + (1.2 if heavy else 0.6) * thock
    return fade(y, 0.0005, 0.005)


def key_typing(dur=1.5, seed=11):
    r = rng(seed)
    out = np.zeros(int(dur * SR) + SR // 10)
    t = 0.01
    i = 0
    while t < dur - 0.06:
        c = key_click(seed * 100 + i) * r.uniform(0.45, 1.0)
        s = int(t * SR)
        out[s:s + len(c)] += c
        # human-ish rhythm: bursts of fast keys with occasional pauses
        t += r.choice([r.uniform(0.055, 0.11), r.uniform(0.16, 0.24)], p=[0.85, 0.15])
        i += 1
    out = out[: int(dur * SR)]
    return reverb(out, wet=0.08, dur=0.3, decay=0.05, seed=seed)[: int(dur * SR)]


def bell(freq, dur, seed=0, bright=1.0):
    """FM bell: carrier : modulator ratio 1 : 3.5 with decaying index."""
    t = t_axis(dur)
    idx = bright * 2.2 * np.exp(-t / 0.15)
    mod = np.sin(2 * np.pi * freq * 3.5 * t)
    y = np.sin(2 * np.pi * freq * t + idx * mod)
    y += 0.35 * np.sin(2 * np.pi * freq * 2.0 * t) * np.exp(-t / 0.12)
    env = adsr(len(t), 0.002, 0.0, 1.0, 0.0) * np.exp(-t / (dur * 0.28))
    return y * env


def ding():
    dur = 0.6
    y = bell(1318.5, dur) + 0.5 * bell(1975.5, dur, bright=0.6)
    return reverb(y, wet=0.22, dur=0.6, decay=0.15, seed=21)[: int(dur * SR)]


def success_chime():
    dur = 0.9
    out = np.zeros(int(dur * SR))
    # A major-ish rising arpeggio: E5, A5, C#6 (bright, positive)
    for k, (f, st) in enumerate([(659.25, 0.0), (880.0, 0.11), (1108.7, 0.22)]):
        b = bell(f, dur - st, bright=0.9) * (0.8 + 0.1 * k)
        s = int(st * SR)
        out[s:s + len(b)] += b
    return reverb(out, wet=0.25, dur=0.8, decay=0.2, seed=22)[: int(dur * SR)]


def error_buzz():
    dur = 0.4
    n = int(dur * SR)
    t = np.arange(n) / SR
    tone = 0.6 * bl_square(110.0, n) + 0.4 * blit_saw(116.5, n)
    tone = butter(tone, 2500, "low", 4)
    gate = np.zeros(n)
    for st in (0.0, 0.2):
        a, b = int(st * SR), int((st + 0.16) * SR)
        gate[a:b] = adsr(b - a, 0.004, 0.02, 0.8, 0.04)
    return tone * gate


def riser(dur, seed):
    n = int(dur * SR)
    t = np.linspace(0, 1, n)
    noise = rng(seed).standard_normal(n)
    nf = bandpass_sweep(noise, 300, 9000, q=1.1)
    f = 110 * 2 ** (3 * t ** 1.5)  # tone rises 3 octaves
    tone = blit_saw(f, n, harmonics_limit=12)
    tone = svf(tone, 400 + 6000 * t ** 2, q=1.5, mode="lp")
    # tremolo speeding up gives tension
    trem = 0.75 + 0.25 * np.sin(phase_from_freq(4 + 20 * t ** 2))
    env = t ** 2.2
    y = (0.8 * nf + 0.35 * tone) * env * trem
    y = fade(y, 0.01, 0.006)
    return y


def impact(soft=False):
    dur = 0.8
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = 42 + (140 if not soft else 80) * np.exp(-t / 0.035)
    sub = np.sin(phase_from_freq(f)) * np.exp(-t / (0.28 if not soft else 0.2))
    sub = np.tanh(1.6 * sub) / np.tanh(1.6)
    tr = butter(rng(31).standard_normal(n), [80, 5000] if not soft else [80, 2000], "band") * exp_env(n, 0.012)
    tail = butter(rng(32).standard_normal(n), 400, "low") * exp_env(n, 0.18) * 0.25
    y = sub + (0.5 if not soft else 0.25) * tr + tail
    y = reverb(y, wet=0.15, dur=0.8, decay=0.25, seed=33)[:n]
    return fade(y, 0.0005, 0.05)


def glitch():
    dur = 0.3
    r = rng(41)
    n = int(dur * SR)
    t = np.arange(n) / SR
    src = blit_saw(220 * (1 + 0.5 * np.sin(2 * np.pi * 9 * t)), n, harmonics_limit=20) + 0.5 * r.standard_normal(n)
    out = np.zeros(n)
    pos = 0
    while pos < n:
        seg = int(r.uniform(0.012, 0.04) * SR)
        mode = r.integers(0, 4)
        chunk = src[pos:pos + seg].copy()
        if mode == 0:  # stutter: repeat a tiny grain
            g = chunk[: max(seg // 4, 64)]
            chunk = np.tile(g, int(np.ceil(seg / len(g))))[:seg]
        elif mode == 1:  # bitcrush + sample-and-hold
            hold = r.integers(6, 24)
            chunk = np.repeat(chunk[::hold], hold)[:seg]
            chunk = np.round(chunk * 4) / 4
        elif mode == 2:  # dropout
            chunk *= 0.05
        else:  # pitch jump
            chunk = np.sin(2 * np.pi * r.uniform(800, 2400) * np.arange(len(chunk)) / SR) * 0.7
        chunk = fade(chunk, 0.0005, 0.0008)  # clean edges between grains
        out[pos:pos + len(chunk)] = chunk
        pos += seg
    out = butter(out, 9000, "low", 4)  # tame aliasing from crushing
    return out


def deploy_launch():
    dur = 1.2
    n = int(dur * SR)
    t = np.linspace(0, 1, n)
    sw = whoosh(dur * 0.75, 250, 7000, seed=51)
    up = np.sin(phase_from_freq(220 * 2 ** (2.5 * t ** 1.3))) * np.sin(np.pi * np.clip(t * 1.25, 0, 1)) ** 2
    out = np.zeros(n + SR)
    out[: len(sw)] += 0.8 * sw
    out[:n] += 0.3 * up
    # sparkle: random high bell blips after the peak
    r = rng(52)
    for k in range(9):
        st = 0.55 + k * 0.06 + r.uniform(-0.015, 0.015)
        f = r.choice([1760, 2093, 2637, 3136, 3520])
        b = bell(f, 0.35, bright=0.5) * (0.35 * (1 - k / 12))
        s = int(st * SR)
        out[s:s + len(b)] += b
    out = reverb(out, wet=0.25, dur=0.8, decay=0.2, seed=53)
    return out[:n]


def notification_stack():
    dur = 0.5
    out = np.zeros(int(dur * SR))
    for k, st in enumerate((0.0, 0.14, 0.28)):
        p = pop(0.12, 1000 + 180 * k, 420 + 60 * k, seed=60 + k) * 0.7
        s = int(st * SR)
        out[s:s + len(p)] += p
    return out


def build():
    return {
        "whoosh_short": (whoosh(0.35, 400, 6000, 1), 0.35),
        "whoosh_long": (whoosh(0.8, 250, 7000, 2), 0.8),
        "swoosh_down": (whoosh(0.5, 6500, 300, 3), 0.5),
        "pop": (pop(), 0.12),
        "pop_soft": (pop(0.12, 800, 260, seed=5), 0.12),
        "click": (fade(key_click(7) * 0.9 + 0.3 * butter(rng(8).standard_normal(int(0.05 * SR)), 4000, "high") * exp_env(int(0.05 * SR), 0.002), 0.0005, 0.006), 0.05),
        "key_typing": (key_typing(), 1.5),
        "key_enter": (key_click(9, heavy=True), 0.09),
        "ding": (ding(), 0.6),
        "success_chime": (success_chime(), 0.9),
        "error_buzz": (error_buzz(), 0.4),
        "riser": (riser(2.0, 12), 2.0),
        "riser_short": (riser(1.0, 13), 1.0),
        "impact": (impact(), 0.8),
        "impact_soft": (impact(soft=True), 0.8),
        "glitch": (glitch(), 0.3),
        "deploy_launch": (deploy_launch(), 1.2),
        "notification_stack": (notification_stack(), 0.5),
    }


def trim_leading(x, thresh_db=-70, pad=0.002):
    """Drop leading near-silence only, so the sound starts on its cue time."""
    a = np.abs(x)
    idx = np.where(a > 10 ** (thresh_db / 20) * a.max())[0]
    s = max(idx[0] - int(pad * SR), 0) if len(idx) else 0
    return x[s:]


# per-sound output level (pop_soft / impact_soft are deliberately quieter)
LEVEL_DB = {"pop_soft": -9.0, "impact_soft": -8.0}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "sfx"))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    for name, (y, dur) in build().items():
        y = np.asarray(y, dtype=float)[: int(dur * SR)]
        y = y - np.mean(y)  # remove DC
        y = trim_leading(y, -70) if not name.startswith("riser") else y
        y = fade(y, 0.002, min(0.02, dur * 0.1))
        y = peak_normalize(y, -3.0 + LEVEL_DB.get(name, 0.0))
        assert np.all(np.isfinite(y))
        sf.write(os.path.join(a.out, name + ".wav"), y.astype(np.float32), SR, subtype="PCM_24")
        print(f"{name:20s} {len(y) / SR:6.3f}s")


if __name__ == "__main__":
    main()
