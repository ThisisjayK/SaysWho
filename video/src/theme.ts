import { Easing } from "remotion";

/**
 * Every colour here is lifted from extension/src/render.css, so the film and the
 * product are the same object. If a token changes there, change it here too.
 */
export const C = {
  ink: "#14140f",
  paper: "#faf9f5",
  paperWarm: "#f1eee5",
  line: "#d8d4c8",
  dim: "#6b6759",
  mute: "#9a968a",

  supported: "#1f6f43",
  supportedBg: "#e6f2ea",
  notSupported: "#a1341c",
  notSupportedBg: "#fbe9e4",
  partial: "#8a5a00",
  partialBg: "#fdf1dc",
  /** Could not verify. The colour of the whole argument. */
  unverified: "#3f4b8a",
  unverifiedBg: "#e9ebf6",
  unchecked: "#6b6759",
  uncheckedBg: "#f0eee7",
} as const;

export const FONT = {
  display: '"Rethink Sans", -apple-system, BlinkMacSystemFont, sans-serif',
  sans: '"Rethink Sans", -apple-system, BlinkMacSystemFont, sans-serif',
  mono: '"JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, monospace',
} as const;

/**
 * Display type is one typeface at two weights rather than two typefaces. The
 * headline weight is heavy and tightly tracked; body sits at 500 and normal
 * tracking, which is enough separation without a second family.
 */
export const DISPLAY_WEIGHT = 700;
export const DISPLAY_TRACKING = "-0.035em";

/**
 * 1920x1080. The layout guidance is written for 1080 wide, so every minimum in
 * it is roughly doubled here.
 */
export const SAFE = { x: 160, y: 140 } as const;

export const TYPE = {
  hero: 132,
  headline: 96,
  statement: 72,
  support: 44,
  label: 26,
} as const;

/** Slow out, no bounce. The house curve for anything that carries text. */
export const EASE_OUT = Easing.bezier(0.16, 1, 0.3, 1);
/** A little overshoot, for objects rather than words. */
export const EASE_POP = Easing.bezier(0.34, 1.4, 0.5, 1);
export const EASE_IN_OUT = Easing.bezier(0.65, 0, 0.35, 1);

export const clamp = {
  extrapolateLeft: "clamp",
  extrapolateRight: "clamp",
} as const;
