"""Synthesized background music bed (minimal modern tech / lo-fi electronic, A minor).

Usage: python bgm.py --duration SECONDS --out PATH [--sections JSON] [--bpm 104] [--meta bgm_meta.json]
"""
import argparse
import json
import os

import numpy as np
import pyloudnorm as pyln
import soundfile as sf
from scipy import signal

from dsp import SR, butter, lookahead_limiter, make_ir, peaking, phase_from_freq, undb

HERE = os.path.dirname(os.path.abspath(__file__))

# A minor: Am9 - Fmaj7 - Cmaj7 - G6 (pad voicings, bass root, arp tones)
CHORDS = [
    {"pad": [57, 60, 64, 67, 71], "root": 33, "arp": [69, 72, 76, 79, 83]},
    {"pad": [53, 57, 60, 64, 67], "root": 29, "arp": [65, 69, 72, 76, 79]},
    {"pad": [55, 60, 64, 67, 71], "root": 36, "arp": [67, 72, 76, 79, 84]},
    {"pad": [55, 59, 62, 64, 67], "root": 31, "arp": [67, 71, 74, 76, 79]},
]

# per-layer level by energy (0 = muted)
LEVELS = {
    "low":   {"pad": 1.0, "arp": 0.55, "arp2": 0.0, "kick": 0.0, "hat": 0.0, "hat16": 0.0, "bass": 0.0, "clap": 0.0, "vinyl": 1.0},
    "mid":   {"pad": 0.9, "arp": 0.8, "arp2": 0.0, "kick": 1.0, "hat": 0.8, "hat16": 0.0, "bass": 1.0, "clap": 0.0, "vinyl": 0.7},
    "high":  {"pad": 0.85, "arp": 1.0, "arp2": 0.55, "kick": 1.0, "hat": 1.0, "hat16": 0.45, "bass": 1.0, "clap": 1.0, "vinyl": 0.6},
    "outro": {"pad": 0.9, "arp": 0.8, "arp2": 0.0, "kick": 0.9, "hat": 0.7, "hat16": 0.0, "bass": 0.9, "clap": 0.0, "vinyl": 0.8},
    "drop":  {"pad": 0.8, "arp": 0.0, "arp2": 0.0, "kick": 0.0, "hat": 0.0, "hat16": 0.0, "bass": 0.0, "clap": 0.0, "vinyl": 0.4},
}
RANK = {"low": 0, "drop": 0, "mid": 1, "outro": 1, "high": 2}


def mtof(m):
    return 440.0 * 2 ** ((m - 69) / 12)


class Bus:
    """Stereo layer buffer with event placement."""

    def __init__(self, n):
        self.x = np.zeros((n, 2))

    def add(self, s, t, gain=1.0, pan=0.0):
        if gain <= 0:
            return
        i = int(round(t * SR))
        if i >= len(self.x):
            return
        s = s if s.ndim == 2 else s[:, None] * np.ones((1, 2))
        m = min(len(s), len(self.x) - i)
        lg, rg = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
        self.x[i:i + m, 0] += s[:m, 0] * gain * lg * np.sqrt(2)
        self.x[i:i + m, 1] += s[:m, 1] * gain * rg * np.sqrt(2)


# ---------------------------------------------------------------- instruments
def kick():
    n = int(0.35 * SR)
    t = np.arange(n) / SR
    f = 48 + 70 * np.exp(-t / 0.03)
    body = np.sin(phase_from_freq(f)) * np.exp(-t / 0.11)
    click = butter(np.random.default_rng(1).standard_normal(n), 1500, "low") * np.exp(-t / 0.003) * 0.15
    y = np.tanh(1.3 * (body + click))
    y[: 48] *= np.linspace(0, 1, 48)
    return y * 0.9


def hat(seed, open_=False):
    n = int((0.28 if open_ else 0.06) * SR)
    t = np.arange(n) / SR
    rng = np.random.default_rng(seed)
    metal = sum(np.sign(np.sin(2 * np.pi * f * t + rng.uniform(0, 6.28))) for f in (317, 421, 563, 709, 857, 1013))
    src = 0.6 * rng.standard_normal(n) + 0.15 * metal
    src = butter(src, 7000, "high", 4)
    src = butter(src, 15000, "low", 2)
    y = src * np.exp(-t / (0.09 if open_ else 0.012))
    y[:24] *= np.linspace(0, 1, 24)
    return y * 0.35


