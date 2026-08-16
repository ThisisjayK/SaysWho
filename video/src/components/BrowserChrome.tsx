import React from "react";
import { interpolate, useCurrentFrame } from "remotion";
import { C, clamp, EASE_OUT, FONT } from "../theme";

/**
 * The frame every piece of screen recording sits in. Product footage is never
 * shown full bleed; it floats, slightly inset, with a soft shadow and a very
 * slow drift so a static capture still has life in it.
 *
 * Drop a <Video> from @remotion/media in as the child once the recordings exist.
 */
export const BrowserChrome: React.FC<{
  children?: React.ReactNode;
  url?: string;
  width?: number;
  height?: number;
  delay?: number;
  drift?: boolean;
}> = ({
  children,
  url = "chatgpt.com",
  width = 1440,
  height = 830,
  delay = 0,
  drift = true,
}) => {
  const frame = useCurrentFrame();

  return (
    <div
      style={{
        width,
        height,
        borderRadius: 22,
        overflow: "hidden",
        backgroundColor: "#ffffff",
        border: `1px solid ${C.line}`,
        boxShadow: `0 60px 140px -50px rgba(20,20,15,0.45), 0 12px 40px -20px rgba(20,20,15,0.18)`,
        display: "flex",
        flexDirection: "column",
        opacity: interpolate(frame, [delay, delay + 20], [0, 1], clamp),
        scale: interpolate(frame, [delay, delay + 40], [0.965, 1], {
          ...clamp,
          easing: EASE_OUT,
        }),
        translate: drift
          ? interpolate(frame, [delay, delay + 300], ["0px 26px", "0px -8px"], {
              ...clamp,
              easing: EASE_OUT,
            })
          : interpolate(frame, [delay, delay + 40], ["0px 26px", "0px 0px"], {
              ...clamp,
              easing: EASE_OUT,
            }),
      }}
    >
      <div
        style={{
          height: 62,
          flexShrink: 0,
          backgroundColor: C.paperWarm,
          borderBottom: `1px solid ${C.line}`,
          display: "flex",
          alignItems: "center",
          paddingInline: 24,
          gap: 12,
        }}
      >
        {[C.line, C.line, C.line].map((c, i) => (
          <div
            key={i}
            style={{ width: 13, height: 13, borderRadius: 999, backgroundColor: c }}
          />
        ))}
        <div
          style={{
            marginLeft: 22,
            flex: 1,
            height: 34,
            borderRadius: 999,
            backgroundColor: "#ffffff",
            border: `1px solid ${C.line}`,
            display: "flex",
            alignItems: "center",
            paddingInline: 18,
            fontFamily: FONT.mono,
            fontSize: 19,
            color: C.mute,
          }}
        >
          {url}
        </div>
      </div>
      <div style={{ flex: 1, position: "relative", overflow: "hidden" }}>{children}</div>
    </div>
  );
};
