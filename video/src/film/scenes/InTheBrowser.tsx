import { Video } from "@remotion/media";
import React from "react";
import { AbsoluteFill, interpolate, Sequence, staticFile, useCurrentFrame } from "remotion";
import { BrowserChrome } from "../../components/BrowserChrome";
import { CameraPush } from "../../components/CameraPush";
import { MaskText } from "../../components/MaskText";
import { Paper } from "../../components/Paper";
import { FOOTAGE } from "../../footage";
import { C, clamp, EASE_OUT, FONT, SAFE, TYPE } from "../../theme";

/**
 * The tool being used, in a real browser, in one take.
 *
 * The footage is a genuine screen recording rather than a recreation, because
 * VIDEO.md's rubric asks for one uncut segment of the extension running, and
 * because a reconstruction of a citation checker would be a strange thing for
 * this project of all projects to ship. RECORDING.md says what to record.
 *
 * The scene is left out of the cut entirely until `FOOTAGE.present` is true.
 * See src/footage.ts.
 *
 * The camera does the pointing. Two pushes: onto the capture warning, which is
 * the tool admitting it cannot see every citation, and onto the row it will not
 * score. Both are clamped so the edge of the recording can never show.
 */

const FRAME_W = 1500;
const FRAME_H = 742;

export const InTheBrowser: React.FC = () => {
  const frame = useCurrentFrame();

  return (
    <Paper>
      <AbsoluteFill
        style={{ alignItems: "center", justifyContent: "center", paddingBottom: 96 }}
      >
        <BrowserChrome url="chatgpt.com" width={FRAME_W} height={FRAME_H} drift={false}>
          <CameraPush
            width={FRAME_W}
            height={FRAME_H - 62}
            poses={[
              { at: 0, zoom: 1, x: 0.5, y: 0.5 },
              // Onto the capture warning. It printed INCOMPLETE on camera; the
              // film points at it rather than talking over it.
              { at: 96, zoom: 1.55, x: 0.42, y: 0.3 },
              { at: 150, zoom: 1.55, x: 0.42, y: 0.3 },
              { at: 200, zoom: 1, x: 0.5, y: 0.5 },
              // Onto the claim it refuses to score.
              { at: 286, zoom: 1.75, x: 0.46, y: 0.62 },
              { at: 350, zoom: 1.75, x: 0.46, y: 0.62 },
            ]}
          >
            <Video
              src={staticFile(FOOTAGE.file)}
              style={{ width: "100%", height: "100%", objectFit: "cover" }}
            />
          </CameraPush>
        </BrowserChrome>
      </AbsoluteFill>

      <Sequence name="Caption" from={26}>
        <AbsoluteFill
          style={{
            padding: `${SAFE.y}px ${SAFE.x}px`,
            justifyContent: "flex-end",
            alignItems: "center",
          }}
        >
          <div
            style={{
              fontFamily: FONT.mono,
              fontSize: 24,
              letterSpacing: "0.06em",
              textTransform: "uppercase",
              color: C.dim,
              opacity: interpolate(frame, [26, 48], [0, 1], clamp),
              translate: interpolate(frame, [26, 56], ["0px 12px", "0px 0px"], {
                ...clamp,
                easing: EASE_OUT,
              }),
            }}
          >
            One answer, marked claim by claim
          </div>
        </AbsoluteFill>
      </Sequence>

      <Sequence name="Every sentence gets a colour" from={FOOTAGE.durationInFrames - 116}>
        <Paper>
          <AbsoluteFill style={{ padding: `${SAFE.y}px ${SAFE.x}px`, justifyContent: "center" }}>
            <MaskText
              lines={["Every sentence gets a colour,", "and one of the colours", "is a refusal."]}
              size={TYPE.statement}
              stagger={7}
            />
          </AbsoluteFill>
        </Paper>
      </Sequence>
    </Paper>
  );
};
