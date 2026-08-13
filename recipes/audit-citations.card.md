# Card: SaysWho citation audit

The human half of the two-customer pair. The agent-facing recipe is
[`audit-citations.md`](audit-citations.md), and the two are updated in the same commit.

## Purpose

You are about to put something from an AI answer into a document other people will act on, and the answer came
back with footnotes. This tells you which two of the six footnotes to go read, so your fifteen minutes go
where the risk is.

## What it can verify

- That a cited page, as fetched, contains a passage supporting the sentence attached to it. The passage is
  quoted and a script confirms it is really on the page.
- That a cited page could or could not be read at all, in eleven distinct outcomes, so "we could not check"
  is never reported as "the citation failed".
- That a page has changed since the answer was written, and whether the passage a verdict rests on existed at
  the time.
- Which sentences carry no citation at all.

## What it cannot verify

- **Whether the claim is true.** Only whether the cited page supports it. A claim can be true and cited to the
  wrong page.
- **Whether the source is any good.** A blog post and a randomised trial are the same object to it.
- **What the answer left out.** Omission is invisible. The uncited count is a floor.
- **Whose fault an unsupported claim is.** Five of the six failure modes below look like a citation failure
  and only one of them is.
- **Anything from one answer's percentages.** Every rate carries its n and an interval.

## Dependencies

Python 3.11 or newer, for `tomllib`. Chrome or a Chromium browser for the extension. Two optional
judge-only packages, `google-genai` (default, free tier) or `anthropic`. Nothing else in the package imports
either, and the fetch, extraction and gate layers are stdlib only. A judge key is needed only for verdicts:
without one you still get liveness and readability for every cited source.

## Commands

```bash
# start the local audit server, then click Audit in the extension
.venv/bin/python -m sayswho.server --judge

# or audit one downloaded capture with nothing running
python3 -m sayswho.cli <capture.json> --judge --report report.html

# the whole frozen stratum, writing the run record, readout, RUN_LOG.md and trace table
python3 tools/run_stratum.py --captures captures/ --judge --goldset <set> --out runs/day7

# re-read a stored page after fixing a selector, without re-running the query
python3 -m sayswho.reextract <page.html> --capture <capture.json>

# check the query freeze by hand; it also runs automatically before every capture
python3 tools/freeze_queries.py check

# privacy and honesty, shown passing. run_stratum runs this first and refuses to continue if it fails
python3 tools/ethics_gate.py
```

## What it produces

An HTML report and its JSON twin in `reports/`, both drawn by the same renderer so the extension and the
harness cannot disagree. Per claim, one of six states. Per run, the unreadable sources with reasons, the
skipped lines in two units, the uncited floor, and every rate it is entitled to publish with its n and 95%
interval. Where a rate is refused, the refusal appears in the number's place.

Everything it writes stays local: `captures/`, `reports/`, `runs/`, `splits/`, `goldset/` and `.cache/` are
all uncommitted, because they carry answer text and quoted page content.

---

## Failure modes

Six, each one you will actually meet, with the signal it gives, what it means, and what to do.

The rule that governs all six: **a result the tool could not measure never becomes a result against the
product.** Five of these six look like "the citation failed" and only one of them is.

Modes 4 and 6 are the two the contract turns on: 4 is drift, 6 is a contract violation the tool refuses rather
than papers over.

---

## 1. The source could not be read

**Signal.** Any code but `SOURCE_OK`: `SOURCE_DEAD_LINK`, `SOURCE_BOT_BLOCKED`, `SOURCE_UNREACHABLE`,
`SOURCE_PAYWALLED`, `SOURCE_EMPTY`, `SOURCE_NOT_HTML`, `SOURCE_ROBOTS_EXCLUDED`, `SOURCE_DRIFTED`,
`SOURCE_NO_TEXT_LAYER`, `SOURCE_UNREADABLE_ENCODING`.

**Means.** Nothing about the claim. The page was dead, or behind a wall, or a PDF, or a JavaScript shell, or
`robots.txt` asked us not to fetch it and we did not.

Three of these are the same arithmetic and three different sentences. `SOURCE_DEAD_LINK` says the citation
points at nothing, which is a finding about the answer. `SOURCE_BOT_BLOCKED` says the site refused an
automated request, and a person clicking the link would probably see the page, which is not.

**Do.** Nothing automatic. These are `UNAUDITABLE`, they are excluded from every denominator by a check that
raises rather than warns, and they are never counted as unsupported. Open the link yourself if the claim
matters. A paywall is a legitimate outcome, and routing around it would corrupt the measurement.

