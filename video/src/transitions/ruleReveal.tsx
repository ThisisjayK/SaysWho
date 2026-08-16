import type {
  TransitionPresentation,
  TransitionPresentationComponentProps,
} from "@remotion/transitions";
import React from "react";
import { AbsoluteFill, interpolate } from "remotion";
import { C, EASE_IN_OUT } from "../theme";

export type RuleRevealProps = { color?: string; from?: "left" | "right" };

/**
 * A hairline rule travels across the frame and the next scene is revealed behind
 * it. The outgoing scene does not move at all, which is what makes this read as
 * a page being uncovered rather than two clips being cross faded.
 */
const RuleReveal: React.FC<TransitionPresentationComponentProps<RuleRevealProps>> = ({
  children,
  presentationDirection,
  presentationProgress,
  passedProps,
}) => {
  const p = interpolate(presentationProgress, [0, 1], [0, 1], { easing: EASE_IN_OUT });
  const fromLeft = (passedProps.from ?? "left") === "left";
  const edge = p * 100;

  if (presentationDirection === "exiting") {
    return <AbsoluteFill>{children}</AbsoluteFill>;
  }

  return (
    <AbsoluteFill>
      <AbsoluteFill
        style={{
          clipPath: fromLeft
            ? `inset(0 ${100 - edge}% 0 0)`
            : `inset(0 0 0 ${100 - edge}%)`,
        }}
      >
        {children}
      </AbsoluteFill>
      <AbsoluteFill
        style={{
          opacity: interpolate(p, [0, 0.06, 0.94, 1], [0, 1, 1, 0]),
        }}
      >
        <div
          style={{
            position: "absolute",
            top: 0,
            bottom: 0,
            left: fromLeft ? `${edge}%` : undefined,
            right: fromLeft ? undefined : `${edge}%`,
            width: 3,
            backgroundColor: passedProps.color ?? C.partial,
          }}
        />
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

export const ruleReveal = (props: RuleRevealProps = {}): TransitionPresentation<RuleRevealProps> => {
  return { component: RuleReveal, props };
};
