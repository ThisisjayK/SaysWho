---
status: ACTIVE
todos_open: 0
last_gate: G4
attestation: unsigned
recipe_version: 0.2.0
type: workflow
---

# Recipe: audit the citations in an AI answer

Companion card: [`audit-citations.card.md`](audit-citations.card.md), six failure modes and what each one
means. The two are updated in the same commit.

---

## 1. Executive Summary

A footnote signals verification while performing none of it. This recipe performs it, and stops where the
evidence stops.

For one AI answer, it produces a per-claim record: every factual sentence, every source cited for it, and one
of six outcomes per claim, each traceable to a fetched page. It never produces an overall score. It refuses
to produce a rate it cannot stand behind, and says which gate refused and why.

**Who runs what.** An agent can execute every command here unattended except two: labelling a gold set and
deciding whether an unsupported claim matters. Both are human calls and §9 says where they stop it.

**The one-line version.** It tells you which two of the six footnotes to go read, so your fifteen minutes go
where the risk is.

## 2. Required Reads

Read these before running anything. Where a document and this recipe disagree, the document wins.

| Source | Path | Use |
|---|---|---|
| Data contract | `DATA_CONTRACT.md` | Fetch politeness, caching, what is never fetched, where private data stays |
| Design document | `SCOPE.md` | §0a core-and-stretch split, §3 the phase gates, §4 the verified-inferred boundary, §7 limitations |
| Status | `STATUS.md` | Which parts have run on real data and which have only ever been tested |
| Findings | `FINDINGS.md` | Every bug that changed a published claim, including the ones this tool caused |
| Break attempts | `BREAK_ATTEMPTS.md` | What was tried against it and what held |
| Run log | `RUN_LOG.md` in the run's `--out` directory | What was run, what it produced, what blocked |
| Query freeze | `queries/FREEZE.json` | The hash manifest. A run against a moved query set measures something else |

**Prerequisites.** Python 3.11 or newer, for `tomllib`. Chrome or a Chromium browser for the extension. An
API key only if you want verdicts rather than liveness: `export GEMINI_API_KEY=...` for the free-tier default,
or `SAYSWHO_JUDGE=anthropic` with `ANTHROPIC_API_KEY`. Both satisfy the same protocol, so nothing else changes.

## 3. Phase Gates

Do not move to a later step until the earlier gate has passed. **Every gate here has a failure path, because a
gate with no failure path is decoration.** Each one is enforced in code and has a test that fails on the bug
the gate exists to catch.

| # | Gate | Passes when | Failure path |
|---|---|---|---|
| E | Ethics | Privacy and honesty both pass | The run stops before fetching. `python3 tools/ethics_gate.py` names which check failed and what to do. `tools/run_stratum.py` runs it first and refuses to continue |
| F | Freeze | `queries/FREEZE.json` matches `queries/*.toml` | The run stops before fetching. `python3 tools/freeze_queries.py check` names the query. Overriding takes `--force --reason` and is recorded permanently in the manifest |
| G0 | Citations exist | The answer carries at least one inline citation | Halts with `NO_CITATIONS`. An uncited answer is a different object, not a zero percent one |
| G2 | Source readable | The page fetched, decoded and extracted to usable text | The claim becomes `UNAUDITABLE` and leaves every denominator. Eleven outcome codes, only `SOURCE_OK` proceeds |
| G1 | Claims split | The answer split into claims bound to citation markers | Skipped lines are counted, listed and published, never dropped. `--dump-skipped` prints them |
| G3 | Span verified | The judge quoted the page and a script confirmed the quote is there | The verdict is voided as `JUDGE_FABRICATED_SPAN` and leaves numerator and denominator together |
| G4 | Judge calibrated | A gold set exists for this judge, judge prompt, claim prompt and split | No aggregate rate is printed, the reason is printed where the number would be, and per-claim verdicts still emit |

Two further refusals behave as gates: `INSUFFICIENT_EVIDENCE` when more than half an answer's claims are
unauditable, and `CAPTURE_UNBOUND` when a capture is not bound to a frozen query. Both withhold rates and
neither withholds per-claim verdicts.

## 4. Primary Stored Tools

Prefer these over ad hoc code. If none fits, say so before writing a temporary script.

