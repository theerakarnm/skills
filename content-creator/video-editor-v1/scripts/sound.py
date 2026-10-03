#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Sound pass: synthesized music bed + self-made SFX + ducked mix, all from Python.

Usage:
  sound.py sfx   PROJECT                         render the 18-sound kit to PROJECT/sound/sfx (once)
  sound.py music PROJECT --reveal 52.65 [--mid-at 4.5] [--drop-bars 2] [--bpm 104]
  sound.py cues  PROJECT                         build PROJECT/assets/audio/cues.json
  sound.py mix   PROJECT [--gap-db 17] [--duck-db 7]
  sound.py all   PROJECT --reveal 52.65          sfx (if missing) + music + cues + mix

Music: the BPM is nudged (96-112) so a bar line lands exactly on --reveal (the big
solution/turn moment); the bed drops to pad-only for --drop-bars bars before it and the
full beat returns on the reveal. Sections: low intro -> mid from --mid-at -> drop -> high -> outro.

Cues come from edit.json (b-roll entries/exits, overlay pop/slam/strike/shake events,
manual "sfx" list) plus each scene's compositions/<id>.sfx.json (scene-local times).
Rules applied: scene-entry whooshes from scenes are dropped (the root already whooshes),
risers are moved so they END on the next impact, and the same sound never plays twice in
a row within 1.5 s (it alternates with a sibling sound).

