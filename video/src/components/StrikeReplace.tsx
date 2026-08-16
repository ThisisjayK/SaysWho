import React from "react";
import { interpolate, useCurrentFrame } from "remotion";
import { C, clamp, DISPLAY_TRACKING, DISPLAY_WEIGHT, EASE_OUT, FONT } from "../theme";

/**
 * A clause is struck out and its replacement arrives underneath it.
 *
 * The film's thesis is a narrowing of the question, from "is this true" to "does
 * the cited page say this". Cutting between two statements asserts the
 * narrowing. Striking one and replacing it performs it, in the same frame, so
 * the viewer sees which question was given up rather than being told.
 *
 * The replacement starts arriving just before the rule finishes, so the new
 * clause carries momentum out of the old one instead of blinking on after it.
 */
export const StrikeReplace: React.FC<{
  lead: string;
  struck: string;
  replacement: string;
  size?: number;
  strikeAt: number;
  name?: string;
}> = ({ lead, struck, replacement, size = 96, strikeAt, name = "Strike and replace" }) => {
  const frame = useCurrentFrame();

  const rule = interpolate(frame, [strikeAt, strikeAt + 9], [0, 1], {
    ...clamp,
    easing: EASE_OUT,
  });
  const swap = interpolate(frame, [strikeAt + 7, strikeAt + 18], [0, 1], {
    ...clamp,
    easing: EASE_OUT,
  });

  const line: React.CSSProperties = {
    fontFamily: FONT.display,
    fontSize: size,
    fontWeight: DISPLAY_WEIGHT,
    letterSpacing: DISPLAY_TRACKING,
    lineHeight: 1.06,
    whiteSpace: "pre",
  };

  return (
    <div
      data-name={name}
      style={{ display: "flex", flexDirection: "column", alignItems: "flex-start" }}
    >
      <div style={{ ...line, color: C.ink }}>{lead}</div>

      <div style={{ position: "relative", display: "inline-block" }}>
        <div style={{ ...line, color: interpolate(swap, [0, 1], [1, 0.42]) > 0.7 ? C.ink : C.dim }}>
          {struck}
        </div>
        <div
          style={{
            position: "absolute",
            left: 0,
            top: size * 0.56,
            width: "100%",
            height: 6,
            backgroundColor: C.notSupported,
            scale: `${rule} 1`,
            transformOrigin: "0% 50%",
          }}
        />
      </div>

      <div
        style={{
          overflow: "hidden",
          paddingBottom: size * 0.16,
          marginBottom: -(size * 0.16),
        }}
      >
        <div
          style={{
            ...line,
            color: C.ink,
            opacity: swap,
            translate: `0px ${interpolate(swap, [0, 1], [size * 0.55, 0])}px`,
          }}
        >
          {replacement}
        </div>
      </div>
    </div>
  );
};
