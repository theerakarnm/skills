# Theerakarn's AI Skills

A collection of AI agent skills that I built for my own work and share with you.
Each skill is a folder with a `SKILL.md` file.
The file teaches an AI coding agent (Claude Code, Codex, Cursor, OpenCode, and other agents that support skills) how to do one job well, step by step, with scripts and references included.

You install a skill once.
After that, you ask your agent in plain words, and it loads the skill when the task matches.

## Skills

| Category | Skill | What it does |
| --- | --- | --- |
| Content creator | [`video-editor-v1`](content-creator/video-editor-v1/SKILL.md) | Edits a Thai (or Thai + English) talking-head selfie clip into a vertical short for TikTok, Reels, and Shorts, with jump cuts, captions, kinetic text, b-roll, music, and sound effects. |

More skills will come.
Star or watch this repo to get updates.

## Install

### Option 1: Skills CLI (recommended)

Install every skill in this repo:

```bash
npx skills add theerakarnm/skills
```

Install one skill only:

```bash
npx skills add theerakarnm/skills@video-editor-v1
```

The CLI asks which agents to install for.
Add `-g` to install globally (for all your projects).

### Option 2: Manual copy

Copy the skill folder into your agent's skills folder.
For example, for Claude Code:

```bash
git clone https://github.com/theerakarnm/skills.git
cp -R skills/content-creator/video-editor-v1 ~/.claude/skills/
```

For agents that use the shared folder, copy it to `~/.agents/skills/` instead.

## Skill guide

### video-editor-v1

Turn one selfie take into a short that keeps people watching.
You give the agent a vertical video file.
The agent plans the edit with you, builds it, and renders a final MP4.

**What you get**

- Accurate Thai word timing from local Whisper large-v3 (no cloud, no API key).
- Frame-exact jump cuts that remove pauses, fillers, false starts, and repeats.
- Thai captions in natural 2-4 word chunks that never split a brand or tech term.
- Punch-in zooms on key words and kinetic text above your head.
- Animated b-roll that shows what you say, with real logos and screenshots.
- A round face picture-in-picture, so you stay on screen during b-roll.
- A music bed and sound effects made in Python (no downloads, no copyright issues), mixed to -14 LUFS.
- One safe zone that works for TikTok, Reels, and Shorts.

**How the flow works**

1. The agent asks a short intake: platforms, how hard to cut, music on or off, and any b-roll you have.
2. It transcribes the clip and looks at the frames.
3. It shows you a beat sheet (hook, cuts, text, b-roll, reveal, call to action) and waits for your OK.
4. It cuts, captions, adds effects, b-roll, and sound.
5. It opens a preview in HyperFrames Studio.
6. You give director notes such as `at 0:07 text covers my face -> move it up`.
7. After you approve, it renders the final video.

The skill also keeps a `creator-profile.md` next to your videos.
It remembers your spelling list, terms to keep together, your accent colour, your handle, and the preferences you give it.
Each new edit gets closer to your style.

**Example prompts**

```text
Edit ~/Videos/my-clip.mp4 into a TikTok short with captions and b-roll.
```

```text
ตัดต่อคลิปนี้ให้หน่อย ~/Videos/my-clip.mp4
```

```text
ใส่ซับให้หน่อย แล้วทำให้คลิปน่าดูขึ้น
```

```text
Check my test shot before I film: ~/Videos/test.mp4
```

**Requirements**

The skill runs on your machine.
It was built and tested on macOS (Apple Silicon).

- An AI agent that supports skills and sub-agents (for example Claude Code).
- [HyperFrames](https://github.com/heygen-com/hyperframes) skills: `npx skills add heygen-com/hyperframes`
- [Node.js](https://nodejs.org/) (for `npx hyperframes`)
- [uv](https://docs.astral.sh/uv/) (every script runs with `uv run` and installs its own Python packages)
- [ffmpeg](https://ffmpeg.org/)
- [whisper.cpp](https://github.com/ggml-org/whisper.cpp) `whisper-cli` (on macOS: `brew install whisper-cpp`)
- The Whisper `ggml-large-v3.bin` model in `~/.cache/whisper-cpp/` (about 3 GB; the skill prints the download command if it is missing)

Check your setup:

```bash
ffmpeg -version && whisper-cli --help && node -v && uv --version && npx hyperframes doctor
```

**Tips for a good result**

- Film vertical 9:16 at 1080x1920 or higher, on a tripod.
- Leave empty wall space above your head for kinetic text.
- Open with your hook line directly, with no greeting.
- Use a quiet room and keep the mic close.

See the full [filming checklist](content-creator/video-editor-v1/references/filming-checklist.md).

**What is inside**

```text
video-editor-v1/
├── SKILL.md        # The step-by-step workflow the agent follows
├── scripts/        # Transcribe, cut, captions, build, sound, and render scripts
├── references/     # Retention techniques, beat sheet, b-roll pipeline, styles, gotchas
├── assets/         # Fonts (Kanit, JetBrains Mono) and the design template
└── evals/          # Test prompts for the skill
```

## Repo layout

Skills are grouped by category:

```text
skills/
└── content-creator/
    └── video-editor-v1/
```

## Feedback

Found a bug, or have an idea for a new skill?
Open an [issue](https://github.com/theerakarnm/skills/issues).
If you made something cool with these skills, tag me and share it.
