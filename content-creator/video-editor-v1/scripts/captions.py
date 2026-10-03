#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy"]
# ///
"""Thai captions: chunk each kept phrase and time every chunk to the cut audio.

Usage:
  captions.py edl.json cut.words.json --out captions.json [--keep "โปรเจกต์,Cloudflare Wrangler"]
              [--em "ปัญหาหลัก,ฟรี"] [--budget 14] [--propose]

Inputs:
  edl.json        from cut_plan.py; each segment has "text" and optional "chunks" ("a / b / c").
  cut.words.json  transcribe.py run on the CUT voice.wav (not the source).

Behaviour:
  - Segments without "chunks" are auto-chunked: Intl.Segmenter words, re-joined with the
    --keep list (brands, loanwords, numbers like 5-6), packed to <= --budget visible
    characters (Thai combining marks do not count), preferring phrase boundaries.
    --propose prints the proposal as JSON lines to paste back into segments.json and stops.
    Always review chunks by eye: a chunk must read as a natural spoken unit.
  - Each chunk is located in the cut transcript by character alignment (spaces/case
    ignored), clamped to its segment window, and shown 80 ms before it is spoken.
  - English words, numbers, and --em words are wrapped in <em> (keyword colour).
  - Verification: prints, per segment, how closely the cut transcript matches the planned
    text. A ratio under 0.80 usually means a clipped word or a bad cut - inspect it.
"""
import argparse
import difflib
import json
import os
import re
import subprocess
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import die, load_json, save_json  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


def vis(s):
    return sum(1 for ch in s if unicodedata.category(ch) != "Mn")


def segment_words(phrases):
    p = subprocess.run(["node", os.path.join(HERE, "thai_segment.mjs")], input=json.dumps(phrases),
                       capture_output=True, text=True)
    if p.returncode:
        die(p.stderr)
    return json.loads(p.stdout)


def join_keep(words, keep):
    """Re-join ICU fragments that spell a keep-together term (no spaces inside)."""
    out, i = [], 0
    terms = sorted([k for k in keep if " " not in k], key=len, reverse=True)
    while i < len(words):
        for kt in terms:
            acc, j = "", i
            while j < len(words) and len(acc) < len(kt):
                acc += words[j]; j += 1
            if acc == kt:
                out.append(kt); i = j; break
        else:
            w = words[i]
            if out and re.fullmatch(r"[,.!?]", w):
                out[-1] += w
            else:
                out.append(w)
            i += 1
    return out


def auto_chunk(text, keep, budget):
    phrases = text.split()
    words = segment_words(phrases)
    units = []  # (phrase string, word list)
    for ph, ws in zip(phrases, words):
        if units and (units[-1][0] + " " + ph) in keep:
            units[-1] = (units[-1][0] + " " + ph, [units[-1][0] + " " + ph]); continue
        units.append((ph, join_keep(ws, keep)))
    chunks, cur = [], ""
    for ph, ws in units:
        cand = (cur + " " + ph) if cur else ph
        if vis(cand) <= budget:
            cur = cand; continue
        prefix = ""
        if cur and vis(cur) <= 3:
            prefix = cur + " "          # a tiny leftover leads into the next phrase
        elif cur:
            chunks.append(cur)
        cur = ""
        if not prefix and vis(ph) <= budget:
            cur = ph; continue
        piece = prefix
        for w in ws:
            if piece.strip() and vis(piece + w) > budget:
                chunks.append(piece.strip()); piece = ""
            piece += w
        cur = piece.strip()
    if cur:
        chunks.append(cur)
    merged = []
    for c in chunks:
        if merged and vis(c) <= 3 and vis(merged[-1]) + vis(c) <= budget + 5:
            merged[-1] = merged[-1] + (" " if (merged[-1] + " " + c) in text else "") + c
        else:
            merged.append(c)
    return merged


EN = re.compile(r"([A-Za-z][A-Za-z0-9\-]*(?: [A-Z][A-Za-z0-9\-]*)*|\d+(?:[-.,:]\d+)*%?)")


