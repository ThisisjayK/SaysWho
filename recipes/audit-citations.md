# Recipe: audit the citations in an AI answer

Nine sections. Everything you need to take one cited answer from a browser tab to a per-claim record you can
act on, and to know what that record does and does not entitle you to say.

The short version of the argument: a footnote signals verification while performing none of it. This recipe
performs it, and stops where the evidence stops.

Companion card for quick reference: [`audit-citations.card.md`](audit-citations.card.md), six failure modes
and what each one means.

---

## 1. What this produces

For one AI answer, a record of every factual claim it made, every source it cited for that claim, and one of
five outcomes per claim:

| Shown as | Means |
|---|---|
| Supported by the cited source | A passage from the cited page was quoted and a script confirmed it is really there |
| Not supported by the cited source | The page was read and does not state this, or states something incompatible |
| Sources disagree | One cited source supports it and another does not. Both shown, neither averaged |
| Could not verify | No verdict stands. The source was unreadable, or the verdict was thrown out |
| No citation to check | The answer attached no source to this sentence |

Plus counts, the sources that could not be read and why, and the lines the splitter skipped.

**No overall score.** Not withheld for tidiness: an answer with three unreadable sources out of six has no
honest percentage, and a tool that prints one anyway has converted missing data into a clean result. See §7.

## 2. When to use this, and when not to

Use it when you are about to put something from an AI answer into a document other people will act on, and
the answer came back with footnotes. It tells you which two of the six footnotes to go read, so your fifteen
minutes go where the risk is.

Do not use it for:

- **Answers with no citations.** Gate G0 halts. An uncited answer is a different object, not a zero percent one.
- **Deciding whether a claim is true.** It checks whether the cited page says what the answer says it says. A
  claim can be perfectly true and cited to the wrong page, and it can be false and faithfully cited to a page
  that is also wrong.
- **Ranking products.** One answer is one answer. The sample sizes here do not support a comparison.
- **Anything behind a login.** No authenticated fetches, ever. See `DATA_CONTRACT.md` §3.

## 3. Before you start

- Python 3.11 or newer, for `tomllib`.
- Chrome or a Chromium browser, for the extension.
- An API key for the judge, if you want verdicts rather than just liveness. Gemini's free tier is the
  default and costs nothing: `export GEMINI_API_KEY=...`. `SAYSWHO_JUDGE=anthropic` with `ANTHROPIC_API_KEY`
  switches to Claude. Both satisfy the same protocol, so nothing else changes.

Load the extension: `chrome://extensions`, developer mode on, "Load unpacked", pick the `extension/`
directory. It runs on claude.ai, chatgpt.com, perplexity.ai and Google search result pages.

Click the toolbar icon once. The popup tells you whether the audit server is running and whether this page
is one SaysWho understands, which is faster than finding out by clicking Audit and waiting.

## 4. Capture the answer

Ask your question in the product as you normally would. When the answer is finished, click the SaysWho
button.

The capture scrolls the answer into existence first, because a long answer is not fully in the DOM until it
has been on screen, and a capture that is quietly short produces a rate over part of the answer while looking
entirely normal. It then reads the answer text, pulls out the citation markers and their URLs, hashes the
text, and downloads two files to `~/Downloads/sayswho/`: the capture record, and the page it came from.

Read the two warnings it can print. `capture_is_known_incomplete` means the page showed citations or text
the capture could not reach, and anything downstream covers part of the answer. A large
`chrome_links_excluded` means the page-furniture filter is eating real citations.

The stored page stays on your machine. A full claude.ai page carries the sidebar, and therefore the titles of
every other conversation you have had.

## 5. Bind it to a query

Skip this if you are auditing an ad hoc answer rather than running a study. Per-claim verdicts work either
way; only rates need the binding.

```bash
python3 tools/bind_capture.py ~/Downloads/sayswho/capture-*.json --list
python3 tools/bind_capture.py ~/Downloads/sayswho/capture-chatgpt-20260812T101500.json --query PR-07
```

Binding refuses a query id that is not in the freeze manifest, and re-verifies the answer hash on the way in,
so binding cannot be the moment an edited answer slips through. Without a binding the audit still runs and
the run says `CAPTURE_UNBOUND` next to every rate it withheld, because a rate has to be able to say what it
is a rate over.

## 6. Run the audit

**The short path.** Start the server once, in a terminal:

```bash
python3 -m sayswho.server --judge
```

