#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy"]
# ///
"""Retention cut planner: turn a list of kept phrases into a frame-exact EDL.

Usage:
  cut_plan.py SOURCE.mp4 words.json segments.json --out edl.json [--sil-db -42] [--min-sil 0.30]

segments.json (you write it after reading words.txt):
  {"segments": [
     {"from": "first words of the kept phrase", "to": "last words of it",
      "text": "the corrected caption text for this phrase",
      "chunks": "optional / caption chunks / split by ' / '"},
     {"src": [61.7, 71.1], "text": "...", "chunks": "..."}     # manual source range override
  ]}
  - List kept phrases in speaking order. Anything not listed is cut
    (pauses, fillers, repeats, false starts, the "sorry this is clickbait" line).
  - "from"/"to" are matched against the transcript ignoring spaces and case,
    so copy them from words.txt exactly as whisper wrote them (typos included).
  - "text" is what the captions will say (fix brand names and mishearings here).

What it does:
  1. Locates each phrase, then snaps each edge to the quietest 10 ms frame
     nearby (start: -0.30..+0.06 s, end: -0.06..+0.35 s) so cuts never clip a word.
  2. Removes internal silences longer than --min-sil below --sil-db, keeping 60 ms each side.
  3. Quantizes every edge to the source frame grid (picture/sound stay in sync).
  4. Writes edl.json with the source keep ranges, an output-time map, the jump-cut
     times (for zoom alternation), and each segment's output window.
"""
import argparse
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import die, energy_db, load_json, probe, save_json, to16k  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source")
    ap.add_argument("words")
    ap.add_argument("segments")
    ap.add_argument("--out", required=True)
    ap.add_argument("--sil-db", type=float, default=-42.0)
    ap.add_argument("--min-sil", type=float, default=0.30)
    a = ap.parse_args()
    info = probe(a.source)
    fps = info["fps"]
    words = load_json(a.words)
    spec = load_json(a.segments)["segments"]
    keep = [(c[0].lower(), c[1], c[2]) for c in words["chars"] if not c[0].isspace()]
    text = "".join(k[0] for k in keep)

    wav = os.path.join(tempfile.mkdtemp(prefix="tths-"), "a.wav")
    to16k(a.source, wav)
    edb, hop = energy_db(wav)
    nf = len(edb)
    print(f"energy: median {sorted(edb)[nf // 2]:.1f} dB, silence threshold {a.sil_db} dB")

    def tf(t):
        return min(max(int(round(t / hop)), 0), nf - 1)

    def snap(t, lo, hi):
        i0, i1 = tf(t + lo), tf(t + hi)
        seg = edb[i0:i1 + 1]
        k = i0 + int(seg.argmin())
        return k * hop + 0.015, float(edb[k])

    def norm(s):
        return "".join(s.split()).lower()

    ranges, after = [], 0.0
    for n, sg in enumerate(spec):
        if "src" in sg:
            s, e = sg["src"]
            ranges.append([s, e]); after = e
            continue
        fa, ta = norm(sg["from"]), norm(sg["to"])
        i = text.find(fa)
        while i >= 0 and keep[i][1] < after - 0.01:
            i = text.find(fa, i + 1)
        if i < 0:
            die(f"segment {n}: 'from' not found after {after:.2f}s: {sg['from']}")
        j = text.find(ta, i)
        if j < 0:
            die(f"segment {n}: 'to' not found after 'from': {sg['to']}")
        j = j + len(ta) - 1
        s, sd = snap(keep[i][1], -0.30, 0.06)
        e, ed = snap(keep[j][2], -0.06, 0.35)
        warn = "  <- loud edge: fine if a neighbouring kept phrase continues here, else listen" if max(sd, ed) > -40 else ""
        print(f"seg {n:2d} src {s:7.2f}-{e:7.2f}  edge dB {sd:6.1f}/{ed:6.1f}{warn}")
        ranges.append([s, e]); after = keep[j][2]

    kept = []
    for n, (s, e) in enumerate(ranges):
        s = max(s, kept[-1][1] if kept else 0.0)
        i0, i1 = tf(s), tf(e)
        cur, k = s, i0
        while k <= i1:
            if edb[k] < a.sil_db:
                k2 = k
                while k2 <= i1 and edb[k2] < a.sil_db:
                    k2 += 1
                t0, t1 = k * hop + 0.015, k2 * hop + 0.015
                if t1 - t0 > a.min_sil and t0 > s + 0.05 and t1 < e - 0.05:
                    kept.append([cur, t0 + 0.06, n]); cur = t1 - 0.06
                k = k2
            else:
                k += 1
        kept.append([cur, e, n])

    q = lambda t: round(round(t * fps) / fps, 4)  # noqa: E731
    kept = [[q(s), q(e), n] for s, e, n in kept]
    kept = [k for k in kept if k[1] - k[0] >= 1 / fps - 1e-6]
    out_map, t = [], 0.0
    for s, e, n in kept:
        out_map.append([s, e, round(t, 4), round(t + e - s, 4), n]); t += e - s
    cuts = [out_map[i][2] for i in range(1, len(out_map)) if abs(out_map[i][0] - out_map[i - 1][1]) > 0.05]
    segout = []
    for n, sg in enumerate(spec):
        parts = [m for m in out_map if m[4] == n]
        if not parts:
            die(f"segment {n} has no kept audio")
        segout.append({"n": n, "text": sg["text"], "chunks": sg.get("chunks", ""),
                       "out_start": parts[0][2], "out_end": parts[-1][3]})
    save_json({"source": os.path.abspath(a.source), "fps": fps, "fps_str": info["fps_str"],
               "sample_rate": info.get("sample_rate", 48000), "duration": round(t, 4),
               "keep": kept, "map": out_map, "cuts": cuts, "segments": segout}, a.out)
    print(f"\n{len(kept)} pieces, {len(cuts)} jump cuts, output {t:.2f}s (source {info['duration']:.2f}s, "
          f"-{100 * (1 - t / info['duration']):.0f}%) -> {a.out}")


if __name__ == "__main__":
    main()