| Command | Does |
|---|---|
| `python3 -m sayswho.cli <capture>` | The whole pipeline over one capture. Fetch and liveness by default; `--judge` adds Phase 1 and Phase 3 |
| `python3 -m sayswho.server --judge` | The local audit server the extension posts to. Loopback only, origin allowlist |
| `python3 -m sayswho.reextract <page.html> --capture <capture.json>` | Re-run selection and extraction over stored bytes, without re-running the query |
| `python3 tools/run_stratum.py --captures captures/ --out runs/<name>` | The honest run over a whole stratum. Writes the run record, readout, `RUN_LOG.md` and the trace table |
| `python3 tools/bind_capture.py <capture> --query <id>` | Bind a capture to a frozen query. Refuses an id that is not in the manifest |
| `python3 tools/freeze_queries.py check` | The freeze check. Runs before every capture path |
| `python3 tools/ethics_gate.py` | The privacy and honesty gate. Exits non-zero when either half fails, and `run_stratum.py` runs it before the honest run |
| `python3 tools/prep_goldset.py --split <split> --capture <record>` | Warm the cache and report what a labelling session will be, before it starts. Fetches only pages it does not already have |
| `python3 tools/label_goldset.py --split <split> --out <gold>` | Label a gold set by hand. Refuses any file carrying judge output, and refuses to start at all if `reports/` or `runs/` already holds a verdict over the same answer |
| `python3 tools/break_attempts.py --all --judge --out runs/break` | The four stretch break attempts, each declaring its failure mode before it runs |
| `python3 tools/reaudit_spans.py` | Re-check voided spans against cached bytes rather than the live web |
| `python3 tools/compare_capture.py` | How many citations the DOM capture missed, measured against an API capture |
| `python3 tools/split_spread.py <capture>` | Phase 1 only, several times, to measure how much the splitter varies |
| `python3 tools/measure_named_recall.py` | Recall and precision of the named-but-unlinked citation patterns |

**No stored script exists** for two things this recipe needs, and both are human work by design: transcribing
and scrubbing the professional query stratum, and labelling the gold set. §9 stops the workflow at each.

## 5. Workflow

### 5.1 Capture the answer

Ask your question in the product as normal. When the answer is finished, click the SaysWho button.

Load the extension first: `chrome://extensions`, developer mode on, "Load unpacked", pick `extension/`. It
runs on claude.ai, chatgpt.com, perplexity.ai and Google search result pages. Click the toolbar icon once and
the popup tells you whether the server is running and whether this page is one SaysWho understands, which is
faster than finding out by clicking Audit and waiting.

The capture scrolls the answer into existence first. A long answer is not fully in the DOM until it has been
on screen, and a capture that is quietly short produces a rate over part of the answer while looking entirely
normal. It then reads the answer text, pulls out the citation markers and their URLs, hashes the text, and
writes the capture record and the page it came from.

Read the two warnings it can print. `capture_is_known_incomplete` means the page held citations or text the
capture could not reach. A large `chrome_links_excluded` means the page-furniture filter is eating real
citations.

The stored page stays on your machine. A full claude.ai page carries the sidebar, and therefore the titles of
every other conversation you have had.

### 5.2 Bind it to a frozen query

Skip this for an ad hoc answer. Per-claim verdicts work either way; only rates need the binding.

```bash
python3 tools/bind_capture.py ~/Downloads/sayswho/capture-*.json --list
python3 tools/bind_capture.py ~/Downloads/sayswho/capture-chatgpt-20260812T101500.json --query PR-07
```

Binding refuses a query id that is not in the freeze manifest, and re-verifies the answer hash on the way in,
so binding cannot be the moment an edited answer slips through.

### 5.3 Run the audit

**The short path.** Start the server once:

```bash
.venv/bin/python -m sayswho.server --judge
```

That has to be a Python with `google-genai` installed, which the repo's virtualenv has. The server will not
start with `--judge` if it cannot build a judge, and it prints which of the two problems it is. Then click the
magnifier on the answer, or Audit in the popup.

**The long path**, which needs nothing running and is what the honest run uses:

```bash
python3 -m sayswho.cli ~/Downloads/sayswho/capture-chatgpt-20260812T101500.json --judge --report report.html
```

The order of operations is the gate table in §3, top to bottom.

To run over a whole frozen stratum instead of one answer:

```bash
python3 tools/run_stratum.py --captures captures/ --judge --goldset <set> --out runs/day7
```

### 5.4 Produce a split to label against

Only if you are building a gold set. Produce the split on its own rather than as a by-product of a judged run:

```bash
python3 -m sayswho.cli captures/PR-07.json --split-only --save-split splits/PR-07.json
```

Phase 1 is a model call and does not return the same split twice, so a stored split is what makes a label mean
anything later. `--split-only` runs Phase 1 and stops, because the labels have to predate the judge and every
other route to a stored split prints the verdicts on the way past. Then label, then judge that same split with
`--split`, so the rate is over the claims a human actually read.

## 6. Output Contract

Every run emits these and nothing else claims to be a result.

**Per claim**, one of six states, each traceable to a fetched page:

| Shown as | Means |
|---|---|
| Supported by the cited source | A passage was quoted and a script confirmed it is really on the page |
| Partly supported by the cited source | The page supports part of this, or a weaker version. What it attaches that the sentence does not is listed with the quote |
| Not supported by the cited source | The page was read and does not state this |
| Sources disagree | One cited source supports it and another does not. Both shown, neither averaged |
| Could not verify | No verdict stands. The source was unreadable, or the verdict was thrown out |
| No citation to check | The answer attached no source to this sentence |

