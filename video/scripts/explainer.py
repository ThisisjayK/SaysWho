"""Recut of the site explainer, so every narration line lands on the picture it describes.

Run it from `video/`:

    python3 scripts/explainer.py

## The sidebar is masked here, not trusted from the input

The ChatGPT sidebar in the browser take carries real conversation titles. The render this script reads,
`out/explainer-masked.mp4`, already had a blur over them, but that blur started nine frames late on the
second browser block: between 47.20 and 47.50 every title was readable at full contrast, in the file that
was on the site. A time gated mask is one arithmetic slip away from a leak, and the slip is invisible unless
somebody samples the exact second it happens.

So the mask is reapplied here over every browser frame rather than inherited. `MASK` matches what was
measured off the good frames of that render: 296 pixels wide, `gblur` at sigma 40, which reproduces its
mean and its maximum luma to within a point. Blurring an already blurred column changes nothing, which is
what makes doing it unconditionally cheap. Any segment carrying browser footage sets `mask=True`, and the
terminal and card segments do not, because their text starts at x=128 and would be smeared by it.

**Check after every rebuild, and do not take the absence of a report as proof:**

    ffmpeg -v error -ss 47.2 -to 138.7 -i ../site/media/explainer.mp4 \
      -vf "crop=292:720:0:0,signalstats,metadata=print:key=lavfi.signalstats.YMAX:file=-" -f null -

Any frame reporting `YMAX` above about 110 inside a browser block is a readable sidebar.

## What moved, and why

The first assembly put the browser take's opening ten seconds at the head. Those ten seconds contain the
capture click, so the capture panel, `INCOMPLETE` and all, was legible from 0:12 while the narration
introduced capture at 0:49 and treated `INCOMPLETE` as news at 1:03. The picture was fifty seconds ahead of
the voice on the beat the film exists for.

The fix is a boundary move, not a re-edit: the opening browser shot now ends with the cursor on the button,
and the click travels to the front of the main browser run. Nothing is cut, nothing is reordered inside the
take, and the join at frame 1416 is seamless because it is continuous in the source recording. Everything
from 47.2s onward sits at the same timestamp it did before, which is why the poster frame is still the
poster frame.

## The script names what is on screen

The first version had twelve lines and left three stretches with picture and no voice: the report panel
opening on its verdict tally, the claim list scrolling, and twenty seconds of `FINDINGS.md` going past with
nothing said about what it is. `ex-07`, `ex-09` and `ex-14` were written for those three, so every file the
demo opens is now named and explained while it is on screen.

The whole script was then rewritten to be spoken rather than recited. Every figure survived that pass
unchanged, and `ex-13` still carries the interval and the n, because kappa without them is the one sentence
that would sink this video.

`ex-11` is the one line still short of its picture. It names the answer level refusal, whose "No overall
score" box is only up between 1:15.7 and about 1:28, and the script's own wording, "the second refusal",
forbids moving it ahead of the grey claims it follows. It sits at 2:08 over the sources list. Fixing that
properly means re-recording the scroll, not rewriting the line.
"""

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
SOURCE = HERE / "out" / "explainer-masked.mp4"
VO = HERE / "public" / "audio" / "explainer"
WORK = HERE / "out" / "recut"
OUT = HERE.parent / "site" / "media" / "explainer.mp4"

FPS = 30
TOTAL_FRAMES = 6396

# Picture, in source frames: start, count, whether the block shows the browser, label. The order is the
# new order; the numbers are where each block lives in `explainer-masked.mp4`. Frames 316 to 421 are the
# capture click, and they are the only thing that moves.
#
# The title card is masked with the browser blocks because the dissolve out of it runs over the browser,
# and its own left 296 pixels are empty gradient, so the blur costs it nothing.
SEGMENTS = [
    (0, 121, True, "title card, from the film"),
    (121, 195, True, "the answer, and the cursor reaching the button"),
    (421, 540, False, "the frozen query set, hash checked"),
    (961, 455, False, "the auditor starting"),
    (316, 105, True, "the capture click, and the panel that prints INCOMPLETE"),
    (1416, 2747, True, "the audit, claim by claim, and both refusals"),
    (4163, 2233, False, "the run readout, FINDINGS, STATUS, the closing card"),
]

MASK = "split[a][b];[b]crop=296:720:0:0,gblur=sigma=40:steps=3[m];[a][m]overlay=0:0"

