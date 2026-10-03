#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Find when phrases are spoken, in order, from a words.json.

Usage:
  timing.py words.json "phrase one" "phrase two" ...

Prints `start end phrase` per phrase. Each search starts after the previous hit,
so list phrases in speaking order. Matching ignores spaces and case, because
whisper spaces Thai unpredictably. Use the printed starts as beat times for
kinetic text, b-roll cues, zoom bumps, and SFX.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import load_json  # noqa: E402


def index(words):
    keep = [(c[0].lower(), c[1], c[2]) for c in words["chars"] if not c[0].isspace()]
    return "".join(k[0] for k in keep), keep


def find(words, phrase, after=0.0):
    s, keep = index(words)
    p = "".join(phrase.split()).lower()
    i = s.find(p)
    while i >= 0 and keep[i][1] < after - 1e-6:
        i = s.find(p, i + 1)
    if i < 0:
        return None
    return keep[i][1], keep[i + len(p) - 1][2]


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    w = load_json(sys.argv[1])
    after = 0.0
    for ph in sys.argv[2:]:
        r = find(w, ph, after)
        if r is None:
            print(f"   ---     ---  {ph}  (not found after {after:.2f})")
            continue
        print(f"{r[0]:7.2f} {r[1]:7.2f}  {ph}")
        after = r[0]


if __name__ == "__main__":
    main()