Then click the magnifier on the answer, or Audit in the popup. The marked result appears in a panel over the
page, and the capture is written to `captures/` by the server, which is where the harness reads them from.
If the server is not running you are told that, rather than told the audit found nothing, and the capture is
downloaded instead so nothing is lost.

**The long path**, which needs nothing running and is what the honest run uses:

```bash
python3 -m sayswho.cli ~/Downloads/sayswho/capture-chatgpt-20260812T101500.json \
  --judge --report report.html
```

What happens, in order:

1. **The freeze check.** If the query set on disk has moved since it was frozen, the run stops. A tuned
   benchmark is the failure mode this exists for, and it applies to the author as much as anyone.
2. **G0.** No citations, no audit.
3. **Fetch.** One request per second per domain, `robots.txt` respected, an identifying User-Agent with a
   contact address, everything cached to disk so a rerun audits the same bytes. Each source gets one of
   seven outcomes, only one of which lets it proceed.
4. **Drift.** Each page is compared against its nearest archived snapshot. A page with no snapshot is
   recorded as unknown, never as unchanged.
5. **G1, claim splitting.** Model inference, labelled as such everywhere it appears. Skipped lines are
   counted and listed, never dropped.
6. **G3, the judge and the span guard.** The judge is never called on a source that is not readable. To say
   SUPPORTED it must quote the page verbatim, and `str.find` then confirms the quote is there. A quote that
   is not there voids the verdict and is counted as `JUDGE_FABRICATED_SPAN`.
7. **G4.** No gold set for this judge, this prompt version and this split means no aggregate rate. Per-claim
   verdicts still emit.

To run over a whole frozen stratum instead of one answer, use `tools/run_stratum.py`, which writes the run
record, the metric readout, `RUN_LOG.md` and the per-number trace table.

Add `--save-split runs/PR-07.split.json` if you plan to label a gold set. Phase 1 is a model call and does
not return the same split twice, so a stored split is what makes a label mean anything later.

## 7. Read the output

Open `report.html`, or hover a marked sentence in the extension's viewer. Both go through the same renderer,
which computes nothing: every state was decided in Python and there is a test that runs the real renderer in
node and compares what appeared on screen against what Python decided.

Three things to read first.

**The unreadable sources.** These are excluded from every denominator, by a contract check that raises
rather than warns. If most of the answer's sources were unreadable, the run prints `INSUFFICIENT_EVIDENCE`
and no rate at all.

**The voided verdicts.** A voided verdict is not a weaker verdict, it is no verdict, and it leaves the
numerator and the denominator together. `EXTRACTION_SUSPECT` in particular means this tool's own reader
probably failed, not the citation.

**The skipped lines.** Two counts, always printed together: blocks, which is what the splitter returns, and
units, which counts table rows and sentences. A table arrives from the DOM as one block, so one skip decision
can discard ninety checkable cells. The gap between the two numbers is the thing to look at.

## 8. What this does not tell you

Stated here because the tool's own output is easy to over-read.

- **Whether the claim is true.** Only whether the cited page supports it.
- **Whether the source is any good.** A blog post and a randomised trial are the same object to this tool.
- **What the answer left out.** Omission is invisible to it. The uncited-claim count is a floor with a
  measured gap under it, not a total.
- **Whether an unsupported claim is the product's fault.** It may be a citation attached to the wrong page,
  a page that changed, or this tool failing to read something.
- **Anything at all from a single answer's percentages.** Every rate ships with its n and an interval, and at
  these sample sizes the honest reading is directional.

## 9. When it goes wrong

Six failure modes and what to do about each are on the companion card. The three you will hit first:

**Everything came back `NOT_FOUND_IN_SOURCE`.** Usually the extractor, not the answer. Check for the thin-page
flag and for `SOURCE_NOT_HTML`. `python3 -m sayswho.reextract <page.html> --capture <capture.json>` re-runs
extraction over the stored bytes without re-running the query.

**The run refuses to print a rate.** That is a gate, and the message says which one. `NO_CALIBRATION` needs a
gold set; `INSUFFICIENT_EVIDENCE` means most of the answer was unreadable; `CAPTURE_UNBOUND` needs §5.

**The freeze check fails.** Something in `queries/` changed after it was frozen. `python3
tools/freeze_queries.py check` names the query. Breaking a freeze on purpose takes `--force --reason` and is
recorded permanently in the manifest.
