# The film

Two things live here. The Remotion project, which is video as React, and the scripts that cut the live demo
and join the two into the film the site carries.

**The published file is `../site/media/sayswho.mp4`, 5:20, narrated.** It is the only video any page links.

| | |
|---|---|
| `src/`, `remotion.config.ts` | The Remotion short. 1920x1080, 30fps, 3558 frames, 118.6s. `npx remotion render Film out/film.mp4` |
| `scripts/explainer.py` | The live demo, recut so every narration line lands on the picture it describes, and masked so the ChatGPT sidebar cannot be read. Writes `out/explainer-web.mp4` |
| `scripts/explainer_tts.py` | The fifteen narration lines, written in `explainer.py`, turned back into audio in the `SOUND.md` voice |
| `scripts/consolidate.py` | The short and the demo, joined into one film. Writes `../site/media/sayswho.mp4` |

Nothing in `out/` is published and nothing in it is committed. `site/media/` holds only what a page links,
which is the film, its poster and the install clip.

`../VIDEO.md` is the script and shot list the demo was cut from, with a section at the top on where the
finished film departs from it.

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

## The two things it was missing, and no longer is

**Sound.** Twenty six lines in the `SOUND.md` voice, positioned by scene and offset in
`src/audio/narration.ts` so a retime carries its own narration. There is no music: a bed was built,
listened to in the cut, and rejected.

**The browser take.** Shot 2026-08-16 and cut to 902 frames at `public/footage/audit.mp4`, so
`src/footage.ts` says `present` and the match cut and both camera pushes are switched on. `RECORDING.md`
lists where the take departs from what it asked for, including the one join where time is genuinely missing
rather than compressed.

## The cue sheet

Regenerate after any retime. Node cannot resolve the project's extensionless TypeScript imports on its own,
so bundle it first with the esbuild Remotion already depends on:

```bash
npx esbuild scripts/cuesheet.mjs --bundle --platform=node --outfile=.cuesheet.cjs && node .cuesheet.cjs && rm .cuesheet.cjs
```
