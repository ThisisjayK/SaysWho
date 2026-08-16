import type {
  TransitionPresentation,
  TransitionPresentationComponentProps,
} from "@remotion/transitions";
import React from "react";
import { AbsoluteFill, interpolate } from "remotion";
import { C, EASE_IN_OUT } from "../theme";

export type DipProps = { color?: string; strength?: number };

/**
 * The quietest cut in the set. Three overlapping ramps rather than two: the
 * outgoing scene fades, a wash of paper rises to peak between the two fades,
 * and the incoming scene rises as the wash falls. Because the wash peaks in the
 * gap rather than during either fade, there is a real interval where the frame
 * is only paper, which is what separates a dip through from a cross dissolve.
 *
 * This exists to make the ordinary cuts quieter. inkSweep means something
 * because it happens twice and stops the frame; widening the gap between the
 * loud cut and the plain one costs nothing and is done here rather than by
 * making inkSweep louder.
 */
const DipThroughPaper: React.FC<TransitionPresentationComponentProps<DipProps>> = ({
  children,
  presentationDirection,
  presentationProgress,
  passedProps,
}) => {
  const p = interpolate(presentationProgress, [0, 1], [0, 1], { easing: EASE_IN_OUT });
  const strength = passedProps.strength ?? 0.55;

  return (
    <AbsoluteFill>
      <AbsoluteFill
        style={{
          opacity:
            presentationDirection === "exiting"
              ? interpolate(p, [0, 0.55], [1, 0], { extrapolateRight: "clamp" })
              : interpolate(p, [0.42, 1], [0, 1], { extrapolateLeft: "clamp" }),
        }}
      >
        {children}
      </AbsoluteFill>

      {presentationDirection === "entering" ? (
        <AbsoluteFill
          style={{
            backgroundColor: passedProps.color ?? C.paper,
            opacity: interpolate(p, [0.1, 0.5, 0.9], [0, strength, 0], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            }),
          }}
        />
      ) : null}
    </AbsoluteFill>
  );
};

export const dipThroughPaper = (props: DipProps = {}): TransitionPresentation<DipProps> => {
  return { component: DipThroughPaper, props };
};
