/**
 * The cut, as pure data.
 *
 * Scene lengths and the cut between each pair live here rather than in Film.tsx
 * so that anything needing the timeline (the soundtrack, a cue sheet, a caption
 * export) can read it without importing the scene components. That is not only
 * tidiness: the soundtrack derives its cue positions from this table, and when
 * it imported them from Film.tsx the two modules formed a cycle and TIMELINE
 * was read before it was built.
 *
 * `overlap` is how many frames the two scenes share. A transition shortens the
 * film by its own length, so the total is the sum of the durations minus the
 * sum of the overlaps.
 *
 * The cuts are deliberately not all the same. `push` is the ordinary one. `rule`
 * marks a change of subject rather than of argument. `blackout` is used exactly
 * twice, on the two cuts the film exists for, so that it still means something
 * when it happens. `dip` ends the film by letting it dissolve into the paper.
 */

import { FOOTAGE } from "../footage";

export type CutKind = "push" | "rule" | "blackout" | "dip" | "match";

/**
 * The browser scene only exists once the take has been recorded. Until then it
 * is not in the film at all, rather than in the film as a placeholder, and every
 * downstream timing (the cue sheet, the narration marks) follows automatically.
 */
export const SCENE_TIMING = [
  { name: "Cold open", duration: 500 },
  { name: "Title", duration: 186 },
  ...(FOOTAGE.present
    ? [{ name: "In the browser", duration: FOOTAGE.durationInFrames }]
    : []),
  { name: "What it does", duration: 588 },
  { name: "The refusal", duration: 640 },
  { name: "Calibration", duration: 760 },
  { name: "Close", duration: 186 },
] satisfies readonly { name: string; duration: number }[];

export const CUTS = [
  { after: "Cold open", kind: "push", overlap: 26 },
  ...(FOOTAGE.present
    ? ([
        { after: "Title", kind: "match", overlap: 30 },
        { after: "In the browser", kind: "push", overlap: 26 },
      ] as const)
    : ([{ after: "Title", kind: "rule", overlap: 34 }] as const)),
  { after: "What it does", kind: "blackout", overlap: 44, word: "Could not verify" },
  { after: "The refusal", kind: "blackout", overlap: 44, word: "How much is a verdict worth" },
  { after: "Calibration", kind: "dip", overlap: 34 },
] satisfies readonly {
  after: string;
  kind: CutKind;
  overlap: number;
  word?: string;
}[];

/** Where every scene starts and every cut sits, in absolute frames. */
export const TIMELINE = (() => {
  let at = 0;
  return SCENE_TIMING.map((scene) => {
    const cut = CUTS.find((c) => c.after === scene.name);
    const start = at;
    at += scene.duration - (cut?.overlap ?? 0);
    return {
      name: scene.name,
      start,
      duration: scene.duration,
      cutAt: cut ? start + scene.duration - cut.overlap : null,
      cutLength: cut?.overlap ?? 0,
      cutKind: (cut?.kind ?? null) as CutKind | null,
    };
  });
})();

export const FILM_DURATION =
  SCENE_TIMING.reduce((n, s) => n + s.duration, 0) -
  CUTS.reduce((n, c) => n + c.overlap, 0);
