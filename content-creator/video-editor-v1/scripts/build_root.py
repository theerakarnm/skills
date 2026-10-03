#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Generate the root HyperFrames composition from edit.json.

Usage:
  build_root.py PROJECT_DIR            (reads PROJECT_DIR/edit.json)

Writes:
  index.html                   A-roll with jump-cut zoom alternation + punch bumps, b-roll hosts,
                               round face PiP during b-roll, overlay + caption layers, master audio.
  compositions/captions.html   one span per caption chunk, pop-in, hard hide.
  compositions/overlays.html   kinetic text over the wall area above the head (y 180-510).
  assets/fonts/*               Kanit + JetBrains Mono copied from the skill if missing.

edit.json (all times are OUTPUT seconds, i.e. after the cut):
{
  "edl": "assets/aroll/edl.json",          # duration + jump cuts come from here
  "captions": "assets/captions.json",
  "audio": "assets/audio/master.wav",
  "accent": "#F6821F", "accent2": "#FBAD41", "caption_em": "#FFB347",
  "zoom": {"base": 1.0, "alt": 1.11, "drift": 0.03, "origin_y": "47%"},
  "bumps": [3.54, 14.13],                  # punch pulses on key words, keep >= 5 s apart
  "caption_top": 1300,                     # caption box is 220 px tall; keep its bottom < 1536
  "pip": {"size": 240, "scale": 0.222, "center_y": 1040},   # center_y = source y of the head centre
  "name_tag": {"text": "@handle", "start": 1.0, "duration": 3.0},  # optional
  "broll": [{"id": "b01-ai-writes-code", "start": 4.75, "end": 11.2}],
  "overlays": [
    {"id": "k-hook", "start": 0.0, "end": 4.53,
     "html": "<div class=\"kcard dark k1a\">...</div><div class=\"kcard bad k1b\">...</div>",
     "events": [[0.05, ".k1a", "pop"], [3.45, ".k1a", "out"], [3.5, ".k1b", "slam"]]}
  ]
}
Overlay classes: kcard (+ dark|bad|acc|acc2|good), kchip (+ acc|bad|good), krow, arrow, ksub,
  strike (write <span class="strike">word<i class="sl"></i></span>), klogo (<img>), cta/cta-q/cta-s, spin.
Event kinds: pop, slam, out, strike (animates .sl inside the overlay), shake, spin.
Elements with a pop/slam event start hidden via CSS (never tl.set at 0: lint gsap_timeline_set_initial_hide).
"""
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import SKILL_DIR, die, load_json  # noqa: E402

W, H = 1080, 1920


def fmt(x):
    return f"{x:.3f}".rstrip("0").rstrip(".")


def fontface():
    css = "".join(f'@font-face{{font-family:"Kanit";src:url("assets/fonts/Kanit-{n}.ttf") format("truetype");'
                  f'font-weight:{w};font-style:normal;}}'
                  for n, w in [("Medium", 500), ("Bold", 700), ("ExtraBold", 800), ("Black", 900)])
    return css + '@font-face{font-family:"JetBrains Mono";src:url("assets/fonts/JetBrainsMono.ttf") format("truetype");font-weight:100 800;}'


SUBHEAD = '<!doctype html>\n<html lang="th">\n<head><meta charset="UTF-8" /></head>\n<body>\n<template>\n'
SUBTAIL = '</template>\n</body>\n</html>\n'


def overlay_css(acc, acc2):
    return f"""
#root{{position:absolute;inset:0;font-family:"Kanit",sans-serif}}
.kt{{position:absolute;left:0;top:180px;width:1080px;height:330px;z-index:9;display:flex;align-items:flex-start;justify-content:center}}
.ktin{{display:flex;flex-direction:column;align-items:center;gap:18px;width:960px}}
.krow{{display:flex;flex-wrap:wrap;justify-content:center;align-items:center;gap:16px}}
.kcard{{display:block;padding:18px 34px;border-radius:26px;font-weight:800;font-size:64px;line-height:1.3;color:#F4F1EC;background:#17191F;border:4px solid #2E323C;box-shadow:0 20px 50px rgba(0,0,0,.35);white-space:nowrap}}
.kcard.bad{{background:#FF5A5F;border-color:#FF5A5F;color:#fff;font-size:92px;font-weight:900}}
.kcard.bad b{{font-weight:900}}
.kcard.acc{{background:{acc};border-color:{acc};color:#140B02;font-size:86px;font-weight:900}}
.kcard.acc2{{background:#17191F;border-color:{acc};color:{acc2};font-size:58px}}
.kcard.good{{background:#3DDC97;border-color:#3DDC97;color:#06180F}}
.kchip{{display:block;padding:12px 26px;border-radius:999px;font-weight:700;font-size:44px;line-height:1.3;color:#F4F1EC;background:#17191F;border:4px solid #2E323C;white-space:nowrap;box-shadow:0 14px 34px rgba(0,0,0,.3)}}
.kchip.acc{{border-color:{acc};color:{acc2}}}
.kchip.bad{{border-color:#FF5A5F;color:#FF8A8D}}
.kchip.good{{border-color:#3DDC97;color:#7FF0C0;font-size:38px}}
.arrow{{display:block;font-size:60px;font-weight:900;color:{acc};text-shadow:0 4px 0 rgba(0,0,0,.25)}}
.ksub{{display:block;font-weight:700;font-size:40px;color:#17191F;background:rgba(244,241,236,.92);padding:8px 22px;border-radius:16px}}
.strike{{position:relative;display:inline-block}}
.sl{{position:absolute;left:-6px;right:-6px;top:52%;height:9px;background:#FF5A5F;border-radius:6px;transform-origin:0 50%;transform:scaleX(0)}}
.klogo{{height:58px;width:auto;vertical-align:-10px;margin-right:10px}}
.spin{{display:inline-block}}
.cta{{display:block;text-align:center;padding:30px 44px;border-radius:34px;background:{acc};border:5px solid {acc2};box-shadow:0 26px 70px rgba(0,0,0,.45)}}
.cta-q{{display:block;font-weight:900;font-size:76px;line-height:1.25;color:#140B02;white-space:nowrap}}
.cta-s{{display:block;font-weight:700;font-size:46px;line-height:1.3;color:#2A1606;margin-top:6px}}
#nametag{{position:absolute;left:60px;top:1190px;z-index:9}}
.ntin{{display:block;padding:10px 26px;border-radius:999px;background:#17191F;border:4px solid {acc};color:#F4F1EC;font-weight:700;font-size:40px;line-height:1.3;white-space:nowrap}}
"""


def overlay_js(ov):
    out = []
    for o in ov:
        kid = o["id"]
        for ev in o.get("events", []):
            t, sel, kind = ev[0], ev[1], ev[2]
            S = f'"#{kid} {sel}"'
            if kind == "pop":
                out.append(f'tl.fromTo({S},{{scale:0.6,y:24,opacity:0}},{{scale:1,y:0,opacity:1,duration:0.32,ease:"back.out(1.8)",immediateRender:false}},{t:.3f});')
            elif kind == "slam":
                out.append(f'tl.fromTo({S},{{scale:1.7,opacity:0}},{{scale:1,opacity:1,duration:0.22,ease:"power4.out",immediateRender:false}},{t:.3f})'
                           f'.fromTo({S},{{rotation:-3}},{{rotation:0,duration:0.35,ease:"elastic.out(1.2,0.4)",immediateRender:false}},{t + 0.2:.3f});')
            elif kind == "out":
                out.append(f'tl.to({S},{{opacity:0,scale:0.9,duration:0.12}},{t:.3f});')
            elif kind == "strike":
                out.append(f'tl.fromTo("#{kid} .sl",{{scaleX:0}},{{scaleX:1,duration:0.25,ease:"power3.out",immediateRender:false}},{t:.3f});')
            elif kind == "shake":
                out.append(f'tl.fromTo({S},{{rotation:0}},{{keyframes:[{{rotation:-4}},{{rotation:4}},{{rotation:-2}},{{rotation:0}}],duration:0.4,immediateRender:false}},{t:.3f});')
            elif kind == "spin":
                d = ev[3] if len(ev) > 3 else max(o["end"] - t, 0.5)
                out.append(f'tl.fromTo({S},{{rotation:0}},{{rotation:540,duration:{d:.3f},ease:"none",immediateRender:false}},{t:.3f});')
            else:
                die(f"overlay {kid}: unknown event kind {kind}")
        out.append(f'tl.fromTo("#{kid} .ktin",{{opacity:1}},{{opacity:0,duration:0.15,immediateRender:false}},{o["end"] - 0.15:.3f});')
    return out


def main():
    if len(sys.argv) != 2:
        print(__doc__); sys.exit(1)
    P = os.path.abspath(sys.argv[1])
    cfg = load_json(os.path.join(P, "edit.json"))
    edl = load_json(os.path.join(P, cfg.get("edl", "assets/aroll/edl.json")))
    caps = load_json(os.path.join(P, cfg.get("captions", "assets/captions.json")))
    DUR = round(edl["duration"], 3)
    acc, acc2, cem = cfg.get("accent", "#F6821F"), cfg.get("accent2", "#FBAD41"), cfg.get("caption_em", "#FFB347")
    os.makedirs(os.path.join(P, "compositions"), exist_ok=True)
    fdir = os.path.join(P, "assets", "fonts")
    os.makedirs(fdir, exist_ok=True)
    for f in os.listdir(os.path.join(SKILL_DIR, "assets", "fonts")):
        if not os.path.exists(os.path.join(fdir, f)):
            shutil.copy(os.path.join(SKILL_DIR, "assets", "fonts", f), fdir)

    bumps = sorted(cfg.get("bumps", []))
    for x, y in zip(bumps, bumps[1:]):
        if y - x < 5:
            print(f"warning: bumps {x} and {y} are under 5 s apart (rare zooms read stronger)")

    # ---------- captions.html ----------
    top = cfg.get("caption_top", 1300)
    if top + 220 > 1536:
        print("warning: caption box reaches the bottom 20% (platform UI zone)")
    cap_css = fontface() + f"""
#root{{position:absolute;inset:0;font-family:"Kanit",sans-serif}}
#capbox{{position:absolute;left:60px;top:{top}px;width:960px;height:220px;display:flex;align-items:center;justify-content:center;text-align:center}}
.cl{{position:absolute;opacity:0;display:block;max-width:960px;font-weight:800;font-size:70px;line-height:1.28;color:#FFFFFF;-webkit-text-stroke:12px #0B0B0D;paint-order:stroke fill;text-shadow:0 7px 0 rgba(0,0,0,.45);transform-origin:50% 60%}}
.cl em{{font-style:normal;color:{cem}}}
"""
    spans = "\n".join(f'<span id="cl{i}" class="cl">{c["html"]}</span>' for i, c in enumerate(caps))
    cjs = "\n".join(f'tl.fromTo("#cl{i}",{{opacity:0,scale:0.86,y:18}},{{opacity:1,scale:1,y:0,duration:0.12,ease:"back.out(2)",immediateRender:false}},{c["show"]:.3f}).set("#cl{i}",{{opacity:0}},{c["hide"]:.3f});'
                    for i, c in enumerate(caps))
    open(os.path.join(P, "compositions", "captions.html"), "w").write(
        SUBHEAD + f"<style>{cap_css}</style>\n"
        f'<div id="root" data-composition-id="captions" data-width="{W}" data-height="{H}" data-duration="{DUR}">\n'
        f'<div id="capbox">\n{spans}\n</div>\n</div>\n<script>\nconst tl = gsap.timeline({{ paused: true }});\n{cjs}\n'
        f'tl.set({{}},{{}},{DUR});\nwindow.__timelines["captions"] = tl;\n</script>\n' + SUBTAIL)

    # ---------- overlays.html ----------
    ov = cfg.get("overlays", [])
    hide = "".join(f"#{o['id']} {e[1]}{{opacity:0}}" for o in ov for e in o.get("events", []) if e[2] in ("pop", "slam"))
    blocks = [f'<div id="{o["id"]}" class="kt clip" data-start="{fmt(o["start"])}" data-duration="{fmt(o["end"] - o["start"])}" '
              f'data-track-index="{n % 4}"><div class="ktin">{o["html"]}</div></div>' for n, o in enumerate(ov)]
    js = overlay_js(ov)
    nt = cfg.get("name_tag")
    if nt:
        blocks.append(f'<div id="nametag" class="clip" data-start="{fmt(nt["start"])}" data-duration="{fmt(nt["duration"])}" '
                      f'data-track-index="5"><span class="ntin">{nt["text"]}</span></div>')
        js.append(f'tl.fromTo("#nametag .ntin",{{x:-60,opacity:0}},{{x:0,opacity:1,duration:0.35,ease:"power3.out",immediateRender:false}},{nt["start"]:.3f})'
                  f'.to("#nametag .ntin",{{opacity:0,duration:0.2}},{nt["start"] + nt["duration"] - 0.2:.3f});')
    open(os.path.join(P, "compositions", "overlays.html"), "w").write(
        SUBHEAD + f"<style>{fontface()}{overlay_css(acc, acc2)}{hide}</style>\n"
        f'<div id="root" data-composition-id="overlays" data-width="{W}" data-height="{H}" data-duration="{DUR}">\n'
        + "\n".join(blocks) + "\n</div>\n<script>\nconst tl = gsap.timeline({ paused: true });\n" + "\n".join(js)
        + f"\ntl.set({{}},{{}},{DUR});\nwindow.__timelines[\"overlays\"] = tl;\n</script>\n" + SUBTAIL)

    # ---------- index.html ----------
    z = cfg.get("zoom", {})
    zb, za, zd, zo = z.get("base", 1.0), z.get("alt", 1.11), z.get("drift", 0.03), z.get("origin_y", "47%")
    bounds = [0.0] + list(edl["cuts"]) + [DUR]
    jz = [f'tl.fromTo("#cam",{{scale:{(zb if i % 2 == 0 else za):.3f}}},{{scale:{(zb if i % 2 == 0 else za) + zd:.3f},'
          f'duration:{max(bounds[i + 1] - bounds[i] - 0.004, 0.01):.3f},ease:"none",immediateRender:false}},{bounds[i] + 0.001:.3f});'
          for i in range(len(bounds) - 1)]
    jb = [f'tl.fromTo("#bump",{{scale:1}},{{scale:1.07,duration:0.14,ease:"power2.out",immediateRender:false}},{t:.3f})'
          f'.to("#bump",{{scale:1,duration:0.45,ease:"power2.inOut"}},{t + 0.145:.3f});' for t in bumps]
    br = cfg.get("broll", [])
    hosts, jh, jp = [], [], []
    for n, b in enumerate(br):
        if not os.path.exists(os.path.join(P, "compositions", b["id"] + ".html")):
            print(f"note: compositions/{b['id']}.html not written yet")
        hosts.append(f'<div id="host-{b["id"]}" class="broll" data-composition-id="{b["id"]}" data-composition-src="compositions/{b["id"]}.html" '
                     f'data-start="{fmt(b["start"])}" data-duration="{fmt(b["end"] - b["start"])}" data-track-index="{2 + n % 2}" '
                     f'data-width="{W}" data-height="{H}"></div>')
        jh.append(f'tl.fromTo("#host-{b["id"]}",{{opacity:0,y:70}},{{opacity:1,y:0,duration:0.16,ease:"power3.out",immediateRender:false}},{b["start"]:.3f})'
                  f'.to("#host-{b["id"]}",{{opacity:0,duration:0.1}},{b["end"] - 0.1:.3f});')
        jp.append(f'tl.fromTo("#pipwrap",{{scale:0.5,opacity:0}},{{scale:1,opacity:1,duration:0.3,ease:"back.out(1.7)",immediateRender:false}},{b["start"] + 0.12:.3f})'
                  f'.to("#pipwrap",{{scale:0.6,opacity:0,duration:0.14,ease:"power2.in"}},{b["end"] - 0.14:.3f});')
    pip = cfg.get("pip", {})
    ps, sc, cy = pip.get("size", 240), pip.get("scale", 0.222), pip.get("center_y", 1040)
    vw, vh = round(W * sc), round(H * sc)
    pl, pt = round(ps / 2 - W / 2 * sc), round(ps / 2 - cy * sc)
    pipsrc = "assets/aroll/pip.mp4" if os.path.exists(os.path.join(P, "assets/aroll/pip.mp4")) else "assets/aroll/aroll.mp4"
    css = fontface() + f"""
*{{margin:0;padding:0;box-sizing:border-box}}
html,body{{margin:0;width:{W}px;height:{H}px;overflow:hidden;background:#0E0F13}}
#root{{position:relative;width:100%;height:100%;overflow:hidden;background:#0E0F13;font-family:"Kanit",sans-serif}}
#cam{{position:absolute;inset:0;transform-origin:50% {zo};will-change:transform}}
#bump{{position:absolute;inset:0;transform-origin:50% {zo}}}
#aroll{{position:absolute;left:0;top:0;width:{W}px;height:{H}px;object-fit:cover}}
.broll{{position:absolute;left:0;top:0;width:{W}px;height:{H}px;z-index:5}}
#pipwrap{{position:absolute;left:{1020 - ps}px;top:190px;width:{ps}px;height:{ps}px;z-index:8;opacity:0;transform-origin:50% 50%}}
#pipring{{position:absolute;inset:0;border-radius:50%;overflow:hidden;border:6px solid {acc};box-shadow:0 18px 50px rgba(0,0,0,.55);background:#d8d5d0}}
#pipvid{{position:absolute;left:{pl}px;top:{pt}px;width:{vw}px;height:{vh}px;object-fit:cover}}
.layer{{position:absolute;left:0;top:0;width:{W}px;height:{H}px}}
"""
    audio = cfg.get("audio", "assets/audio/master.wav")
    nl = "\n      "
    html = f"""<!doctype html>
<html lang="th">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width={W}, height={H}" />
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
    <style>{css}</style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{DUR}" data-width="{W}" data-height="{H}">
      <div id="cam"><div id="bump">
        <video id="aroll" class="clip" src="assets/aroll/aroll.mp4" data-start="0" data-duration="{DUR}" data-track-index="0" muted playsinline></video>
      </div></div>
      {nl.join(hosts)}
      <div id="pipwrap"><div id="pipring">
        <video id="pipvid" class="clip" data-layout-allow-overflow src="{pipsrc}" data-start="0" data-duration="{DUR}" data-track-index="1" muted playsinline></video>
      </div></div>
      <div id="overlays" class="layer" data-composition-id="overlays" data-composition-src="compositions/overlays.html" data-start="0" data-duration="{DUR}" data-track-index="6" data-width="{W}" data-height="{H}" style="z-index:9"></div>
      <div id="captions" class="layer" data-track-kind="captions" data-composition-id="captions" data-composition-src="compositions/captions.html" data-start="0" data-duration="{DUR}" data-track-index="7" data-width="{W}" data-height="{H}" style="z-index:12"></div>
      <audio id="master-mix" src="{audio}" data-start="0" data-duration="{DUR}" data-track-index="50" data-volume="1"></audio>
    </div>
    <script>
      const tl = gsap.timeline({{ paused: true }});
      {nl.join(jz + jb + jh + jp)}
      tl.set({{}}, {{}}, {DUR});
      window.__timelines["main"] = tl;
    </script>
  </body>
</html>
"""
    open(os.path.join(P, "index.html"), "w").write(html)
    print(f"wrote index.html ({DUR}s, {len(bounds) - 1} zoom segments, {len(bumps)} bumps, {len(br)} b-roll, "
          f"{len(ov)} overlays, {len(caps)} captions)")


if __name__ == "__main__":
    main()
