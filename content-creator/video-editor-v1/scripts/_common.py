"""Shared helpers for the thai-talking-head-shorts scripts (stdlib + numpy only)."""
import json
import os
import shutil
import subprocess
import sys

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_MODEL = os.path.expanduser("~/.cache/whisper-cpp/ggml-large-v3.bin")
MODEL_URL = "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3.bin"


def die(msg):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


def run(cmd, **kw):
    """Run a command list, fail loudly with its output."""
    p = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if p.returncode != 0:
        die(f"command failed ({p.returncode}): {' '.join(cmd)}\n{p.stdout[-2000:]}\n{p.stderr[-4000:]}")
    return p.stdout


def need(binary):
    if not shutil.which(binary):
        die(f"'{binary}' is not on PATH")


def probe(path):
    """Return fps (float), fps_str, width, height, audio sample rate, duration."""
    need("ffprobe")
    out = run(["ffprobe", "-v", "error", "-show_entries",
               "stream=codec_type,width,height,r_frame_rate,sample_rate:format=duration",
               "-of", "json", path])
    j = json.loads(out)
    info = {"duration": float(j["format"]["duration"])}
    for s in j["streams"]:
        if s["codec_type"] == "video" and "fps" not in info:
            n, d = s["r_frame_rate"].split("/")
            info.update(fps=float(n) / float(d), fps_str=s["r_frame_rate"], width=s["width"], height=s["height"])
        if s["codec_type"] == "audio" and "sample_rate" not in info:
            info["sample_rate"] = int(s["sample_rate"])
    return info


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(obj, path):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)


def energy_db(wav16k_path, hop=0.01, win=0.03):
    """Frame RMS in dBFS of a 16 kHz mono 16-bit wav. Returns (db array, hop)."""
    import numpy as np
    import wave
    with wave.open(wav16k_path) as w:
        sr = w.getframerate()
        a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    h, n = int(sr * hop), int(sr * win)
    nf = max((len(a) - n) // h, 1)
    idx = np.arange(nf)[:, None] * h + np.arange(n)[None, :]
    rms = np.sqrt((a[idx] ** 2).mean(1) + 1e-12)
    return 20 * np.log10(rms), hop


def to16k(src, dst):
    need("ffmpeg")
    run(["ffmpeg", "-v", "error", "-y", "-i", src, "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", dst])
