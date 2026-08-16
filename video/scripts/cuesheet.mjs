// Prints the film's timeline and every audio cue with timecodes, straight out of
// the same data the render uses. Run it after any retime and hand the output to
// whoever is cutting the sound.
//
// Node cannot resolve the project's extensionless TypeScript imports on its own,
// so bundle it first with the esbuild Remotion already depends on:
//
//   npx esbuild scripts/cuesheet.mjs --bundle --platform=node --outfile=.cuesheet.cjs \
//     && node .cuesheet.cjs && rm .cuesheet.cjs
import { TIMELINE, FILM_DURATION } from "../src/film/timing.ts";
import { CUES } from "../src/audio/cues.ts";

const tc = (f) => {
  const s = f / 30;
  return `${String(Math.floor(s / 60)).padStart(2, "0")}:${(s % 60).toFixed(2).padStart(5, "0")}`;
};

console.log(`FILM  ${FILM_DURATION} frames, ${tc(FILM_DURATION)} at 30fps\n`);
console.log("SCENE               START     CUT AT    CUT");
for (const s of TIMELINE) {
  console.log(
    `${s.name.padEnd(18)}  ${tc(s.start)}   ${s.cutAt !== null ? tc(s.cutAt) : "  --  "}    ${s.cutKind ?? ""}`,
  );
}

console.log("\nCUE                        AT        FILE                     VOL   NOTE");
for (const c of [...CUES].sort((a, b) => a.at - b.at)) {
  console.log(
    `${c.id.padEnd(24)}  ${tc(c.at)}   ${c.file.padEnd(24)} ${String(c.volume ?? 0.5).padEnd(5)} ${c.note}`,
  );
}
