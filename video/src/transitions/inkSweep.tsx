import type {
  TransitionPresentation,
  TransitionPresentationComponentProps,
} from "@remotion/transitions";
import React from "react";
import { AbsoluteFill, interpolate } from "remotion";
import { C, EASE_IN_OUT, FONT } from "../theme";

export type InkSweepProps = { word?: string; color?: string };

/**
 * A solid panel sweeps up, holds the frame completely black for a beat, and
 * keeps going, revealing the next scene behind it. It carries a word through
 * the blackout, which is what turns a wipe into a beat: these are the film's
 * two section titles, and the only two cuts that change the argument.
 *
 * **The panel used to hold black for exactly one frame**, at p=0.5, because
 * panelY went 1080 to 0 to -1080 with no dwell. The word faded in and out over
 * a third of a 44 frame transition, so "How much is a verdict worth" had about
 * half a second on screen and could not be read at all. A title nobody can read
 * is worse than no title: it reads as a glitch. So the panel now dwells at full
 * cover, and the word holds at full opacity inside that dwell rather than only
 * touching it in passing.
 */
const InkSweep: React.FC<TransitionPresentationComponentProps<InkSweepProps>> = ({
  children,
  presentationDirection,
  presentationProgress,
  passedProps,
}) => {
  const p = interpolate(presentationProgress, [0, 1], [0, 1], { easing: EASE_IN_OUT });
  const color = passedProps.color ?? C.ink;

  // The panel covers the frame between COVER_IN and COVER_OUT, and dwells there.
  // Everything outside that window is the sweep itself.
  const COVER_IN = 0.4;
  const COVER_OUT = 0.6;
  const panelY = interpolate(p, [0, COVER_IN, COVER_OUT, 1], [1080, 0, 0, -1080]);

  return (
    <AbsoluteFill>
      <AbsoluteFill
        style={{
          opacity: presentationDirection === "exiting" ? (p < 0.5 ? 1 : 0) : p >= 0.5 ? 1 : 0,
          scale:
            presentationDirection === "exiting"
              ? interpolate(p, [0, 0.5], [1, 0.97], { extrapolateRight: "clamp" })
              : interpolate(p, [0.5, 1], [1.03, 1], { extrapolateLeft: "clamp" }),
        }}
      >
        {children}
      </AbsoluteFill>

      {presentationDirection === "entering" ? (
        <AbsoluteFill
          style={{
            backgroundColor: color,
            translate: `0px ${panelY}px`,
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          {passedProps.word ? (
            <div
              style={{
                fontFamily: FONT.mono,
                fontSize: 34,
                letterSpacing: "0.28em",
                textTransform: "uppercase",
                color: C.paper,
                // Up before the panel finishes covering, held through the whole
                // dwell, gone only once the panel is moving again.
                opacity: interpolate(p, [0.28, 0.4, 0.6, 0.72], [0, 1, 1, 0], {
                  extrapolateLeft: "clamp",
                  extrapolateRight: "clamp",
                }),
                translate: `0px ${interpolate(p, [0.28, 0.72], [14, -14])}px`,
              }}
            >
              {passedProps.word}
            </div>
          ) : null}
        </AbsoluteFill>
      ) : null}
    </AbsoluteFill>
  );
};

export const inkSweep = (props: InkSweepProps = {}): TransitionPresentation<InkSweepProps> => {
  return { component: InkSweep, props };
};
