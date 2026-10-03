# Show-off effects (optional mode)

Use these only when the creator asks, or when the take includes a clean plate.
They take more prep and render time, and they are the ones people rewatch and share.
Each effect must land on an exact word and have a twist.

## Cutout of the creator

```
npx hyperframes remove-background assets/aroll/aroll.mp4 -o assets/aroll/me.webm -b assets/aroll/room.webm --quality best
```

- `me.webm` is the creator with alpha; `room.webm` is the hole-cut background.
- The hole is not inpainted: composite the clean-plate still (`frames.py --at`) or a blurred plate underneath.
- Fast hands and loose hair give soft edges; avoid hero effects on fast motion.

## Recipes

- **Text behind the creator.**
  Stack: aroll (bottom) -> big kinetic word -> `me.webm` (top).
  The word appears to sit between the wall and the person.
- **Layers split ("wall, me, text").**
  Pull the cutout forward with a small scale and shadow, push the room back with blur; then hide the creator layer on cue so the empty room keeps talking.
  Needs the clean plate.
- **Frame on one side, explainer on the other.**
  Shrink the A-roll into a rounded frame on the right (keep audio); build the explainer (titles, icons, a chart) on the left, timed to the next 2-3 spoken points.
- **Logo in the hand / thrown at the camera.**
  Punch in on the open hand, place the official logo (SVG) on the palm with a 3D tilt (`transformPerspective`), then fly it to the lens with a glass-crack overlay.
  Search the registry first: `npx hyperframes catalog --query "glass crack" --json`.
- **Floating screens behind.**
  Cutout in front, 3-4 short clips of past work on tilted 3D cards behind.

## Rules

- One show-off effect per 20-30 seconds at most; the rest of the edit stays clean.
- Check every show-off moment with zoomed snapshots before showing the user.
- Search `npx hyperframes catalog --query "<look>"` before hand-building any named look.