Mix defaults (--gap-db 17 --duck-db 7) keep a fast talker's music audible; the master is
-14 LUFS integrated with a -1 dBFS true-peak ceiling. Dependencies are pulled by `uv run --with`.
"""
import argparse
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import die, load_json, save_json  # noqa: E402

KIT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sound")
SFX = ["click", "deploy_launch", "ding", "error_buzz", "glitch", "impact", "impact_soft", "key_enter", "key_typing",
       "notification_stack", "pop", "pop_soft", "riser", "riser_short", "success_chime", "swoosh_down",
       "whoosh_long", "whoosh_short"]
SIBLING = {"pop": "pop_soft", "pop_soft": "pop", "whoosh_short": "whoosh_long", "whoosh_long": "whoosh_short",
           "impact": "impact_soft", "impact_soft": "impact", "click": "key_enter", "key_enter": "click",
           "ding": "success_chime", "success_chime": "ding", "swoosh_down": "whoosh_short", "glitch": "click"}


def py(script, *args):
    cmd = ["uv", "run", "--quiet", "--with", "numpy", "--with", "scipy", "--with", "soundfile", "--with", "pyloudnorm",
           "python", os.path.join(KIT, script), *args]
    p = subprocess.run(cmd, cwd=KIT, capture_output=True, text=True)
    if p.returncode:
        die(f"{script} failed:\n{p.stdout[-2000:]}\n{p.stderr[-3000:]}")
    print(p.stdout.strip()[-1500:])


def paths(P):
    cfg = load_json(os.path.join(P, "edit.json"))
    edl = load_json(os.path.join(P, cfg.get("edl", "assets/aroll/edl.json")))
    return cfg, edl


def do_sfx(P):
    out = os.path.join(P, "sound", "sfx")
    os.makedirs(out, exist_ok=True)
    py("sfx.py", "--out", out)


def do_music(P, a):
    cfg, edl = paths(P)
    dur = edl["duration"]
    beat_bar = 240 / a.bpm
    n = max(round(a.reveal / beat_bar), a.drop_bars + 2)
    bar = a.reveal / n
    bpm = 240 / bar
    if not 96 <= bpm <= 112:
        print(f"warning: bpm {bpm:.1f} outside 96-112; reveal at {a.reveal}s may not suit a bar line")
    secs = [{"start": 0, "energy": "low"}, {"start": a.mid_at, "energy": "mid"},
            {"start": round(a.reveal - a.drop_bars * bar, 3), "energy": "drop"},
            {"start": a.reveal, "energy": "high"}, {"start": round(max(dur - 4.0, a.reveal + bar), 3), "energy": "outro"}]
    os.makedirs(os.path.join(P, "assets", "audio"), exist_ok=True)
    sp = os.path.join(P, "sound", "sections.json")
    save_json(secs, sp)
    py("bgm.py", "--duration", f"{dur}", "--out", os.path.join(P, "assets", "audio", "bgm.wav"), "--sections", sp,
       "--bpm", f"{bpm:.3f}", "--meta", os.path.join(P, "assets", "audio", "bgm_meta.json"))
    cfg["music"] = {"reveal": a.reveal, "bpm": round(bpm, 3), "bar": round(bar, 4)}
    save_json(cfg, os.path.join(P, "edit.json"))


def root_cues(cfg):
    cues = []
    for b in cfg.get("broll", []):
        cues += [{"sfx": "whoosh_short", "t": round(b["start"] - 0.06, 3), "gain_db": -9},
                 {"sfx": "swoosh_down", "t": round(b["end"] - 0.12, 3), "gain_db": -14}]
    first_slam = True
    for o in cfg.get("overlays", []):
        for ev in o.get("events", []):
            t, kind = ev[0], ev[2]
            if kind == "pop":
                cues.append({"sfx": "pop", "t": t, "gain_db": -11})
            elif kind == "slam":
                cues.append({"sfx": "impact" if first_slam and t < 6 else "impact_soft", "t": t, "gain_db": -4 if first_slam and t < 6 else -3})
                first_slam = False
            elif kind == "strike":
                cues.append({"sfx": "glitch", "t": t, "gain_db": -12})
            elif kind == "shake":
                cues.append({"sfx": "click", "t": t, "gain_db": -10})
    nt = cfg.get("name_tag")
    if nt:
        cues.append({"sfx": "pop_soft", "t": nt["start"], "gain_db": -12})
    cues += cfg.get("sfx", [])
    return cues


def scene_cues(P, cfg):
    out = []
    for b in cfg.get("broll", []):
        f = os.path.join(P, "compositions", b["id"] + ".sfx.json")
        if not os.path.exists(f):
            print(f"note: no {b['id']}.sfx.json")
            continue
        for c in load_json(f):
            if c.get("sfx") not in SFX or not 0 <= c["t"] <= b["end"] - b["start"]:
                continue
            if c["sfx"] in ("whoosh_short", "whoosh_long", "swoosh_down") and c["t"] <= 0.35:
                continue
            out.append({"sfx": c["sfx"], "t": round(b["start"] + c["t"], 3),
                        "gain_db": max(min(c.get("gain_db", -8), 0), -18)})
    return out


def do_cues(P):
    cfg, _ = paths(P)
    cues = root_cues(cfg) + scene_cues(P, cfg)
    hits = sorted(c["t"] for c in cues if c["sfx"] in ("impact", "impact_soft", "deploy_launch"))
    for c in cues:
        if c["sfx"] in ("riser", "riser_short"):
            L = 2.0 if c["sfx"] == "riser" else 1.0
            nxt = [t for t in hits if c["t"] <= t <= c["t"] + L + 0.6]
            if nxt:
                c["t"] = round(max(nxt[0] - L, 0), 3)
    cues.sort(key=lambda c: c["t"])
    swapped = 0
    for i in range(1, len(cues)):
        p, c = cues[i - 1], cues[i]
        if c["sfx"] == p["sfx"] and c["t"] - p["t"] < 1.5 and c["sfx"] in SIBLING:
            c["sfx"] = SIBLING[c["sfx"]]; swapped += 1
    save_json(cues, os.path.join(P, "assets", "audio", "cues.json"))
    print(f"{len(cues)} cues ({swapped} swapped to avoid back-to-back repeats) -> assets/audio/cues.json")


def do_mix(P, a):
    py("mix.py", "--voice", os.path.join(P, "assets", "aroll", "voice.wav"), "--bgm", os.path.join(P, "assets", "audio", "bgm.wav"),
       "--cues", os.path.join(P, "assets", "audio", "cues.json"), "--out", os.path.join(P, "assets", "audio", "master.wav"),
       "--sfx-dir", os.path.join(P, "sound", "sfx"), "--gap-db", str(a.gap_db), "--duck-db", str(a.duck_db))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["sfx", "music", "cues", "mix", "all"])
    ap.add_argument("project")
    ap.add_argument("--reveal", type=float)
    ap.add_argument("--mid-at", type=float, default=4.5)
    ap.add_argument("--drop-bars", type=int, default=2)
    ap.add_argument("--bpm", type=float, default=104.0)
    ap.add_argument("--gap-db", type=float, default=17.0)
    ap.add_argument("--duck-db", type=float, default=7.0)
    a = ap.parse_args()
    P = os.path.abspath(a.project)
    if a.cmd in ("music", "all") and a.reveal is None:
        die("--reveal is required (output time of the big turn / solution moment)")
    if a.cmd == "sfx" or (a.cmd == "all" and not os.path.exists(os.path.join(P, "sound", "sfx", "pop.wav"))):
        do_sfx(P)
    if a.cmd in ("music", "all"):
        do_music(P, a)
    if a.cmd in ("cues", "all"):
        do_cues(P)
    if a.cmd in ("mix", "all"):
        do_mix(P, a)


if __name__ == "__main__":
    main()
