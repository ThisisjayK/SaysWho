# Findings so far

Observations from building the tool, before any measured run.

**Every entry here is n equals one.** These are things seen while making the pipeline work on real answers,
not results. The honest run on the frozen query set is day 7, and nothing below survives into the writeup as
a rate. They are recorded now because they arrived earlier than the schedule expected them to and would
otherwise be lost in commit messages.

## 1. A research report can name fifteen sources and link one

Claude Research, breast cancer screening market in Boston, 2026-08-07. The report ran to 20,288 characters
and cited by name throughout: "LeClair et al., *Supportive Care in Cancer*, 2022", "Rajabiun et al.,
*Cancer*, 2025;131(1):e35671", "published in *Nature Health* (Nov 2025)", "clinicaltrials.gov NCT03514433".

Exactly one of them was a hyperlink.

The claims attached to those names are the checkable kind: a 78% mortality difference, an adjusted odds
ratio of 2.06 with a confidence interval, a cost of $979 to $1,759 per patient.

`SCOPE.md` §7 anticipated omission, meaning sentences with no citation. This is the opposite shape. The
sentence *is* cited, in a form a person can follow and a script cannot. A named citation does more
rhetorical work than a footnote, because it carries an author and a journal and a year, and less of it can
be checked, because there is nothing to fetch.

Detection is built (`CITATION_NOT_LINKED`, nine found on that report against one link) and reports a floor
rather than a total. Resolving those names to papers is deliberately not built: choosing a paper nobody
pointed at and judging a claim against it would be inventing the evidence.

## 2. Perplexity renders citations a script cannot resolve

Same question, Perplexity, 2026-08-07. The answer text showed 11 source chips. Eight had anchors. Four
(`uspreventiveservicestaskforce`, `massgeneral`, `bidmc`, `triagecancer`) had no href in the DOM at all.
Six additional "+1" controls each hid at least one more source behind a click.

Roughly a third of the visible citations were not links.

Not yet diagnosed. Whether those chips hold their URL somewhere unreached, or only after a click, changes
whether this is an implementation gap or the same finding as item 1 in a different form.

## 3. On a real report, the auditable claim count was zero

Running the day 2 pipeline over the Claude report above:

```
named, unlinked  9 sources named in prose with no URL
G0 passed        1 citations, 1 unique URLs
  SOURCE_UNREACHABLE   403   https://aacrjournals.org/cebp/article/32/12_Supplement/A039/...
auditable        0 of 1 sources
unauditable      1, excluded from every denominator
```

The single link returned 403. Nothing in the document was auditable.

Two caveats that matter more than the result. The 403 is very likely bot detection rather than a broken
link, so a person clicking it would probably see the page: `SOURCE_UNREACHABLE` currently collapses "this
citation is broken" and "this citation is unreadable to anyone automated", and those are different findings.
And this is one report, chosen because it was open, not sampled.

## 4. The span guard is narrower than the scope document claimed

Written on day 3 while testing break attempt 5. `SCOPE.md` §6 said the guard would "contain the blast
radius" of a prompt injection. Building it showed the containment splits cleanly in two.

An injection that **orders a verdict without naming evidence** is caught. The judge obeys the page, invents a
span to justify the verdict, and the substring check voids it.

An injection that **dictates the span** is not caught, and the reason is structural rather than a bug to fix.
Writing a span into the instruction puts that span on the page. The guard tests presence; the attacker
controls the page; so the attacker can always satisfy presence. No substring check survives this.

The same hole exists without any adversary: a judge can quote a real but irrelevant sentence and call it
support. The guard checks presence, never relevance.

So the guarantee is not "the judge cannot invent its evidence." It is "the judge cannot invent evidence the
page does not contain." Against an adversarial page those are different sentences. The writeup uses the
second one, and the gold set is what measures the gap between them.

This was found because a test written to assert the guard *worked* failed. Both cases are now pinned by
tests, including the one that fails by design and is kept rather than fixed.

## 5. The drift check flags reference lists as drift

First live judged run, day 3, over a ChatGPT capture. One of nine sources came back `SOURCE_DRIFTED` at
containment 0.6210 and was excluded from the denominator. It should not have been.

