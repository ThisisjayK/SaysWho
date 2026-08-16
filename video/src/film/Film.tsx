import type { TransitionPresentation, TransitionTiming } from "@remotion/transitions";
import { linearTiming, springTiming, TransitionSeries } from "@remotion/transitions";
import React from "react";
import { AbsoluteFill } from "remotion";
import { Soundtrack } from "../audio/Soundtrack";
import "../fonts";
import { dipThroughPaper } from "../transitions/dipThroughPaper";
import { inkSweep } from "../transitions/inkSweep";
import { matchCut } from "../transitions/matchCut";
import { paperPush } from "../transitions/paperPush";
import { ruleReveal } from "../transitions/ruleReveal";
import { Calibration } from "./scenes/Calibration";
import { Chat } from "./scenes/Chat";
import { Close } from "./scenes/Close";
import { InTheBrowser } from "./scenes/InTheBrowser";
import { Refusal } from "./scenes/Refusal";
import { Title } from "./scenes/Title";
import { WhatItDoes } from "./scenes/WhatItDoes";
import { CUTS, CutKind, SCENE_TIMING } from "./timing";

export { FILM_DURATION, TIMELINE } from "./timing";

/** Scene name to the component that draws it. Lengths live in timing.ts. */
const COMPONENTS: Record<string, React.FC> = {
  "Cold open": Chat,
  Title,
  "In the browser": InTheBrowser,
  "What it does": WhatItDoes,
  "The refusal": Refusal,
  Calibration,
  Close,
};

export const SCENES = SCENE_TIMING.map((scene) => ({
  ...scene,
  component: COMPONENTS[scene.name],
}));

type Presentation = TransitionPresentation<Record<string, unknown>>;

const presentationFor = (cut: (typeof CUTS)[number]): Presentation => {
  const kind: CutKind = cut.kind;
  if (kind === "blackout") {
    return inkSweep({ word: "word" in cut ? cut.word : undefined }) as Presentation;
  }
  if (kind === "rule") return ruleReveal() as Presentation;
  if (kind === "match") return matchCut() as Presentation;
  if (kind === "dip") return dipThroughPaper() as Presentation;
  return paperPush() as Presentation;
};

const timingFor = (cut: (typeof CUTS)[number]): TransitionTiming =>
  cut.kind === "push"
    ? springTiming({ config: { damping: 200 }, durationInFrames: cut.overlap })
    : linearTiming({ durationInFrames: cut.overlap });

export const Film: React.FC = () => {
  return (
    <AbsoluteFill>
      {/* Silent until files land in public/audio and are named in the manifest. */}
      <Soundtrack bed="bed.mp3" />
      <TransitionSeries>
        {SCENES.flatMap((scene) => {
          const cut = CUTS.find((c) => c.after === scene.name);
          const nodes: React.ReactNode[] = [
            <TransitionSeries.Sequence
              key={scene.name}
              name={scene.name}
              durationInFrames={scene.duration}
            >
              <scene.component />
            </TransitionSeries.Sequence>,
          ];
          if (cut) {
            nodes.push(
              <TransitionSeries.Transition
                key={`${scene.name}-cut`}
                presentation={presentationFor(cut)}
                timing={timingFor(cut)}
              />,
            );
          }
          return nodes;
        })}
      </TransitionSeries>
    </AbsoluteFill>
  );
};
