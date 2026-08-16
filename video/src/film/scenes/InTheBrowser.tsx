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
 * this project of all projects to ship. RECORDING.md says what to record, and
 * src/footage.ts lists the four ways the take that got shot differs from it.
 *
 * The scene is left out of the cut entirely until `FOOTAGE.present` is true.
 * See src/footage.ts.
 *
 * The camera does the pointing, and the poses below are frame numbers into this
 * particular take. Re-cut the footage and they are the thing to redo. Two
 * pushes: onto the capture warning, which is the tool admitting it cannot see
 * every citation, and onto the row it will not score, which then drifts to the
 * row it did verify. Both are clamped so the edge of the recording can never
 * show, which is why an x of 0.84 is safe to ask for.
 */

/**
 * The window, at the recording's own aspect so nothing is cropped twice.
 *
 * `objectFit: cover` will happily throw away a third of a taller recording to
 * fill a wide box, which is what an earlier cut of this scene did: the panel
 * lost its heading at the top and its source list at the bottom, in CSS, after
 * the footage had already been cropped once in the edit. So the frame is sized
 * from the file rather than the file being made to fit a frame.
 *
 * This take is 1920 x 1396, which is nearly square, so the window has to be
 * narrower than the last one to leave the caption its room: 1080 wide puts the
 * bottom edge 28px clear of it. Read the constant off FOOTAGE rather than
 * retyping it, so a recut of a different shape cannot silently letterbox.
 */
const FRAME_W = 1080;
const FRAME_H = Math.round(FRAME_W / (FOOTAGE.width / FOOTAGE.height)) + 62;

export const InTheBrowser: React.FC = () => {
  const frame = useCurrentFrame();

  return (
    <Paper>
      <AbsoluteFill
        style={{ alignItems: "center", justifyContent: "center", paddingBottom: 150 }}
      >
        <BrowserChrome url="chatgpt.com" width={FRAME_W} height={FRAME_H} drift={false}>
          <CameraPush
            width={FRAME_W}
            height={FRAME_H - 62}
            poses={[
              // Every move below is deliberately slower than it needs to be.
              // CameraPush eases between poses, so the gap between two poses is
              // the duration of the move: ~55 frames to travel, ~80 to sit
              // still and let the thing being pointed at be read. The focal
              // points are measured off the cut, not guessed.
              //
              // The beats, in frames: typing to 197, the popup 197 to 317, the
              // capture toast 310 to 460, the ramped wait 452 to 482, the panel
              // 475 to 535, Supported 527 to 593, Not supported 586 to 691,
              // Sources disagree 683 on. Everything after 786 is behind the
              // closing card, which is what the tail of the last segment is for.
              { at: 0, zoom: 1, x: 0.5, y: 0.5 },
              // Barely a move. The question is being typed and the answer is
              // arriving; a still frame for six seconds reads as a freeze.
              { at: 120, zoom: 1.08, x: 0.5, y: 0.45 },
              { at: 200, zoom: 1.08, x: 0.5, y: 0.45 },
              // Onto the popup in the top right: the extension being opened,
              // which is what this take set out to show.
              { at: 250, zoom: 1.85, x: 0.92, y: 0.1 },
              { at: 305, zoom: 1.85, x: 0.92, y: 0.1 },
              // A pan rather than a cut, down onto the capture toast: the tool
              // saying it cannot see every citation on this answer.
              { at: 362, zoom: 1.7, x: 0.8, y: 0.67 },
              { at: 445, zoom: 1.7, x: 0.8, y: 0.67 },
              // Wide, and still, through the one second that stands in for five
              // minutes, and through the panel arriving.
              { at: 478, zoom: 1, x: 0.5, y: 0.5 },
              { at: 505, zoom: 1, x: 0.5, y: 0.5 },
              // The counts, then three rows in the order the run produced them:
              // one it verified, one the page contradicts, and one where two
              // sources disagree and neither is averaged away.
              { at: 535, zoom: 1.5, x: 0.68, y: 0.35 },
              { at: 560, zoom: 1.6, x: 0.675, y: 0.33 },
              { at: 590, zoom: 1.75, x: 0.675, y: 0.33 },
              { at: 625, zoom: 1.7, x: 0.63, y: 0.43 },
              { at: 685, zoom: 1.7, x: 0.63, y: 0.43 },
              { at: 725, zoom: 1.55, x: 0.68, y: 0.52 },
              { at: FOOTAGE.durationInFrames - 116, zoom: 1.55, x: 0.68, y: 0.52 },
            ]}
          >
            <Video
              src={staticFile(FOOTAGE.file)}
              style={{ width: "100%", height: "100%", objectFit: "cover" }}
            />
          </CameraPush>
        </BrowserChrome>
      </AbsoluteFill>

      {/* RECORDING.md forbids speeding the audit up, and gives the reason: a
          sped-up audit is a claim about latency this project has not measured.
          The take is ramped through the wait anyway, because this audit ran
          for roughly five minutes and the film cannot hold on a spinner for
          that long. So the compression is stated on screen while it is
          happening, with the measured number, which is the difference between
          compressing a wait and hiding one. */}
      <Sequence name="The ramp, declared" from={415} durationInFrames={130}>
        <AbsoluteFill
          style={{
            // Under the caption, not above the window. The taller frame leaves
            // no room at the top, and a top-aligned line landed inside the fake
            // URL bar and read as part of the page rather than as a note about
            // the film.
            padding: `${SAFE.y}px ${SAFE.x}px 72px`,
            justifyContent: "flex-end",
            alignItems: "center",
          }}
        >
          <div
            style={{
              fontFamily: FONT.mono,
              fontSize: 22,
              letterSpacing: "0.06em",
              textTransform: "uppercase",
              color: C.dim,
              opacity: interpolate(frame, [415, 440, 515, 545], [0, 1, 1, 0], clamp),
            }}
          >
            The audit took about five minutes. You are seeing one second of it.
          </div>
        </AbsoluteFill>
      </Sequence>

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
