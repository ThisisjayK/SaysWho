/**
 * The screen recording, and whether it exists yet.
 *
 * The browser scene is left out of the cut entirely until `present` is true,
 * rather than showing a placeholder. A film that renders with a slate in it is
 * a film someone will eventually send to a professor by accident.
 *
 * **Shot 2026-08-16, assembled from two recordings of one session.** It is not
 * the take RECORDING.md describes, and the departures are all deliberate:
 *
 * - **A new CO-02 conversation**, not the archived one behind `runs/day9/`. Ten
 *   claims and a verdict mix of its own, including two `Sources disagree`, a
 *   state no earlier take ever put on screen. Nothing in this scene reads a
 *   number off the footage, and the two captions claim only that an answer is
 *   marked claim by claim, which is true of what is shown. A caption here that
 *   grew a figure would have to take it from this recording, never `runData.ts`.
 * - **Two files, one session.** The first recording runs out while the audit is
 *   still going; the second picks up 27 seconds later with the panel drawn. The
 *   join is a crossfade at the point where the wait ends, which is the only
 *   place in the cut where time is missing rather than compressed.
 * - **The audit took about five minutes.** Clicked at 00:54 into the first
 *   recording, still running when it ends at 05:33, finished before the second
 *   starts: between 4m39s and 5m06s. That is the free tier's rate limits over
 *   ten claims, and it is a much slower number than the 22 seconds measured on
 *   the previous take. One second of it is in the cut, and the film says so on
 *   screen while the ramp runs.
 * - **Dark mode**, and the window is the page only: this recording has no
 *   browser toolbar in it, so nothing needed cropping and `BrowserChrome` draws
 *   the only browser on screen.
 *
 * Every join is a 0.25s crossfade and the fast passes carry motion blur, so the
 * speed changes read as speed rather than as cuts.
 *
 * The source recordings are not in the repo. They live on the Desktop they were
 * shot on, and this file is the cut down version.
 */
export const FOOTAGE = {
  file: "footage/audit.mp4",
  present: true,
  /** Length of the take, in frames at 30fps. */
  durationInFrames: 902,
  /** Native size of the recording. The scene letterboxes nothing; it fits this. */
  width: 1920,
  height: 1396,
} as const;
