import React from "react";
import { AbsoluteFill, interpolate, Sequence, useCurrentFrame } from "remotion";
import { ClaimRow } from "../../components/ClaimRow";
import { MaskText } from "../../components/MaskText";
import { Paper } from "../../components/Paper";
import { RUN } from "../../runData";
import { C, clamp, EASE_OUT, FONT, SAFE, TYPE } from "../../theme";

const settled = RUN.demo.claims.filter((c) => c.verdict !== "COULD_NOT_VERIFY").slice(0, 2);
const unverified = RUN.demo.claims.find((c) => c.verdict === "COULD_NOT_VERIFY");

/**
 * The gate, quoted rather than paraphrased. The reason string is the one the run
 * actually recorded, so the strongest moment in the film is a screenshot of the
 * project's own output rather than a marketing line about it.
 */
const WithheldCard: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill
      style={{
        padding: `${SAFE.y}px ${SAFE.x}px`,
        justifyContent: "center",
        gap: 56,
      }}
    >
      <div
        style={{
          fontFamily: FONT.mono,
          fontSize: 30,
          letterSpacing: "0.12em",
          color: C.unverified,
          opacity: interpolate(frame, [8, 28], [0, 1], clamp),
        }}
      >
        {RUN.demo.withheldCode}
      </div>

      <MaskText
        name="No support rate"
        lines={["It will not score", "the answer either."]}
        size={TYPE.hero}
        color={C.paper}
        delay={20}
      />

      <div
        style={{
          maxWidth: 1400,
          paddingLeft: 32,
          borderLeft: `3px solid ${C.unverified}`,
          fontFamily: FONT.sans,
          fontSize: 36,
          lineHeight: 1.5,
          letterSpacing: "-0.01em",
          color: "rgba(250,249,245,0.72)",
          opacity: interpolate(frame, [58, 86], [0, 1], clamp),
          translate: interpolate(frame, [58, 92], ["0px 18px", "0px 0px"], {
            ...clamp,
            easing: EASE_OUT,
          }),
        }}
      >
        {RUN.demo.withheld[0]?.split(": ").slice(1).join(": ")}
      </div>
    </AbsoluteFill>
  );
};

/** The centre of the film. A claim it will not score, and an answer it will not rate. */
export const Refusal: React.FC = () => {
  return (
    <>
      <Sequence name="Grey row" durationInFrames={440}>
        <Paper>
          <AbsoluteFill
            style={{ padding: `${SAFE.y}px ${SAFE.x}px`, justifyContent: "center", gap: 26 }}
          >
            {settled.map((c, i) => (
              <div key={c.id} style={{ opacity: 0.34 }}>
                <ClaimRow
                  text={c.text}
                  verdict={c.verdict as "SUPPORTED" | "NOT_SUPPORTED"}
                  appearAt={-60}
                  settleAt={-40}
                />
              </div>
            ))}
            {unverified ? (
              <ClaimRow
                text={unverified.text}
                verdict="COULD_NOT_VERIFY"
                appearAt={16}
                settleAt={62}
                emphasis
              />
            ) : null}
          </AbsoluteFill>

          <Sequence name="Refuses to score" from={168} durationInFrames={140}>
            <Paper>
              <AbsoluteFill
                style={{ padding: `${SAFE.y}px ${SAFE.x}px`, justifyContent: "center" }}
              >
                <MaskText
                  lines={[
                    "This one it will not score.",
                    "The cited page is gone,",
                    "so there is nothing to check against.",
                  ]}
                  size={TYPE.statement}
                  color={C.unverified}
                />
              </AbsoluteFill>
            </Paper>
          </Sequence>

          <Sequence name="A number here is invented" from={308}>
            <Paper>
              <AbsoluteFill
                style={{ padding: `${SAFE.y}px ${SAFE.x}px`, justifyContent: "center" }}
              >
                <MaskText
                  lines={["Every other tool", "gives you a number here."]}
                  size={TYPE.statement}
                  color={C.dim}
                />
                <Sequence name="Invented" from={62} layout="none">
                  <div style={{ marginTop: 44 }}>
                    <MaskText
                      lines={["A number here is invented."]}
                      size={TYPE.headline}
                      wordStagger={4}
                    />
                  </div>
                </Sequence>
              </AbsoluteFill>
            </Paper>
          </Sequence>
        </Paper>
      </Sequence>

      <Sequence name="Withheld rate" from={440}>
        <Paper tone="ink">
          <WithheldCard />
        </Paper>
      </Sequence>
    </>
  );
};
