import { TIMELINE } from "../film/timing";

/**
 * Everything the film wants to hear, and when.
 *
 * Cut cues are derived from the timeline so they cannot drift out of sync with
 * an edit. Beat cues inside a scene are written as an offset from that scene's
 * start for the same reason: retiming a scene carries its own sounds with it.
 *
 * Nothing here plays until the matching file exists in public/audio. A missing
 * file is skipped rather than throwing, so the film always renders.
 */

export type Cue = {
  id: string;
  /** Absolute frame. */
  at: number;
  file: string;
  volume?: number;
  note: string;
};

const sceneStart = (name: string) => TIMELINE.find((s) => s.name === name)?.start ?? 0;
const beat = (scene: string, offset: number) => sceneStart(scene) + offset;

/** The two blackout cuts get the only real impacts in the film. */
const CUT_SOUND: Record<string, { file: string; volume: number; note: string }> = {
  blackout: {
    file: "cut-blackout.mp3",
    volume: 0.85,
    note: "Low soft impact under the ink sweep. The only two loud moments.",
  },
  push: { file: "cut-push.mp3", volume: 0.3, note: "Paper movement, barely there." },
  rule: { file: "cut-rule.mp3", volume: 0.26, note: "A thin sweep travelling with the rule." },
  dip: { file: "cut-dip.mp3", volume: 0.22, note: "Air, no transient. The film letting go." },
};

export const CUES: Cue[] = [
  ...TIMELINE.flatMap((scene) =>
    scene.cutAt !== null && scene.cutKind
      ? [
          {
            id: `cut-after-${scene.name}`,
            // Landing the sound a few frames into the cut, not on its first
            // frame, is what makes a transition feel struck rather than
            // accompanied.
            at: scene.cutAt + Math.round(scene.cutLength * 0.35),
            ...CUT_SOUND[scene.cutKind],
          },
        ]
      : [],
  ),

  {
    id: "question-send",
    at: beat("Cold open", 78),
    file: "ui-send.mp3",
    volume: 0.4,
    note: "The question is sent. One soft key, no click.",
  },
  {
    id: "verdict-supported",
    at: beat("What it does", 216),
    file: "verdict-settle.mp3",
    volume: 0.5,
    note: "A claim resolves green. Warm, short, no bell.",
  },
  {
    id: "span-confirmed",
    at: beat("What it does", 278),
    file: "span-confirm.mp3",
    volume: 0.45,
    note: "The span is found on the page. The one satisfying sound in the film.",
  },
  {
    id: "verdict-not-supported",
    at: beat("What it does", 374),
    file: "verdict-settle-low.mp3",
    volume: 0.5,
    note: "A claim resolves rust. Same shape as the green one, lower.",
  },
  {
    id: "refusal-row",
    at: beat("The refusal", 62),
    file: "verdict-withhold.mp3",
    volume: 0.55,
    note: "Could not verify lands. A sound that stops rather than resolves.",
  },
  {
    id: "gate-refuses",
    at: beat("The refusal", 448),
    file: "gate-close.mp3",
    volume: 0.6,
    note: "INSUFFICIENT_EVIDENCE on the ink card. Low, final, not a slam.",
  },
  {
    id: "kappa-lands",
    at: beat("Calibration", 190),
    file: "figure-land.mp3",
    volume: 0.4,
    note: "0.30 arrives, after its interval. Soft, no fanfare, it is not good news.",
  },
  {
    id: "near-miss",
    at: beat("Calibration", 688),
    file: "near-miss.mp3",
    volume: 0.45,
    note: "The two intervals nearly touching. A held tone, slightly uneasy.",
  },
];

/** Frames to seconds, for anything that has to talk to a DAW or a script. */
export const asSeconds = (frame: number, fps = 30) => (frame / fps).toFixed(2);
