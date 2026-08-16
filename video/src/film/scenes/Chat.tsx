import React from "react";
import { AbsoluteFill, interpolate, Sequence, useCurrentFrame } from "remotion";
import { MaskText } from "../../components/MaskText";
import { Paper } from "../../components/Paper";
import {
  AI_BALL,
  AI_PALETTE,
  PERSON,
  PERSON_PALETTE,
  PixelIcon,
} from "../../components/PixelIcon";
import { RUN } from "../../runData";
import { C, clamp, EASE_OUT, EASE_POP, FONT, TYPE } from "../../theme";

/**
 * A chat, and deliberately not a named one.
 *
 * Every tool in SCOPE.md §1b does this. Putting one company's interface in the
 * opening would narrow the argument to that company and invite a head to head
 * comparison this project has not run, which §5a is explicit about not claiming.
 * So the assistant is a painted ball and the person is a person.
 */

const QUESTION = RUN.demo.question;
const ANSWER_CLAIMS = RUN.demo.claims.slice(0, 4);

const STREAM_FROM = 128;
const STREAM_TO = 296;

/**
 * Inter-word gaps, in arbitrary units, normalised below to fill the stream
 * window. A model does not emit at a constant rate: two words land together,
 * then nothing for a beat, then three more. A linear character counter is the
 * one thing in this scene that reads as an animation rather than a recording,
 * and the irregularity is the whole tell.
 */
const GAPS = [
  2, 1, 3, 0, 4, 2, 1, 6, 2, 1, 0, 3, 3, 2, 7, 1, 2, 0, 3, 4, 2, 1, 3, 2, 0, 5, 3, 1, 2,
];

type Word = { text: string; sentence: number; start: number };

const { WORDS, CHIP_AT } = (() => {
  const raw: { text: string; sentence: number }[] = [];
  ANSWER_CLAIMS.forEach((c, s) => {
    c.text.split(/\s+/).forEach((w) => raw.push({ text: w, sentence: s }));
  });

  const offsets: number[] = [];
  let cursor = 0;
  raw.forEach((_, i) => {
    offsets.push(cursor);
    cursor += GAPS[i % GAPS.length];
  });
  // Normalise so the last word always lands on STREAM_TO whatever the answer's
  // length happens to be, and the rhythm inside stays uneven.
  const span = cursor || 1;
  const scale = (STREAM_TO - STREAM_FROM) / span;

  const words: Word[] = raw.map((w, i) => ({
    ...w,
    start: STREAM_FROM + offsets[i] * scale,
  }));

  // The citation is stapled on a beat after the sentence it belongs to, rather
  // than arriving with it. The claim persuades first; the receipt follows.
  const chipAt: number[] = ANSWER_CLAIMS.map((_, s) => {
    const last = [...words].reverse().find((w) => w.sentence === s);
    return (last?.start ?? STREAM_FROM) + 14;
  });

  return { WORDS: words, CHIP_AT: chipAt };
})();

const Avatar: React.FC<{ who: "person" | "ai"; at: number }> = ({ who, at }) => {
  const frame = useCurrentFrame();
  return (
    <div
      style={{
        width: 76,
        height: 76,
        borderRadius: 999,
        overflow: "hidden",
        flexShrink: 0,
        backgroundColor: who === "ai" ? "transparent" : "#e4e0d3",
        opacity: interpolate(frame, [at, at + 12], [0, 1], clamp),
        scale: interpolate(frame, [at, at + 20], [0.72, 1], { ...clamp, easing: EASE_POP }),
      }}
    >
      <PixelIcon
        grid={who === "ai" ? AI_BALL : PERSON}
        palette={who === "ai" ? AI_PALETTE : PERSON_PALETTE}
        size={76}
      />
    </div>
  );
};

const Row: React.FC<{ who: "person" | "ai"; at: number; children: React.ReactNode }> = ({
  who,
  at,
  children,
}) => {
  const frame = useCurrentFrame();
  return (
    <div
      style={{
        display: "flex",
        gap: 30,
        alignItems: "flex-start",
        translate: interpolate(frame, [at, at + 24], ["0px 20px", "0px 0px"], {
          ...clamp,
          easing: EASE_OUT,
        }),
      }}
    >
      <Avatar who={who} at={at} />
      <div style={{ flex: 1, paddingTop: 8, minHeight: 76 }}>{children}</div>
    </div>
  );
};