# Narration, in output seconds. Every offset below was measured against the recut picture rather than
# estimated, the same rule `src/audio/narration.ts` follows for the film.
GAIN_DB = -2.75  # the level the first mix used, measured off the render rather than guessed

# `video/public/audio/` is gitignored, because the repo's rule is that the written line is the source and
# the mp3 is build output. So the twelve lines are written here. Regenerate them into
# `public/audio/explainer/` with the `SOUND.md` voice, `txYZyFyf0wIEgqUsHmno`, one file per line, and the
# offsets below stay valid as long as the durations do. They are measured, so check them if a line is
# re-cut: a line that grows past its slot walks onto the next shot, which is the bug this recut fixed.
NARRATION = [
    ("film-title.wav", 1.25, "SaysWho reads them.",
     "the film's title card, left where it was"),
    ("ex-01.mp3", 2.95,
     "Every answer here arrives with its sources attached. The citation is the part that does the "
     "persuading. And nothing that wrote this answer ever read them.",
     "the answer and its chips, 4.03 to 10.53"),
    ("ex-02.mp3", 12.60,
     "So I wrote the questions first. Twenty four of them, frozen with hashes before I captured a single "
     "answer. If I'd tuned one after seeing a result, this check fails. It passes.",
     "the freeze check, which prints OK at about 15.5"),
    ("ex-03.mp3", 30.50,
     "Capture works on its own. Verdicts need this one: a local auditor that fetches every cited page and "
     "reads it. It refuses to start unless its judge can actually answer.",
     "the server banner, which finishes printing at about 33.6"),
    ("ex-04.mp3", 44.50,
     "So capture grabs the answer, hashes it, and lists every source it cites.",
     "the click lands at 44.20 and the panel draws at 44.30"),
    ("ex-05.mp3", 49.00,
     "And straight away it tells me something I'd rather not know. Two controls are hiding citations it "
     "couldn't reach. Across ten answers that's at least twenty missing out of fifty three. A tool that "
     "didn't count them would look more accurate and be less honest.",
     "INCOMPLETE is on the panel until it is dismissed at about 52.5"),
    ("ex-06.mp3", 66.20,
     "Now the audit. Every cited page gets fetched. Every claim gets judged against the page it points "
     "at. And every quote gets checked by a script against the document that came back.",
     "the audit is running, and the panel opens at 75.7 as the line ends"),
    ("ex-07.mp3", 77.60,
     "So this is the report it writes. The answer's hash, the adapter it used to read the page, and every "
     "claim sorted by what its source turned out to say. Six of the twelve aren't cited at all, so "
     "they're listed and left unscored.",
     "the panel opens on its tally and its No overall score box, 75.7 to about 88"),
    ("ex-08.mp3", 92.00,
     "Here it is, claim by claim. Green means it quoted a passage and a script confirmed that passage is "
     "really on the page. Rust means the page was read and doesn't say this. That's a statement about the "
     "citation, not about the world.",
     "the green card at 96 and the rust card at 104"),
    ("ex-09.mp3", 109.00,
     "Every claim's here, including the ones with nothing to check. I could drop those and the report "
     "would look tidier. It'd also tell you less.",
     "the list opens, uncited rows and all"),
    ("ex-10.mp3", 117.50,
     "And three come back grey. Could not verify. Those pages couldn't be read, so nothing gets scored. "
     "Every other tool I looked at promises you a number here. A number here is invented.",
     "ALL CLAIMS, with the three Could not verify rows on screen"),
    ("ex-11.mp3", 128.50,
     "Then the second refusal, and it's the better one. No overall score, because more than half this "
     "answer's cited claims produced no verdict that stands.",
     "the sources list, ending as the cut to the run readout lands"),
    ("ex-12.mp3", 139.10,
     "Ten answers. A hundred and thirty nine model calls. The stratum rate is withheld, and the gate "
     "names its own reason. Then the one number I care about most, because it's about this tool and not "
     "about anybody else's.",
     "STRATUM RATE withheld is on screen from 143.9 to 150.5"),
    # Trimmed from a longer take. The readout shot runs 30.6s and this line plus the one before it have to
    # end inside it, so the wind-up went and every figure stayed. The interval is not negotiable here.
    ("ex-13.mp3", 152.40,
     "Forty five claims, labelled blind before the judge saw them. Cohen's kappa is zero point three "
     "zero, interval zero point zero zero four to zero point six, over thirty five pairs. That lower "
     "bound doesn't rule out chance. It's published because it's unflattering.",
     "JUDGE AGAINST HUMAN, kappa and its interval, from about 156"),
    ("ex-14.mp3", 169.90,
     "This is FINDINGS.md. It's where things that went wrong get written down while they're still "
     "embarrassing. A research report that named fifteen sources and linked exactly one of them. A gate "
     "that threw out an entire table because it looked like furniture. A span guard narrower than the "
     "design document promised.",
     "the FINDINGS.md shot, 169.4 to 189.5"),
    ("ex-15.mp3", 192.10,
     "One last row. The one I'd leave out if I could. The real research questions this was built for are "
     "gone, and retyping them from memory would have made a published sentence false. So it never ran, "
     "and the table says so.",
     "the blocker table lands at 202.3, under the last sentence"),
    ("film-close.wav", 205.75,
     "It cannot tell you a source is right. A well cited falsehood passes. It can tell you when nobody "
     "checked.",
     "the film's two closing lines, over its closing card"),
]

