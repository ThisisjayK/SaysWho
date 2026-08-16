# SaysWho

<p align="center">
  <img src="docs/bird-letter.svg" width="200"
       alt="A pastel pink bird hovering in place, wings beating, a letter held in its legs">
</p>

AI search tools cite their sources. Nothing in the pipeline checks whether those sources say what the answer
claims they say. SaysWho is a Chrome extension and a Python auditor that does the checking, one claim at a
time, against the page that was actually fetched.

Note: this is a graduate capstone, not a product. It is independent work and is not affiliated with Anthropic,
OpenAI, Google or Perplexity. Their sites are named only because they are what it reads.

## What it does

Point it at an answer with footnotes. It splits the answer into individual factual claims, fetches every cited
page, and marks each claim with one of six states:

| What you see | What it means |
|---|---|
| Supported by the cited source | A passage from the page was quoted, and a script confirmed it is really there |
| Partly supported by the cited source | The page supports a weaker version of it. What it attaches that the claim does not is listed with the quote: "association, claim says reduction", "US subgroup only" |
| Not supported by the cited source | The page was read and does not state this, or states something incompatible with it. That is a statement about the citation, not about the world: the claim may be true and cited to the wrong page |
| Sources disagree | One cited source supports the claim and another does not. Both are shown and neither is averaged |
| Could not verify | Dead link, paywall, scan, or a page that changed since the answer was written. No verdict stands, and this is not evidence for or against the claim |
| No citation to check | The sentence carries no citation |

"Could not verify" is never counted as unsupported and never enters the denominator of a published rate.
Uncited claims are reported separately, because this tool cannot tell whether they needed a citation.

To return `SUPPORTED` the judge has to quote the span from the fetched page that justifies it. A script then
confirms by string match that the span really is in the document. A span that is not there voids the verdict.
There is no confidence score anywhere in the system, and a test enforces that.

## How it works

```
  Capture                  Audit                      Read
  (extension)              (Python)                   (panel or report)
       |                        |                          |
  scroll the answer        fetch every cited URL      each claim marked
  into the DOM             under DATA_CONTRACT.md     where it sits
       |                        |                          |
  extract the text         split it into claims       rates carry an n
  and citation URLs             |                     and an interval,
       |                   judge each claim           or a gate withholds
  hash it, save the        against its source         them
  capture and the               |
  page bytes               check the quoted span
                                |
                           apply gates G0 to G4
```

Capture works on its own with nothing installed. Verdicts need the Python side running, because the gates, the
claim splitter and the span check have one implementation and it is not in JavaScript.

## Requirements

| What | Why | Notes |
|---|---|---|
| Chrome or a Chromium browser | The extension is Manifest V3 | Loaded unpacked, no store listing |
| Python 3.11 or newer | `tomllib` is used to read the frozen query files | Standard library only for fetch, extraction and gates |
| A judge API key | Only the judge calls a model | `GEMINI_API_KEY` by default, free tier at aistudio.google.com |
| `google-genai` | The default judge client | The only install needed for a normal run |
| `anthropic` | Alternative judge | Optional, only if you pass `--judge-provider anthropic` |
| Node | The extractor parity test runs the extension's own code | Optional, tests only |

Nothing else is a dependency. The fetch, extraction, re-extraction and gate layers are standard library on
purpose, so the parts that decide what a page says have nothing to hide behind.

## Install

### 1. Clone

```bash
git clone https://github.com/ThisisjayK/SaysWho.git
```

### 2. Load the extension

Open `chrome://extensions`, turn on Developer mode, click Load unpacked, and pick the `extension/` folder
inside the clone. Then open an answer on claude.ai, chatgpt.com, perplexity.ai, or a Google search with an AI
Overview. Two round buttons appear at the bottom right. Hover them to see what they do.

That is the whole install for Capture. It saves the answer text, the citation URLs and the page bytes, with
the answer hashed so a later audit can prove it is reading the same answer.

### 3. Start the auditor, if you want verdicts

