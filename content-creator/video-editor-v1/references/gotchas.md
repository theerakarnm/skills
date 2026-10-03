# Verified gotchas (hyperframes v0.8.106-0.8.114, this Mac)

Each item below cost a debugging round once.
Apply them before the first lint, not after.

## Composition and lint

- Asset paths inside `compositions/*.html` must be project-root-relative (`assets/fonts/...`, `assets/broll/logos/...`).
  `../assets/` fails lint with `invalid_parent_traversal_in_asset_path`.
- Never hide an element with `tl.set(el, {opacity:0}, 0)` inside the paused timeline (`gsap_timeline_set_initial_hide`, frame 0 shows it).
  Put `opacity:0` in CSS and animate with `fromTo(..., {immediateRender:false})`.
- A root clip that contains nested divs triggers `nested_structure_needs_subcomposition`.
  Kinetic text and captions therefore live in sub-compositions (`overlays.html`, `captions.html`); `build_root.py` already does this.
- Mark the caption host with `data-track-kind="captions"` (`caption_track_kind_missing`).
- `GSAP target not found` means a selector matched nothing.
  Classic case: a strike written as `<s>` while the timeline animates `.sl`.
  Write `<span class="strike">word<i class="sl"></i></span>`.
- Back-to-back tweens on the same property at the same instant warn `overlapping_gsap_tweens`.
  Leave a 1-5 ms gap (start next segment at `t+0.001`, shorten the previous by 0.004 s).
- Two `<video>` elements with the same src/start/duration warn `duplicate_media_discovery_risk`.
  The PiP uses its own small `pip.mp4`, which also decodes faster.

## Layout and contrast checks (`hyperframes check`)

- `content_overlap` on fanned or rotated terminals is reported per child span.
  `data-layout-allow-overlap` must go on those spans themselves, not only on the parent line or window.
- The PiP video intentionally overflows its round mask: give `#pipvid` `data-layout-allow-overflow`.
- The contrast audit ignores `-webkit-text-stroke`.
  Orange caption keywords with a 12 px black outline get flagged (about 1.3:1) although they read well.
  Treat that one as a known false positive; confirm with a zoomed snapshot.
- Decorative outline-only "ghost" text fails as `text_not_painted`, and tinting its fill fails contrast instead.
  Remove ghost text rather than fight the audit.
- Code-editor line numbers in muted gray (#5b5f6b) fail 3:1; use #7a7e8c or lighter.

## Media

- SVGs scraped from docs sites often lack `xmlns`, so `<img>` shows a broken image.
  Run `scripts/fix_svgs.py assets/broll/logos` after every logo download.
- Dark brand marks vanish on the dark background: GitHub, OpenAI, AWS wordmark text, DigitalOcean (no fill = black).
  Use the white or `-dark` variant, or a small off-white tile behind the logo.
- Emoji in scenes depend on the render machine's emoji font.
  Scene workers should draw icons as inline SVG.
  Short emoji in root kinetic text render fine locally on macOS.
- The `media-use` resolver (`resolve.mjs`) may fail with `Module not found ~/.agents/packages/cli`.
  Fallback for logos: svgl (`https://api.svgl.app?search=<name>`) then simple-icons (`https://cdn.jsdelivr.net/npm/simple-icons@latest/icons/<slug>.svg`).
- Cloudflare docs moved some command pages; capture the live CLI reference (`/workers/wrangler/commands/workers/`), not old deep links.

## Rendering and audio

- `hyperframes render` re-mixes audio quieter (measured -16.4 LUFS from a -14 LUFS master).
  `finalize.py` remuxes the designed master back onto the copied video stream.
- A full 2:15 render at `-q delivery` took about 5.5 minutes and 140-150 MB.
- `snapshot` writes `contact-sheet-1..N.jpg` when there are many frames, not `contact-sheet.jpg`.
- `animation-map.mjs` needs `HYPERFRAMES_SKILL_BOOTSTRAP_DEPS=1` and `HYPERFRAMES_SKILL_PKG_VERSION=<cli version>`.
- The snapshot bundler skips sub-compositions behind a symlinked `compositions/` folder ("file is empty"); temp roots need real copies.

## Transcription and Thai text

- The medium q5 model mangles tech terms (CloudFair, ไอคิดโคตร); use `ggml-large-v3.bin` with `--dtw large.v3 -nfa`.
- Whisper still mishears English inside Thai speech ("Break-in, Font-in" = Backend, Frontend; "Instant" = Instance; "Row" = Log).
  Fix them in `segments.json` "text" and ask the creator about anything unsure.
- `Intl.Segmenter('th')` splits loanwords and brands (โปรเจกต์ -> โปร|เจ|กต์, มันม่วง -> มัน|ม่วง).
  Pass them in `--keep` so chunks never break inside them.
- Never animate Thai per character; tone marks and vowels detach. Animate whole words or chunks.

## Agent runtime (Prime Agent RLM)

- `attach_image` is called directly: `await attach_image(path)`.
- The REPL may lack `agent_message`; collect children with `rlm.collect(...)` and remove them with `rlm.delete_subagent(handle)`.
- An `ELEVENLABS_API_KEY` that is a key ID (not `sk_...`) returns 400 `api_key_id_used_as_api_key`; do not retry, ask for the secret key.
