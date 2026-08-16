import type {
  TransitionPresentation,
  TransitionPresentationComponentProps,
} from "@remotion/transitions";
import React from "react";
import { AbsoluteFill, interpolate } from "remotion";
import { EASE_OUT } from "../theme";

export type PaperPushProps = { shadow?: boolean };

/**
 * The incoming scene rises and pushes the outgoing one up out of frame, with the
 * outgoing losing a little scale and focus so the eye follows the arriving card.
 *
 * The two halves move at different rates on purpose. Equal rates read as a slide
 * between two flat images; unequal rates read as one sheet of paper laid over
 * another, which is the whole trick.
 */
const PaperPush: React.FC<TransitionPresentationComponentProps<PaperPushProps>> = ({
  children,
  presentationDirection,
  presentationProgress,
  passedProps,
}) => {
  const p = interpolate(presentationProgress, [0, 1], [0, 1], { easing: EASE_OUT });

  if (presentationDirection === "exiting") {
    return (
      <AbsoluteFill
        style={{
          translate: `0px ${interpolate(p, [0, 1], [0, -170])}px`,
          scale: interpolate(p, [0, 1], [1, 0.94]),
          opacity: interpolate(p, [0, 0.85], [1, 0], { extrapolateRight: "clamp" }),
          filter: `blur(${interpolate(p, [0, 1], [0, 7])}px)`,
        }}
      >
        {children}
      </AbsoluteFill>
    );
  }

  return (
    <AbsoluteFill
      style={{
        translate: `0px ${interpolate(p, [0, 1], [1080, 0])}px`,
        boxShadow:
          passedProps.shadow === false
            ? undefined
            : `0 -60px 120px -40px rgba(20,20,15,${interpolate(p, [0, 1], [0.38, 0])})`,
      }}
    >
      {children}
    </AbsoluteFill>
  );
};

export const paperPush = (props: PaperPushProps = {}): TransitionPresentation<PaperPushProps> => {
  return { component: PaperPush, props };
};