The source is a PubMed abstract. Comparing the archived and live extractions directly: the archive held
10,153 characters, the live page 6,575, and the 498 missing 5-grams are all from the **Similar articles** and
**Cited by** blocks. Author names, DOIs, publication dates of *other* papers. The abstract itself, which is
the only part a claim would ever cite, is unchanged.

So the drift check measured the page's furniture rather than its content, and a false `SOURCE_DRIFTED`
removes a genuinely auditable source from every rate. This inflates the unauditable rate and deflates the
denominator, in the direction that flatters the tool's headline caution while hiding a real miss.

The containment metric was chosen to tolerate a page that *grew* (§6 of `DATA_CONTRACT.md`). This is the
opposite case: the page shrank, and what it shed was noise. Any site with a "related content" block will
behave this way.

**Fixed the same day.** Page-level containment stopped being a gate. It now answers only "is this still the
same document", at a threshold near zero rather than near one. Whether a change mattered became a per-claim
question: after the span guard confirms the judge's span is on the live page, the span is checked against the
archived copy too, and a span that postdates the answer voids the verdict as `SPAN_ADDED_AFTER_GENERATION`.
The model cannot have read it, so it is not evidence about that answer.

The reference-list case is now a regression test, with the real PubMed authors in it.

**Confirmed against live data on 2026-08-07**, re-running the same capture. PubMed came back
`DRIFT_PAGE_CHANGED` at containment 0.6210, the same number that used to exclude it, and stayed auditable.
Auditable sources went from 6 of 9 to 7 of 9. A passing test is not a run, so this is the run.

## 6. Most sources have no archived snapshot at all

Same run: five of six readable sources returned `DRIFT_NO_SNAPSHOT`. The Wayback Machine simply has nothing
near the generation timestamp for ordinary `mass.gov` and hospital pages.

Reported as unknown rather than as unchanged, which is the correct behaviour, but it means the drift check is
mostly unable to run on this kind of source. Whatever drift rate the writeup reports will be over a small and
non-random subset: the pages popular enough to be archived. That is a coverage limitation and belongs beside
the number.

## 7. Three silent-shortfall bugs in one day of building

Unrendered text, citations hidden behind a "+N" control, and a stale content script. Each produced a capture
that parsed cleanly, carried a plausible citation count, and was wrong. None announced itself.

All three were caught by comparing two sources of truth against each other: `innerText` against
`textContent`, chip count against anchor count, a capture against what was on screen. None was caught by
looking at the output and judging whether it seemed right.

That is the same failure this project exists to catch, appearing in the tool built to catch it. It is a
better argument for the span guard than any explanation of the span guard.

## 8. The claim splitter is not deterministic, and the skip count moves

The day 3 run split a ChatGPT answer into 20 claims and 139 skipped lines. Re-running Phase 1 over the byte
identical capture, same `answer_sha256`, same judge, same pinned model, same `claims-v1` prompt, returned 20
claims again and 119 skipped lines.

**Corrected after a third run.** This entry originally said the kept side was stable and only the skip count
moved. That was two data points and it was wrong. The third pipeline run returned 15 claims, and a five-run
Phase 1 spread (`tools/split_spread.py`) settled it:

| | min | max | spread | mean | stdev |
|---|---|---|---|---|---|
| claims | 15 | 21 | 6 | 18.2 | 2.9 |
| skipped | 104 | 156 | 52 | 112.2 | 13.4 |
| uncited | 0 | 9 | 9 | 5.6 | 3.9 |

Eight splits in total, one answer, one judge, one prompt version.

Phase 1 never sees a source document, only the answer text and the citation markers, so none of this is a
side effect of the extraction work in item 11. It is the splitter alone.

`uncited_claim_count` is the worst of the three. `SCOPE.md` §7 offers it as the evidence for how much
omission blindness there is, and across eight runs of the same answer it ranged from zero to nine. A single
run reporting zero would have read as "this answer cites everything it asserts".

So none of these are properties of the answer. They are properties of one splitting run over that answer, and
§3 publishes all three. Any rate derived from a split now carries the number of splits it is over.