def clap(seed=3):
    n = int(0.3 * SR)
    t = np.arange(n) / SR
    rng = np.random.default_rng(seed)
    env = np.zeros(n)
    for k, d in enumerate((0.0, 0.009, 0.019, 0.027)):
        i = int(d * SR)
        env[i:] += np.exp(-(t[: n - i]) / (0.006 if k < 3 else 0.07)) * (0.8 if k < 3 else 1.0)
    y = butter(rng.standard_normal(n), [900, 5000], "band", 2) * env
    y[:24] *= np.linspace(0, 1, 24)
    return y * 0.3


def bass_note(midi, dur):
    n = int((dur + 0.08) * SR)
    t = np.arange(n) / SR
    f = mtof(midi)
    y = np.sin(2 * np.pi * f * t) + 0.18 * np.sin(4 * np.pi * f * t)
    y = np.tanh(1.5 * y) / np.tanh(1.5)
    a, r = int(0.006 * SR), int(0.07 * SR)
    env = np.ones(n)
    env[:a] = np.linspace(0, 1, a)
    s_end = n - r
    env[s_end:] = np.linspace(1, 0, r) ** 2
    env *= 0.85 + 0.15 * np.exp(-t / 0.15)
    return y * env * 0.55


_pluck_cache = {}


def pluck(midi, seed=0):
    key = (midi, seed)
    if key in _pluck_cache:
        return _pluck_cache[key]
    n = int(0.6 * SR)
    t = np.arange(n) / SR
    f = mtof(midi)
    out = np.zeros((n, 2))
    det = (-4, 4)  # cents per channel for width
    for ch in range(2):
        ff = f * 2 ** (det[ch] / 1200)
        y = np.zeros(n)
        for k in range(1, 30):
            if k * ff > 9000:
                break
            tau = 0.32 / (1 + 0.9 * (k - 1))
            y += np.sin(2 * np.pi * k * ff * t + 0.3 * k) / k ** 1.15 * np.exp(-t / tau)
        out[:, ch] = y
    out[:48] *= np.linspace(0, 1, 48)[:, None]
    out[-480:] *= np.linspace(1, 0, 480)[:, None]
    _pluck_cache[key] = out * 0.22
    return _pluck_cache[key]


_pad_cache = {}


def pad_chord(ci, dur):
    key = (ci, round(dur, 4))
    if key in _pad_cache:
        return _pad_cache[key]
    rel = 1.2
    n = int((dur + rel) * SR)
    t = np.arange(n) / SR
    out = np.zeros((n, 2))
    rng = np.random.default_rng(100 + ci)
    for m in CHORDS[ci]["pad"]:
        f = mtof(m)
        for ch in range(2):
            for v, cents in enumerate((-9, 0, 9)):
                ff = f * 2 ** ((cents + (3 if ch else -3)) / 1200)
                ph0 = rng.uniform(0, 2 * np.pi)
                for k in range(1, 9):
                    if k * ff > 5000:
                        break
                    out[:, ch] += np.sin(2 * np.pi * k * ff * t + ph0 * k) / k
    out = butter(out, 1600, "low", 2)
    out = butter(out, 170, "high", 2)
    a = int(0.45 * SR)
    env = np.ones(n)
    env[:a] = np.sin(np.linspace(0, np.pi / 2, a)) ** 2
    rs = int(dur * SR)
    env[rs:] = np.cos(np.linspace(0, np.pi / 2, n - rs)) ** 2
    env *= 1 + 0.06 * np.sin(2 * np.pi * 0.25 * t)  # slow breathing
    out *= env[:, None]
    out /= np.max(np.abs(out)) + 1e-9
    _pad_cache[key] = out * 0.28
    return _pad_cache[key]