def markup(text, em):
    out = EN.sub(r"<em>\1</em>", text)
    for w in sorted(em, key=len, reverse=True):
        if w and w in out and f"<em>{w}" not in out:
            out = out.replace(w, f"<em>{w}</em>", 1)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("edl")
    ap.add_argument("cut_words")
    ap.add_argument("--out", required=True)
    ap.add_argument("--keep", default="", help="comma list of keep-together terms")
    ap.add_argument("--em", default="", help="comma list of extra keyword-highlight words")
    ap.add_argument("--budget", type=int, default=14)
    ap.add_argument("--propose", action="store_true")
    a = ap.parse_args()
    edl, cw = load_json(a.edl), load_json(a.cut_words)
    keep = [k.strip() for k in a.keep.split(",") if k.strip()]
    em = [k.strip() for k in a.em.split(",") if k.strip()]
    segs = edl["segments"]
    chunked = []
    for s in segs:
        ch = [c.strip() for c in s["chunks"].split(" / ")] if s.get("chunks") else auto_chunk(s["text"], keep, a.budget)
        if "".join("".join(ch).split()) != "".join(s["text"].split()):
            die(f"segment {s['n']}: chunks do not spell the text exactly:\n  {ch}\n  {s['text']}")
        chunked.append(ch)
    if a.propose:
        for s, ch in zip(segs, chunked):
            print(json.dumps({"n": s["n"], "chunks": " / ".join(ch)}, ensure_ascii=False))
        return

    cut = [(c[0].lower(), c[1], c[2]) for c in cw["chars"] if not c[0].isspace()]
    B = "".join(c[0] for c in cut)
    flat = []  # (char, chunk index)
    meta = []
    for s, ch in zip(segs, chunked):
        for c in ch:
            meta.append({"seg": s["n"], "text": c, "lo": s["out_start"], "hi": s["out_end"]})
            for x in "".join(c.split()).lower():
                flat.append((x, len(meta) - 1))
    A = "".join(x for x, _ in flat)
    sm = difflib.SequenceMatcher(None, A, B, autojunk=False)
    t0s, t1s = [None] * len(A), [None] * len(A)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for d in range(i2 - i1):
                t0s[i1 + d], t1s[i1 + d] = cut[j1 + d][1], cut[j1 + d][2]
    known = [i for i, v in enumerate(t0s) if v is not None]
    if not known:
        die("no alignment between captions and cut transcript")
    import numpy as np
    s0 = np.interp(range(len(A)), known, [t0s[i] for i in known])
    s1 = np.interp(range(len(A)), known, [t1s[i] for i in known])
    print(f"alignment: {100 * len(known) / len(A):.1f}% of caption characters matched the cut audio")
    caps = []
    for ci, m in enumerate(meta):
        idx = [i for i, (_, c) in enumerate(flat) if c == ci]
        st = min(max(float(s0[idx[0]]), m["lo"]), m["hi"])
        en = min(max(float(s1[idx[-1]]), m["lo"]), m["hi"])
        if caps:
            st = max(st, caps[-1]["start"] + 0.2)
        caps.append({"seg": m["seg"], "text": m["text"], "start": round(st, 3), "end": round(en, 3)})
    dur = edl["duration"]
    for i, c in enumerate(caps):
        nxt = caps[i + 1]["start"] if i + 1 < len(caps) else dur
        c["show"] = round(max(c["start"] - 0.08, 0), 3)
        c["hide"] = round(min(nxt - 0.08, max(c["end"] + 0.35, c["start"] + 0.5)), 3) if i + 1 < len(caps) else round(dur, 3)
        if c["hide"] <= c["show"] + 0.15:
            c["hide"] = round(c["show"] + 0.2, 3)
        c["html"] = markup(c["text"], em)
    save_json(caps, a.out)
    print(f"{len(caps)} caption chunks -> {a.out}")
    print("\nverification (planned text vs cut transcript per segment):")
    bad = 0
    for s in segs:
        heard = "".join(c[0] for c in cut if s["out_start"] - 0.1 <= c[1] <= s["out_end"] + 0.1)
        r = difflib.SequenceMatcher(None, "".join(s["text"].split()).lower(), heard).ratio()
        flag = "  <- CHECK" if r < 0.80 else ""
        bad += bool(flag)
        print(f"  seg {s['n']:2d} {r:.2f}{flag}  {s['text'][:60]}")
    print("all segments look intact" if not bad else f"{bad} segment(s) need a listen")


if __name__ == "__main__":
    main()
