# design.md - "{{TITLE}}" Thai short (style profile: tech-dark-accent)

Brand truth for every scene of this 1080x1920 vertical video (TikTok / Reels / Shorts).
Concept angle: {{CONCEPT}}

## Palette (use only these)

- `--bg` #0E0F13 (near-black, slightly warm) - full-bleed background of every b-roll scene.
- `--panel` #17191F - cards, terminals, chat bubbles.
- `--panel-2` #20232B - nested surfaces, code blocks.
- `--line` #2E323C - 2-3px borders and hairlines.
- `--fg` #F4F1EC - primary text (warm off-white).
- `--muted` #A7A9B0 - secondary text and labels.
- `--accent` {{ACCENT}} - {{ACCENT_NAME}}: focal highlights, keywords, progress, glows.
- `--accent-2` {{ACCENT2}} - lighter orange for gradients-free secondary highlights.
- `--bad` #FF5A5F - errors, bugs, cost.
- `--good` #3DDC97 - success, check marks, deployed states.

Rules: one accent hue ({{ACCENT_NAME}}); red and green only as semantic status.
No full-screen linear gradients (they band); use solid bg plus localized radial glows of --accent at 15-25% opacity.
Subtle 2-4% film grain or a faint 48px grid pattern (--line at 35% opacity) is the house background texture.

## Typography

Fonts live in `assets/fonts/` and must be declared with in-file `@font-face` using PROJECT-ROOT-relative paths even inside `compositions/` files, e.g. `url("assets/fonts/Kanit-Black.ttf")` and `src="assets/broll/logos/cloudflare.svg"` - never `../assets/` (lint error invalid_parent_traversal_in_asset_path).

- Display + Thai: **Kanit** - `Kanit-Black.ttf` (900), `Kanit-ExtraBold.ttf` (800), `Kanit-Bold.ttf` (700), `Kanit-Medium.ttf` (500).
- Code / terminal / labels: **JetBrains Mono** - `JetBrainsMono.ttf` (variable, 100-800). It has no Thai glyphs, so any mixed Thai string in a mono context must fall back to Kanit: `font-family: "JetBrains Mono", "Kanit", monospace`.
- Sizes for this phone format: hero words 120-200px (900), headlines 72-110px (800), card titles 44-56px (700), body/labels 30-40px (500), terminal text 30-34px mono. Never below 26px.
- Thai text: never animate per character; animate whole words or phrases. Line-height 1.25+ for Thai (tone marks stack above).

## Layout and safe zones (universal for TikTok, Reels, Shorts)

- Canvas 1080x1920.
- Keep important content inside x 60-1020.
- Top 170px: no content (platform UI).
- y 1200-1500 is the CAPTION BAND owned by the root composition. Scenes must keep this band visually quiet (only background texture there).
- y > 1520: no important content (platform description and buttons). Background only.
- Top-right PiP: the root shows a round face picture-in-picture at x 800-1020, y 190-410 during b-roll scenes. Scenes must leave that box empty (background only).
- So the scene content zone is: header row x 60-760, y 190-410; main stage x 60-1020, y 440-1170.

## Components

- Terminal window: --panel body, 3 dots header (--bad, --accent-2, --good at 14px), title in mono --muted 26px, radius 28px, 3px --line border, inner padding 36px, prompt `$` in --accent.
- Card: --panel, radius 28px, 3px --line border, shadow 0 30px 80px rgba(0,0,0,.45).
- Chip/pill: radius 999px, 3px border, mono or Kanit 700 34px, check icon in --good.
- Chat bubble (user): --panel-2, radius 32px 32px 8px 32px, right aligned; (agent): --panel with a full 3px --accent border, radius 32px 32px 32px 8px.
- Logos: official SVGs in `assets/broll/logos/` (never redraw). Prefer the light/white variant of a mark on --bg; dark marks (GitHub, OpenAI, AWS text, DigitalOcean) vanish on it - use their `-dark`/white variant or a small off-white tile behind them.

## Motion personality

Snappy and confident: entrances 0.3-0.5s with `back.out(1.6)` pops for chips and `power3.out` / `expo.out` slides for cards; vary eases.
Every scene keeps something moving (slow drift/breathe on glows, cursor blink, subtle camera push 1.00 -> 1.04 over the scene).
Hard cuts in and out are owned by the root (it adds a whoosh); scenes should be fully composed by 0.25s and still moving at their last frame.

## Icons and emoji

Draw icons as inline SVG (check, X, lock, rocket, bug, robot, wrench).
Emoji glyphs depend on the render machine's fonts; inline SVG always renders.
Short emoji inside root kinetic text are fine for local renders on this Mac.
