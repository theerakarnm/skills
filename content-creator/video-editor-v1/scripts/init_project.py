#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Scaffold a HyperFrames project for one talking-head short.

Usage:
  init_project.py VIDEO --slug my-topic [--root videos] [--title "..."] [--accent "#F6821F"]
                  [--accent2 "#FBAD41"] [--accent-name "Cloudflare orange"] [--concept "..."]

Creates <dir of VIDEO>/<root>/<slug>/ with:
  hyperframes init (blank, general-video), design.md from the skill's style template,
  edit.json skeleton, sound/, assets/{aroll,audio,broll/logos,broll/shots,fonts},
  .gitignore for regenerable heavy files, and a git repo with a first commit
  (commit before every review round so any change can be rolled back: v1, v2, ...).
Prints the project path. Write BRIEF.md right after (hyperframes init refuses a non-empty dir).
"""
import argparse
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import SKILL_DIR, die, run, save_json  # noqa: E402

GITIGNORE = """renders/
snapshots/
.hyperframes/
assets/aroll/*.mp4
assets/aroll/*.wav
assets/audio/*.wav
sound/sfx/
node_modules/
.eyes/
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--slug", required=True)
    ap.add_argument("--root", default="videos")
    ap.add_argument("--title", default="")
    ap.add_argument("--accent", default="#F6821F")
    ap.add_argument("--accent2", default="#FBAD41")
    ap.add_argument("--accent-name", default="accent orange")
    ap.add_argument("--concept", default="(write one sentence: the visual metaphor for this video's message)")
    a = ap.parse_args()
    video = os.path.abspath(a.video)
    if not os.path.exists(video):
        die(f"no such video: {video}")
    base = os.path.join(os.path.dirname(video), a.root)
    P = os.path.join(base, a.slug)
    if os.path.exists(P) and os.listdir(P):
        die(f"{P} exists and is not empty")
    os.makedirs(base, exist_ok=True)
    run(["npx", "--yes", "hyperframes@latest", "init", os.path.join(a.root, a.slug), "--non-interactive",
         "--example=blank", "--skill=general-video"], cwd=os.path.dirname(video))
    for d in ["assets/aroll", "assets/audio", "assets/broll/logos", "assets/broll/shots", "assets/fonts", "sound", "compositions"]:
        os.makedirs(os.path.join(P, d), exist_ok=True)
    for f in os.listdir(os.path.join(SKILL_DIR, "assets", "fonts")):
        shutil.copy(os.path.join(SKILL_DIR, "assets", "fonts", f), os.path.join(P, "assets", "fonts"))
    t = open(os.path.join(SKILL_DIR, "assets", "templates", "design.md"), encoding="utf-8").read()
    t = (t.replace("{{TITLE}}", a.title or a.slug).replace("{{CONCEPT}}", a.concept)
         .replace("{{ACCENT2}}", a.accent2).replace("{{ACCENT}}", a.accent).replace("{{ACCENT_NAME}}", a.accent_name))
    open(os.path.join(P, "design.md"), "w", encoding="utf-8").write(t)
    save_json({"source_video": video, "edl": "assets/aroll/edl.json", "captions": "assets/captions.json",
               "audio": "assets/audio/master.wav", "accent": a.accent, "accent2": a.accent2, "caption_em": "#FFB347",
               "zoom": {"base": 1.0, "alt": 1.11, "drift": 0.03, "origin_y": "47%"}, "bumps": [], "caption_top": 1300,
               "pip": {"size": 240, "scale": 0.222, "center_y": 1040}, "broll": [], "overlays": [], "sfx": []},
              os.path.join(P, "edit.json"))
    open(os.path.join(P, ".gitignore"), "w").write(GITIGNORE)
    subprocess.run(["git", "init", "-q"], cwd=P)
    subprocess.run(["git", "add", "-A"], cwd=P)
    subprocess.run(["git", "commit", "-q", "-m", "Scaffold project"], cwd=P)
    print(P)


if __name__ == "__main__":
    main()
