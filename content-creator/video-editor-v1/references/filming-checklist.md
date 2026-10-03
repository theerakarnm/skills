# Filming checklist (send this before the creator records)

A clean take decides how good captions, cutouts, and effects can look.
A phone is enough.

## Camera and light

- Phone on a tripod or stable surface; the frame never moves, so effects stay locked to the creator.
- Record vertical 9:16 at 1080x1920 or higher, 30 fps.
  A 576x1024 source looks soft after upscaling.
- Leave headroom: the whole head plus a hand's width above it, so kinetic text has an empty wall area.
- Light on the face, some distance from the wall (cleaner cutouts, less shadow).
- Quiet room, mic close to the mouth: Whisper hears better, and so do viewers.

## While talking

- Open with the hook line directly; no greeting.
- One idea per sentence; pause a beat between ideas (the cut removes the pause later).
- Say edit requests out loud if wanted ("zoom in on my hand", "put the logo here"); the skill finds them in the transcript.
  Hold still for a second where an effect lands.
- Say the call to action slowly and clearly; it is the line that matters most.

## Before stopping

- For show-off effects: step out and record 2 seconds of the empty room (clean plate).
  If an object will "come alive", record 2 more seconds without it.

## Test shot check (5-second clip)

Run `scripts/frames.py test.mp4 --out .eyes-test --every 0.5`, look at the sheet, and report:
face lighting, distance from the wall, head room, anything important near the frame edges, and resolution.
Tell the creator exactly what to fix before the real take.
