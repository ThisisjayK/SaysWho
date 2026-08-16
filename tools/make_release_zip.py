"""Build the archive the website hands out.

    python3 tools/make_release_zip.py

**The file list comes from `git ls-files`, not from walking the tree.** That is the
whole safety argument. Everything this project keeps off GitHub is already named in
`.gitignore` for a stated reason: captures, stored pages, fetch cache, splits, gold
sets, run records, reports and the correspondence with the professor. A walker would
have to re-derive that list and would drift from it the first time a rule changed. Git
already knows, so it is asked.

On top of that the archive drops the video project and the site's own media, because a
person downloading this wants the tool, and adds three gates that run before anything is
written:

1. **No secret-shaped string** survives into the archive. An `sk_`, an `AIza`, a private
   key header or an `xi-api-key` aborts the build rather than shipping.
2. **No personal information.** The maintainer's contact address is replaced with a
   placeholder and home directory paths are reduced to `~`, and the substitutions are
   printed so the scrub is never silent.
3. **Nothing outside the tracked tree.** Anything git does not list cannot get in.

Failing loudly beats a quiet archive with a key in it, which is the same argument
`gates.py` makes about rates.
"""

from __future__ import annotations

import re
import subprocess
import sys
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "site" / "sayswho.zip"

#: Written for the archive rather than copied from the repo, whose README links to a dozen
#: documents this archive deliberately does not carry.
README = """# SaysWho

Checks whether the pages an AI answer cites actually say what the answer attributes to them.

## Install the extension

1. Open `chrome://extensions`
2. Turn on **Developer mode**, top right
3. Click **Load unpacked** and select the `extension` folder in here
4. Open an answer on chatgpt.com, claude.ai, perplexity.ai or a Google search

**Capture** works now, with nothing else running. It writes the answer, its hash and every
cited URL to your downloads folder, plus the page as it stood at capture time.

## Run the auditor, for verdicts

Fetching the cited pages and judging them happens outside the browser.

```bash
python3 -m venv .venv
.venv/bin/pip install google-genai
export GEMINI_API_KEY=your-real-key
.venv/bin/python -m sayswho.server --judge
```

A free key comes from aistudio.google.com. It is read from the environment and never
written to a file. The server binds to 127.0.0.1 only and refuses to start if the provider
rejects the key, so a green light in the popup means it works.

Then click **Audit**. Every claim comes back marked with what its source actually says.

## What is in here

`extension/` the extension. `sayswho/` the audit server and pipeline. `queries/` the frozen
query set, which the server hash-checks before it will start, and `tools/freeze_queries.py`
which is that check.

Python 3.11 or newer. `google-genai` is the only install, and only the judge uses it: the
fetching, extraction and gates are standard library.

## What it cannot do

It cannot tell you whether a source is right. A well cited falsehood passes clean. It is
blind to what an answer left out. It cannot tell a peer-reviewed paper from a blog post.

Where a cited page cannot be read, no verdict is produced and nothing is scored, and where
half or more of an answer cannot be checked it prints no rate for that answer at all. There
is no confidence score anywhere in it.
"""

#: What the archive contains, as an allowlist rather than a list of exclusions. The
#: question a downloader is asking is "what do I need to run this", and answering it by
#: subtraction meant shipping the working list, the video shot list, the course write-up
#: and the agent instructions, none of which run anything.
#:
#: Each entry earns its place at runtime:
#:
#: `extension/`  the product. Manifest V3, no build step, loaded unpacked.
#: `sayswho/`    the audit server and pipeline. Capture works without it; verdicts do not.
#: `queries/`    the frozen query set. `sayswho.server` refuses to start if the freeze
#:               check fails, and the check hashes these files.
#: `tools/freeze_queries.py`
#:               that check. `queryset.freeze_intact` shells out to it, so it is a runtime
#:               dependency rather than a development one, which is easy to miss.
#: `tools/validate_queries.py`
#:               imported by the above. Left out of the first version of this list, which
#:               is how the first archive shipped a server that could not start: the freeze
#:               check died on ModuleNotFoundError and the server refuses to run without it.
#:               Found by extracting the archive and running it, not by reading the list.
KEEP_PREFIXES = (
    "extension/",
    "sayswho/",
    "queries/",
    "tools/freeze_queries.py",
    "tools/validate_queries.py",
)

