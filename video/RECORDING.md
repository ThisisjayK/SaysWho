# Recording the browser take

**Shot on 2026-08-16. `video/public/footage/audit.mp4` exists, `present` is true
and the scene is in the cut.** What follows is what this document asked for, kept
because a reshoot is still worth doing and this is the brief for it. Read the
next section first: the take that got shot differs from the brief in four ways,
and one of them is that the brief was wrong.

## What was actually shot, and where it departs from the below

Reshot 2026-08-16 at 14:09 and 14:15, and the cut in the film is assembled from
both recordings.

- **The whole flow, which is what this take was for.** An empty chat, the
  question typed, the answer arriving, the extension opened from the toolbar,
  Audit clicked in the popup rather than on the page, and the panel filling.
- **A new CO-02 conversation**, not the archived one. Ten claims, and a verdict
  mix of its own including two `Sources disagree`, a state no earlier take put
  on screen. Nothing in the scene reads a number off the footage. Do not caption
  this footage with a figure from `runData.ts`.
- **The audit took about five minutes.** Clicked 54 seconds into the first
  recording, still running when that recording ends at 5m33s, done before the
  second starts 27 seconds later: between 4m39s and 5m06s. The previous take
  measured 22 seconds for the same button on a different answer, so treat
  neither number as the latency of this tool. Both are one observation each.
- **Two files, one session.** The first runs out mid-audit; the second picks up
  with the panel drawn. The join is a crossfade at exactly that point, and it is
  the only place in the cut where time is missing rather than compressed.
- **Dark mode**, and the recording holds the page only, no browser toolbar, so
  nothing needed cropping and `BrowserChrome` draws the only browser on screen.

If you reshoot to this brief, everything below still applies except the beat
timings, which now carry the measured audit.

When the file changes, set `durationInFrames` in [src/footage.ts](src/footage.ts)
to its real length. The scene, the match cut into it and the camera pushes all
switch on from `present`, and the cue sheet retimes itself. With `present` false
the scene is not in the cut at all, so nothing renders with a placeholder in it.

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

**However long the audit actually takes, plus about a minute, cut down
afterwards.** The earlier version of this table said 12 seconds and gave the
audit one of them. The audit has taken 22 seconds once and five minutes once, so
a 12-second take could only ever have held the click or the result and never
both. Do not cut, and do not stop the recording while the audit is running. If a
step fails, start the take again.

| Beat | Do | The camera will |
|---|---|---|
| 0:00 | Sit on the answer, citation chips visible. | Hold on the whole window. |
| 0:02 | Click **SaysWho: capture**. | Hold. |
| 0:03 | **It prints INCOMPLETE. Do not move the mouse.** Let it sit for four or five seconds. | Push in on the warning and hold. |
| 0:08 | Click **SaysWho: audit**. | Pull back out to the whole window. |
| 0:08 onward | **The wait, and budget for minutes rather than seconds.** It has run 22 seconds once and about five minutes once. Do not scroll, do not touch anything, and do not stop recording: the 2026-08-16 take ran out mid-audit and cost a join. It is ramped in the edit, not in the room. | Hold wide. |
| 0:30 | The panel fills. Read it for a moment before moving. | Hold. |
| 0:35 onward | Hover the rows, slowly, **a good four seconds each**, so a card is legible when the edit lands on it. Hover the grey *Could not verify* one and a green one, in either order. | Push onto each in turn. |
| ~1:15 | Stop. | |

Four seconds a row is the part that matters. The cards are the shot, and a hover
held for one second cannot be used at all.

The pushes in [InTheBrowser.tsx](src/film/scenes/InTheBrowser.tsx) are frame
numbers into the cut-down file, not into your take. Recut the footage and they
are the thing to redo.

## Two things not to do

**Do not speed anything up in the room, and declare it if you do it in the
edit.** This rule used to be a flat ban, on the ground that a sped-up audit is a
claim about latency this project has not measured. Two measurements now exist,
both from 2026-08-16 and both single observations: 22 seconds over nine claims
and two PDFs, and about five minutes over ten claims on the free tier. So the
wait may be ramped to keep the film watchable, on one condition, which the scene
meets: the real number is on screen while it happens. Compressing a wait and
hiding one are different acts, and the difference is whether the viewer is told.
Do not average the two numbers into a latency claim. Neither is a benchmark.

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
