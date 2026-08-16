/**
 * The screen recording, and whether it exists yet.
 *
 * The browser scene is left out of the cut entirely until `present` is true,
 * rather than showing a placeholder. A film that renders with a slate in it is
 * a film someone will eventually send to a professor by accident.
 *
 * When the take is recorded, drop it at video/public/footage/audit.mp4, set
 * `present` to true, and set `durationInFrames` to its real length. See
 * RECORDING.md for what to record and how.
 */
export const FOOTAGE = {
  file: "footage/audit.mp4",
  present: false,
  /** Length of the take, in frames at 30fps. */
  durationInFrames: 380,
  /** Native size of the recording. The scene letterboxes nothing; it fits this. */
  width: 1280,
  height: 800,
} as const;
