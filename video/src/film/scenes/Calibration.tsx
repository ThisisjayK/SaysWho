import React from "react";
import { AbsoluteFill, Sequence } from "remotion";
import { ClassAgreement } from "../../components/ClassAgreement";
import { IntervalBar } from "../../components/IntervalBar";
import { MaskText } from "../../components/MaskText";
import { Paper } from "../../components/Paper";
import { RUN } from "../../runData";
import { C, FONT, SAFE, TYPE } from "../../theme";

/**
 * The tool turned on itself, in three beats.
 *
 * The headline kappa, then where that agreement actually comes from, then the
 * fact that the second beat's whole story survives on 0.21 of a percentage
 * point. Each beat is ordered so no figure can be legible before the interval it
 * belongs to has finished drawing. See IntervalBar's header comment.
 */
export const Calibration: React.FC = () => {
  return (
    <Paper>
      <Sequence name="So how much is a verdict worth" durationInFrames={116}>
        <AbsoluteFill style={{ padding: `${SAFE.y}px ${SAFE.x}px`, justifyContent: "center" }}>
          <MaskText lines={["So how much", "is one of its verdicts worth?"]} size={TYPE.headline} />
        </AbsoluteFill>
      </Sequence>

      <Sequence name="Kappa" from={116} durationInFrames={286}>
        <AbsoluteFill
          style={{
            padding: `${SAFE.y}px ${SAFE.x}px`,
            justifyContent: "center",
            gap: 52,
          }}
        >
          <div
            style={{
              fontFamily: FONT.sans,
              fontSize: 34,
              lineHeight: 1.4,
              letterSpacing: "-0.015em",
              color: C.dim,
              maxWidth: 1280,
            }}
          >
            Forty five claims hand labelled blind, before the judge saw any of them.
          </div>

          <IntervalBar
            value={RUN.kappa.value}
            interval={RUN.kappa.interval}
            n={RUN.kappa.n}
            label="agreement with a human, Cohen's kappa"
            delay={26}
          />

          <Sequence name="The lower bound" from={118} layout="none">
            <div style={{ maxWidth: 1280 }}>
              <MaskText
                lines={["The lower bound is 0.004.", "It cannot rule out chance."]}
                size={56}
                color={C.ink}
                stagger={6}
              />
            </div>
          </Sequence>
        </AbsoluteFill>
      </Sequence>

      <Sequence name="Where it agrees" from={402} durationInFrames={126}>
        <AbsoluteFill style={{ padding: `${SAFE.y}px ${SAFE.x}px`, justifyContent: "center" }}>
          <MaskText
            lines={["It agrees with me best", "on one kind of claim,", "and worst on another."]}
            size={TYPE.statement}
            stagger={7}
          />
        </AbsoluteFill>
      </Sequence>

      <Sequence name="Per class" from={528}>
        <AbsoluteFill
          style={{
            padding: `${SAFE.y}px ${SAFE.x}px`,
            justifyContent: "center",
          }}
        >
          <ClassAgreement delay={10} />
        </AbsoluteFill>
      </Sequence>
    </Paper>
  );
};