def reverse_cymbal(dur, seed=9):
    n = int(dur * SR)
    t = np.arange(n) / SR
    rng = np.random.default_rng(seed)
    y = butter(rng.standard_normal((n, 2)), 3000, "high", 2)
    y = butter(y, 12000, "low", 2)
    env = np.exp(-t / (dur * 0.35))[::-1]
    y *= env[:, None]
    y[-96:] *= np.linspace(1, 0, 96)[:, None]
    return y * 0.12


def vinyl(n, seed=5):
    rng = np.random.default_rng(seed)
    hiss = butter(rng.standard_normal((n, 2)), [1500, 8000], "band", 1) * 0.004
    crack = np.zeros((n, 2))
    k = int(n / SR * 6)
    pos = rng.integers(0, n - 200, k)
    amp = rng.uniform(0.01, 0.05, k) * (rng.random(k) < 0.85)
    for p, a in zip(pos, amp):
        crack[p:p + 60, rng.integers(0, 2)] += a * np.exp(-np.arange(60) / 8) * rng.choice([-1, 1])
    crack = butter(crack, 6000, "low", 2)
    return hiss + crack


# ---------------------------------------------------------------- arrangement
def default_sections(duration):
    return [
        {"start": 0.0, "energy": "low"},
        {"start": 6.0, "energy": "mid"},
        {"start": 0.35 * duration, "energy": "high"},
        {"start": 0.85 * duration, "energy": "outro"},
    ]


def bar_energies(sections, nbars, bar):
    """Quantize section starts to the nearest bar; expand 'drop' to 1 bar then return."""
    secs = sorted(sections, key=lambda s: s["start"])
    q = []
    for s in secs:
        b = int(round(s["start"] / bar))
        b = min(max(b, 0), nbars)
        if q and q[-1][0] == b:
            q[-1] = (b, s["energy"])
        else:
            q.append((b, s["energy"]))
    if not q or q[0][0] != 0:
        q.insert(0, (0, "low"))
    per = []
    used = []
    prev_energy = "low"
    for i, (b, e) in enumerate(q):
        end = q[i + 1][0] if i + 1 < len(q) else nbars
        if end <= b:
            continue
        for k in range(b, end):
            if e == "drop":
                per.append("drop" if k == b else (prev_energy if prev_energy != "drop" else "high"))
            else:
                per.append(e)
        used.append({"bar": b, "start": round(b * bar, 4), "end": round(end * bar, 4), "energy": e})
        if e != "drop":
            prev_energy = e
    return per[:nbars], used


