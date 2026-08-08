# The extension

Manifest V3. Day 2 scope is capture only.

## What it does today

Adds a button to claude.ai, chatgpt.com, perplexity.ai and Google search pages. Clicking it reads the last
answer out of the DOM, extracts the citation markers and their URLs, hashes the answer text, and downloads a
capture JSON that the harness can read:

```bash
python3 -m sayswho.cli ~/Downloads/sayswho/capture-claude-20260807T120000.json
```

## What it does not do

No marking, no verdicts, nothing on screen that claims a citation holds up. Phase 1 and Phase 3 arrive on
day 3, and a marking UI built before there is anything behind it would be exactly the finding-shaped output
this project exists to refuse.

## Loading it

```bash
open -a "Google Chrome" --args --load-extension="$PWD/extension" --user-data-dir=/tmp/sayswho-profile
```

That uses a throwaway profile, so it will not touch your real Chrome and you will not be signed in to
anything. To use it against a logged-in session, load it at `chrome://extensions` with developer mode on and
point it at the `extension/` directory.

## The selectors are not verified

Every adapter in `src/adapters.js` carries `verified: false`, and that flag is written into every capture the
extension emits. None of them has been run against the real logged-in page yet.

This is the failure mode worth understanding before trusting any number that comes out of a capture. If a
selector misses the citation markers, the pipeline sees an answer with fewer citations than it had. G0 may
still pass. The support rate then gets computed over a subset of the answer, and nothing downstream looks
wrong, because a capture bug does not announce itself. It just makes the number quietly incorrect.

Verifying an adapter means opening the product, capturing a real answer, and checking by eye that the
captured text and the citation list match what is on screen. Only then does `verified` become `true`, and the
commit that flips it should say what was checked.

Until then, treat captures as structurally correct and substantively unconfirmed.

## Permissions, and why each one is here

| Permission | Why |
|---|---|
| `storage` | The API key and cached verdicts, from day 3 |
| `downloads` | Writing the capture JSON so the harness can read it |
| Host permissions on the four products | Reading the rendered answer |
| `optional_host_permissions: <all_urls>` | Fetching cited sources from day 3. Optional and requested at the point of use rather than granted at install, because a blanket read-any-site permission asked for up front is a lot to hand over for a tool you have not tried yet |

## Stored pages

Every capture also downloads the page as it stood, next to the capture JSON:

```bash
python3 -m sayswho.reextract ~/Downloads/sayswho-page-claude-20260808T000132.html --capture ~/Downloads/sayswho/capture-claude-2026-08-08T0001320000.json
```

That re-runs container selection and citation extraction over the same bytes. A selector fix no longer means
reloading three tabs and capturing again, which matters for a reason beyond convenience: re-capturing
re-runs the query, so the answer can change between attempts and a selector fix and an answer change arrive
together with no way to tell them apart.

**What re-extraction recovers:** citations, the container choice, the structure. All of it comes from the
markup.

**What it does not:** the answer text. The extension reads `innerText`, which depends on layout and
stylesheets a stored HTML file does not carry. Re-extraction reports citations and leaves the captured text
alone, rather than producing a slightly different text that would quietly disagree with the capture it came
from.

**These files stay on your machine.** A full claude.ai page carries the sidebar, and therefore the titles of
every other conversation, which are real queries from real work. `.gitignore` keeps them out and
`DATA_CONTRACT.md` §9 is the reason.

## Parity

`src/capture.js` computes sha256 over the UTF-8 bytes of the answer text, exactly as `sayswho.records.sha256`
does. The Python loader recomputes it and rejects any capture whose recorded hash does not match its text.

That is the beginning of the §9 parity check rather than the whole of it. Identical hashing proves the two
sides agree about what the input was. Proving they agree about the verdict needs the judge, which is day 3.
