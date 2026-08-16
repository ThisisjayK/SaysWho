# Sound: cue sheet and narration

The film is 2678 frames, 1:29.27 at 30fps. Everything below is generated from or
timed against `src/film/timing.ts`, which is the same table the render uses.

Regenerate the cue sheet after any retime:

```bash
npx esbuild scripts/cuesheet.mjs --bundle --platform=node --outfile=.cuesheet.cjs && node .cuesheet.cjs && rm .cuesheet.cjs
```

## How the audio is wired

Three independent layers in `src/audio/Soundtrack.tsx`, so any one can be absent
without breaking the others.

1. **Bed.** One file, `public/audio/bed.mp3`, at 0.16. Almost subliminal.
2. **Effects.** One file per cue in `src/audio/cues.ts`. Cut cues derive their
   position from the timeline, so retiming a scene carries its sound with it.
3. **Narration.** One file per line, positioned by frame.

`AVAILABLE` in `Soundtrack.tsx` is the manifest. A file only plays once it is
both dropped into `public/audio` and named there. That is deliberate: a missing
asset should not fail a render eighty seconds into a ninety second film.

## Mix intent

Narration carries the argument. The bed is atmosphere and ducks under every
line. Effects mark decisions rather than decorate motion.

**The two blackout cuts at 0:39.50 and 0:59.37 are the only moments allowed to be
loud.** They are the cuts the film exists for. If anything else in the mix
competes with them, that thing is wrong, not the blackout.

Nothing should sound triumphant. There is no success chime when a claim is
supported, because `SUPPORTED` here means a span was found in a fetched page,
which is a narrower claim than a chime communicates.

## Effect cues

| At | Cue | Character |
|---|---|---|
| 00:02.60 | `ui-send` | The question is sent. One soft key, no click. |
| 00:16.10 | `cut-push` | Paper movement, barely there. |
| 00:21.27 | `cut-rule` | A thin sweep travelling with the rule. |
| 00:28.07 | `verdict-settle` | A claim resolves green. Warm, short, no bell. |
| 00:30.13 | `span-confirm` | The span is found. The one satisfying sound in the film. |
| 00:33.33 | `verdict-settle-low` | A claim resolves rust. Same shape, lower. |
| 00:39.50 | `cut-blackout` | Low soft impact. Loud. |
| 00:41.07 | `verdict-withhold` | Could not verify. A sound that stops rather than resolves. |
| 00:53.93 | `gate-close` | `INSUFFICIENT_EVIDENCE`. Low, final, not a slam. |
| 00:59.37 | `cut-blackout` | Low soft impact. Loud. |
| 01:05.20 | `figure-land` | Kappa arrives, after its interval. No fanfare. It is not good news. |
| 01:21.80 | `near-miss` | The two intervals nearly touching. A held tone, slightly uneasy. |
| 01:23.47 | `cut-dip` | Air, no transient. The film letting go. |

## Narration script

About 195 words. Timings are where each line **starts**. Record as separate
takes, one file per line, named as in the table; the manifest positions them by
frame so a line running long does not push the ones after it.

Two lines are load-bearing and must be delivered as written.

| Start | File | Line |
|---|---|---|
| 00:02.4 | `vo-01.mp3` | You ask a question, and the answer arrives already carrying sources. |
| 00:08.6 | `vo-02.mp3` | The citation is what does the persuading. |
| 00:12.2 | `vo-03.mp3` | Nothing in the pipeline checks it. |
| 00:21.6 | `vo-04.mp3` | This does not ask whether a claim is true. |
| 00:24.4 | `vo-05.mp3` | It asks a narrower one. Does the page that was cited actually say this. |
| 00:28.4 | `vo-06.mp3` | Supported means it found the sentence on the page, and a script confirmed the quote is really in the document that was fetched. |
| 00:34.2 | `vo-07.mp3` | Not supported is a statement about the citation, not about the world. The claim may be true and cited to the wrong page. |
| 00:41.4 | `vo-08.mp3` | And sometimes it says nothing at all. |
| 00:44.8 | `vo-09.mp3` | This claim's only source is a page that is gone. There is nothing to check against, so it will not score it. |
| 00:50.6 | `vo-10.mp3` | **Every other tool I looked at gives you a number here. A number here is invented.** |
| 00:54.4 | `vo-11.mp3` | It refuses at the answer level too. More than half this answer's cited claims produced no verdict that stands, so it withholds the rate. |
| 01:02.0 | `vo-12.mp3` | Forty five claims, hand labelled blind, before the judge saw any of them. |
| 01:05.6 | `vo-13.mp3` | **Agreement with a human is a kappa of 0.30, with a confidence interval from 0.004 to 0.60, over 35 pairs. That lower bound is the honest part. At this sample size it cannot rule out chance.** |
| 01:14.0 | `vo-14.mp3` | It agrees best on "the page does not say this", and worst on "the page partly says this". |
| 01:21.6 | `vo-15.mp3` | Those two intervals miss each other by two tenths of a point. The finding holds, barely, and the graphic says so. |
| 01:24.6 | `vo-16.mp3` | Unauditable claims are counted, named, and kept out of every rate. |

### The two that cannot be paraphrased

**`vo-13`.** VIDEO.md names quoting 0.30 without its interval as the one sentence
that would sink the video. The interval and the n are part of the line, not a
caption under it. If the take runs long, cut something else.

**`vo-10`.** "Every other tool" is a claim about competitors. `SCOPE.md` §5a
allows it only as a claim about their marketing copy, because the head to head
has not been run. If the delivery makes it sound like a measured comparison,
soften it to "every other tool I looked at says it will give you a number here".

### Also do not say

- Any stratum support rate. There isn't one. Per-answer and per-domain rates are
  real and may be read, with their n.
- That the two `CONTRADICTED` verdicts were catches. Both were read by hand and
  both look like the judge conflating an adjacent category. `FINDINGS.md` item 25.
- That the citation capture is complete. It is not, by a measured floor of 37.7%.

## If narration is recorded live

The timings above are targets, not constraints. Record the lines first, measure
them, then retime scenes in `src/film/timing.ts` to fit the delivery rather than
compressing the delivery to fit the picture. Scene lengths are one table and the
cue sheet regenerates from it.
