import React from "react";
import { Interactive, interpolate, useCurrentFrame } from "remotion";
import { clamp, C, DISPLAY_TRACKING, DISPLAY_WEIGHT, EASE_OUT, FONT } from "../theme";

/**
 * Type that rises out of its own baseline rather than fading in.
 *
 * By default each line is one mask, which is the calm editorial reading. Pass
 * `wordStagger` and each word gets its own mask instead, so the line assembles
 * left to right. Use that on the two or three lines that carry the film and
 * leave the rest on lines; word staggering everything is exhausting to watch.
 */
export const MaskText: React.FC<{
  lines: string[];
  size?: number;
  color?: string;
  font?: string;
  weight?: number;
  lineHeight?: number;
  letterSpacing?: string;
  delay?: number;
  stagger?: number;
  wordStagger?: number;
  align?: "left" | "center";
  italic?: boolean;
  name?: string;
}> = ({
  lines,
  size = 96,
  color = C.ink,
  font = FONT.display,
  weight = DISPLAY_WEIGHT,
  lineHeight = 1.06,
  letterSpacing = DISPLAY_TRACKING,
  delay = 0,
  stagger = 5,
  wordStagger,
  align = "left",
  italic = false,
  name = "Statement",
}) => {
  const frame = useCurrentFrame();

  const glyph = (text: string, start: number, key: string) => (
    <span
      key={key}
      style={{
        display: "inline-block",
        overflow: "hidden",
        paddingBottom: size * 0.16,
        marginBottom: -(size * 0.16),
        verticalAlign: "bottom",
      }}
    >
      <span
        style={{
          display: "inline-block",
          translate: interpolate(
            frame,
            [start, start + 28],
            [`0px ${size * 1.15}px`, "0px 0px"],
            { ...clamp, easing: EASE_OUT },
          ),
          opacity: interpolate(frame, [start, start + 12], [0, 1], clamp),
        }}
      >
        {text}
      </span>
    </span>
  );

  return (
    <Interactive.Div
      name={name}
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: align === "center" ? "center" : "flex-start",
      }}
    >
      {lines.map((line, i) => {
        const lineStart = delay + i * stagger;
        return (
          <div
            key={line + String(i)}
            style={{
              fontFamily: font,
              fontSize: size,
              fontWeight: weight,
              fontStyle: italic ? "italic" : "normal",
              lineHeight,
              letterSpacing,
              color,
              whiteSpace: "pre-wrap",
              textAlign: align,
            }}
          >
            {wordStagger === undefined
              ? glyph(line, lineStart, line + String(i))
              : line
                  .split(" ")
                  .map((word, w) =>
                    glyph(
                      w === 0 ? word : ` ${word}`,
                      lineStart + w * wordStagger,
                      `${i}-${w}-${word}`,
                    ),
                  )}
          </div>
        );
      })}
    </Interactive.Div>
  );
};
