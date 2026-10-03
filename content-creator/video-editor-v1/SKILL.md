---
name: video-editor-v1
description: Edit a Thai (or Thai+English) selfie / talking-head clip into a retention-optimized vertical short for TikTok, Reels, and Shorts with HyperFrames - local Whisper large-v3 word timing, frame-exact jump cuts that remove pauses and fillers, Thai word-chunk captions, jump-cut zooms, kinetic text, parallel-built animated b-roll with real logos and screenshots, a round face PiP, and a Python-synthesized music bed plus self-made sound effects mixed to -14 LUFS. Use this whenever the user hands over a vertical or talking-head video and asks to edit it, cut it, add subtitles/captions, make it viral or more engaging, add b-roll, kinetic text, sound, or music - even if they only say "ตัดต่อคลิปนี้", "ใส่ซับให้หน่อย", "ทำให้คลิปน่าดู", "ทำคลิปสั้น", "ทำเหมือนคลิปที่แล้ว", or name a video file in a personal_brand folder. Also use it to apply timed director notes ("at 0:07 ...") to such an edit, or to check a test shot before filming.
---

# Thai talking-head shorts

Turn one selfie take into a short that keeps people watching, in the creator's approved style.
The pipeline is HyperFrames (HTML -> MP4) plus small scripts in this skill.
Every effect is timed to a spoken word, because the transcript has a time for every character.

The default look is the `tech-dark-accent` profile from the first edit the creator loved (`references/styles.md`).
The worked example lives at `~/Desktop/Claude-Cowork/personal_brand/02102026/videos/wrangler-ai-deploy/` (edit.json, STORYBOARD.md, design.md, compositions/).

`SKILL` below means this skill's directory (`~/.agents/skills/video-editor-v1`).

## 0. Before anything

1. Find `creator-profile.md` in the video's folder or a parent folder and read it (spelling list, keep-together terms, accent, handle, learned preferences).
   If none exists, create one from `references/creator-profile-template.md` with what you learn this run.
2. Run every script with `uv run` (each declares its own dependencies inline; system python has no numpy).
   Check tools once: `ffmpeg`, `whisper-cli`, `node`, `uv`, `npx hyperframes doctor`, and `~/.cache/whisper-cpp/ggml-large-v3.bin` (download command is printed by `transcribe.py` if missing; ~10 min, start it in the background).
3. Ask only the short intake, in one message, with defaults stated (skip anything the request or profile already answers):
   - platforms (default: TikTok, Reels, Shorts - one universal safe zone);
   - how hard to cut (default: retention cut, about -20% length; or keep full length);
   - music on or off (default: on, synthesized);
   - any own b-roll, screen recordings, logos, or `refs/` style examples.
     Also mention the optional show-off mode (cutouts, text behind the creator) only if a clean plate exists.
4. Load the HyperFrames knowledge this run relies on: read `~/.agents/skills/hyperframes-core/SKILL.md` and its `references/creator-editing-recipes.md` once; the rest is summarized here and in `references/gotchas.md` (read gotchas fully before writing any HTML).

If the user only wants a test shot checked before filming, run `references/filming-checklist.md` and stop.

## 1. Scaffold

```
uv run SKILL/scripts/init_project.py VIDEO --slug <kebab-topic> --title "<title>" --accent "<hex>" --accent2 "<hex>" --accent-name "<name>" --concept "<one sentence>"
```

Then write `BRIEF.md` (workflow general-video, flow automation, storyboard no, message, destination social-all, aspect 9:16, language th) using the creator's own words for the intent.
Pick the accent from the main brand in the story (`references/styles.md`).

## 2. Ears and eyes

```
uv run SKILL/scripts/transcribe.py VIDEO --out P/assets/source.words.json
uv run SKILL/scripts/frames.py VIDEO --out P/.eyes --every 1
```

- Read `source.words.txt` fully.
  Understand the message the creator wants to land, the arc (hook -> problem -> agitate -> solution/turn -> proof -> payoff -> CTA), and the single strongest moment.
- Look at every `.eyes/sheet_N.jpg` with `attach_image`.
  Note: head position (PiP `center_y`), hand zones, empty wall above the head (kinetic text zone), resolution and framing problems.
- Fix mishearings with the profile's spelling list.
  For anything you cannot resolve from context, list "heard -> I think" pairs and ask the creator once.
- Find spoken edit requests ("ซูมเข้าไปที่มือ", "zoom in on my hand") and plan them as effects on that word.

## 3. Beat sheet (gate)

Show the beat sheet table from `references/beat-sheet.md` in chat: hook, cuts, every kinetic text, every b-roll window, the reveal, the CTA, sound marks.
State the message in one sentence and the expected final length.
Wait for OK; fold corrections in and show it again.
Rules come from `references/viral-shorts-techniques.md` (read its final checklist).

## 4. Retention cut

Write `P/assets/segments.json` (format in `cut_plan.py --help`, example `references/example-segments.json`):
kept phrases in order, each with whisper's own `from`/`to` words, the corrected caption `text`, and `chunks`.

What to cut: dead air, "นะครับผม / เนาะ / อะไรอย่างนี้" fillers, repeated phrases, false starts, apologies for clickbait, and explanations that delay the payoff.
Open on the hook line; end on the question or CTA.

```
uv run SKILL/scripts/cut_plan.py VIDEO P/assets/source.words.json P/assets/segments.json --out P/assets/aroll/edl.json
uv run SKILL/scripts/render_cut.py P/assets/aroll/edl.json --dir P/assets/aroll
uv run SKILL/scripts/transcribe.py P/assets/aroll/voice.wav --out P/assets/cut.words.json
```

