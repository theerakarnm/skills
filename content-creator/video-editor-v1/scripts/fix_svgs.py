#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Make SVG files usable in <img>: add the missing xmlns and drop web-app class attributes.

Usage:
  fix_svgs.py DIR

SVGs scraped from docs sites (e.g. Cloudflare product icons) often lack
xmlns="http://www.w3.org/2000/svg"; inline they work, but in <img> they render as a
broken image. The glyph itself is not changed (never redraw a brand mark).
"""
import os
import re
import sys

d = sys.argv[1] if len(sys.argv) > 1 else "."
fixed = []
for f in sorted(os.listdir(d)):
    if not f.endswith(".svg"):
        continue
    p = os.path.join(d, f)
    s = open(p, encoding="utf-8").read()
    m = re.search(r"<svg\b[^>]*>", s)
    if not m:
        continue
    tag = m.group(0)
    if 'xmlns="http://www.w3.org/2000/svg"' in tag:
        continue
    nt = re.sub(r'\sclass="[^"]*"', "", tag.replace("<svg", '<svg xmlns="http://www.w3.org/2000/svg"', 1))
    open(p, "w", encoding="utf-8").write(s.replace(tag, nt, 1))
    fixed.append(f)
print(f"fixed {len(fixed)} svg(s): {', '.join(fixed)}" if fixed else "all svgs ok")