```bash
python3 -m venv .venv && .venv/bin/pip install google-genai
export GEMINI_API_KEY=...
.venv/bin/python -m sayswho.server --judge
```

The server listens on `127.0.0.1:8765` and nothing else. The extension's second button posts a capture to it
and draws the result in a panel over the page. If it cannot build a judge it refuses to start and says which
of the two problems it hit, rather than starting and failing an hour into a run.

Click the toolbar icon for a status panel: whether the server is up, whether it has a judge, whether the
current page's adapter has ever been checked against a real page, and what the last capture found. The in-page
buttons can be turned off there if you would rather not have an overlay on someone else's product.

## Commands

Everything below runs from the repo root with the virtualenv's Python.

| Command | What it does |
|---|---|
| `python3 -m sayswho.cli <capture.json>` | Re-verify the hash, refuse an answer with no citations, fetch every cited URL, record a fetch outcome per source |
| `python3 -m sayswho.cli <capture.json> --judge` | The above, plus split into claims, judge each one, check every span |
| `python3 -m sayswho.cli <capture.json> --report out.html` | Write a standalone report: the answer with each claim marked, next to the source's own words |
| `python3 -m sayswho.server --judge` | Loopback audit server on port 8765, which is what the extension's Audit button talks to |
| `python3 -m sayswho.reextract <page.html> --capture <capture.json>` | Re-run extraction over the stored bytes and compare it to what the extension produced |
| `python3 tools/run_stratum.py --captures captures/ --judge --out runs/today` | Audit every capture bound to a frozen query, writing the run record, the metric readout, `RUN_LOG.md` and a trace table |
| `python3 tools/freeze_queries.py check` | Verify no frozen query was added, removed or edited. Runs before any capture run |
| `python3 tools/bind_capture.py <capture.json> --query CO-07` | Bind a capture to the frozen query that produced it. `--list` shows every binding, `--in-order` pairs a batch against a stratum |
| `python3 tools/prep_goldset.py --split splits/*.json` | Warm the fetch cache and report what a labelling session will involve, before any labels exist |
| `python3 tools/label_goldset.py --split splits/*.json --out goldset/mine.gold.json` | The hand-labelling session that a judged rate is calibrated against |

Useful flags on `sayswho.cli`: `--split-only` writes the claim split and no verdicts, which is how a gold set
gets built without seeing the judge's answers first. `--split` reuses a stored split so a rate is computed
over the same claims a human read. `--goldset` attaches labels. `--dump-skipped` prints every line the
splitter dropped with its reason. `--check-existence` looks up named but unlinked citations in Crossref, for
existence only and never for support.

## Configuration

| Variable | Effect |
|---|---|
| `GEMINI_API_KEY` or `GOOGLE_API_KEY` | Key for the default judge |
| `ANTHROPIC_API_KEY` | Key for the alternative judge, read by the Anthropic client |
| `SAYSWHO_JUDGE` | Judge provider, `gemini` or `anthropic`, same as `--judge-provider` |
| `SAYSWHO_GEMINI_MODEL` | Override the Gemini model id |
| `SAYSWHO_MODEL` | Override the Anthropic model id |

A judge is swappable by writing a new client against the same protocol. The gates are not, and a provider that
needs the span guard relaxed to pass is the wrong provider.

## Repo layout

