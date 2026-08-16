import React from "react";
import { interpolate, useCurrentFrame } from "remotion";
import { C, clamp, EASE_IN_OUT, EASE_OUT, FONT } from "../theme";

/**
 * A point estimate and its 95% interval, drawn as one object.
 *
 * VIDEO.md names quoting 0.30 without its interval as the one sentence that
 * would sink the video, so this component is ordered to make that frame
 * impossible to render. Two rules, and both were violated by the first version:
 *
 * 1. The band, its end labels and the written interval all complete BEFORE the
 *    number becomes legible. The first version counted the number up over
 *    frames 0 to 40 while the band ran 22 to 64, so there was roughly a second
 *    of "0.30" sitting above an unfinished band and no interval text at all.
 * 2. The band grows outward from the point estimate rather than rightward from
 *    the lower bound. Growing from the lower bound made its leading edge pass
 *    under the dot, which read as a progress bar filling to 0.30. An interval
 *    is a thing a value sits inside, and it has to look like one at every frame,
 *    not only at the last one.
 *
 * There is deliberately no count-up. A figure ticking up from 0.00 is the
 * grammar of a growth dashboard, and it performs a precision the interval
 * exists to deny.
 */

const BAND_IN = 42;
const TICKS_AT = 30;
const CI_AT = 38;
/** Nothing about the number may start before this. See rule 1 above. */
const NUMBER_AT = 48;

export const IntervalBar: React.FC<{
  value: number;
  interval: readonly [number, number];
  n: number;
  domain?: readonly [number, number];
  label: string;
  width?: number;
  delay?: number;
}> = ({ value, interval, n, domain = [0, 1], label, width = 1180, delay = 0 }) => {
  const frame = useCurrentFrame();
  const [lo, hi] = interval;
  const [d0, d1] = domain;
  const x = (v: number) => ((v - d0) / (d1 - d0)) * width;

  // Grown from the point outward, clamped to the interval on each side.
  const spread = interpolate(frame, [delay, delay + BAND_IN], [0, 1], {
    ...clamp,
    easing: EASE_IN_OUT,
  });
  const left = x(value) - (x(value) - x(lo)) * spread;
  const right = x(value) + (x(hi) - x(value)) * spread;

  const numberIn = interpolate(frame, [delay + NUMBER_AT, delay + NUMBER_AT + 18], [0, 1], {
    ...clamp,
    easing: EASE_OUT,
  });

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 34, width }}>
      <div style={{ display: "flex", alignItems: "baseline", gap: 26, minHeight: 168 }}>
        <div
          style={{
            fontFamily: FONT.display,
            fontSize: 168,
            fontWeight: 700,
            lineHeight: 0.9,
            letterSpacing: "-0.04em",
            color: C.ink,
            opacity: numberIn,
            filter: `blur(${interpolate(numberIn, [0, 1], [10, 0])}px)`,
            translate: `0px ${interpolate(numberIn, [0, 1], [14, 0])}px`,
          }}
        >
          {value.toFixed(2)}
        </div>
        <div
          style={{
            fontFamily: FONT.sans,
            fontSize: 34,
            color: C.dim,
            letterSpacing: "-0.01em",
            opacity: interpolate(
              frame,
              [delay + NUMBER_AT + 8, delay + NUMBER_AT + 26],
              [0, 1],
              clamp,
            ),
          }}
        >
          {label}
        </div>
      </div>

      {/* The axis, the band, and the point. The band is the message. */}
      <div style={{ position: "relative", height: 96, width }}>
        <div
          style={{
            position: "absolute",
            top: 44,
            left: 0,
            width,
            height: 2,
            backgroundColor: C.line,
            opacity: interpolate(frame, [delay, delay + 16], [0, 1], clamp),
          }}
        />
        <div
          style={{
            position: "absolute",
            top: 26,
            left,
            width: right - left,
            height: 38,
            borderRadius: 999,
            backgroundColor: C.paperWarm,
            border: `1px solid ${C.line}`,
          }}
        />
        <div
          style={{
            position: "absolute",
            top: 31,
            left: x(value) - 14,
            width: 28,
            height: 28,
            borderRadius: 999,
            backgroundColor: C.ink,
            scale: interpolate(frame, [delay + 4, delay + 22], [0, 1], {
              ...clamp,
              easing: EASE_OUT,
            }),
          }}
        />
        {[
          { at: lo, text: lo.toFixed(3) },
          { at: hi, text: hi.toFixed(3) },
        ].map((tick) => (
          <div
            key={tick.text}
            style={{
              position: "absolute",
              top: 78,
              left: x(tick.at),
              translate: "-50% 0",
              fontFamily: FONT.mono,
              fontSize: 24,
              color: C.dim,
              fontVariantNumeric: "tabular-nums",
              opacity: interpolate(frame, [delay + TICKS_AT, delay + TICKS_AT + 14], [0, 1], clamp),
            }}
          >
            {tick.text}
          </div>
        ))}
      </div>

      <div
        style={{
          fontFamily: FONT.mono,
          fontSize: 26,
          letterSpacing: "0.03em",
          color: C.dim,
          opacity: interpolate(frame, [delay + CI_AT, delay + CI_AT + 14], [0, 1], clamp),
        }}
      >
        95% CI {lo.toFixed(3)} to {hi.toFixed(3)}, n={n}
      </div>
    </div>
  );
};