**Watch for.** `SOURCE_ROBOTS_EXCLUDED` is not `SOURCE_UNREACHABLE`. Unreachable means we tried and could
not; robots-excluded means we chose not to try. Same arithmetic, different sentence to publish. If you are
reporting a dead-link rate, it is `SOURCE_DEAD_LINK` alone, not the union of all six.

---

## 2. We could read the page and read it badly

**Signal.** `EXTRACTION_SUSPECT` on a voided verdict, or the `THIN` flag: a large page that yielded almost no
text.

**Means.** The claim's own numbers or names are in the page's markup and missing from what the extractor
produced. So the verdict is a fact about this tool's reader, not about the source.

**Do.** `python3 -m sayswho.reextract <page.html> --capture <capture.json>` to re-run extraction over the
stored bytes. Fixing the extractor does not need the query re-run.

**Watch for.** This is the most dangerous mode on the card, because untreated it produces
`NOT_FOUND_IN_SOURCE`, the one verdict that accuses the product and the one verdict carrying no span to
check. The guard is deliberately biased toward losing coverage rather than toward accusing. Neither its false
positive nor its false negative rate is known yet.

---

## 3. The judge invented its evidence

**Signal.** `JUDGE_FABRICATED_SPAN`.

**Means.** The judge returned a quote that is not in the document it was given. Gate G3 caught it by
substring match, and the verdict was voided.

**Do.** Nothing. It is counted and published as a rate about the judge rather than fixed quietly. A voided
verdict is not a weaker verdict, it is no verdict, so it leaves the numerator and the denominator together.

**Watch for.** The guarantee is narrower than it sounds. The guard rules out evidence the page does not
contain. It does not rule out a wrong verdict backed by a real but irrelevant sentence, and against a page
that was written to attack it, an injected instruction that dictates its own span puts that span on the page
and satisfies the check. That case is pinned by a test that fails by design.

---

## 4. The page changed after the answer was written

**Signal.** `DRIFT_PAGE_CHANGED`, or `SPAN_ADDED_AFTER_GENERATION` on a voided verdict.

**Means.** The live page differs from the archived copy nearest the answer's timestamp. Drift alone does not
exclude anything: a reference list that churned is still the same document. What voids a verdict is the
narrower fact that the *quoted passage* was not there when the answer was written.

**Do.** Read the verdict as unmeasurable rather than as wrong. The model cannot have read a sentence that did
not exist yet.

**Watch for.** `DRIFT_NO_SNAPSHOT` is not `DRIFT_UNCHANGED`. Most pages have no archived copy near the right
date, and unknown stays unknown.

---

## 5. The answer said something and cited nothing

**Signal.** A claim shown as "No citation to check", or a non-zero `uncited_claim_count`, or
`CITATION_NOT_LINKED` for a source named in prose with no URL.

**Means.** The answer asserted something without attaching a source. It is not unsupported and it is not
unauditable. It is uncheckable, and it enters no denominator.

**Do.** Treat these as the highest-risk sentences in the answer, because nothing anywhere is even claiming to
back them.

**Watch for.** The count is a floor twice over. The splitter also skips lines at G1, and some of those are
factual: the run prints how many skipped units carry a number or two proper nouns, so the floor has a
measured gap under it rather than an unknown one.

---

## 6. The tool refused to give you a number

**Signal.** `NO_CALIBRATION`, `INSUFFICIENT_EVIDENCE`, `CAPTURE_UNBOUND`, or a `ConflictedAggregate` error.

**Means.** In order: no gold set exists for this judge, prompt version and split, so no aggregate rate may be
printed; more than half this answer's claims produced no verdict that stands; this capture is not bound to a
frozen query, so a rate could not say what it is a rate over; or you asked for an aggregate including a
product whose vendor also supplies the judge.

**Do.** Read the per-claim verdicts, which all still stand. To lift the first, label a gold set. Make the
split with `--split-only` so no verdict is in front of you while you label, then
`python3 tools/label_goldset.py --split ... --out ...`. One set may cover several answers; it records the
splits it holds labels for and G4 accepts any of them.

If the tool refuses to start, saying this answer already has a verdict on disk, that is the point: label a
fresh answer, or pass `--supplemental` and accept that those labels are reported on their own and excluded
from the agreement number.

**Watch for.** This is the tool working. An absent number invites a reader to compute their own, so each
refusal prints its reason where the number would have been.

---

## The one-line version

`SUPPORTED` means a script confirmed a real sentence on the real page backs the claim. Everything else on
this card means the tool could not establish that, and only mode 2's opposite (a clean read, a live page, a
verified span, and still no support) is evidence against the citation.
