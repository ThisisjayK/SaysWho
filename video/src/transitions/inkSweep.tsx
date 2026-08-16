import type {
  TransitionPresentation,
  TransitionPresentationComponentProps,
} from "@remotion/transitions";
import React from "react";
import { AbsoluteFill, interpolate } from "remotion";
import { C, EASE_IN_OUT, FONT } from "../theme";

export type InkSweepProps = { word?: string; color?: string };

/**
 * A solid panel sweeps up, covers the frame completely at the midpoint, and
 * keeps going, revealing the next scene behind it. Optionally it carries a word
 * through the blackout, which is what turns a wipe into a beat.
 *
 * Reserved for the two cuts that change the argument. Used more often than that
 * it stops meaning anything.
 */
const InkSweep: React.FC<TransitionPresentationComponentProps<InkSweepProps>> = ({
  children,
  presentationDirection,
  presentationProgress,
  passedProps,
}) => {
  const p = interpolate(presentationProgress, [0, 1], [0, 1], { easing: EASE_IN_OUT });
  const color = passedProps.color ?? C.ink;

  // The panel covers the frame from p=0.5 onward, so each side only needs to be
  // painted while it is actually visible.
  const panelY = interpolate(p, [0, 0.5, 1], [1080, 0, -1080]);

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
                opacity: interpolate(p, [0.32, 0.5, 0.68], [0, 1, 0], {
                  extrapolateLeft: "clamp",
                  extrapolateRight: "clamp",
                }),
                translate: `0px ${interpolate(p, [0.3, 0.7], [22, -22])}px`,
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