```
SaysWho/
├── extension/              # Manifest V3 extension: capture, audit button, panel, popup
│   └── src/
├── sayswho/                # The Python package
│   ├── cli.py              # Audit one capture
│   ├── server.py           # Loopback audit server for the extension
│   ├── fetch.py            # Fetching, under the rules in DATA_CONTRACT.md
│   ├── extract.py          # HTML to text
│   ├── pdf.py              # PDF text layer
│   ├── reextract.py        # Re-extraction and parity against the extension
│   ├── claims.py           # Splitting an answer into claims
│   ├── judge.py            # Judge protocol and prompt, provider agnostic
│   ├── gemini.py           # Default judge client
│   ├── model.py            # Alternative judge client
│   ├── gates.py            # G0 to G4, the refusals
│   ├── rates.py            # Aggregation, and the rules on what may not be aggregated
│   ├── goldset.py          # Labels, agreement, kappa
│   └── harness.py          # Run records, readout, trace table
├── tools/                  # Query freezing, binding, labelling, stratum runs, break attempts
├── tests/                  # 803 tests, offline except the node parity check
│   └── parity/
├── queries/                # The frozen query strata
├── captures/               # Captured answers
├── splits/                 # Stored claim splits
├── goldset/                # Hand labels
├── runs/                   # Run records and readouts
├── recipes/                # How to actually use it
├── SCOPE.md                # The design document
├── DATA_CONTRACT.md        # What may be fetched, stored and published
├── FINDINGS.md             # What has been observed, at the sample sizes observed
├── BREAK_ATTEMPTS.md       # Attempts to break it, including the two that worked
├── STATUS.md               # Every core and stretch item, done or not done, with a reason
└── TODO.md                 # The working list
```

Start with [`recipes/audit-citations.md`](recipes/audit-citations.md) and the one page card of
[six ways it goes wrong](recipes/audit-citations.card.md).

## What it cannot do

It checks whether a source says what the answer claims it says. It cannot check whether the source is true, so
a well cited falsehood passes clean. That limit is not fixable inside this design.

It is blind to omission. An answer can score well by citing its safe sentences and leaving the risky ones
bare, and 42 of the 158 claims in the run described below carry no citation at all.

It cannot tell a peer reviewed paper from a blog post. Both are a page with text on it as far as the fetcher
is concerned.

An unreachable source makes a claim "Could not verify" rather than unsupported. That is a deliberate refusal
to turn our own fetch failure into somebody else's citation failure, and it means the could-not-verify rate
measures this tool's access as much as anything about the answer.

It does not mark the product's own sentences in place. The reason is in `extension/README.md`.

## Where the numbers stand

The pipeline has run end to end twice. Over 24 Perplexity answers it published no support rate at all, because
the gold set covered 4 of the 24 splits and gate G4 will not publish a rate it cannot calibrate. Over 10
ChatGPT answers, with 45 hand-labelled pairs behind it, the gate opened and per-answer and per-domain rates
printed for the first time.

**The most useful number the second run produced is the one about the tool itself.** Checked against 35 blind
human labels, the judge agrees at a Cohen's kappa of 0.304, 95% CI 0.004 to 0.604. The lower bound does not
exclude chance, so that is a wide-interval estimate rather than a calibration, and it should be read as a
reason to distrust individual verdicts. It agrees best on "the page does not say this", 77.3% precision and
recall over n=22, and worst on "the page partly says this", 16.7% precision over n=6.

The stratum rate is still withheld, now because one answer of the ten had more than half its cited claims
unreadable, and an aggregate over the rest would be an aggregate over whichever answers happened to be
measurable. The withheld rate is the intended behaviour rather than a bug to route around.

One limit on all of it: ChatGPT hides part of its citation list behind "+N" controls the DOM never renders, so
those ten answers yielded 33 citations with at least 20 more missing, a floor of 37.7%. Every rate above is
over inline-rendered citations rather than over the product's citations, and the direction of that error is
against the product. `FINDINGS.md` item 23.

`FINDINGS.md` records what has been observed and at what n, `STATUS.md` lists every item done and not done
with a reason, and both of them are more current than this section.

Two known limits on the sample: the questions in the frozen consumer stratum were written rather than asked by
a real user, and every rate produced from them says so in its own header. The professional stratum, which was
to be transcribed from real work sessions, is reported not done, because the sessions are gone and retyping
the questions from memory would have made a published sentence false.

## Context

A graduate capstone at Northeastern University, for a course on computational skepticism: the practice of
checking whether a system does the thing it says it does. Applying that to this tool is the assignment, which
is why the limits above are in the README rather than in a footnote at the end.
