# Card: six ways a citation audit goes wrong

One page. Each failure mode is one you will actually meet, with the signal it gives, what it means, and what
to do. Full walkthrough in [`audit-citations.md`](audit-citations.md).

The rule that governs all six: **a result the tool could not measure never becomes a result against the
product.** Five of these six look like "the citation failed" and only one of them is.

---

## 1. The source could not be read

**Signal.** `SOURCE_DEAD_LINK`, `SOURCE_BOT_BLOCKED`, `SOURCE_UNREACHABLE`, `SOURCE_PAYWALLED`,
`SOURCE_EMPTY`, `SOURCE_NOT_HTML`, `SOURCE_ROBOTS_EXCLUDED`, `SOURCE_DRIFTED`.

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

**Do.** Read the per-claim verdicts, which all still stand. To lift the first, label a gold set:
`python3 tools/label_goldset.py --split ... --out ...`.

**Watch for.** This is the tool working. An absent number invites a reader to compute their own, so each
refusal prints its reason where the number would have been.

---

## The one-line version

`SUPPORTED` means a script confirmed a real sentence on the real page backs the claim. Everything else on
this card means the tool could not establish that, and only mode 2's opposite (a clean read, a live page, a
verified span, and still no support) is evidence against the citation.