def render(duration, sections, bpm=104.0, seed=2026):
    beat = 60.0 / bpm
    bar = 4 * beat
    n = int(round(duration * SR))
    tail = 2.0
    nbars = int(np.floor((duration - tail) / bar + 1e-9))
    music_end = nbars * bar
    energies, used = bar_energies(sections, nbars, bar)
    rng = np.random.default_rng(seed)

    names = ["pad", "arp", "arp2", "kick", "hat", "hat16", "bass", "clap", "fx", "vinyl"]
    bus = {k: Bus(n) for k in names}
    K = kick()
    H = [hat(s) for s in range(6)]
    HO = hat(77, open_=True)
    C = clap()
    arp_pat = [0, 2, 1, 3, 2, 4, 3, 1]
    arp2_pat = [4, 3, 2, 3, 4, 2, 1, 2, 4, 3, 2, 0, 1, 2, 3, 4]
    bass_pat = [(0.0, 1.35, 0), (1.5, 0.4, 0), (2.5, 0.9, 7), (3.5, 0.4, 12)]
    swing = 0.06 * beat  # late off-beat 16ths/8ths

    for b in range(nbars):
        e = energies[b]
        L = LEVELS[e]
        t0 = b * bar
        ci = b % 4
        ch = CHORDS[ci]
        var = (b // 4) % 2  # 8-bar cycle variation so loops never sound like a restart
        r = np.random.default_rng(seed + b)
        # pad: one sustained chord per bar, overlapping release
        bus["pad"].add(pad_chord(ci, bar), t0, L["pad"])
        # arp: 8ths; low energy = quarter notes only
        for i in range(8):
            if e == "low" and i % 2:
                continue
            idx = arp_pat[(i + 2 * var) % 8]
            m = ch["arp"][idx]
            tt = t0 + i * beat / 2 + (swing if i % 2 else 0)
            bus["arp"].add(pluck(m), tt, L["arp"] * r.uniform(0.75, 1.0), pan=0.25 * np.sin(i * np.pi / 2))
        # fuller arp layer an octave up on 16ths (high only)
        for i in range(16):
            if L["arp2"] <= 0:
                break
            m = ch["arp"][arp2_pat[i]] + 12
            tt = t0 + i * beat / 4 + (swing / 2 if i % 2 else 0)
            bus["arp2"].add(pluck(m), tt, L["arp2"] * (0.5 + 0.5 * (i % 4 == 0)) * r.uniform(0.6, 0.9), pan=-0.4 if i % 2 else 0.4)
        # drums
        kpat = [0, 2] if b % 2 == 0 else [0, 2, 2.75]
        for k in kpat:
            bus["kick"].add(K, t0 + k * beat, L["kick"] * (1.0 if k in (0, 2) else 0.7))
        for i in range(8):
            off = i % 2 == 1
            tt = t0 + i * beat / 2 + (swing if off else 0)
            vel = (0.95 if off else 0.6) * r.uniform(0.85, 1.0)
            if e == "high" and i == 7 and b % 2 == 1:
                bus["hat"].add(HO, tt, L["hat"] * 0.7, pan=0.2)
            else:
                bus["hat"].add(H[r.integers(0, 6)], tt, L["hat"] * vel, pan=0.2)
        for i in range(16):
            if i % 2 == 0 or L["hat16"] <= 0:
                continue
            bus["hat16"].add(H[r.integers(0, 6)], t0 + i * beat / 4 + swing / 2, L["hat16"] * r.uniform(0.3, 0.5), pan=-0.3)
        for k in (1, 3):
            bus["clap"].add(C, t0 + k * beat + 0.004, L["clap"])
        # bass
        for st, du, semi in bass_pat:
            if var == 1 and st == 3.5:
                semi = 10
            bus["bass"].add(bass_note(ch["root"] + 12 + semi if semi else ch["root"] + 12, du * beat), t0 + st * beat, L["bass"])
        # fills into the next bar if energy rises (or a drop returns)
        if b + 1 < nbars:
            nxt = energies[b + 1]
            rising = RANK[nxt] > RANK[e] or (e == "drop" and nxt != "drop")
            if rising and nxt != "drop":
                bus["fx"].add(reverse_cymbal(bar, seed + b), t0, 1.0)
                if LEVELS[nxt]["hat"] > 0:
                    for j in range(8):  # 32nd-note hat roll over the last beat, crescendo
                        bus["fx"].add(H[j % 6], t0 + 3 * beat + j * beat / 8, 0.25 + 0.6 * j / 7, pan=0.1)
            elif nxt == "drop":
                bus["fx"].add(reverse_cymbal(beat * 2, seed + b), t0 + bar - 2 * beat, 0.8)

    # final ringing chord in the tail
    bus["pad"].add(pad_chord(0, 0.6), music_end, 1.0)
    bus["vinyl"].x[:] = vinyl(n) * np.array([[1.0, 1.0]])
    vin_curve = np.ones(n)
    for b in range(nbars):
        vin_curve[int(b * bar * SR):int((b + 1) * bar * SR)] = LEVELS[energies[b]]["vinyl"]
    bus["vinyl"].x *= signal.fftconvolve(vin_curve, np.hanning(4801) / np.hanning(4801).sum(), mode="same")[:, None]

    # outro fade: drums/bass fade over the last 4 s of music; tonal layers keep going into the tail
    t = np.arange(n) / SR
    f_drums = np.clip((music_end - t) / 4.0, 0, 1) ** 1.5
    f_tonal = np.clip((duration - t) / (duration - music_end + 4.0), 0, 1) ** 1.2
    for k in ("kick", "hat", "hat16", "bass", "clap", "fx"):
        bus[k].x *= f_drums[:, None]
    for k in ("arp", "arp2", "vinyl"):
        bus[k].x *= f_tonal[:, None]

    # mix with reverb send
    gains = {"pad": 1.6, "arp": 1.4, "arp2": 0.9, "kick": 0.5, "hat": 1.1, "hat16": 0.9, "bass": 0.38, "clap": 0.8, "fx": 0.9, "vinyl": 0.8}
    sends = {"pad": 0.35, "arp": 0.35, "arp2": 0.3, "clap": 0.25, "hat": 0.05, "fx": 0.2}
    dry = sum(bus[k].x * gains[k] for k in names)
    send = sum(bus[k].x * gains[k] * sends[k] for k in sends)
    ir = make_ir(1.8, 0.45, seed=11, stereo=True, lp=6000)
    wet = np.stack([signal.fftconvolve(send[:, c], ir[:, c])[:n] for c in range(2)], axis=1)
    wet = butter(wet, 250, "high", 2)
    mix = dry + 0.6 * wet

    # keep the voice band free: cut lows rumble, soften 300-600 Hz body and dip 1-4 kHz presence
    mix = butter(mix, 30, "high", 2)
    mix = peaking(mix, 450, -2.0, q=0.8)
    mix = peaking(mix, 2200, -4.0, q=0.6)
    mix = peaking(mix, 3800, -2.0, q=1.0)
    # sidechain-style pump on the tonal layers is implied by kick; keep it subtle: none here

    # clean tail: last 2 s fade fully to silence
    tail_n = int(tail * SR)
    mix[-tail_n:] *= (np.cos(np.linspace(0, np.pi / 2, tail_n)) ** 2)[:, None]
    mix[:96] *= np.linspace(0, 1, 96)[:, None]

    beat_times = [round(i * beat, 4) for i in range(int(nbars * 4) + 1)]
    meta = {
        "bpm": bpm,
        "bar_seconds": round(bar, 6),
        "beat_seconds": round(beat, 6),
        "duration": duration,
        "music_end": round(music_end, 4),
        "bars": nbars,
        "beat_times": beat_times,
        "bar_times": [round(i * bar, 4) for i in range(nbars + 1)],
        "sections": used,
    }
    return mix, meta


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--duration", type=float, required=True, help="total length in seconds (includes the 2 s tail)")
    ap.add_argument("--out", required=True, help="output WAV path (48 kHz stereo float)")
    ap.add_argument("--sections", default=None, help='JSON list or path, e.g. [{"start":0,"energy":"low"},{"start":8,"energy":"mid"}]')
    ap.add_argument("--bpm", type=float, default=104.0)
    ap.add_argument("--lufs", type=float, default=-20.0)
    ap.add_argument("--meta", default=os.path.join(HERE, "bgm_meta.json"))
    a = ap.parse_args()
    if a.sections:
        txt = open(a.sections).read() if os.path.exists(a.sections) else a.sections
        sections = json.loads(txt)
    else:
        sections = default_sections(a.duration)
    bad = [s for s in sections if s["energy"] not in LEVELS]
    if bad:
        raise SystemExit(f"unknown energy in {bad}; use low|mid|high|drop|outro")
    mix, meta = render(a.duration, sections, bpm=a.bpm)
    meter = pyln.Meter(SR)
    lufs = meter.integrated_loudness(mix)
    mix = mix * undb(a.lufs - lufs)
    mix = lookahead_limiter(mix, -1.0)
    final = meter.integrated_loudness(mix)
    assert np.all(np.isfinite(mix))
    sf.write(a.out, mix.astype(np.float32), SR, subtype="FLOAT")
    meta["lufs_integrated"] = round(final, 2)
    meta["peak_dbfs"] = round(20 * np.log10(np.max(np.abs(mix)) + 1e-12), 2)
    with open(a.meta, "w") as f:
        json.dump(meta, f, indent=1)
    print(f"BPM {meta['bpm']}  bar {meta['bar_seconds']:.4f}s  beat {meta['beat_seconds']:.4f}s  bars {meta['bars']}")
    for s in meta["sections"]:
        print(f"  section {s['energy']:6s} bar {s['bar']:3d}  {s['start']:8.3f}s -> {s['end']:8.3f}s")
    print(f"LUFS {final:.2f}  peak {meta['peak_dbfs']:.2f} dBFS  -> {a.out}  meta -> {a.meta}")


if __name__ == "__main__":
    main()
