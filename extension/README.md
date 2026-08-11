# The extension

Manifest V3. It captures an answer, and it renders a finished audit. It does not produce the audit.

## What it does today

Two round buttons sit in the bottom-right corner, side by side. Hovering either one names it.

**Capture** (the viewfinder). Reads the last answer out of the DOM, extracts the citation markers and their
URLs, hashes the answer text, and downloads a capture JSON.

**Audit** (the magnifier). Posts that same record to the local server and draws the result in a panel over
the page, stepping aside so the panel does not open on top of it. No terminal step in the loop:

```bash
python3 -m sayswho.server --judge
```

The capture is downloaded before anything is posted, so if the server is not running the record still
exists and nothing is lost. A server that is not running is reported as a server that is not running, never
as an audit that found nothing.

**Render.** `src/report.html` opens a report JSON and shows the answer with every claim marked. Hovering a
marked sentence gives the cited page's own words, the ones the span guard confirmed are really on that page.

The steps in between, if you would rather run them yourself:

```bash
python3 -m sayswho.cli ~/Downloads/sayswho/capture-chatgpt-20260808T001618.json \
  --judge --report report.html --report-json report.json
```

`report.html` opens in any browser with no extension at all. `report.json` is what the extension's viewer
loads. Both go through `src/render.js`, so the two views cannot disagree.

## What it does not do

**It does not produce verdicts on its own**, and it never will. The fetch layer, the gates and the span
guard are Python and stay Python. Reimplementing them here would create a second implementation of exactly
what the §9 parity check exists to compare, and the two would drift apart under maintenance. `audit.js`
posts JSON and draws what comes back; there is a test asserting it does not so much as mention a verdict
name.

**It does not mark the product's own sentences in place.** The payload carries character offsets into the
answer text, and mapping those onto a live DOM that re-renders as you scroll is separate work with its own
failure modes, the worst of which is putting a verdict beside the wrong sentence. The panel shows the marked
answer next to the page instead.

**Every node is built through the DOM API, never `innerHTML`.** claude.ai enforces Trusted Types, where an
`innerHTML` assignment throws, and the failure would be total: no buttons at all, on the product this was
first screenshotted against. There is a test for it, and the rule applies to anything added later.

**The browser leg is not covered by tests.** The server is, thoroughly, and so are the things about this
package that can be checked without a browser: every file the manifest names exists, every script parses,
the stylesheet cannot restyle the product's page, and the host permission matches the endpoint the code
calls. Whether the panel looks right on claude.ai is not something the suite knows, and `STATUS.md` says so
rather than counting it as working.

## Skipping the terminal step

`tools/install_watcher.sh` installs a launchd agent that audits any new capture and writes its report:

```bash
tools/install_watcher.sh
```

It uses `WatchPaths`, so launchd starts the job when `~/Downloads/sayswho` changes and the job exits when
its queue is empty. Nothing of this project runs between captures: no daemon, no polling loop, no port. A
macOS notification says when a report is ready, and reports land in `~/Downloads/sayswho-reports`.

Remove it with `tools/install_watcher.sh --uninstall`.

Three things worth knowing about it. The key is read from `~/.zshrc` by `run_watcher.sh` rather than written
into the launchd plist, because a plist is a file on disk and `DATA_CONTRACT.md` §8 says the key never goes
into one. Reports are written to a *different* directory than the one being watched, since writing into the
watched directory would retrigger the job forever. And a run that fails is recorded as failed and retried
next time rather than skipped, because a missing report otherwise looks exactly like a capture you forgot to
make.

## Opening the report viewer

Load the extension, then open `chrome-extension://<id>/src/report.html` and pick a `report.json`. The file
is read in the tab and nothing is uploaded.

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
