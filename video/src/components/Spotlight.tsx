import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { clamp, EASE_IN_OUT, EASE_OUT } from "../theme";

export type Pose = {
  /** Centre of the hole, in pixels within a 1920x1080 frame. */
  x: number;
  y: number;
  /** Radii of the fully transparent core. */
  rx: number;
  ry: number;
  /** Frame this pose is reached. */
  at: number;
};

/**
 * A dim layer with a soft hole punched through it, which can glide from one
 * target to another and tighten as it goes.
 *
 * This exists for the span receipt. Fading a quoted sentence in from nothing is
 * the grammar of a sentence being written; the claim being made is the opposite,
 * that the sentence was already on the page and the tool located it. Narrowing
 * the light onto text that is already there is what finding looks like.
 *
 * The veil is paper, not black. Laying dark over cream turns the surround olive,
 * because a warm light background does not darken gracefully. Washing the
 * surround toward the page instead reads as attention narrowing rather than as
 * a light being switched off, and it keeps every colour in the frame on palette.
 *
 * The feather is very wide on purpose. At 1920 across, anything tighter shows
 * the ellipse as a shape, and the moment a viewer can see the spotlight's edge
 * it stops being a look and starts being an effect.
 */
export const Spotlight: React.FC<{
  poses: Pose[];
  dim?: number;
  fadeIn?: number;
  fadeOut?: [number, number];
}> = ({ poses, dim = 0.72, fadeIn = 14, fadeOut }) => {
  const frame = useCurrentFrame();
  const times = poses.map((p) => p.at);

  const track = (key: "x" | "y" | "rx" | "ry") =>
    poses.length === 1
      ? poses[0][key]
      : interpolate(
          frame,
          times,
          poses.map((p) => p[key]),
          { ...clamp, easing: EASE_IN_OUT },
        );

  const start = poses[0].at;
  const alpha =
    interpolate(frame, [start, start + fadeIn], [0, dim], { ...clamp, easing: EASE_OUT }) *
    (fadeOut ? interpolate(frame, fadeOut, [1, 0], clamp) : 1);

  const mask = `radial-gradient(ellipse ${track("rx")}px ${track("ry")}px at ${track("x")}px ${track("y")}px, transparent 30%, #000 100%)`;

  return (
    <AbsoluteFill
      style={{
        backgroundColor: `rgba(250,249,245,${alpha})`,
        maskImage: mask,
        WebkitMaskImage: mask,
        pointerEvents: "none",
      }}
    />
  );
};