Read the cut transcript.
If a stray word survived a seam (for example "ทุกคน" after "ใช่ไหมครับ"), override that segment with `"src": [start, end]` and rerun.

## 5. Captions

Chunks are 2-4 words that read as one spoken unit, at most ~14 visible characters, never splitting a keep-together term.
Use `--propose` to get auto chunks, then hand-edit them into `segments.json` ("a / b / c") and rerun `cut_plan.py` (fast) before captions.

```
uv run SKILL/scripts/captions.py P/assets/aroll/edl.json P/assets/cut.words.json --out P/assets/captions.json --keep "<profile keep-together, comma list>"
```

Every segment must pass the verification (ratio >= 0.80); a low ratio means a clipped word: fix the cut first.

## 6. Face-time layer (edit.json -> build_root.py)

Fill `P/edit.json` (schema in `build_root.py --help`, real example `references/example-edit.json`):

- `bumps`: 3-6 punch pulses on the hardest-hitting words, at least 5 s apart (hook number, the turn, the reveal, the CTA).
- `overlays`: kinetic text on the wall above the head, one idea per card, exact word times from `scripts/timing.py`.
  Hook card in the first 0.1 s; strike-throughs for "not X but Y"; chips for lists; a slam for the payoff word; CTA card at the end.
  Give every effect a small twist (strike, shake, count, slam), not just a fade.
- `name_tag`: the creator's @handle the first time they speak, if the profile says so.
- `pip.center_y`: source y of the head centre from the frames; check that the whole head (hair included) shows.

```
uv run SKILL/scripts/build_root.py P
```

## 7. B-roll (parallel)

Follow `references/broll-pipeline.md`: choose windows, write `STORYBOARD.md` with scene-local beats, spawn the asset worker early, build packets, then spawn all scene workers in one wave (2-3 scenes each).
Model choice follows the user's delegation policy (assets: glm-5.3-flash max; scenes: opus medium) - say which and why in the progress update.
While workers run, do the sound pass and checks on the root.
Merge each finished scene into `edit.json` "broll" and rerun `build_root.py`.

## 8. Sound (all Python, no downloads)

```
uv run SKILL/scripts/sound.py all P --reveal <output time of the big turn>
```

It renders the 18-sound kit, a music bed whose bar line lands on the reveal (2-bar pad-only drop before it), merges root and scene cues (no back-to-back repeats, risers ending on impacts), and mixes voice + ducked bed + SFX to -14 LUFS / -1 dBTP.
Rerun `sound.py cues P` and `sound.py mix P` after any timing change.
If the creator wants music louder or softer, change `--gap-db` / `--duck-db` and say the numbers.
The mix is numeric only: tell the user to listen and report.

## 9. Verify, then preview

```
cd P && npx hyperframes lint && npx hyperframes check
npx hyperframes snapshot --at <every b-roll midpoint and every overlay moment> --no-end -o /tmp/<slug>-snap --describe false
```

- Fix every error using `references/gotchas.md`; the outlined-caption contrast warning is a known false positive.
- Look at every contact sheet with `attach_image`; be picky: overlaps, clipped Thai tone marks, text in the bottom 20% or under the PiP, logos invisible on dark.
- Commit a version: `git -C P add -A && git commit -m "v1: first full edit"`.
- `npx hyperframes preview --background` and give the user the Studio URL plus a short list of what is in the edit, what you could not check (audio by ear), and known warnings.

## 10. Director notes loop

Ask for notes as "at 0:07 <what is wrong> -> <what to see>", one per line.
For each note: `frames.py` or `snapshot --at` that time before and after the fix, show it if visual, and commit `vN`.
Record any preference the creator states twice in `creator-profile.md` ("Preferences learned").

## 11. Render (only after approval)

```
uv run SKILL/scripts/finalize.py P        # run with bash() in the background, ~6 min for 2:15
```

Report the `_final.mp4` path, size, duration, LUFS and peak, and look at `renders/<slug>_sheet.jpg` first.
Offer, once: an English-caption version (same timing, translated `text`/`chunks`, rerun captions + build_root + finalize), or a reply-to-comment follow-up clip.

## Quality bar (what made the first edit work)

- Hook: spoken line + on-screen text + punch in the first 3 s.
- A visual change every 3-5 s; jump-cut zoom alternation hides every cut.
- B-roll shows exactly what is being said, with real logos and real screenshots, never generic stock.
- The reveal sits near the middle as a re-hook, with the music drop and an impact.
- Captions never cover the face or the app UI; English tech words pop in the accent colour.
- The face stays present (PiP) during b-roll.
- The ending is a question that invites comments, then stop.

## References

- `references/viral-shorts-techniques.md` - researched retention rules with sources and a 24-point checklist.
- `references/beat-sheet.md` - plan table format and planning rules.
- `references/broll-pipeline.md` - storyboard format, asset and scene worker prompts, merge steps.
- `references/gotchas.md` - every lint/check/render/transcription trap already hit, with fixes.
- `references/styles.md` - default style profile, per-brand accents, style-by-reference and named styles.
- `references/show-off-effects.md` - optional cutout and 3D effects (needs a clean plate).
- `references/filming-checklist.md` - what to tell the creator before filming; test-shot check.
- `references/creator-profile-template.md` - the per-creator memory file.
- `references/example-edit.json`, `references/example-segments.json` - real configs from the first edit.
