import React from "react";
import { interpolate, useCurrentFrame } from "remotion";
import { RUN } from "../runData";
import { C, clamp, EASE_IN_OUT, EASE_OUT, FONT } from "../theme";

/**
 * Where the judge and the human agree, and where they do not, with both
 * intervals drawn on one axis.
 *
 * The point of the graphic is the near miss. 77.3% has a lower bound of 56.56
 * and 16.7% has an upper bound of 56.35, so the two intervals clear each other
 * by 0.21 of a percentage point. The film's best available sentence, that the
 * judge agrees well on one category and badly on another, is true and survives
 * on two tenths of a point, and both of those facts belong in the same frame.
 *
 * One deliberate departure from the obvious design. It is tempting to scale each
 * row's axis by n so the small sample looks small. That would make the same
 * percentage land at two different x positions and the rows would stop being
 * comparable, which is the one thing a shared axis is for. n is already visible
 * in the thing that matters: the n=6 interval is more than four times wider than
 * the n=22 one, because that is what a small sample does.
 */

const ROWS = RUN.perClass;
const AXIS = 1400;
const x = (v: number) => (v / 100) * AXIS;

/**
 * The two bounds that nearly touch, and the gap between them. The gap comes from
 * the run's raw bounds via sync-run.mjs, not from subtracting the rounded ones
 * on screen, and is printed to one decimal so the on-screen arithmetic agrees
 * with it either way.
 */
const NEAR_MISS_AT = Math.min(ROWS[0].interval[0], ROWS[1].interval[1]);
const GAP = RUN.perClassGap;

const Row: React.FC<{
  row: (typeof ROWS)[number];
  accent: string;
  at: number;
}> = ({ row, accent, at }) => {
  const frame = useCurrentFrame();
  const [lo, hi] = row.interval;

  const spread = interpolate(frame, [at + 10, at + 52], [0, 1], {
    ...clamp,
    easing: EASE_IN_OUT,
  });
  const left = x(row.precision) - (x(row.precision) - x(lo)) * spread;
  const right = x(row.precision) + (x(hi) - x(row.precision)) * spread;

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 16,
        width: AXIS,
        opacity: interpolate(frame, [at, at + 16], [0, 1], clamp),
        translate: interpolate(frame, [at, at + 26], ["0px 24px", "0px 0px"], {
          ...clamp,
          easing: EASE_OUT,
        }),
      }}
    >
      <div style={{ display: "flex", alignItems: "baseline", gap: 22 }}>
        <div
          style={{
            fontFamily: FONT.display,
            fontSize: 64,
            fontWeight: 700,
            letterSpacing: "-0.035em",
            color: accent,
            // The figure is not allowed to arrive before its band exists.
            opacity: interpolate(frame, [at + 52, at + 66], [0, 1], clamp),
          }}
        >
          {row.precision.toFixed(1)}%
        </div>
        <div
          style={{
            fontFamily: FONT.sans,
            fontSize: 34,
            fontWeight: 500,
            letterSpacing: "-0.015em",
            color: C.dim,
          }}
        >
          &ldquo;{row.label}&rdquo;
        </div>
      </div>

      <div style={{ position: "relative", height: 54, width: AXIS }}>
        <div
          style={{
            position: "absolute",
            top: 26,
            left: 0,
            width: AXIS,
            height: 2,
            backgroundColor: C.line,
          }}
        />
        <div
          style={{
            position: "absolute",
            top: 12,
            left,
            width: right - left,
            height: 30,
            borderRadius: 999,
            backgroundColor: C.paperWarm,
            border: `1px solid ${C.line}`,
          }}
        />
        <div
          style={{
            position: "absolute",
            top: 16,
            left: x(row.precision) - 11,
            width: 22,
            height: 22,
            borderRadius: 999,
            backgroundColor: accent,
            scale: interpolate(frame, [at + 6, at + 22], [0, 1], {
              ...clamp,
              easing: EASE_OUT,
            }),
          }}
        />
      </div>

      <div
        style={{
          fontFamily: FONT.mono,
          fontSize: 24,
          letterSpacing: "0.03em",
          color: C.dim,
          fontVariantNumeric: "tabular-nums",
          opacity: interpolate(frame, [at + 40, at + 56], [0, 1], clamp),
        }}
      >
        95% CI {lo.toFixed(1)} to {hi.toFixed(1)}, n={row.n}
      </div>
    </div>
  );
};

export const ClassAgreement: React.FC<{ delay?: number }> = ({ delay = 0 }) => {
  const frame = useCurrentFrame();
  const missIn = interpolate(frame, [delay + 150, delay + 176], [0, 1], clamp);

  return (
    <div style={{ position: "relative", display: "flex", flexDirection: "column", gap: 54 }}>
      <Row row={ROWS[0]} accent={C.ink} at={delay} />
      <Row row={ROWS[1]} accent={C.partial} at={delay + 62} />

      {/* The two bounds nearly meeting, called out once the rows have settled. */}
      <div
        style={{
          position: "absolute",
          left: x(NEAR_MISS_AT),
          top: 74,
          bottom: 54,
          width: 2,
          backgroundColor: C.notSupported,
          opacity: missIn * 0.75,
          scale: `1 ${missIn}`,
          transformOrigin: "50% 0%",
        }}
      />
      <div
        style={{
          position: "absolute",
          left: x(NEAR_MISS_AT) + 22,
          bottom: -8,
          fontFamily: FONT.mono,
          fontSize: 24,
          letterSpacing: "0.03em",
          color: C.notSupported,
          opacity: missIn,
          translate: interpolate(missIn, [0, 1], ["0px 10px", "0px 0px"]),
        }}
      >
        {GAP.toFixed(1)} points apart
      </div>
    </div>
  );
};