Worse for day 5: the gold set is labelled against one split. Claim ids are positional, `#001` through
`#0NN` in splitter order, so `#009` in one run and `#009` in the next are not the same sentence. A gold set
labelled by id against a re-derived split would not merely lose claims, it would silently relabel them. The
gold set has to be pinned to a stored split and judged against that stored split, whatever unit the support
rate settles on.

**Pinning also separates two kinds of variance that were previously compounded.** With the split stored and
re-used, two runs over the same 20 claims and the same 7 sources produced 18 judgements each, identical in
aggregate (4 supported, 7 not-found, 6 partial, 1 fabricated span) and differing on two individual
claim-source pairs. So the judge moves too, and much less than the splitter does.

Before pinning there was no way to tell those apart: a changed number could have been the split or the
judge. That matters for day 5, because the kappa is supposed to measure the judge, and an unpinned split
would have folded splitter variance into it.

Also found on the way: the run published the skip count and discarded the skipped text, so this could not
have been checked at all. Fixed with `--dump-skipped`, and the split is now carried in the `--json` record.

## 9. Gate G1 skips by form rather than by content, so one skip can discard ninety claims

Reading the 119 lines, roughly a third are unarguable furniture: 24 headings, five Google Maps cards that
rode along in the DOM complete with star ratings and phone numbers, a "Give feedback" control, the arrow
blocks of a journey map, and the closing source list.

Two things in the remainder are not furniture.

**Tables are skipped whole.** One skipped line is the answer's entire competitive matrix: thirteen
capabilities against eight organisations, roughly ninety cells, each asserting something checkable such as
whether BWH offers breast MRI or whether MBCCP transportation assistance is "Strong". It was skipped as
"table data". Five more table rows went the same way.

This breaks the arithmetic the rate is built on. A DOM capture flattens a table into one text block, so the
unit being skipped is a block, and "119 skipped against 20 kept" puts a heading and a ninety cell matrix in
the same denominator. The skip rate does not measure the share of the answer that went unchecked, and until
the unit is fixed it should not be reported as though it does.

**The skip list absorbs uncited claims.** These four were labelled framing or opinion, and each asserts
something checkable about a named organisation:

- "BWH's Comprehensive Breast Health Center provides breast-risk assessment, screening and prevention
  planning, with patient coordinators helping patients through the process."
- "Dedicated breast imaging nurse navigator ... MRI/ultrasound/biopsy"
- "3D mammography ... Saturday availability at some locations"
- "MBCCP is primarily designed around underserved populations."

None carries a citation. Had G1 kept them they would have landed in `uncited_claim_count`, which reported 8.
So that 8 is a floor, not a count, and part of the omission blindness §7 admits to is being absorbed by the
skip list rather than counted by it. The failure mode is quiet in the same way as the others: the number is
published, it looks like a measurement, and it is smaller than the thing it names.

Two claims that were skipped as opinion do state facts, on citywide navigation across six hospitals and on
BIDMC's AI risk estimation, but both restate claims the splitter kept, so no citation went unaudited because
of them.

## 10. The span guard voided a live verdict

Same re-run: one verdict came back `SUPPORTED` and was voided as `JUDGE_FABRICATED_SPAN`, 1 of 9 span-bearing
verdicts. Day 3 was 0 of 7.

Across both runs that is 1 of 16, and it is not a rate. It is recorded because the guard fired on ordinary
output rather than only on the adversarial test written to trip it, which is the first evidence that the
fabricated-span rate §5 promises to publish will not be zero.

## 11. Every way the tool fails to read a page comes out as the same verdict

Asked how the pipeline avoids missing tables, images and PDFs, and the answer turned out to be that mostly it
did not, and that all of the misses converge on one output.

`DATA_CONTRACT.md` §5 said "Readability for HTML, PDFs parsed if a text layer exists". Neither was true.
Extraction was a stdlib `HTMLParser`, and there was no content-type check anywhere in the fetch layer, so a
cited PDF was handed to an HTML parser and whatever fell out was judged. Same shape as the gzip bug in item
7: parses without error, produces plausible output, matches nothing. The contract described a tool that had
not been built, which is the failure this project audits other people for.

