import React from "react";
import { AbsoluteFill, interpolate, Sequence, useCurrentFrame } from "remotion";
import { MaskText } from "../../components/MaskText";
import { Paper } from "../../components/Paper";
import { C, clamp, EASE_OUT, FONT, TYPE } from "../../theme";

/**
 * The name, and the one sentence under it. A rule draws out from the centre
 * first, so the wordmark has something to land on rather than arriving into
 * empty paper.
 */
export const Title: React.FC = () => {
  const frame = useCurrentFrame();

  return (
    <Paper>
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", gap: 34 }}>
        <div
          style={{
            width: interpolate(frame, [0, 34], [0, 620], { ...clamp, easing: EASE_OUT }),
            height: 2,
            backgroundColor: C.line,
            marginBottom: 10,
          }}
        />

        <Sequence name="Wordmark" from={14} layout="none">
          <MaskText
            name="SaysWho"
            lines={["SaysWho"]}
            size={TYPE.hero}
            align="center"
            letterSpacing="-0.04em"
          />
        </Sequence>

        <Sequence name="Tagline" from={44} layout="none">
          <div
            style={{
              fontFamily: FONT.sans,
              fontSize: TYPE.support,
              lineHeight: 1.4,
              letterSpacing: "-0.015em",
              color: C.dim,
              textAlign: "center",
              maxWidth: 1180,
              opacity: interpolate(frame, [44, 68], [0, 1], clamp),
              translate: interpolate(frame, [44, 74], ["0px 18px", "0px 0px"], {
                ...clamp,
                easing: EASE_OUT,
              }),
            }}
          >
            Checks whether the cited page says what the sentence says.
          </div>
        </Sequence>
      </AbsoluteFill>
    </Paper>
  );
};