#: Substitutions, applied to every text file. Left is a regex, right is the replacement.
SCRUBS: list[tuple[str, str, str]] = [
    (
        r"kappagantula\.j@northeastern\.edu",
        "you@example.com",
        "maintainer contact address",
    ),
    (
        r"/Users/[A-Za-z0-9._-]+/",
        "~/",
        "home directory paths",
    ),
    # One docstring in sayswho/ethics.py explains the gate by reference to the assignment
    # it was written for, which means nothing to somebody who downloaded a browser
    # extension. The sentence is true either way; only the framing goes.
    (
        r"`SCOPE\.md` \u00a78 and the capstone's attestation row both ask for the same thing, and they ask for it in the same\nwords: show",
        "This project's own attestation rule asks for one thing and asks for it plainly: show",
        "capstone framing in a docstring",
    ),
]

#: Anything matching these in the final bytes stops the build. Deliberately broader than
#: the keys this project actually uses.
FORBIDDEN = [
    (r"sk_[A-Za-z0-9]{24,}", "an ElevenLabs or OpenAI style key"),
    (r"AIza[A-Za-z0-9_\-]{30,}", "a Google API key"),
    (r"AQ\.[A-Za-z0-9]{20,}", "a Google Cloud style key"),
    (r"xi-api-key\s*[:=]\s*['\"][^'\"]+", "an ElevenLabs key in a header"),
    (r"-----BEGIN [A-Z ]*PRIVATE KEY-----", "a private key"),
    (r"kappagantula", "the maintainer's name in an address"),
    (r"/Users/[A-Za-z0-9._-]+/", "a home directory path"),
]

TEXT_SUFFIXES = {
    ".py", ".md", ".txt", ".toml", ".json", ".js", ".ts", ".tsx", ".html", ".css",
    ".yml", ".yaml", ".cfg", ".ini", ".sh", ".mjs", ".gitignore",
}


def tracked_files() -> list[str]:
    out = subprocess.run(
        ["git", "ls-files", "-z"], cwd=REPO, capture_output=True, text=True, check=True
    ).stdout
    return [p for p in out.split("\0") if p]


def is_text(path: str) -> bool:
    return Path(path).suffix in TEXT_SUFFIXES or Path(path).name.startswith(".")


def scrub(text: str) -> tuple[str, list[str]]:
    hits = []
    for pattern, replacement, label in SCRUBS:
        text, n = re.subn(pattern, replacement, text)
        if n:
            hits.append(f"{label} x{n}")
    return text, hits


def main() -> int:
    tracked = tracked_files()
    files = [f for f in tracked if f.startswith(KEEP_PREFIXES)]
    dropped = len(tracked) - len(files)

    staged: dict[str, bytes] = {}
    scrubbed: dict[str, list[str]] = {}
    for rel in files:
        raw = (REPO / rel).read_bytes()
        if is_text(rel):
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                staged[rel] = raw
                continue
            text, hits = scrub(text)
            if hits:
                scrubbed[rel] = hits
            raw = text.encode("utf-8")
        staged[rel] = raw

    # The gates, over exactly the bytes that are about to be written.
    failures = []
    for rel, raw in staged.items():
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            continue
        for pattern, label in FORBIDDEN:
            if re.search(pattern, text):
                failures.append(f"  {rel}: {label}")

    if failures:
        print("REFUSING TO BUILD. The archive would have carried:")
        print("\n".join(sorted(set(failures))))
        print()
        print("Add a rule to SCRUBS, or gitignore the file, then run again.")
        return 2

    staged["README.md"] = README.encode("utf-8")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for rel, raw in sorted(staged.items()):
            z.writestr(f"sayswho/{rel}", raw)

    size = OUT.stat().st_size
    print(f"{OUT.relative_to(REPO)}  {len(staged)} files, {size / 1024:.0f} KB")
    print(f"  {dropped} tracked files left out; kept only {', '.join(KEEP_PREFIXES)}")
    if scrubbed:
        print("  scrubbed:")
        for rel, hits in sorted(scrubbed.items()):
            print(f"    {rel}: {'; '.join(hits)}")
    print("  gates passed: no key, no contact address, no home path")
    return 0


if __name__ == "__main__":
    sys.exit(main())
