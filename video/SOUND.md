# Sound: cue sheet and narration

The film is 3454 frames, 1:55.13 at 30fps. Everything below is generated from or
timed against `src/film/timing.ts`, which is the same table the render uses.

**It was 2678 frames when this document was written.** The browser take landed
and added a 902 frame scene after the title, and the two blackouts went from 44
frames to 96 so their section titles can actually be read. Every timing below is
the retimed one. The effect cues were regenerated; the narration table was
recomputed by hand, keeping each line where it sat inside its own scene.

## Voice

`txYZyFyf0wIEgqUsHmno` on ElevenLabs, chosen 2026-08-16. Every `vo-*.mp3` uses
it, so a reshoot of one line matches the rest.

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

Regenerated 2026-08-16 against the retimed film. Two of these are new and were
asked for by name: the keys and the pop that opens the film.

| At | Cue | Character |
|---|---|---|
| 00:00.40 | `keys-typing` | The question being typed. Soft, dry, no room. Under everything else. |
| 00:02.60 | `ui-send` | The question is sent. One soft key, no click. |
| 00:04.27 | `answer-pop` | The answer appears. A soft message pop, not a chime and not a win. |
| 00:16.10 | `cut-push` | Paper movement, barely there. |
| 00:21.37 | `cut-match` | The title becoming the browser. One soft transient, no tail. |
| 00:50.50 | `cut-push` | Paper movement, barely there. |
| 00:57.40 | `verdict-settle` | A claim resolves green. Warm, short, no bell. |
| 00:59.47 | `span-confirm` | The span is found. The one satisfying sound in the film. |
| 01:02.67 | `verdict-settle-low` | A claim resolves rust. Same shape, lower. |
| 01:07.73 | `cut-blackout` | Low soft impact. Loud. |
| 01:08.67 | `verdict-withhold` | Could not verify. A sound that stops rather than resolves. |
| 01:21.53 | `gate-close` | `INSUFFICIENT_EVIDENCE`. Low, final, not a slam. |
| 01:25.87 | `cut-blackout` | Low soft impact. Loud. |
| 01:31.07 | `figure-land` | Kappa arrives, after its interval. No fanfare. It is not good news. |
| 01:47.67 | `near-miss` | The two intervals nearly touching. A held tone, slightly uneasy. |
| 01:49.33 | `cut-dip` | Air, no transient. The film letting go. |

**`cut-match` is new because the cue for it was broken rather than missing.**
`CUT_SOUND` had no entry for the match cut, which only exists once
`FOOTAGE.present` is true, so the cue was built with an undefined file. The
render dropped it silently, because `AVAILABLE[undefined]` is falsy, and the
cue sheet script crashed on it. A kind with no sound defined now produces no cue
at all rather than a cue that reads as real and plays nothing.

## Narration script

Rewritten 2026-08-16 as one script for the whole film rather than a set of
captions read aloud. About 250 words over 1:55.

Three rules it was written to. **The picture already says a lot**, so a line that
repeats the words on screen was cut; the narration sets up what is about to
appear and then gets out of the way. **No sentence claims more than the repo can
show**, which is why the competitor line is about what other tools say rather
than about what they do, and why nothing here is called accurate, powerful or
best. **Short sentences, concrete nouns, no adjectives doing work a verb should
do.**

The scene-and-offset column is the one to trust. Absolute times are derived from
it and will be wrong after the next retime.

**Three written lines were cut after they were recorded**, because hearing them
read while the same words sit on screen is one beat spent twice, and the scenes
were over length by roughly the time they took. `vo-14`, because the screen
already says *Not supported by the cited source is a claim about the citation,
not about the world* in full. `vo-17`, because the screen already says *Every
other tool I looked at promises a number here*. `vo-20`, because Calibration
opens on *So how much is one of its verdicts worth?*, which is the same setup.
The files still exist in `public/audio` and are simply not in the manifest, so
putting one back is one line.

