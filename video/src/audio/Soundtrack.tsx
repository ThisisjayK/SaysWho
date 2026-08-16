import { Audio } from "@remotion/media";
import React from "react";
import { Sequence, staticFile } from "remotion";
import { CUES } from "./cues";

/**
 * The film's audio, in three independent layers so any one of them can be
 * absent without the others breaking.
 *
 * `AVAILABLE` is the manifest. A file only plays once it is both dropped into
 * public/audio and named here, which keeps a missing asset from failing a
 * render at minute eighty of a ninety second film.
 *
 * The mix intent, in one line: narration carries the argument, the bed is
 * almost subliminal and ducks under every line, and the effects exist to mark
 * decisions rather than to decorate motion. The two blackout cuts are the only
 * moments allowed to be loud.
 */
export const AVAILABLE: Record<string, boolean> = {
  // Set true as each file lands in public/audio.
};

export type Narration = {
  file: string;
  /** Absolute frame the line starts on. */
  at: number;
  volume?: number;
};

export const Soundtrack: React.FC<{
  bed?: string;
  bedVolume?: number;
  narration?: Narration[];
}> = ({ bed, bedVolume = 0.16, narration = [] }) => {
  return (
    <>
      {bed && AVAILABLE[bed] ? (
        <Audio src={staticFile(`audio/${bed}`)} volume={bedVolume} />
      ) : null}

      {CUES.filter((cue) => AVAILABLE[cue.file]).map((cue) => (
        <Sequence key={cue.id} name={`sfx ${cue.id}`} from={cue.at} layout="none">
          <Audio src={staticFile(`audio/${cue.file}`)} volume={cue.volume ?? 0.5} />
        </Sequence>
      ))}

      {narration
        .filter((line) => AVAILABLE[line.file])
        .map((line) => (
          <Sequence key={line.file} name={`vo ${line.file}`} from={line.at} layout="none">
            <Audio src={staticFile(`audio/${line.file}`)} volume={line.volume ?? 1} />
          </Sequence>
        ))}
    </>
  );
};
