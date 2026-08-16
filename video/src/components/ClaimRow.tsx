import React from "react";
import { interpolate, useCurrentFrame } from "remotion";
import { C, clamp, EASE_OUT, EASE_POP, FONT } from "../theme";

export type Verdict =
  | "SUPPORTED"
  | "PARTIALLY_SUPPORTED"
  | "NOT_SUPPORTED"
  | "MIXED"
  | "COULD_NOT_VERIFY"
  | "PENDING";

const VERDICT: Record<Verdict, { dot: string; bg: string; label: string }> = {
  SUPPORTED: { dot: C.supported, bg: C.supportedBg, label: "Supported by the cited source" },
  PARTIALLY_SUPPORTED: { dot: C.partial, bg: C.partialBg, label: "Partly supported" },
  NOT_SUPPORTED: { dot: C.notSupported, bg: C.notSupportedBg, label: "Not supported by the cited source" },
  MIXED: { dot: C.partial, bg: C.partialBg, label: "Sources disagree" },
  COULD_NOT_VERIFY: { dot: C.unverified, bg: C.unverifiedBg, label: "Could not verify" },
  PENDING: { dot: C.line, bg: "transparent", label: "" },
};

/**
 * One claim as the panel draws it: the sentence, a state dot, and the state in
 * words. `settleAt` is when the verdict lands, so a scene can resolve claims one
 * after another instead of all at once.
 */
export const ClaimRow: React.FC<{
  text: string;
  verdict: Verdict;
  settleAt: number;
  appearAt?: number;
  emphasis?: boolean;
}> = ({ text, verdict, settleAt, appearAt = 0, emphasis = false }) => {
  const frame = useCurrentFrame();
  const v = VERDICT[verdict];
  const settled = frame >= settleAt;
  const shown = settled ? v : VERDICT.PENDING;

  return (
    <div
      style={{
        display: "flex",
        gap: 26,
        alignItems: "flex-start",
        padding: "26px 30px",
        borderRadius: 14,
        border: `1px solid ${C.line}`,
        backgroundColor: shown.bg === "transparent" ? "rgba(255,255,255,0.55)" : shown.bg,
        opacity: interpolate(frame, [appearAt, appearAt + 14], [0, 1], clamp),
        translate: interpolate(frame, [appearAt, appearAt + 20], ["0px 22px", "0px 0px"], {
          ...clamp,
          easing: EASE_OUT,
        }),
        scale: emphasis
          ? interpolate(frame, [settleAt, settleAt + 18], [1, 1.035], {
              ...clamp,
              easing: EASE_POP,
            })
          : 1,
        boxShadow: emphasis && settled ? `0 18px 50px -22px ${C.unverified}` : "none",
      }}
    >
      <div
        style={{
          width: 20,
          height: 20,
          borderRadius: 20,
          marginTop: 12,
          flexShrink: 0,
          backgroundColor: shown.dot,
          scale: interpolate(frame, [settleAt, settleAt + 12], [0.7, 1], {
            ...clamp,
            easing: EASE_POP,
          }),
        }}
      />
      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        <div
          style={{
            fontFamily: FONT.sans,
            fontSize: 34,
            lineHeight: 1.35,
            letterSpacing: "-0.01em",
            color: C.ink,
          }}
        >
          {text}
        </div>
        {shown.label ? (
          <div
            style={{
              fontFamily: FONT.mono,
              fontSize: 22,
              letterSpacing: "0.04em",
              textTransform: "uppercase",
              color: shown.dot,
              opacity: interpolate(frame, [settleAt, settleAt + 12], [0, 1], clamp),
            }}
          >
            {shown.label}
          </div>
        ) : null}
      </div>
    </div>
  );
};