| Scene + offset | Start | File | Line |
|---|---|---|---|
| Cold open +2.4 | 00:02.4 | `vo-01.mp3` | Every AI answer now arrives with its sources attached. |
| Cold open +6.2 | 00:06.2 | `vo-02.mp3` | The links are what make it feel checked. |
| Cold open +9.6 | 00:09.6 | `vo-03.mp3` | They are also the part nobody opens. |
| Cold open +12.8 | 00:12.8 | `vo-04.mp3` | And nothing that produced this answer ever read them. |
| Title +2.0 | 00:17.8 | `vo-05.mp3` | SaysWho reads them. |
| In the browser +3.5 | 00:24.5 | `vo-06.mp3` | It runs on the page the answer is already on. |
| In the browser +9.0 | 00:30.0 | `vo-07.mp3` | It takes the answer, hashes it, and lists every source it cites. |
| In the browser +13.5 | 00:34.5 | `vo-08.mp3` | It tells you when it cannot see them all. Two here are hidden behind a control. |
| In the browser +19.0 | 00:40.0 | `vo-09.mp3` | Then it fetches every cited page and reads it. |
| In the browser +24.5 | 00:45.5 | `vo-10.mp3` | Every sentence comes back marked, with the source's own words underneath. |
| What it does +1.0 | 00:51.2 | `vo-11.mp3` | It does not ask whether a claim is true. |
| What it does +4.0 | 00:54.2 | `vo-12.mp3` | It asks whether the page that was cited says it. |
| What it does +7.8 | 00:58.0 | `vo-13.mp3` | Supported means it quoted the page, and a script confirmed the quote is really there. |
| The refusal +2.6 | 01:09.2 | `vo-15.mp3` | And sometimes it gives you nothing. |
| The refusal +6.2 | 01:12.8 | `vo-16.mp3` | This claim's only source is a page that is gone. There is nothing to read, so it will not score it. |
| The refusal +12.4 | 01:19.0 | `vo-18.mp3` | A number here is invented. |
| The refusal +15.8 | 01:22.4 | `vo-19.mp3` | It refuses at the answer level too. |
| Calibration +3.4 | 01:28.1 | `vo-21.mp3` | Forty five claims, labelled blind, before the judge saw any of them. |
| Calibration +8.3 | 01:33.0 | `vo-22.mp3` | **Agreement is a kappa of 0.30, confidence interval 0.004 to 0.60, over thirty five pairs.** |
| Calibration +16.0 | 01:40.7 | `vo-23.mp3` | **The lower bound is the honest part. Chance is not ruled out.** |
| Calibration +19.6 | 01:44.3 | `vo-24.mp3` | It agrees best when the page simply does not say it. Worst when the page partly does. |
| Close +1.4 | 01:50.3 | `vo-25.mp3` | It cannot tell you a source is right. A well cited falsehood passes. |
| Close +3.6 | 01:52.5 | `vo-26.mp3` | It can tell you when nobody checked. |

### The two that cannot be paraphrased

**`vo-22` and `vo-23`.** VIDEO.md names quoting 0.30 without its interval as the
one sentence that would sink the video. The interval and the n are part of the
line, not a caption under it, and `vo-23` is why the number is in the film at
all. If a take runs long, cut something else.

**`vo-17`.** "Every other tool" is a claim about competitors. `SCOPE.md` §5a
allows it only as a claim about their marketing copy, because the head to head
has not been run, which is why the line is now written as *says it will give you
a number* rather than *gives you*. **The on-screen text in `Refusal.tsx` still
reads "Every other tool gives you a number here"**, unqualified, which is the
stronger claim §5a does not allow. Fix the picture or accept that the voice is
carrying the caveat alone.

**`vo-19`.** The gate fires at `measured * 2 <= total`, so it triggers when half
an answer's cited claims or more come back with no standing verdict. The
docstring and `INSUFFICIENT_EVIDENCE_DETAIL` in `rates.py` both say "more than
half", which is off by the equality case. The line avoids the number entirely
and lets the screen state the rule.

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
