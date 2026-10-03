# Style profiles and style-by-reference

## Default profile: tech-dark-accent

The style of the first edit (wrangler-ai-deploy, 2026-10-02), which the creator liked.

- A-roll talking head with jump cuts; zoom alternates 1.00 / 1.11 per cut with a slow 3% drift.
- B-roll scenes are full-bleed dark (#0E0F13) cards, terminals, chat UIs, diagrams; faint 48 px grid; one accent glow.
- Round face PiP (240 px, accent ring) top-right during b-roll.
- Kinetic text on the wall above the head: dark cards, accent cards, chips, strike-through, slams.
- Captions: Kanit ExtraBold 70 px, white with a 12 px black outline, English words and numbers in a warm accent.
- Fonts: Kanit (Thai display/body) + JetBrains Mono (code).
- Accent per topic: take it from the main brand in the story (Cloudflare #F6821F / #FBAD41, Vercel white, Supabase #3ECF8E, AWS #FF9900, Google #4285F4, LINE #06C755, Anthropic/Claude #D97757).
  If there is no brand, use the creator profile's default accent.

## Style by reference

When the creator puts screenshots, a GIF, or a clip in `refs/`:

1. Pull frames from clips (`frames.py refs/clip.mp4 --out .eyes-refs --every 0.5`) and view them with screenshots.
2. Describe the style back in five bullets: layout, fonts, colors, motion, pacing.
3. Wait for OK; then write a new `design.md` from it (keep the safe zones and Thai typography rules).
4. Build something similar with the creator's words and colors, not a copy.

## Named styles

One line is enough ("cinematic movie trailer", "Vox-style explainer", "Apple product reveal", "breaking news", "retro 80s VHS").
Describe the interpretation in five bullets before building, then follow the same steps.
Mixing works: a named style plus one reference for the detail that matters most.
Read `~/.agents/skills/hyperframes-creative/references/visual-styles.md` for named looks.