# The two lines the bookend took from the film are cut back out of the render rather than re-rendered,
# so they keep the level and the room they were mixed at.
FILM_CLIPS = [("film-title.wav", 1.25, 1.45), ("film-close.wav", 204.05, 6.05)]


def run(cmd: list[str]) -> None:
    if subprocess.call(cmd) != 0:
        sys.exit(f"failed: {' '.join(str(c) for c in cmd)}")


def main() -> None:
    if not SOURCE.exists():
        sys.exit(f"{SOURCE} is missing. It is the masked render, and this script will not cut without it.")
    if sum(n for _, n, _, _ in SEGMENTS) != TOTAL_FRAMES:
        sys.exit("the segment list does not account for every frame of the source")

    WORK.mkdir(parents=True, exist_ok=True)
    for f in WORK.glob("*"):
        f.unlink()

    print("picture")
    parts = []
    at = 0
    for i, (start, count, browser, note) in enumerate(SEGMENTS):
        part = WORK / f"v{i}.mp4"
        run(["ffmpeg", "-v", "error", "-accurate_seek", "-ss", f"{start / FPS:.6f}",
             "-i", str(SOURCE), "-frames:v", str(count), "-an",
             *(["-filter_complex", MASK] if browser else []),
             "-c:v", "libx264", "-crf", "21", "-preset", "slow", "-pix_fmt", "yuv420p",
             str(part), "-y"])
        parts.append(part)
        print(f"  {at / FPS:7.2f}  {count / FPS:6.2f}s  {'masked  ' if browser else '        '}{note}")
        at += count

    listing = WORK / "parts.txt"
    listing.write_text("".join(f"file '{p.name}'\n" for p in parts))
    picture = WORK / "picture.mp4"
    run(["ffmpeg", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(listing),
         "-c", "copy", str(picture), "-y"])

    print("narration")
    for name, start, length in FILM_CLIPS:
        run(["ffmpeg", "-v", "error", "-ss", str(start), "-t", str(length), "-i", str(SOURCE),
             "-vn", "-ac", "2", "-ar", "48000", str(WORK / name), "-y"])

    inputs, chains, labels = [], [], []
    for i, (name, at_s, _text, note) in enumerate(NARRATION):
        src = WORK / name if name.endswith(".wav") else VO / name
        inputs += ["-i", str(src)]
        gain = "" if name.endswith(".wav") else f"volume={GAIN_DB}dB,"
        chains.append(
            f"[{i}:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,"
            f"{gain}adelay=delays={int(at_s * 1000)}:all=1[n{i}]"
        )
        labels.append(f"[n{i}]")
        print(f"  {at_s:7.2f}  {name:15s} {note}")

    graph = ";".join(chains) + ";" + "".join(labels) + f"amix=inputs={len(NARRATION)}:normalize=0[aout]"
    track = WORK / "narration.m4a"
    run(["ffmpeg", "-v", "error", *inputs, "-filter_complex", graph, "-map", "[aout]",
         "-t", f"{TOTAL_FRAMES / FPS:.3f}", "-c:a", "aac", "-b:a", "160k", str(track), "-y"])

    run(["ffmpeg", "-v", "error", "-i", str(picture), "-i", str(track),
         "-map", "0:v", "-map", "1:a", "-c", "copy", "-movflags", "+faststart", str(OUT), "-y"])
    print(f"wrote {OUT}  ({OUT.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
