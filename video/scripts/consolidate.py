"""One film out of the two, for a page that should not ask anybody to pick.

Run it from `video/`:

    python3 scripts/consolidate.py

`out/film-web.mp4` is the two minute Remotion piece at web size and `out/explainer-web.mp4` is the
narrated walkthrough. Both are build output and neither is published: only the film this script writes
is. They were separate embeds on the site, and the explainer already borrows the film's title card to open on
and its closing card to end on, so playing both in a row says two things twice.

So the join is not a concatenation. The film plays up to its closing card, the explainer's body plays
without the bookends it borrowed, and then the film's closing card ends the whole thing. The title card is
seen once, at 0:16 where the film puts it, and the two closing lines are heard once, at the end.

## Nothing spoken is cut, and nothing is trimmed any more

Both trim points sit inside a measured silence in the track they cut, so no word is clipped and the
crossfades have nothing to fade over but room tone.

An earlier version of this file also shortened two stretches inside the explainer, 6.0s off the audit panel
opening and 13.0s off the `FINDINGS.md` shot, because both ran silent and long. That was the wrong repair.
The picture was not too long, the script was too short: neither the report panel nor `FINDINGS.md` had a
line saying what it was. `explainer.py` now has one for each, so the footage they were cut from is back and
the voice covers it.

## The mask still travels

`out/explainer-web.mp4` carries the blur over the ChatGPT conversation titles, and the film's browser take
was shot with the sidebar collapsed, so neither input needs masking here. This script only trims and
dissolves, so the pixels arrive as they left. Re-run the scan in `explainer.py` against the output anyway;
the point of that scan is that it costs nothing and the failure it catches is invisible.
"""

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
SITE = HERE.parent / "site" / "media"
OUTDIR = HERE / "out"
FILM = OUTDIR / "film-web.mp4"
EXPL = OUTDIR / "explainer-web.mp4"
OUT = SITE / "sayswho.mp4"

# source, start, end, crossfade into the next piece, what it is.
# The film is silent from 109.15 to 111.80 and the explainer from 75.5 to 91.0, 169.3 to 192.1 and
# 205.34 to 205.75. Every boundary below is inside one of those.
# The last join is a splice, not a dissolve. The explainer's final seconds are already the film's closing
# card, because the bookend put it there: its dip at 204.90 is the film at 110.30, so explainer 205.70 is
# the film at 111.10. Crossfading that into the film's own card at any other timestamp dissolves the card
# into itself one beat out of step and prints the wordmark twice, which is what the second build did.
# Resuming the film at exactly 111.10 makes the dip continuous instead, so 0.10s is enough to hide the seam.
PIECES = [
    (FILM, 0.00, 110.00, 0.35, "the film, up to but not including its closing card"),
    (EXPL, 2.60, 205.70, 0.10, "the whole walkthrough, from the first narrated line to the last"),
    (FILM, 111.10, 118.60, None, "the film's closing card, and its two last lines"),
]


def main() -> None:
    for f in (FILM, EXPL):
        if not f.exists():
            sys.exit(f"{f} is missing")

    chains, vlabels, alabels = [], [], []
    for i, (src, a, b, _x, note) in enumerate(PIECES):
        chains.append(
            f"[{i}:v]trim={a}:{b},setpts=PTS-STARTPTS,fps=30,format=yuv420p[v{i}]"
        )
        chains.append(f"[{i}:a]atrim={a}:{b},asetpts=PTS-STARTPTS,aresample=48000[a{i}]")
        vlabels.append(f"[v{i}]")
        alabels.append(f"[a{i}]")
        print(f"  {b - a:6.2f}s  {src.name:15s} {a:7.2f} to {b:7.2f}   {note}")

    # xfade needs the offset into the running total, so it is carried rather than recomputed.
    total = PIECES[0][2] - PIECES[0][1]
    vprev, aprev = "[v0]", "[a0]"
    for i in range(1, len(PIECES)):
        x = PIECES[i - 1][3]
        length = PIECES[i][2] - PIECES[i][1]
        vout = "[vout]" if i == len(PIECES) - 1 else f"[x{i}]"
        aout = "[aout]" if i == len(PIECES) - 1 else f"[y{i}]"
        chains.append(f"{vprev}[v{i}]xfade=transition=fade:duration={x}:offset={total - x:.3f}{vout}")
        chains.append(f"{aprev}[a{i}]acrossfade=d={x}{aout}")
        total += length - x
        vprev, aprev = vout, aout

    print(f"  {total:6.2f}s  total  ({int(total) // 60}:{total % 60:05.2f})")

    cmd = ["ffmpeg", "-v", "error"]
    for src, *_ in PIECES:
        cmd += ["-i", str(src)]
    cmd += ["-filter_complex", ";".join(chains), "-map", "[vout]", "-map", "[aout]",
            "-c:v", "libx264", "-crf", "21", "-preset", "slow", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(OUT), "-y"]
    if subprocess.call(cmd) != 0:
        sys.exit("ffmpeg failed")
    print(f"wrote {OUT}  ({OUT.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
