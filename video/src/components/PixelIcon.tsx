import React from "react";

/**
 * Pixel art drawn from a character grid, in the same crisp-edge register as the
 * repo's bird. One character per pixel, one entry per character in the palette,
 * '.' always transparent.
 */
export const PixelIcon: React.FC<{
  grid: readonly string[];
  palette: Record<string, string>;
  size?: number;
  style?: React.CSSProperties;
}> = ({ grid, palette, size = 96, style }) => {
  const n = grid.length;
  return (
    <svg
      viewBox={`0 0 ${n} ${n}`}
      width={size}
      height={size}
      shapeRendering="crispEdges"
      style={{ display: "block", flexShrink: 0, ...style }}
    >
      {grid.flatMap((row, y) =>
        row.split("").map((ch, x) =>
          ch === "." ? null : (
            <rect key={`${x}-${y}`} x={x} y={y} width={1} height={1} fill={palette[ch]} />
          ),
        ),
      )}
    </svg>
  );
};

/**
 * The assistant. A painted ball rather than anyone's logo: this film is about
 * what every one of these tools does, so naming one of them would narrow the
 * argument and invite a comparison the project has not run.
 */
export const AI_BALL = [
  ".....bbbrrr.....",
  "...bbbbbrrrrr...",
  "..bbbbbbrrrrrr..",
  ".bbbBBbbrrrrrrr.",
  ".bbBBBbbrrrrrrr.",
  "bbbBBBbbrrrrrrrr",
  "bbbbbbbbrrrrrrrr",
  "bbbbbbbbrrrrrrrr",
  "bbbbbbbyyrrrrrrr",
  "bbbbbyyyyyyrrrrr",
  "bbbbyyyyyyyyrrrr",
  ".byyyyyyyyyyyyr.",
  ".yyyyyyyyyyyyyy.",
  "..yyyyyyyyyyyy..",
  "...yyyyyyyyyy...",
  ".....yyyyyy.....",
] as const;

export const AI_PALETTE: Record<string, string> = {
  r: "#c4432f",
  b: "#3f4b8a",
  B: "#5d6ab0",
  y: "#d9a54a",
};

export const PERSON = [
  ".....oooooo.....",
  "...oooooooooo...",
  "..oooooooooooo..",
  ".oooooxxxxooooo.",
  ".ooooxxxxxxoooo.",
  "oooooxxxxxxooooo",
  "oooooxxxxxxooooo",
  "ooooooxxxxoooooo",
  "oooooooooooooooo",
  "oooooooooooooooo",
  "oooooxxxxxxooooo",
  ".oooxxxxxxxxooo.",
  ".ooxxxxxxxxxxoo.",
  "..oxxxxxxxxxxo..",
  "...xxxxxxxxxx...",
  ".....xxxxxx.....",
] as const;

export const PERSON_PALETTE: Record<string, string> = {
  o: "#e7e3d7",
  x: "#4a4639",
};
