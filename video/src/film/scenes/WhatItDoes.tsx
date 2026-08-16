import React from "react";
import { AbsoluteFill, interpolate, Sequence, useCurrentFrame } from "remotion";
import { ClaimRow } from "../../components/ClaimRow";
import { MaskText } from "../../components/MaskText";
import { Paper } from "../../components/Paper";
import { Spotlight } from "../../components/Spotlight";
import { StrikeReplace } from "../../components/StrikeReplace";
import { RUN } from "../../runData";
import { C, clamp, EASE_OUT, FONT, SAFE, TYPE } from "../../theme";

/** Cut at a word boundary, so the quotation never ends mid-phrase. */
const trim = (text: string, max: number) =>
  text.length <= max ? text : `${text.slice(0, text.lastIndexOf(" ", max))} ...`;

const supported = RUN.demo.claims.find((c) => c.verdict === "SUPPORTED" && c.span.length > 0);
const notSupported = RUN.demo.claims.find((c) => c.verdict === "NOT_SUPPORTED");

/**
 * The quoted passage, and the fact that a script confirmed it is really there.
 *
 * It does not fade in from nothing any more. The paragraph is already on screen,
 * in mute grey, before the spotlight reaches it; what changes is that the matched
 * sentence rises to ink while the light narrows onto it. What was always there
 * versus what got matched is the entire receipt.
 */
const SpanReceipt: React.FC<{ span: string; delay: number }> = ({ span, delay }) => {
  const frame = useCurrentFrame();
  const found = interpolate(frame, [delay, delay + 22], [0, 1], { ...clamp, easing: EASE_OUT });

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 16,
        marginLeft: 76,
        paddingLeft: 32,
        borderLeft: `3px solid ${C.line}`,
        maxWidth: 1180,
        height: 190,
      }}
    >
      <div
        style={{
          fontFamily: FONT.sans,
          fontSize: 36,
          lineHeight: 1.45,
          color: interpolate(found, [0, 1], [0, 1]) > 0.5 ? C.ink : C.mute,
        }}
      >
        &ldquo;{trim(span, 150)}&rdquo;
      </div>
      <div
        style={{
          fontFamily: FONT.mono,
          fontSize: 22,
          letterSpacing: "0.04em",
          textTransform: "uppercase",
          color: found > 0.9 ? C.supported : C.mute,
          opacity: interpolate(frame, [delay - 30, delay - 16], [0, 1], clamp),
        }}
      >
        {found > 0.9 ? "Span confirmed present in the fetched page" : "Searching the fetched page"}
      </div>
    </div>
  );
};

/**
 * What the tool actually answers, and what a verdict is made of. The rows are
 * real claims and real verdicts from CO-02 in the day 9 run.
 *
 * Every element in the panel is mounted for the whole sequence and animates only
 * opacity and offset, so nothing reflows. That matters here beyond tidiness: the
 * spotlight's targets are absolute pixel positions, and a panel that re-centres
 * itself as rows arrive would drag the light off the thing it is pointing at.
 */
export const WhatItDoes: React.FC = () => {
  return (
    <Paper>
      <Sequence name="It does not ask whether this is true" durationInFrames={168}>
        <AbsoluteFill style={{ padding: `${SAFE.y}px ${SAFE.x}px`, justifyContent: "center" }}>
          <StrikeReplace
            lead="It does not ask"
            struck="whether this is true."
            replacement="whether the page says this."
            size={TYPE.headline}
            strikeAt={66}
          />
        </AbsoluteFill>
      </Sequence>

      <Sequence name="Panel" from={168} durationInFrames={280}>
        <AbsoluteFill
          style={{
            padding: `${SAFE.y}px ${SAFE.x}px`,
            justifyContent: "center",
            gap: 26,
          }}
        >
          {supported ? (
            <ClaimRow text={supported.text} verdict="SUPPORTED" appearAt={0} settleAt={48} />
          ) : null}
          {supported ? <SpanReceipt span={supported.span} delay={110} /> : null}
          {notSupported ? (
            <ClaimRow
              text={notSupported.text}
              verdict="NOT_SUPPORTED"
              appearAt={162}
              settleAt={206}
            />
          ) : null}
        </AbsoluteFill>

        {/* Wide over the claim, then down and tight onto the quoted sentence. */}
        <Spotlight
          poses={[
            { at: 62, x: 960, y: 372, rx: 900, ry: 260 },
            { at: 96, x: 960, y: 372, rx: 860, ry: 230 },
            { at: 132, x: 790, y: 618, rx: 640, ry: 186 },
          ]}
          fadeOut={[196, 226]}
        />
      </Sequence>

      <Sequence name="Statement about the citation" from={448}>
        <AbsoluteFill style={{ padding: `${SAFE.y}px ${SAFE.x}px`, justifyContent: "center" }}>
          <MaskText
            lines={[
              "Not supported by the cited source",
              "is a claim about the citation,",
              "not about the world.",
            ]}
            size={TYPE.statement}
            color={C.notSupported}
          />
        </AbsoluteFill>
      </Sequence>
    </Paper>
  );
};
