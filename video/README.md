# The explainer film

A 90 second film about what SaysWho does, built in [Remotion](https://remotion.dev), which is video as
React. 1920x1080, 30fps.

This is the short film. `../VIDEO.md` is the script and shot list for the longer graded cut, which contains
the uncut demo segment the rubric asks for. Both are meant to share this design system.

```bash
npm i
npx remotion studio          # preview and edit
npx remotion render Film out/film.mp4
```

Remotion is free for individuals and for teams of up to three.

## No figure in this film is typed by hand

`scripts/sync-run.mjs` reads a run record and generates `src/runData.ts`. Every claim, verdict, quoted span
and rate on screen comes from there, and the question text is read out of the frozen query file so the words
shown are the words that were hashed.

```bash
node scripts/sync-run.mjs ../runs/day9/run.json
```

Regenerate rather than correcting a number in `src/runData.ts`. It also prints the gap between the two
per-class intervals and says so loudly if a future run makes them overlap, because the film has a beat built
on them missing each other by 0.21 of a point.

## The rule that shapes the components

`VIDEO.md` names quoting kappa without its interval as the one thing that would sink the video. So
`IntervalBar.tsx` takes the interval as a required prop and finishes drawing the band, its bounds and the
written `95% CI ..., n=...` before the number becomes legible. The frame showing a bare point estimate
cannot be rendered, rather than being something a person has to remember not to make.

The first version did not do this, despite a comment claiming it did. Both the ordering and the direction
the band grew were wrong. See the header comment in that file.

There is no count-up anywhere. A figure ticking up from zero performs a precision the interval exists to
deny.

## Layout

| | |
|---|---|
| `src/theme.ts` | Palette and type scale. Every colour is lifted from `extension/src/render.css`, so the film and the product are the same object. |
| `src/film/timing.ts` | Scene lengths and cuts, as pure data. Everything downstream reads from here. |
| `src/film/Film.tsx` | Scene name to component, and the cut grammar. |
| `src/film/scenes/` | One file per scene. |
| `src/transitions/` | Four cuts. `paperPush` is ordinary, `ruleReveal` marks a change of subject, `inkSweep` is used exactly twice on the cuts the film exists for, `dipThroughPaper` ends it. `matchCut` switches on with the footage. |
| `src/audio/` | The soundtrack, silent until files land in `public/audio` and are named in the manifest. See `SOUND.md`. |
| `src/footage.ts` | One flag. The browser scene is not in the cut until the take exists. See `RECORDING.md`. |

## Two things it is missing

**Sound.** `SOUND.md` has the cue sheet with timecodes and the narration script timed to the cut.

**The browser take.** `RECORDING.md` says what to record. The match cut into the frame and both camera
pushes are built and switch on from `src/footage.ts`.

## The cue sheet

Regenerate after any retime. Node cannot resolve the project's extensionless TypeScript imports on its own,
so bundle it first with the esbuild Remotion already depends on:

```bash
npx esbuild scripts/cuesheet.mjs --bundle --platform=node --outfile=.cuesheet.cjs && node .cuesheet.cjs && rm .cuesheet.cjs
```
