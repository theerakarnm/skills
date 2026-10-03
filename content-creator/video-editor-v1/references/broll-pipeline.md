# B-roll pipeline: storyboard, assets, parallel scene workers

B-roll scenes are full-screen HyperFrames sub-compositions that cover the talking head while the voice continues.
They are the most expensive part of the edit, so plan them on paper and build them in parallel.

## 1. Pick the windows

- Choose spans where the words describe something showable (a tool, a pain, a number, a process).
- 2-10 s each, about 15-35% of the runtime in total, never more than ~10 s without the face.
- Start and end on caption chunk boundaries (`captions.json` show times), so the cut feels motivated.
- Keep the hook (first ~4.5 s) and the CTA on the face.
- Get exact beat times with `scripts/timing.py cut.words.json "phrase" ...`.

## 2. STORYBOARD.md (one frame per scene, dispatch unit)

Frontmatter: `format: 1080x1920`, `duration`, `message`, `arc`, `audience`, `mode: autonomous`.
Then one block per scene; beats are scene-local seconds synced to the speaker.
Cite 2-4 motion rules from `~/.agents/skills/hyperframes-animation/rules-index.md` (ids only).

Example block from the first edit:

```markdown
## Frame 8 - สั่ง AI ดู Log แบบ Read Only

- src: compositions/b08-agent-reads-logs.html
- status: outline
- duration: 8.8s
- global_start: 71.6s
- transition_in: cut
- rules: discrete-text-sequence, context-sensitive-cursor, spring-pop-entrance
- voiceover: "เราสามารถบอกได้เลยว่า โอเค เข้าไปดู Log นี้ให้หน่อย ไปอ่าน Error ตรงนี้ให้หน่อย แบบ Read Only แล้วก็มาบอกว่าสาเหตุมันคืออะไร"
- scene: สั่ง AI ดู Log แบบ Read Only
- poster: 6.16

Beats (scene-local seconds, synced to the speaker; each must land within +-0.05s):
- 0.96s: user chat bubble types: "เข้าไปดู log ของ shop-api ให้หน่อย"
- 3.00s: agent tool-call row: `$ npx wrangler tail shop-api --format pretty` streams 3-4 log lines
- 4.98s: one red line: `✘ Error: D1_ERROR: no such column: discount_code` gets highlighted
- 6.26s: badge "🔒 Read Only" pops on the tool row
- 7.46s: agent answer bubble: "สาเหตุ: migration 0007 ยังไม่ได้ apply บน production" with a ✓

Agent chat UI card filling the stage: chat bubbles per design.md, a tool-call block styled as terminal. Keep Thai in Kanit, commands in JetBrains Mono. This is the core demo, so make every beat legible.
```

Then build packets:

```
node ~/.agents/skills/general-video/scripts/frame-packets.mjs --project "$P" --storyboard "$P/STORYBOARD.md"
```

## 3. Asset worker (spawn first, in parallel with planning)

Model: `zai/glm-5.3-flash`, thinking `max` (clear criteria, high volume).
Prompt skeleton:

```
You are the b-roll asset worker for a Thai short about <topic>.
Project dir: <P>. Put everything in <P>/assets/broll/ (logos/, shots/) and write manifest.json
(id, path, kind, source_url, license_or_note, width, height, what_it_shows).
Do NOT read or use API keys or credentials; no authenticated calls; edit nothing outside assets/broll/.
1. LOGOS: official SVGs only, never redraw: <brand list>. Try `node ~/.agents/skills/media-use/scripts/resolve.mjs --type logo`;
   if it fails use svgl (https://api.svgl.app?search=<name>) then simple-icons. Save a light variant for dark backgrounds.
   Product icons from the vendor docs pages if needed. Run <SKILL>/scripts/fix_svgs.py on logos/ at the end.
2. SCREENSHOTS: Playwright Chromium (executablePath under ~/.cache/hyperframes/chrome if needed), viewport 1200x1500 @2x,
   prefers-color-scheme dark, dismiss cookie banners, do not inject CSS that hides headers. Pages: <url list>.
   Also a tight crop_*.png of the key region (max 1600 px wide).
3. Contact sheet contact.jpg; view it with attach_image; recapture blank, cookie-walled, or unreadable shots.
Reply with the manifest summary and failures.
```

## 4. Scene workers (2-3 scenes each, all in one wave)

Model: `anthropic/claude-opus-5-5`, thinking `medium` (design judgment).
Prompt skeleton (fill the brackets; keep every rule, each one came from a real failure):

```
You are a HyperFrames frame worker. Your complete role is in this file - read it FIRST and follow it exactly:
<P>/.hyperframes/frame-packets/_role.md
Then build these scenes one after another, each from its own packet:
- <P>/.hyperframes/frame-packets/<id>.md ...

## Dispatch context
- PROJECT_DIR: <P>; frame_ids: <ids>; canvas 1080x1920, 30 fps.
- Design truth: <P>/design.md (palette, Kanit + JetBrains Mono via @font-face, safe zones, the PiP box
  x800-1020 y190-410 that must stay empty, the caption band y1200-1500 that must stay quiet).
- Asset paths are PROJECT-ROOT-relative even inside compositions/ (assets/fonts/..., assets/broll/logos/...). Never ../assets/.
- Logos: <P>/assets/broll/logos/ (exact filenames; use white/-dark variants on the dark bg). Screenshots: only those your packet names.
- Each scene root: data-width="1080" data-height="1920", data-duration = packet duration, own full-bleed --bg background.
- Beat times are scene-local and synced to speech: hit them within 0.05 s.
- Icons as inline SVG, not emoji. Never animate Thai per character.
- Also write compositions/<id>.sfx.json: [{"t": <scene-local s>, "sfx": "<name>", "gain_db": -18..0}], 3-8 cues, names from:
  click deploy_launch ding error_buzz glitch impact impact_soft key_enter key_typing notification_stack pop pop_soft
  riser riser_short success_chime swoosh_down whoosh_long whoosh_short. No entry whoosh (the root adds it).
- Validate in a temp root at <P>/.hyperframes/tmp-<id>/ with REAL copies of compositions (symlinks break snapshots):
  lint must be 0 errors; snapshot 3-5 times; view with attach_image; fix overlaps, clipped tone marks, overflow,
  anything in the PiP box or caption band. Delete the temp root afterwards. Never edit index.html or other scenes.
- Never use the em dash character.
Reply with files written, measured durations, and open issues.
```

## 5. Merge

- `rlm.collect(handles, timeout_ms=0)` to watch progress; delete finished workers with `rlm.delete_subagent`.
- Add each scene to `edit.json` "broll" (id, start, end in output seconds), rerun `build_root.py`, `sound.py cues`, `sound.py mix`.
- Run `npx hyperframes check`; fix per `gotchas.md`; snapshot every scene midpoint and look at the sheets.
