"""Shared DSP helpers for the synthesized sound kit (numpy/scipy only)."""
import numpy as np
from scipy import signal

SR = 48000


def t_axis(dur, sr=SR):
    return np.arange(int(round(dur * sr))) / sr


def db(x):
    return 20 * np.log10(np.maximum(np.abs(x), 1e-12))


def undb(d):
    return 10 ** (d / 20)


def fade(x, fin=0.003, fout=0.01, sr=SR):
    x = x.copy()
    ni, no = int(fin * sr), int(fout * sr)
    if ni > 0:
        x[:ni] *= np.sin(np.linspace(0, np.pi / 2, ni)) ** 2
    if no > 0:
        x[-no:] *= np.cos(np.linspace(0, np.pi / 2, no)) ** 2
    return x


def adsr(n, a, d, s, r, sr=SR):
    """Smooth envelope in seconds; sustain level s; total length n samples."""
    a, d, r = int(a * sr), int(d * sr), int(r * sr)
    sus = max(n - a - d - r, 0)
    env = np.concatenate([
        np.linspace(0, 1, a, endpoint=False) ** 1.5 if a else np.zeros(0),
        1 - (1 - s) * (1 - np.exp(-5 * np.linspace(0, 1, d, endpoint=False))) / (1 - np.exp(-5)) if d else np.zeros(0),
        np.full(sus, s),
        s * np.exp(-5 * np.linspace(0, 1, r)) if r else np.zeros(0),
    ])
    out = np.zeros(n)
    m = min(n, len(env))
    out[:m] = env[:m]
    return out


def exp_env(n, tau, sr=SR):
    return np.exp(-np.arange(n) / (tau * sr))


def phase_from_freq(f, sr=SR):
    return 2 * np.pi * np.cumsum(f) / sr


