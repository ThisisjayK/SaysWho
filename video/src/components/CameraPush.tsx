import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { clamp, EASE_IN_OUT } from "../theme";

export type Pose = {
  at: number;
  /** 1 is the whole frame. 1.8 is a comfortable read on a claim row. */
  zoom: number;
  /** Where to centre, as a fraction of the frame. 0.5, 0.5 is the middle. */
  x: number;
  y: number;
};

/**
 * A camera over a fixed rectangle, for pushing into part of a screen recording.
 *
 * The clamp is the whole component. Panning at a given zoom can only move the
 * frame so far before the edge of the source comes into view, and a recording
 * with cream showing along one side looks like a mistake rather than a move. So
 * the requested centre is pulled back to whatever the zoom can actually afford,
 * every frame, rather than being trusted.
 */
export const CameraPush: React.FC<{
  poses: Pose[];
  width: number;
  height: number;
  children: React.ReactNode;
}> = ({ poses, width, height, children }) => {
  const frame = useCurrentFrame();
  const times = poses.map((p) => p.at);

  const at = (key: "zoom" | "x" | "y") =>
    poses.length === 1
      ? poses[0][key]
      : interpolate(
          frame,
          times,
          poses.map((p) => p[key]),
          { ...clamp, easing: EASE_IN_OUT },
        );

  const zoom = at("zoom");
  // How far the centre may travel from the middle before an edge shows.
  const room = (size: number) => (size * (zoom - 1)) / 2 / zoom;
  const pull = (value: number, size: number) => {
    const wanted = (0.5 - value) * size * zoom;
    const limit = room(size) * zoom;
    return Math.max(-limit, Math.min(limit, wanted));
  };

  return (
    <AbsoluteFill style={{ overflow: "hidden", width, height }}>
      <AbsoluteFill
        style={{
          scale: zoom,
          translate: `${pull(at("x"), width)}px ${pull(at("y"), height)}px`,
        }}
      >
        {children}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