const Chip: React.FC<{ n: number; at: number }> = ({ n, at }) => {
  const frame = useCurrentFrame();
  const p = interpolate(frame, [at, at + 9], [0, 1], { ...clamp, easing: EASE_OUT });
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        width: 34,
        height: 34,
        marginLeft: 8,
        borderRadius: 999,
        backgroundColor: C.partialBg,
        border: `1px solid ${C.partial}`,
        color: C.partial,
        fontFamily: FONT.mono,
        fontSize: 20,
        verticalAlign: "middle",
        opacity: p,
        scale: interpolate(p, [0, 1], [0.62, 1]),
      }}
    >
      {n}
    </span>
  );
};

/** Three pixels, breathing, while the answer is on its way. */
const Thinking: React.FC<{ at: number; until: number }> = ({ at, until }) => {
  const frame = useCurrentFrame();
  if (frame < at || frame > until) return null;
  return (
    <div style={{ display: "flex", gap: 10, paddingTop: 16 }}>
      {[0, 1, 2].map((i) => (
        <div
          key={i}
          style={{
            width: 14,
            height: 14,
            backgroundColor: C.mute,
            opacity: interpolate(
              (frame - at + i * 6) % 30,
              [0, 10, 20, 30],
              [0.25, 1, 0.25, 0.25],
            ),
          }}
        />
      ))}
    </div>
  );
};

/**
 * A word arrives at once and then settles from fresh-token grey into ink over
 * the next third of a second. Two channels, arrival and settling, is what makes
 * generated text look generated.
 */
const StreamedWord: React.FC<{ word: Word }> = ({ word }) => {
  const frame = useCurrentFrame();
  if (frame < word.start) return null;
  const settle = interpolate(frame, [word.start, word.start + 10], [0, 1], clamp);
  return (
    <span style={{ color: settle < 1 ? C.mute : C.dim, opacity: interpolate(settle, [0, 0.4], [0, 1], clamp) }}>
      {word.text}{" "}
    </span>
  );
};

export const Chat: React.FC = () => {
  const frame = useCurrentFrame();

  // The question is typed by a person, so it is per character and even. The
  // answer is streamed by a model, so it is per word and it is not.
  const questionChars = Math.round(
    interpolate(frame, [12, 74], [0, QUESTION.length], clamp),
  );

  return (
    <Paper>
      <AbsoluteFill
        style={{
          paddingInline: 260,
          paddingTop: 210,
          opacity: interpolate(frame, [330, 372], [1, 0.13], clamp),
          filter: `blur(${interpolate(frame, [330, 372], [0, 6], clamp)}px)`,
        }}
      >
        <div style={{ display: "flex", flexDirection: "column", gap: 54 }}>
          <Row who="person" at={4}>
            <div
              style={{
                fontFamily: FONT.sans,
                fontWeight: 500,
                fontSize: 46,
                lineHeight: 1.45,
                letterSpacing: "-0.02em",
                color: C.ink,
              }}
            >
              {QUESTION.slice(0, questionChars)}
            </div>
          </Row>

          <Row who="ai" at={92}>
            <Thinking at={96} until={STREAM_FROM + 2} />
            <div
              style={{
                fontFamily: FONT.sans,
                fontWeight: 400,
                fontSize: 42,
                lineHeight: 1.62,
                letterSpacing: "-0.015em",
              }}
            >
              {ANSWER_CLAIMS.map((claim, s) => (
                <React.Fragment key={claim.id}>
                  {WORDS.filter((w) => w.sentence === s).map((w, i) => (
                    <StreamedWord key={`${s}-${i}`} word={w} />
                  ))}
                  <Chip n={s + 1} at={CHIP_AT[s]} />{" "}
                </React.Fragment>
              ))}
            </div>
          </Row>
        </div>
      </AbsoluteFill>

      <Sequence name="Nobody opens them" from={352}>
        <AbsoluteFill
          style={{ paddingInline: 260, justifyContent: "center", alignItems: "flex-start" }}
        >
          <MaskText
            name="Nobody opens the sources"
            lines={["Nobody opens", "the sources."]}
            size={TYPE.hero}
            stagger={9}
            wordStagger={5}
          />
        </AbsoluteFill>
      </Sequence>
    </Paper>
  );
};
