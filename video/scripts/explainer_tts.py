"""Generate the explainer's narration from the lines written in `explainer.py`.

    export ELEVENLABS_API_KEY=...
    python3 scripts/explainer_tts.py            # only the files that are missing
    python3 scripts/explainer_tts.py --all      # every line, after a script rewrite

`video/public/audio/` is gitignored because the written line is the source and the mp3 is output. This is
the script that turns one into the other, so a wiped audio directory is a command rather than a loss.

The voice is the one `SOUND.md` names, so a reshoot of a single line still matches the rest. The two clips
taken from the film are not generated here: `explainer.py` cuts those out of the render itself, which keeps
the level and the room they were mixed at.

Durations are not fixed. A rewritten line comes back longer or shorter than the one it replaces, and the
offsets in `explainer.py` are measured against the picture, so this prints the new duration of every file
next to the slot it has to fit. A line that outgrows its slot walks onto the next shot, which is the bug the
recut existed to fix in the first place.
"""

import os
import sys
import json
import time
import subprocess
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from explainer import NARRATION, VO  # noqa: E402

VOICE = "txYZyFyf0wIEgqUsHmno"
MODEL = "eleven_multilingual_v2"


def duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True,
    )
    return float(out.stdout.strip() or 0.0)


def main() -> None:
    key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if not key:
        sys.exit("ELEVENLABS_API_KEY is not set. This script will not read a key out of the repo.")
    redo_all = "--all" in sys.argv
    VO.mkdir(parents=True, exist_ok=True)

    lines = [(n, t) for n, at, t, note in NARRATION if not n.endswith(".wav")]
    slots = {n: at for n, at, _t, _note in NARRATION}
    order = [n for n, _at, _t, _note in NARRATION]

    for name, text in lines:
        dest = VO / name
        if dest.exists() and not redo_all:
            print(f"  {name:12s} kept")
            continue
        req = urllib.request.Request(
            f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE}",
            data=json.dumps({"text": text, "model_id": MODEL}).encode(),
            headers={"xi-api-key": key, "Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                dest.write_bytes(r.read())
        except Exception as e:  # the key, the quota or the network. All three read the same from here.
            sys.exit(f"  {name} failed: {e}")
        print(f"  {name:12s} {dest.stat().st_size:>7} bytes  {duration(dest):5.2f}s   {text[:52]}")
        time.sleep(0.4)

    print("\nwhat each line now occupies, and what follows it:")
    for i, name in enumerate(order):
        if name.endswith(".wav"):
            continue
        at = slots[name]
        ends = at + duration(VO / name)
        nxt = slots[order[i + 1]] if i + 1 < len(order) else None
        gap = f"{nxt - ends:+6.2f}s to the next line" if nxt else ""
        flag = "  OVERLAPS" if nxt is not None and nxt < ends else ""
        print(f"  {name:12s} {at:7.2f} to {ends:7.2f}  {gap}{flag}")


if __name__ == "__main__":
    main()
