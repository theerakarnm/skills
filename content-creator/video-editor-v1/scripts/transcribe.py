#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy"]
# ///
"""Ears: transcribe a clip with whisper.cpp large-v3 and DTW token timestamps.

Usage:
  transcribe.py INPUT --out words.json [--lang th] [--model PATH]

Writes:
  words.json  {"text", "chars": [[char, t0, t1], ...], "segments": [{"start","end","text"}]}
  words.txt   one segment per line with times, for reading and planning.

Two passes (~70 s each for a 2:48 clip on this Mac):
  - text pass: normal decoding, the most accurate words;
  - timing pass: DTW token alignment (--dtw large.v3, flash attention off). Plain
    whisper.cpp timestamps drift up to ~1 s on Thai; DTW lands on the word.
The text is aligned to the DTW times character by character. Each token's time is
spread across its characters, so Thai text without spaces can be located exactly.
"""
import argparse
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import DEFAULT_MODEL, MODEL_URL, die, need, run, save_json, to16k  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input")
    ap.add_argument("--out", required=True)
    ap.add_argument("--lang", default="th")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--threads", default="8")
    ap.add_argument("--single-pass", action="store_true", help="DTW pass only (faster, may drop words)")
    a = ap.parse_args()
    need("whisper-cli")
    if not os.path.exists(a.model):
        die(f"model missing: {a.model}\nDownload (2.9 GB, ~10 min): curl -L --fail -o {a.model} {MODEL_URL}")
    tmp = tempfile.mkdtemp(prefix="tths-")
    wav = os.path.join(tmp, "a16k.wav")
    to16k(a.input, wav)
    import difflib
    import json

    def whisper(tag, extra):
        base = os.path.join(tmp, tag)
        run(["whisper-cli", "-m", a.model, "-l", a.lang, "-f", wav, "-ojf", "-of", base, "-t", a.threads, *extra])
        return json.load(open(base + ".json", encoding="utf-8"))

    def tokens(j):
        return [t for s in j["transcription"] for t in s["tokens"] if not t["text"].startswith("[_")]

    jt = whisper("timing", ["--dtw", "large.v3", "-nfa"])
    tt = tokens(jt)
    tchars = []
    for k, t in enumerate(tt):
        t0 = max(t.get("t_dtw", -1), 0) / 100
        t1 = (tt[k + 1].get("t_dtw", -1) / 100) if k + 1 < len(tt) else t0 + 0.2
        t1 = max(t1, t0 + 0.01)
        n = len(t["text"]) or 1
        for q, ch in enumerate(t["text"]):
            tchars.append([ch, t0 + (t1 - t0) * q / n, t0 + (t1 - t0) * (q + 1) / n])
    if a.single_pass:
        j, chars = jt, tchars
    else:
        # The DTW pass (flash attention off) sometimes drops or garbles words that the normal pass
        # gets right (verified: "ที่เราไม่ต้องสนใจ" vanished, "freelance" became "Philips").
        # So take the TEXT from a normal pass and the TIMES from the DTW pass, aligned per character.
        j = whisper("text", [])
        text_chars = [ch for t in tokens(j) for ch in t["text"]]
        A, B = "".join(text_chars), "".join(c[0] for c in tchars)
        t0s, t1s = [None] * len(A), [None] * len(A)
        for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, A, B, autojunk=False).get_opcodes():
            if tag == "equal":
                for d in range(i2 - i1):
                    t0s[i1 + d], t1s[i1 + d] = tchars[j1 + d][1], tchars[j1 + d][2]
        known = [i for i, v in enumerate(t0s) if v is not None]
        import numpy as np
        i0 = np.interp(range(len(A)), known, [t0s[i] for i in known])
        i1_ = np.interp(range(len(A)), known, [t1s[i] for i in known])
        chars = [[ch, float(i0[i]), float(i1_[i])] for i, ch in enumerate(text_chars)]
        print(f"aligned text pass to DTW times: {100 * len(known) / max(len(A), 1):.1f}% exact matches")
        # unmatched stretches (words only the text pass heard) get interpolated times
    chars = [[c, round(x, 3), round(y, 3)] for c, x, y in chars]
    segs = [{"start": s["offsets"]["from"] / 1000, "end": s["offsets"]["to"] / 1000, "text": s["text"].strip()}
            for s in j["transcription"]]
    text = "".join(c[0] for c in chars)
    save_json({"text": text, "chars": chars, "segments": segs}, a.out)
    txt = os.path.splitext(a.out)[0] + ".txt"
    with open(txt, "w", encoding="utf-8") as f:
        for s in segs:
            f.write(f"{s['start']:7.2f}-{s['end']:7.2f}  {s['text']}\n")
    print(f"wrote {a.out} ({len(chars)} chars) and {txt}")


if __name__ == "__main__":
    main()