def blit_saw(freq, n, sr=SR, harmonics_limit=None):
    """Band-limited saw via additive synthesis (freq may be array)."""
    f = np.broadcast_to(np.asarray(freq, dtype=float), (n,))
    ph = phase_from_freq(f, sr)
    fmax = f.max()
    K = int((sr / 2 * 0.9) // max(fmax, 1))
    if harmonics_limit:
        K = min(K, harmonics_limit)
    out = np.zeros(n)
    for k in range(1, max(K, 1) + 1):
        out += ((-1) ** (k + 1)) * np.sin(k * ph) / k
    return out * (2 / np.pi)


def bl_square(freq, n, sr=SR, harmonics_limit=None):
    f = np.broadcast_to(np.asarray(freq, dtype=float), (n,))
    ph = phase_from_freq(f, sr)
    K = int((sr / 2 * 0.9) // max(f.max(), 1))
    if harmonics_limit:
        K = min(K, harmonics_limit)
    out = np.zeros(n)
    for k in range(1, max(K, 1) + 1, 2):
        out += np.sin(k * ph) / k
    return out * (4 / np.pi)


def bandpass_sweep(x, f_start, f_end, q=2.0, sr=SR, block=256):
    """Time-varying 2-pole state-variable bandpass (TPT/SVF), exponential sweep."""
    n = len(x)
    fc = np.geomspace(f_start, f_end, n)
    return svf(x, fc, q, mode="bp", sr=sr)


def svf(x, fc, q=0.707, mode="lp", sr=SR):
    """Zavalishin TPT state-variable filter with per-sample cutoff."""
    fc = np.broadcast_to(np.asarray(fc, dtype=float), x.shape)
    g = np.tan(np.pi * np.clip(fc, 10, sr * 0.45) / sr)
    k = 1.0 / q
    a1 = 1 / (1 + g * (g + k))
    a2 = g * a1
    a3 = g * a2
    ic1 = ic2 = 0.0
    out = np.empty_like(x)
    sel = {"lp": 0, "bp": 1, "hp": 2}[mode]
    for i in range(len(x)):
        v0 = x[i]
        v3 = v0 - ic2
        v1 = a1[i] * ic1 + a2[i] * v3
        v2 = ic2 + a2[i] * ic1 + a3[i] * v3
        ic1 = 2 * v1 - ic1
        ic2 = 2 * v2 - ic2
        if sel == 0:
            out[i] = v2
        elif sel == 1:
            out[i] = v1
        else:
            out[i] = v0 - k * v1 - v2
    return out


def butter(x, fc, kind="low", order=2, sr=SR):
    sos = signal.butter(order, fc, btype=kind, fs=sr, output="sos")
    return signal.sosfilt(sos, x, axis=0)


def peaking(x, f0, gain_db, q=1.0, sr=SR):
    """RBJ peaking EQ."""
    A = 10 ** (gain_db / 40)
    w0 = 2 * np.pi * f0 / sr
    alpha = np.sin(w0) / (2 * q)
    b = [1 + alpha * A, -2 * np.cos(w0), 1 - alpha * A]
    a = [1 + alpha / A, -2 * np.cos(w0), 1 - alpha / A]
    return signal.lfilter(np.array(b) / a[0], np.array(a) / a[0], x, axis=0)


def shelf(x, f0, gain_db, kind="low", sr=SR):
    A = 10 ** (gain_db / 40)
    w0 = 2 * np.pi * f0 / sr
    cw, sw = np.cos(w0), np.sin(w0)
    alpha = sw / 2 * np.sqrt(2)
    sa = 2 * np.sqrt(A) * alpha
    if kind == "low":
        b = [A * ((A + 1) - (A - 1) * cw + sa), 2 * A * ((A - 1) - (A + 1) * cw), A * ((A + 1) - (A - 1) * cw - sa)]
        a = [(A + 1) + (A - 1) * cw + sa, -2 * ((A - 1) + (A + 1) * cw), (A + 1) + (A - 1) * cw - sa]
    else:
        b = [A * ((A + 1) + (A - 1) * cw + sa), -2 * A * ((A - 1) + (A + 1) * cw), A * ((A + 1) + (A - 1) * cw - sa)]
        a = [(A + 1) - (A - 1) * cw + sa, 2 * ((A - 1) - (A + 1) * cw), (A + 1) - (A - 1) * cw - sa]
    return signal.lfilter(np.array(b) / a[0], np.array(a) / a[0], x, axis=0)


def make_ir(dur=1.2, decay=0.35, seed=7, sr=SR, stereo=False, lp=7000):
    """Synthetic reverb IR: exponentially decaying filtered noise."""
    rng = np.random.default_rng(seed)
    n = int(dur * sr)
    ch = 2 if stereo else 1
    ir = rng.standard_normal((n, ch)) * np.exp(-np.arange(n) / (decay * sr))[:, None]
    ir = butter(ir, lp, "low", 2, sr)
    ir[: int(0.008 * sr)] *= np.linspace(0, 1, int(0.008 * sr))[:, None]
    ir /= np.sqrt(np.sum(ir ** 2, axis=0, keepdims=True))
    return ir if stereo else ir[:, 0]


def reverb(x, wet=0.2, dur=1.0, decay=0.3, seed=7, sr=SR):
    ir = make_ir(dur, decay, seed, sr)
    w = signal.fftconvolve(x, ir)[: len(x) + len(ir) - 1]
    y = np.zeros(len(w))
    y[: len(x)] += x * (1 - wet)
    return y + w * wet


def peak_normalize(x, target_db=-3.0):
    p = np.max(np.abs(x))
    return x if p == 0 else x * undb(target_db) / p


def trim_silence(x, thresh_db=-60, pad=0.005, sr=SR):
    a = np.abs(x) if x.ndim == 1 else np.max(np.abs(x), axis=1)
    idx = np.where(a > undb(thresh_db) * a.max())[0]
    if len(idx) == 0:
        return x
    s = max(idx[0] - int(pad * sr), 0)
    e = min(idx[-1] + int(pad * sr), len(x))
    return x[s:e]


def follower(x, attack, release, rate):
    """One-pole attack/release follower on a control-rate signal (rate = frames per second)."""
    ca = np.exp(-1 / (attack * rate)) if attack > 0 else 0.0
    cr = np.exp(-1 / (release * rate))
    out = np.empty(len(x))
    cur = float(x[0]) if len(x) else 0.0
    for i, v in enumerate(x):
        c = ca if v > cur else cr
        cur = v + (cur - v) * c
        out[i] = cur
    return out


def lookahead_limiter(x, ceiling_db=-1.0, lookahead=0.005, release=0.12, sr=SR, oversample=4, block=32):
    """Lookahead peak limiter. Peak is measured on a 4x oversampled signal (true-peak approximation).
    Gain never exceeds what is needed: min-filter over the lookahead window, block-rate release,
    then a positive smoothing kernel shorter than the lookahead window."""
    from scipy.ndimage import minimum_filter1d
    x2 = x if x.ndim == 2 else x[:, None]
    n = len(x2)
    ceil = undb(ceiling_db)
    up = signal.resample_poly(x2, oversample, 1, axis=0)
    pk = np.max(np.abs(up), axis=1)
    pk = np.pad(pk, (0, n * oversample - len(pk)))[: n * oversample].reshape(n, oversample).max(axis=1)
    need = np.minimum(1.0, ceil / np.maximum(pk, 1e-12))
    la = max(int(lookahead * sr), block)
    g1 = minimum_filter1d(need, 2 * la + 1, mode="nearest")
    nb = int(np.ceil(n / block))
    gb = np.pad(g1, (0, nb * block - n), constant_values=1.0).reshape(nb, block).min(axis=1)
    # instant attack, exponential release (in the "gain reduction" domain)
    gr = follower(1 - gb, 0.0, release, sr / block)
    r = np.repeat(np.minimum(1 - gr, gb), block)[:n]
    w = np.hanning(la + 1)
    w /= w.sum()
    g = signal.fftconvolve(r, w, mode="same")
    y = x2 * g[:, None]
    y = np.clip(y, -ceil, ceil)
    return y if x.ndim == 2 else y[:, 0]
