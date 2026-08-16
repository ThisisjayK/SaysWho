import React from "react";
import { AbsoluteFill, interpolate, Sequence, useCurrentFrame } from "remotion";
import { MaskText } from "../../components/MaskText";
import { Paper } from "../../components/Paper";
import { C, clamp, EASE_OUT, FONT, TYPE } from "../../theme";

export const Close: React.FC = () => {
  const frame = useCurrentFrame();

  return (
    <Paper>
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", gap: 30 }}>
        <MaskText
          lines={["SaysWho"]}
          size={TYPE.hero}
          align="center"
          letterSpacing="-0.04em"
        />

        <Sequence name="Sign off" from={26} layout="none">
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: 18,
              marginTop: 8,
              opacity: interpolate(frame, [26, 50], [0, 1], clamp),
              translate: interpolate(frame, [26, 56], ["0px 16px", "0px 0px"], {
                ...clamp,
                easing: EASE_OUT,
              }),
            }}
          >
            <div
              style={{
                fontFamily: FONT.sans,
                fontSize: 38,
                letterSpacing: "-0.015em",
                color: C.dim,
                textAlign: "center",
              }}
            >
              Unauditable claims are counted, named, and kept out of every rate.
            </div>
            <div
              style={{
                fontFamily: FONT.mono,
                fontSize: 26,
                letterSpacing: "0.03em",
                color: C.mute,
              }}
            >
              github.com/ThisisjayK/SaysWho
            </div>
          </div>
        </Sequence>
      </AbsoluteFill>
    </Paper>
  );
};