**Per run**: the sources that could not be read and why, the lines the splitter skipped in two units, the
uncited-claim floor, and every rate the run is entitled to publish with its n, its 95% interval and how many
splits it is over. Beside each rate it did not publish, the reason.

**No score, anywhere.** Not withheld for tidiness: an answer with three unreadable sources out of six has no
honest percentage, and a tool that prints one has converted missing data into a clean result.

**Files written**, relative to where the server or the CLI was started:

| Where | What |
|---|---|
| `reports/report-<product>-<stamp>.html` | The audit. Opens in any browser with nothing running |
| `reports/report-<product>-<stamp>.json` | The same audit as data, for the extension's viewer |
| `captures/capture-<product>-<stamp>.json` | The answer and its citations, hashed |
| `.cache/fetch/` | Every page fetched, so a rerun audits the same bytes |
| `runs/<name>/` | The run record, the metric readout, `RUN_LOG.md` and the per-number trace table |

`captures/`, `reports/`, `runs/`, `splits/`, `goldset/`, `.cache/` and stored pages are all uncommitted by
design. They carry answer text and quoted page content.

## 7. Verification Checks

How to confirm the run did what it says, rather than that it finished.

1. **The unreadable sources.** Excluded from every denominator by a contract check that raises rather than
   warns. If most sources were unreadable the run prints `INSUFFICIENT_EVIDENCE` and no rate at all.
2. **The voided verdicts.** A voided verdict is no verdict and leaves numerator and denominator together.
   `EXTRACTION_SUSPECT` means this tool's reader probably failed, not the citation.
3. **The skipped lines.** Two counts, always together: blocks, which is what the splitter returns, and units,
   which counts table rows and sentences. A table arrives as one block, so one skip can discard ninety
   checkable cells. The gap between the numbers is the thing to read.
4. **The trace table.** Every published figure traced to the record it came from. Generated, not typed.
5. **The suite.** `python3 -m pytest` proves each gate fails on its target bug rather than merely existing.
6. **The ethics gate.** `python3 tools/ethics_gate.py` checks privacy against git rather than against the
   `.gitignore` text, since a rule that exists and does not match is worth nothing. It runs the honesty
   tests rather than citing them. Its output is the artefact the attestation asks for.
7. **Parity.** The extension and the harness are checked against each other by running the real renderer in
   node over a payload the real Python built, and comparing state by state.

## 8. Logging Rules

`tools/run_stratum.py` writes `RUN_LOG.md` into its `--out` directory automatically. Add an entry by hand
whenever you do something the harness did not:

```markdown
## YYYY-MM-DD, short task name

- **Recipe:** audit-citations
- **Inputs:** the commands run and the captures or splits they read
- **Outputs:** files created or updated
- **Result:** what worked, with the numbers it produced
- **Open issues:** what did not work, and what is still blocked
```

Log a run against real data, a created or updated audit, a changed freeze or gold set, a blocker, and a
decision about what not to use. Do not log the query text of a professional-stratum capture, real names, or
any private application detail. Never log an API key.

## 9. Stop Conditions

Stop and hand back to a human when any of these happens. Do not work around them.

- **The freeze check fails.** Something in `queries/` moved after it was frozen. Do not pass `--force` to get
  the run moving; find out what changed.
- **G0 halts.** The answer has no citations. There is nothing to audit and no number to report.
- **G4 refuses a rate.** Report the refusal. Do not compute a percentage by hand from the per-claim verdicts,
  which is the one contamination path no gate can close.
- **`INSUFFICIENT_EVIDENCE`.** More than half the answer was unauditable. The answer is not evidence about the
  product.
- **The budget cap halts the judge.** A claim skipped for quota is a hole in the denominator, not a claim that
  passed. Rerun rather than publishing the partial run.
- **A source needs a login or sits behind a paywall.** `SOURCE_PAYWALLED` is a legitimate outcome. Routing
  around it corrupts the measurement and violates `DATA_CONTRACT.md` §3.
- **The gold set does not exist yet.** No stored script can produce one. Labelling is human work and it has to
  happen before the judge runs.
- **The professional query stratum is empty.** No stored script can fill it. The queries must be real questions
  actually asked, scrubbed by hand, or the limitations argument in `SCOPE.md` §7 becomes false.

## 10. What This Does Not Tell You

Stated here because the output is easy to over-read.

- **Whether the claim is true.** Only whether the cited page supports it.
- **Whether the source is any good.** A blog post and a randomised trial are the same object to this tool.
- **What the answer left out.** Omission is invisible. The uncited-claim count is a floor with a measured gap
  under it, not a total.
- **Whether an unsupported claim is the product's fault.** It may be a citation attached to the wrong page, a
  page that changed, or this tool failing to read something. Five of the card's six failure modes look like a
  citation failure and only one of them is.
- **Anything from one answer's percentages.** Every rate ships with its n and an interval, and at these sample
  sizes the honest reading is directional.
