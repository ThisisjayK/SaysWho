import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { C } from "../theme";

/** Ten fixed positions the grain steps through, never interpolated. */
const GRAIN_OFFSETS = [
  [-12, -8],
  [6, -14],
  [-4, 10],
  [13, 5],
  [-9, -3],
  [2, 12],
  [-14, 7],
  [9, -11],
] as const;

/**
 * The stage. Warm paper, a very slight grain, and a vignette so large type does
 * not float on a flat white field. Everything else in the film sits on this.
 */
export const Paper: React.FC<{
  children?: React.ReactNode;
  tone?: "paper" | "warm" | "ink";
}> = ({ children, tone = "paper" }) => {
  const frame = useCurrentFrame();
  const isInk = tone === "ink";
  // The noise is never regenerated, only shifted, so the render stays
  // deterministic under any seek while the grain reads as emulsion rather than
  // as a decal sitting on top of the frame.
  const [gx, gy] = GRAIN_OFFSETS[Math.floor(frame / 2) % GRAIN_OFFSETS.length];
  const bg = isInk ? C.ink : tone === "warm" ? C.paperWarm : C.paper;

  return (
    <AbsoluteFill style={{ backgroundColor: bg }}>
      <AbsoluteFill
        style={{
          backgroundImage: isInk
            ? `radial-gradient(120% 90% at 50% 0%, rgba(255,255,255,0.07) 0%, rgba(255,255,255,0) 62%)`
            : // Warm in the middle, warmer and slightly darker at the edges. A
              // white centre wash turns the cream into office paper.
              `radial-gradient(112% 88% at 50% 10%, rgba(255,253,246,0.92) 0%, rgba(238,232,218,0.62) 52%, rgba(20,20,15,0.11) 100%)`,
        }}
      />
      <AbsoluteFill style={{ overflow: "hidden" }}>
        {/* Two passes. Multiply alone can only darken, and paper has light
            fibres as well as dark specks, so a screen pass with a different
            seed supplies the other half. */}
        {(
          [
            { blend: "multiply" as const, seed: 1, opacity: isInk ? 0.5 : 0.62 },
            { blend: "screen" as const, seed: 7, opacity: isInk ? 0.22 : 0.34 },
          ]
        ).map((pass) => (
          <div
            key={pass.blend}
            style={{
              position: "absolute",
              top: "-50%",
              left: "-50%",
              width: "200%",
              height: "200%",
              opacity: pass.opacity,
              mixBlendMode: pass.blend,
              translate: `${gx}% ${gy}%`,
            }}
          >
            <svg width="100%" height="100%">
              <filter id={`paper-grain-${pass.blend}`}>
                <feTurbulence
                  type="fractalNoise"
                  baseFrequency="0.66"
                  numOctaves={3}
                  seed={pass.seed}
                  stitchTiles="stitch"
                />
                <feColorMatrix type="saturate" values="0" />
              </filter>
              <rect
                width="100%"
                height="100%"
                filter={`url(#paper-grain-${pass.blend})`}
                opacity={0.055}
              />
            </svg>
          </div>
        ))}
      </AbsoluteFill>
      {children}
    </AbsoluteFill>
  );
};
