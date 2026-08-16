import type {
  TransitionPresentation,
  TransitionPresentationComponentProps,
} from "@remotion/transitions";
import React from "react";
import { AbsoluteFill, interpolate } from "remotion";
import { EASE_IN_OUT } from "../theme";

export type MatchCutProps = {
  /** The rect the outgoing scene collapses into, matching the browser frame. */
  width?: number;
  height?: number;
  radius?: number;
};

/**
 * The outgoing statement shrinks to exactly the rect the incoming browser frame
 * occupies, growing the same corner radius on the way, so the sentence becomes
 * the window it was talking about.
 *
 * It is a clip rather than a scale. Scaling the whole frame down to the rect
 * would shrink the type with it, which reads as the film zooming out; clipping
 * to the rect leaves the type at its own size and reads as the frame closing in
 * around it. The small scale that is here is only to give the collapse
 * somewhere to go.
 */
const MatchCut: React.FC<TransitionPresentationComponentProps<MatchCutProps>> = ({
  children,
  presentationDirection,
  presentationProgress,
  passedProps,
}) => {
  const p = interpolate(presentationProgress, [0, 1], [0, 1], { easing: EASE_IN_OUT });
  const w = passedProps.width ?? 1500;
  const h = passedProps.height ?? 742;
  const radius = passedProps.radius ?? 22;

  if (presentationDirection === "exiting") {
    const insetX = interpolate(p, [0, 1], [0, (1920 - w) / 2]);
    const insetY = interpolate(p, [0, 1], [0, (1080 - h) / 2]);
    return (
      <AbsoluteFill
        style={{
          clipPath: `inset(${insetY}px ${insetX}px round ${interpolate(p, [0, 1], [0, radius])}px)`,
          scale: interpolate(p, [0, 1], [1, 0.985]),
          opacity: interpolate(p, [0.6, 1], [1, 0], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          }),
        }}
      >
        {children}
      </AbsoluteFill>
    );
  }

  return (
    <AbsoluteFill
      style={{
        opacity: interpolate(p, [0.5, 1], [0, 1], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        }),
      }}
    >
      {children}
    </AbsoluteFill>
  );
};

export const matchCut = (props: MatchCutProps = {}): TransitionPresentation<MatchCutProps> => {
  return { component: MatchCut, props };
};
