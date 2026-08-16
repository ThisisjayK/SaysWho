# Recording the browser take

Everything around this shot is built. The film is missing one file:
`video/public/footage/audit.mp4`.

When it exists, set `present: true` in [src/footage.ts](src/footage.ts) and set
`durationInFrames` to its real length. The scene, the match cut into it and the
two camera pushes all switch on from that one flag, and the cue sheet retimes
itself. Until then the scene is not in the cut at all, so nothing renders with a
placeholder in it.

## Capture settings

| | |
|---|---|
| Window size | **1280 x 800**, exactly. `src/footage.ts` expects it and the panel used to widen on long URLs below this. |
| Frame rate | 30fps, to match the film. |
| Colour scheme | **Light mode.** The panel follows the page and light reads better here. |
| Cursor | Visible. Do not add click highlights or a ripple; the film's camera does the pointing. |
| Audio | Do not record system audio. The mix is built separately. |
| Format | H.264 mp4. Anything QuickTime or OBS writes by default is fine. |

Free recorders, in order of preference: **Cap** (cap.so) for the smoothed cursor,
**OBS** if the take must not fail, **QuickTime** if you want zero setup.

## Before you roll

1. `python3 tools/freeze_queries.py check` passes.
2. The server is already running and has stopped printing to the terminal:
   `.venv/bin/python -m sayswho.server --judge`. It refuses to start without a
   key and says so, which is good design and a bad first ten seconds of a video.
3. The **CO-02** conversation is open on chatgpt.com. That is the colon cancer
   screening question, and it is the only answer in the day 9 run that both
   scores claims and refuses to score others, because one of its two sources is
   a genuine 404.
4. Browser zoom at 100%. Extensions other than SaysWho disabled, so the toolbar
   is not a row of other people's logos.

## What to record, in one take

Roughly 12 seconds. Do not cut. If a step fails, start the take again.

| Beat | Do | The camera will |
|---|---|---|
| 0:00 | Sit on the answer, citation chips visible. | Hold on the whole window. |
| 0:02 | Click **SaysWho: capture**. | Hold. |
| 0:03 | **It prints INCOMPLETE. Do not move the mouse.** Let it sit for a full second. | Push in on the warning at 0:03.2 and hold until 0:05. |
| 0:05 | Click **SaysWho: audit**. | Pull back out to the whole window. |
| 0:06 | Let the panel fill at its own speed. Do not scroll while it is working. | Hold. |
| 0:08 | Hover a **green** claim so the source's own words appear. | Hold. |
| 0:09.5 | Hover the **grey** one, the claim marked *Could not verify*. | Push in on that row at 0:09.5 and hold to the end. |
| 0:12 | Stop. | |

The two pushes are already timed in
[InTheBrowser.tsx](src/film/scenes/InTheBrowser.tsx). If your take runs to a
different length, the poses there are frame numbers and are the thing to adjust,
not the recording.

## Two things not to do

**Do not speed anything up.** The audit taking a moment is the honest part. A
sped-up audit is a claim about latency this project has not measured.

**Do not retake because INCOMPLETE appeared.** That warning is the point. It is
the tool saying it cannot see all of this answer's citations, and across the ten
day 9 answers at least 20 of 53 were behind "+N" controls, a floor of 37.7%. A
take without it would look better and be worth less.

## After

```bash
mkdir -p video/public/footage
cp <your-recording>.mp4 video/public/footage/audit.mp4
```

Then in `src/footage.ts` set `present: true` and put the real frame count in
`durationInFrames`. Check it with:

```bash
ffprobe -v error -select_streams v:0 -count_frames -show_entries stream=nb_read_frames -of csv=p=0 video/public/footage/audit.mp4
```