Alongside it, `svg` was in the drop list, so chart labels and figure titles were discarded, and `img alt`
was never read at all, so a claim resting on a data visualisation had nowhere to be found.

**The convergence is the finding.** A PDF, a JavaScript shell, a chart, a dropped table: every one of them
produces `NOT_FOUND_IN_SOURCE`. That is the verdict that accuses the product being audited, and because it
carries no span by definition, gate G3 never touches it. So the one verdict with no deterministic check
behind it is also the one every silent failure lands on, and it points outward.

Four mitigations built, all stdlib:

- `SOURCE_NOT_HTML`, decided by `Content-Type` and by a `%PDF-` sniff that runs even when the header
  disagrees. PDFs are now unauditable rather than mis-parsed, which is a worse-looking number and a truer one
- SVG text and `img alt` are extracted. On the real capture this recovered between 25 and 50 characters per
  source, which is small, and it is the difference between a chart's numbers existing and not
- A thin-page flag: over 50KB of markup yielding under 0.002 of it as text. Flag only, never a code
- The extraction check on `NOT_FOUND_IN_SOURCE`: if the claim's own numbers or proper nouns are in the markup
  and absent from the extracted text, the verdict is voided as `EXTRACTION_SUSPECT` and the claim becomes
  unauditable

The last one is deliberately biased and the bias is the point. A false positive costs coverage. A false
negative publishes "the cited source does not support this" when the truth is "we could not read the part
that does". Only the day 5 gold set can measure which way it errs, and until then the mitigation is a
mitigation rather than a fix.

**It did not fire on the first capture it ran against, and checking why narrowed the claim.** All six
`NOT_FOUND_IN_SOURCE` verdicts stood. Running the guard's inputs by hand against the cached pages rather than
assuming that was correct: none of the six was close, because none of the six claims contained a number at
all, and no proper noun in them had been dropped by the extractor. Sentences like "It specifically serves
underserved populations, including eligible uninsured/underinsured Massachusetts residents" carry nothing
distinctive enough for the check to work with.

So the guard has no coverage on qualitative claims, which on this capture was six of six. It defends the
numeric claims, which are the ones a reader acts on, and it leaves prose assertions where they were. Recorded
in `SCOPE.md` §7. The other two guards, `SOURCE_NOT_HTML` and the thin-page flag, had nothing to catch on
this capture either: it cites no PDFs and no page came back suspiciously thin. All three are tested and only
one has been exercised on live data.

**Then it fired twice, and both were wrong.** On the next run, against a stored split, two
`NOT_FOUND_IN_SOURCE` verdicts were voided as `EXTRACTION_SUSPECT`. The claim listed MBCCP services
including case management and transportation assistance. Checking the pages by hand: neither mentions case
management or childcare anywhere, and "transportation" appears only in the site-wide hamburger menu as
`/topics/transportation`. The judge was right, and the guard overrode it.

Two causes, and the first is the embarrassing one:

- **The permissive parser was never wired in.** `extract.raw_text` was written for exactly this comparison
  and then never called: the guard was handed the raw markup instead. So "Case" matched a `switch`
  statement's `case` keyword inside a `<script>`. The function existed, was tested, and was dead.
- **Even wired in, it kept navigation on purpose.** The docstring said the question was "could this have
  been on the page at all", and that framing was wrong. Furniture repeated site-wide is not evidence that a
  particular page's body said anything. `raw_text` now excludes `nav`, `header`, `footer`, `form` and
  `iframe` as well as scripts and styles, and keeps only what a body might plausibly hold: `aside`, SVG
  text, and `alt` and `title` attributes.

The guard against publishing our own silent failures had a silent failure, and it failed in the direction of
suppressing correct findings rather than inventing them, which is the safer direction and still wrong. It was
caught by reading the two voided verdicts rather than by any test, which is the same lesson as item 7: the
output looked reasonable, and only checking the specific pages showed it was not.

One correction fell out of the same pass: `NOT_FOUND_IN_SOURCE` was setting `span_verified = True`, meaning
"nothing to check". Nothing counted it, so no published number was wrong, but a marking interface reading
that field would have put a tick beside the only verdict carrying no evidence at all.
