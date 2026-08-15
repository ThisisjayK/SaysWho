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

## 12. The unit of the rate was never decided, and the two choices give different numbers

`SCOPE.md` §5 said `SUPPORTED / auditable claims` from the day it was written, and I read that sentence
several dozen times without noticing it does not say what an item is. A claim citing three sources: is that
one item or three?

Claim #009 from the day 3 run answers it concretely. It came back `SUPPORTED` by one source and
`NOT_FOUND_IN_SOURCE` by two. Counted in claim-source pairs that is 1 of 3, which reads as mostly
unsupported. Counted in claims, with any supporting source enough, it is 1 of 1, which reads as fully
supported. Same evidence, same run, and the two numbers are as far apart as they can get.

Nothing in the pipeline was wrong. Three judgements existed and nothing combined them, so the number simply
had not been computed yet, and it would have been computed the first time somebody needed a headline figure,
by whichever line of code got there first.

Decided: the unit is the claim-source pair, and it is now pinned by a test rather than by this paragraph. It
is the question the tool asks, and it is the unit a human labels in, so the gold set and the rate count the
same objects. The claim-level rate is published beside it, because the pair unit lets a claim citing five
sources weigh five times as much and a reader is entitled to see what that did.

**The general shape.** An ambiguous denominator does not announce itself. It sits in a specification looking
like a definition until someone tries to compute it, and by then there is usually a number attached to it
that nobody wants to change.

## 13. Verdict-class stratification cannot be done in a blind gold set

`SCOPE.md` §3 Phase 4 asks for the gold set to be stratified across products *and across verdict classes*,
filling `UNAUDITABLE` and `CONTRADICTED` first, because a class the set never contains cannot be calibrated.
That instruction is half impossible and I did not notice until I built the sampler.

The verdict classes are the judge's output. §12 puts the labelling on day 5 specifically so it precedes the
judge run. So stratifying on verdict class requires knowing what the judge said, and a sample selected using
the judge's own output is not a blind sample. The two requirements are in direct conflict and the scope
document asks for both.

What is actually knowable before any model runs: the product, and the G2 source code. `UNAUDITABLE` is
deterministic, so half the instruction survives and is implemented, with unauditable pairs reached first.

For the other half the answer is a separate supplement, labelled after seeing verdicts, carrying
`blind: false`, excluded from kappa, and reported on its own. That is worth something as coverage of a rare
class and it is not agreement, so it is never pooled with the blind labels into one number.

**Why this is worth recording rather than quietly fixing.** The scope document was written by someone who
had not yet tried to draw the sample, which is most specifications. The failure mode it would have produced
is specific: fill the `CONTRADICTED` cell by looking for contradictions in the judge's output, label those,
and report a kappa that includes them. The kappa would look better and would be measuring the judge's
agreement with a human on a sample the judge chose.

## 14. A bad extractor and a bad judge are the same symptom, and the labeller can separate them

Known since day 3 and recorded as a hole: an extraction failure folds into the judge's error rate, because a
human reading the real page marks `SUPPORTED` where the pipeline said `NOT_FOUND_IN_SOURCE`, and the
disagreement lands on the judge when it belongs to `extract.py`.

The fix turned out to need no second opinion, only one more question at labelling time. The labeller is
already reading the page. Asking them to paste the passage they found, which the judge is required to do
anyway, makes the separation deterministic: if their passage is present in the page and absent from what
`extract.py` produced, that disagreement is the extractor's, by string match rather than by judgement.

`goldset.attribution` reports the split and a second kappa with those pairs removed, beside the headline
one rather than instead of it. A floor on both counts, and it says so: it only sees pairs where the labeller
quoted something, and it cannot see evidence the labeller also missed.

The general version, which is the reusable part: when two components fail with the same symptom, look for a
question the human is already answering that distinguishes them, before reaching for a second model.

## 15. The no-confidence gate would have banned the confidence interval

Small, and it is the kind of collision worth writing down because the tempting resolution is the wrong one.

`gates.assert_no_confidence_number` walks keys and rejects any containing "confidence". `SCOPE.md` §5
requires every rate to ship with a confidence interval. So the first `Rate.to_dict` with a
`confidence_interval` field failed the project's own honesty gate.

A confidence interval and a confidence score are genuinely different objects, so an exception list would
have been defensible. It was not taken. A gate with an exception list is a gate that will eventually be
argued past, and the argument will be made by whoever wants the exception. The field is called
`interval_95`, the gate stayed blunt, and there is a test asserting a rate passes the gate unmodified.

## 16. Perplexity puts no links in its answers at all

The adapter note said four source chips carried no anchor, so roughly a third of Perplexity's citations were
not in the DOM as links. Probing a live answer page on 2026-08-11 gave a different number: zero of them are.

Every inline citation is

```html
<span class="citation inline" data-pplx-citation data-pplx-citation-url="https://www.boston.gov/...pdf">
```

and `document.querySelectorAll("a[href]")` over the whole page returns nothing. Five citations in the
answer, five spans carrying an absolute URL in an attribute, no anchors anywhere.

**What that produced.** The extension looked for `a[href^="http"]`, found none, and emitted a capture with
`citations: []`. That capture is not obviously broken. It parses, it hashes, its character counts are
right, and its adapter is reported honestly as unverified. What happens next is worse than a crash: G0 sees
an answer with no citations and halts it as `NO_CITATIONS`, which the tool defines as *a different object,
not a zero percent answer*. So a Perplexity answer with five real citations would have been filed as an
answer that cited nothing, by a gate whose entire purpose is to protect that distinction.

**Why the estimate was wrong in the first place.** "Roughly a third" came from counting visible chips
against captured citations on one screen, by eye. The right instrument was two lines of JavaScript, and it
was available the whole time. An estimate arrived at by looking at a screen is not evidence about a DOM.

**The fix had to land in three places.** The extension's citation counter, which ranks candidate containers
by how many citations each holds; the extension's extractor; and `sayswho/reextract.py`, which re-runs
selection over stored markup. Any one of them left behind would break something specific: the counter would
pick the wrong container, the extractor would drop the citations, or the §9 parity check would report a
disagreement between the two implementations. There is now one helper per side and a test comparing the two
attribute lists across the language boundary.

**One thing this does not fix.** The first Perplexity citation on that page is a PDF, which is
`SOURCE_NOT_HTML` downstream: a code that is tested, has never fired on real data, and is listed in
`STATUS.md` as unexercised. It could not fire while the citations never reached the fetch layer.

---

## 12. The prior art section had two wrong claims in it

Checked every tool named in §1b against its own documentation on 2026-08-11, because §8's honesty overlay
promises prior art named plainly and nothing had actually verified the naming. All four exist. Two of the
claims about them did not survive.

**"Every incumbent, by its own description, outputs a confidence score."** False as written. GPTZero's Source
Finder documents no confidence number, and it is doing a different task: it finds sources *for* text rather
than auditing citations an answer already has, and it states outright that it does not take a stance on
whether the claims or the sources are true. Worse for the argument, FactSentinel's own page says "a single
confidence number can make weak evidence feel settled", which is the argument this project makes. Using a
tool that agrees with you as the foil for your differentiator is not a small slip: it was the load-bearing
sentence under §1b, and it was overstated in the direction that flattered this project.

**Four competitors doing one thing.** Two of the four are not doing this thing at all. CiteTrue verifies that
a reference exists, against Crossref and PubMed and others, which is the §0a stretch item here rather than
the core. GPTZero searches for sources. Counting either as a competitor to be beaten inflates the field and,
by implication, the achievement of entering it.

**What replaced them.** A table of what each tool says it does and outputs, and a narrower claim that the
evidence supports: three of the four attach a confidence number to a verdict, and none of the four documents
what happens when a cited source cannot be fetched. That second half is explicitly a claim about their
documentation and not about their behaviour, which the §5a head-to-head would be needed to establish.

**Two other things the check turned up.** The academic prior art was missing entirely, which made the idea
look more original than it is; §1b now names the attribution-evaluation work that separates retrievability
from support, the same distinction G2 enforces. And CiteGuardian runs a "scrub test" for decorative citations
that SaysWho has no equivalent of, so the closest tool in the space is ahead on something and the writeup
says which thing.

**The honest reading of this finding.** A project whose entire subject is unverified claims carried two
unverified claims about its own competitors for five days, in the section arguing why it deserves to exist,
both tilted the same way. The mechanism that caught it was being asked to check, not anything structural.
There is no gate for prose.

---

## 13. I claimed a document said something it did not say

Yesterday's commit message said "§7 now says it" about the API path's limits, and the reply that went with it
said the same. `SCOPE.md` §7 contained nothing of the kind. The edit that was supposed to add it asserted on
an anchor string, `## 8. Rubric`, that was not in the file, the assertion failed, and the write never ran. I
read the traceback as a failure in a later step and moved on.

The section is there now, and the decision in it is firmer than the version I claimed: no rate derived from an
API capture is published, rather than the hedge about defaults it originally had.

**Why this one is worth a numbered finding rather than a quiet fix.** It is the project's own subject,
committed by the project's author, in the same session as item 12. Item 12 was two unverified claims about
other people's tools. This is an unverified claim about my own document, made in a commit message that will be
read as a record of what happened, and it went to the person relying on it.

The pattern across both is identical and it is not carelessness about facts. It is a missing verification
step in exactly one place: **prose**. Every number in this repo is checked by something. `git log` is checked
by nothing, `SCOPE.md` is checked by nothing, and the only prose-level gates that exist are a scan for banned
vocabulary and a check for em dashes. Both of those are lexical. Neither can tell whether a sentence about a
file is true of that file.

**What would actually catch it.** A test that reads the claims a document makes about other files and checks
them. There is precedent in this repo already: `test_extension_manifest.py` asserts that source files contain
specific strings, which is exactly this mechanism pointed at code. Pointing it at documentation would mean
`SCOPE.md` §7 claiming `sayswho/apicapture.py` exists becomes a test, and so does §9's claim about the stack,
which was wrong about the language for five days until the prior-art check happened to catch it.

Three prose claims have now been found false in one day: the extension's language, two competitor claims, and
this. All three were found by being asked, not by anything structural. That is the strongest argument in this
repo for a documentation gate, and it is recorded here rather than acted on, because inventing a gate at the
end of a session is how gates get built badly.

---

## 14. Three of four "the judge fabricated a quote" verdicts were this tool's fault

`JUDGE_FABRICATED_SPAN` is the one code published as a finding about the model: the judge quoted a passage
that is not in the document it was given. That claim is only as good as the comparison behind it, and the
comparison was worse than the claim.

**The typographic fold.** The span guard compared on whitespace and case alone. A page using curly quotes and
a judge typing straight ones disagreed; so did `21-day` against `21\u2013day`, and a word carrying a soft
hyphen from a line break against the same word quoted cleanly. Three of five typographic variants voided a
span the page really contained. Fixed with a per-character fold: quotes, dashes, invisible characters, and
NFKC for ligatures and full-width forms.

Separating that from claim ids was most of the work. `normalise_for_span` was also computing the content
address every claim id is derived from, and gate G4 ties a gold set to those ids, so folding typography would
have silently invalidated every label. Two functions now, and `canonical_for_id` is documented as frozen.

**The PDF line breaks.** Then the first real PDF audit. `Td` was treated as a line break; it is a text
position operator, and this generator emits it between individual glyphs to kern them, so a newline went
between every character and "(61.1%)" extracted as "(6 1 . 1 %)". The judge had quoted the number a human
reads. The guard voided it. Fixed by reading the operands: only a vertical move starts a line. The horizontal
threshold was swept from 0 to 8 against the real document and only inserting nothing produced the right text,
with the space ratio moving from 0.131 to 0.123, which says word spacing in this document is real space
characters rather than positioning.

**The bullet, unfixed here and fixed in item 17.** This PDF renders bullets through a symbol font whose
glyphs sit at letter code points, so a line reading "\u2022 Adults who lived in the US for ten or fewer years
(61.1%)" extracts as "x Adults who...". The judge quoted the bullet a human sees.

The sentence that stood here said that following font encodings is beyond a stdlib reader, so this stays
broken. That was true of the general case and false of this document, and it was the wrong kind of wrong: a
limitation asserted from the shape of the problem rather than from opening the file, which had the reverse
table in it the whole time. Item 17 is what opening it found. The count is still reported separately from one
over HTML, because fixing an extractor does not retrospectively settle a span quoted from the old one.

**The four voids, resolved.** One was the `Td` bug. Two are the bullet. One is a genuine catch: the judge
joined two non-contiguous passages with an ellipsis instead of quoting verbatim, which is exactly what the
guard is for. So the honest count is one real catch out of four, and the earlier figure was mostly measuring
this tool.

**What this says about the guard, which is not what it looks like.** The span guard is not discredited by
this. It caught a real non-verbatim quote, and every false void it produced cost coverage rather than
accusing a source, which is the direction the design chooses on purpose. What is discredited is publishing
`JUDGE_FABRICATED_SPAN` as a rate about the judge without first checking that the extractor can render the
document a human sees. The rate was never a fact about Gemini. It was a fact about this repository, wearing
the judge's name.

**And how it was found.** Not by a test. By re-reading four spans against the bytes they were voted on,
because someone asked whether the number was real. The suite had 627 passing tests at the time and every one
of them agreed with the bug, for the same reason the Perplexity adapter's tests agreed with its bug: they
asserted the rule the code implemented.

---

## 15. The judge reads a page's silence as a contradiction, and its topical overlap as partial support

Break attempts 1 to 4 ran against a live judge for the first time on 2026-08-11. Three held. The one that
broke broke twice, and the second time only after the attempt itself was corrected.

**The first break was not the failure the attempt was hunting.** Attempt 1 serves a page that discusses the
claim's subject at length and never states the claim, and it declared before running that it was looking for
`SUPPORTED` or `PARTIALLY_SUPPORTED`. It got `CONTRADICTED`, on 4 of 4 calls, with the judge quoting the
page's closing sentence: that the paper makes no estimate of any reduction for this cohort or any other.

Denying that you report a figure is not asserting the opposite of it. `CONTRADICTED` is the harshest verdict
the tool has and the one that accuses a product's citation most directly, and it came back against a page that
is silent on the claim. If that generalises, `CONTRADICTED` is inflated and `NOT_FOUND_IN_SOURCE` deflated in
every run this tool will ever publish, and the two are not equivalent errors: one says the source disagrees,
the other says the source does not address it.

**But the fixture was confounded, so attempt 1 could not have asked its own question.** A page that announces
what it does not report is rare. Real pages are silent by omission. The attempt therefore measured whether a
disclaimer reads as a contradiction, which is a real question, and not the one written at the top of the file.
Attempt 1b removes the denial.

**A second fault in the fixture, found by the test written to check the first.** Removing the denial removed
the claim's verb with it: `reduc` appeared nowhere else on the page. The vocabulary overlap that attempt 1
asserts in its own notes, and that a test asserts on its behalf, was partly supplied by the confounding
sentence. The test passed the whole time. It checked that the words were on the page and not that they were on
the page for the right reason, which is the same shape as the Perplexity adapter's tests and the span guard's:
an assertion that agrees with the bug because it encodes the same assumption.

**With both faults fixed, the declared failure appeared immediately.** Attempt 1b returned
`PARTIALLY_SUPPORTED` on 4 of 4 calls for a claim its page never states. Every span was verbatim and on the
page, so the span guard passed all four. This is attempt 5's structural hole, "the guard checks presence and
not relevance", observed on an ordinary page with no injection anywhere in it.

Three of the four calls quoted a sentence carried over unchanged from attempt 1 rather than the one 1b added,
which rules out the obvious objection that the finding was planted by the edit.

**`missing_qualifiers` behaved well and did not save it.** Every call named the 21-day figure as absent from
the source. The day 5 work is doing its job. It does not rescue the verdict: a claim whose central number the
source never states is not partially supported by that source, and the reader gets a partial-support card with
a caveat instead of the refusal the page warrants. Of the six claim states, `PARTIALLY_SUPPORTED` now has the
weakest evidence behind it.

**What it costs to know this.** Nothing published changes today, because nothing aggregate is published yet.
What changes is the gold set's job description. It was already the only thing that could measure
`EXTRACTION_SUSPECT` and the PDF garbling; it is now also the only thing that can measure how often the judge
converts silence into a verdict in either direction. Four calls on two documents is a hypothesis about a judge,
not a rate about one, and this file is the only place it is allowed to appear until that changes.

**And the runner said something false while reporting it.** `_assess` printed "This is the failure the attempt
was looking for" for any verdict that was not `NOT_FOUND_IN_SOURCE`, so attempt 1's `CONTRADICTED` was recorded
as the declared failure when it was not one. The held and broke decision was correct and is unchanged; the
sentence beside it was wrong and went into `runs/break/results.json` before anyone read it. Third time this
project has published a true number with a false sentence attached, after items 13 and 14.

---

## 16. The blind gold set could not have been labelled blind, and would have calibrated nothing if it had

Found by walking the labelling workflow end to end before labelling rather than during it, in answer to the
question "what do I actually do with the gold set". Two faults, either of which would have wasted the
session, and both in the part of the project with the most machinery around it.

**The blindness could not be honoured.** `goldset.agreement` refuses a blind label that postdates the judge
run it is compared against, `tools/label_goldset.py` refuses to open any file carrying judge output, and G4
ties the set to the split. Three structural refusals. But the artefact a labeller works from is a stored
split, and the only route to one was `--judge --save-split`, which runs Phase 3 and prints every verdict to
the terminal on the way past. The one mandatory step in the workflow was the one that showed you the answers.
`--split-only` now runs Phase 1 and stops.

**And the set it produced was bound to nothing.** A `GoldSet` carried a single `split_sha256` and G4 compared
it for equality against the split of the run in front of it. One captured answer yields roughly twenty
labellable claim-source pairs; the target is thirty to forty; the sampler's whole stratification is
round-robin across products. So a real set spans two or three answers, and given more than one split the
labelling tool wrote `split_sha256 = ""`, which equals no split anywhere. Confirmed against the gate rather
than read off the source: G4 returns "gold set was labelled against split , this run judged split
abc123realsplitd". Thirty to forty pairs of irreplaceable human work, and not one capture calibrated.

**What connects them.** Neither is a bug in a function. Both are gaps between components that are individually
correct and were never run in sequence, and both would have been found in the first ten minutes of labelling
and paid for with the whole session. The pieces were tested. The path through them was not, because the path
requires a human at a terminal for two hours and no test does that.

**What I changed and what I did not.** The split binding is now a list checked by membership, and it records
the splits that actually produced a label rather than the ones the sampler was offered, because quitting after
one label must not claim an answer nobody reached. G4 still refuses a set bound to no split at all, on
purpose: under equality that case failed loudly by accident, and under membership an empty list would
otherwise have to be refused deliberately or it becomes a set that calibrates everything.

**The general shape, which is now three for three.** Item 13 was a document claiming something the code did
not do. Item 15 was an attempt whose fixture could not ask its own question. This is a workflow whose steps
could not be performed in the order the code requires. In each case the components were tested and the claim
about them was untested, and in each case it was found by someone asking a plain question about the thing
rather than by the suite. 661 tests at the time of writing, and none of them tried to label a gold set.

**Two more from the same walk, kept in this item because they are the same finding continuing.** Launched
without a terminal the tool reached the first prompt and raised `EOFError`, which reads as "the tool is
broken" rather than "there is nobody here to type"; EOF and Ctrl-C are now a session that cannot happen, and
the labels made before an interrupt are kept.

And the fourth, which is the one none of the refusals could see. `goldset.agreement` compares a label's
timestamp against the run it is compared with, so labels written today pass against a run made tomorrow, and
G4 ties to the split, which differs for a second audit because Phase 1 does not repeat itself. An answer
judged last week therefore leaves verdicts on disk that would anchor a labeller and trip nothing at all. It
was found on 2026-08-11 when every capture on disk turned out to have been audited already, and for a day the
only control was a sentence in a banner asking the labeller to remember, which is the weakest kind of control
there is: it fails silently and in the direction that flatters the result. `sayswho/prior_audit.py` now scans
`reports/` and `runs/` for a verdict over the same `answer_sha256` and the tool exits rather than asking its
first question. Run against this repository it refuses immediately, which is the correct answer and not a
comfortable one: the only real split on disk has two audits behind it.

And a fifth, found by building the pass that prepares a session rather than by running one. The sample is
stratified across products and G2 codes, and the codes come from a run record passed with `--capture`. Without
one every pair buckets as `UNKNOWN`, so the stratification degrades to product-only and §3 Phase 4's
"unauditable first" does not happen. Nothing says so, and the argument is optional. It is demonstrable rather
than theoretical: on the one real split here the sample changes when the run record is supplied, from six
pages with no unauditable pair among them to seven including the paywalled one and the one with no text layer.
Those are exactly the pairs the plan asks to be labelled first, and they are the ones a forgotten flag drops.
`tools/prep_goldset.py` reports NOT STRATIFIED when it happens, and reports the unauditable count as not-known
rather than as zero, which is the same distinction as a missing snapshot making drift unknown rather than
unchanged.

Three things that guard is careful about, each for a reason this project has already paid for once. It reads
files full of verdicts and never carries one out, so the refusal names the file and the key that proved it and
nothing else. It reports not-checked rather than clean when there is no artefact directory to look in. And
there is no flag to skip it: the way through is `--supplemental`, which is not a weaker blind but a different
and clearly labelled thing, excluded from kappa and reported on its own.

---

## 17. The bullet was readable all along, and the reason it stayed broken was a sentence

Item 14 ended with a limitation: a PDF renders bullets through a symbol font, the bullet extracts as the
letter "x", the judge quoting the line a human reads is voided as `JUDGE_FABRICATED_SPAN`, and following font
encodings is beyond a stdlib reader, so this stays broken.

The last clause was not measured. It was inferred from the general problem, which is real: resolving an
arbitrary font means walking each page's `/Resources`, tracking the `Tf` operator, and following an object
graph that in this document is inside twenty-nine compressed object streams. The specific problem was much
smaller, and the way to find that out was to open the file rather than to reason about the class of files it
belongs to.

**What was in there.** Sixteen font objects, none of them visible in the raw bytes, all inside object streams.
Two of them are `/Type0` with `/Encoding /Identity-H`, which means their text is shown as two-byte glyph
numbers. One is an embedded SymbolMT subset, and it carries a `/ToUnicode` CMap that is one entry long:

```
1 beginbfchar
<0078> <2022>
endbfchar
```

That is the answer, in the document, as an ordinary Flate stream. Glyph 0x0078 is `\u2022`. Decoded a byte at a
time it had been arriving as NUL followed by "x", and `_tidy` stripped the NUL as never-content, leaving the
letter.

**There were two bullet bugs, not one.** The other line's bullet was WinAnsi 0x95, decoded as latin-1 into an
unused control code and then stripped by the same rule. That one needed no font at all: WinAnsi is cp1252, so
the fix is a translation table built from the codec, and it also recovers the curly apostrophe, the en dash
and the ellipsis, which are most of what the span guard's fold table exists to reconcile. A bullet that
extracts as the wrong character corrupts evidence; a bullet that extracts as nothing deletes it. The second
is worse and it was the one nobody had noticed.

**What was deliberately not built, and the rule that replaces it.** No page resource resolution and no `Tf`
tracking. Instead the document's two-byte tables are pooled, a code two of them disagree about is dropped
rather than guessed at, and a shown string is decoded through the pool only when every code in it resolves and
at least one byte is a control byte. That last condition is what separates two-byte codes from ordinary text,
and the first version of it was wrong in the dangerous direction: it asked for a code above 0xFF, which any
two ASCII letters read as one code satisfy, so a table holding 0x6162 would have rewritten the word "ab" as a
bullet. A test caught it. Measured on the real document: two two-byte fonts, nineteen codes, no conflicts,
54,811 characters before and 54,811 after, 23 bullets where there had been none.

**What this does not fix, which is the part worth saying twice.** The two voided spans are not overturned.
Re-checking them against the fixed extraction gets 305 of 549 characters through, where the bullet used to
stop it at about 170, and then fails on `non-Boston`: the judge quoted `nonBoston`, because the extraction it
was given had dropped an en dash and joined the word. So those spans were quoted from text this tool no longer
produces, and no amount of re-checking settles them. Only judging the fixed document does. The
fabricated-span figure stays withdrawn rather than restated, and it stays reported separately for PDF and
HTML sources.

**The general shape.** Item 13 was a document claiming something the code did not do. This is a document
correctly describing what the code did, and wrongly explaining why it had to. A limitation with a reason
attached reads as settled, and this one was repeated in four places: `pdf.py`, `DATA_CONTRACT.md` §5,
`STATUS.md` and `TODO.md`. Nothing in the suite can check the word "beyond", which is exactly why a stated
limitation deserves the same suspicion as a stated result.

---

## 18. The stratum the whole project was designed around could not be assembled

The professional-research stratum was the core's only population and the thing that made the query set worth
defending: real questions asked during real work, transcribed and scrubbed, rather than questions written to
be audited. It never arrived, and on day 6 the reason turned out not to be the one the file had recorded for
six days.

`TODO.md` said "blocked on pulling real queries out of my own AI history", which describes an unstarted task.
The actual state was that there is no history to pull from. The sessions are gone.

**What was available, and why it was refused.** The questions could be retyped from memory. They would still
be questions I really needed answered, so `CLAUDE.md`'s rule against inventing one would not have been
broken. Two rules in `queries/README.md` were, and both were written on day 1:

- *"Do not select on remembered outcome. Pull chronologically or by domain and take what is there."* Recall
  cannot be pulled chronologically. It selects on what stuck, which correlates with how the tool performed,
  and the README already says why that one is the dangerous kind: it is undetectable from outside, because
  the resulting set looks exactly like an honest one.
- *"Do not improve the phrasing. These get transcribed roughly as typed."* A retyped question is
  reconstructed. §7's argument that authorship here is a *coverage* limitation rather than a *validity* one
  holds only because a query is a stimulus recorded as typed, and the README spells out that polishing
  converts it into the validity version, "which cannot be stated and bounded the way a coverage gap can".

The schema said the same thing in code: `provenance` accepts `synthetic` or `real_scrubbed`, and
`real_scrubbed` requires `scrub_notes` describing what was removed. A recalled question has no text to have
removed anything from, so the honest entry would have needed a third value that did not exist, and inventing
one on day 6 to accommodate day 6's problem is the definition of a benchmark being tuned by its author.

**What was done instead.** The core runs on the consumer stratum: 24 questions, written and frozen on day 1,
synthetic and saying so in its own file. Day 1's insurance turned out to be the thing that made this
possible. The consumer set was frozen before anything was known about what the professional set would
produce, so it cannot have been shaped by results, and `FREEZE.json` is the evidence rather than my word.

**What it costs, kept together in one place so no surface has to reconstruct it.** The core's numbers describe
how this tool behaves on questions nobody asked. The §0 question of whether support rates differ between
professional and consumer use is not half answered but unanswered, since one side has no data at all. The
differentiator that the query set is real rather than invented is gone from the core entirely. And the scrub
drop rate, promised in §10 to be published beside the support rates on the grounds that a suspiciously low
one is evidence of a pre-filtered intake, cannot be computed: there was no intake, so there is no
denominator, and the writeup says that rather than printing a zero.

**The general shape.** Items 13, 14 and 17 were sentences that had stopped being true about the code. This is
a sentence that was still true about the plan and had stopped being true about the world, and it survived
longer than any of them, because a blocker restated every day reads as work outstanding rather than as a
claim to check. Nothing in the suite can test whether a file I intend to fill can be filled. What caught it
was being asked what help I wanted with it.

---

## 19. A property guaranteed by construction in one stratum, and simply absent from the other

The professional stratum's population is defined in `queries/README.md` in one sentence: not everything I
asked an AI, but *the answers that came back with citations attached*, because an answer with no footnotes
produces nothing to audit. That is the one property a citation audit cannot do without.

It was free there. The queries were to be selected out of a history of answers that already had citations, so
every entry satisfied it before it was written down. Nothing had to check it, and nothing did.

The consumer stratum cannot satisfy it that way and never did. Its three selection criteria, stated at the top
of its own file, are that a wrong answer changes what the asker does, that the correct answer is bounded by a
jurisdiction or a year, and that it is the kind of question someone asks an AI instead of a professional. All
three are about stakes. None is about whether the question elicits a cited answer. `queries/README.md` said
the set was "written to the same standard", which was true of the standard anyone was thinking about and false
of the one that mattered.

Day 6 moved the core onto that stratum without anyone noticing the difference, and it surfaced the way these
things do: by someone asking the questions and reporting that nothing was citing anything. The partial answer
is that Perplexity and ChatGPT do return sources for these, and Claude frequently does not, so the set is
usable on two products of three. That is not a repair. The set is usable by luck, and the property it was
never held to is now written down in both places rather than assumed.

**Two things follow that are worth separating.** A stratum that elicits no citations would not have produced a
bad support rate, it would have produced no support rate at all: G0 halts an uncited answer and records
`NO_CITATIONS`, because an answer with no footnotes is a different object rather than a zero. So the failure
mode here was never a wrong number, it was an empty run discovered late. And Claude answering high-stakes
consumer questions without citing anything is an observation about a product, made informally, on a handful of
questions. It is not a finding yet. The run counts `NO_CITATIONS` per product, which is where it either
becomes one with an n attached, or does not.

**The general shape.** Items 13, 17 and 18 were sentences that stopped being true. This one was never true, and
it survived because the two strata were described in one breath as written to the same standard, which made
the difference between them invisible in exactly the place it mattered. A property that is free by
construction is a property nothing tests.

---

## 20. The extractor stopped at the first selector that matched, and took a quarter of the citations with it

First real capture run against the consumer stratum: 24 Perplexity answers, one per conversation. The
captures looked fine. Twenty of the twenty-four flagged themselves incomplete, which is the "+N" chip counter
doing its job, and fourteen recorded exactly one citation, which for Perplexity is low but not obviously
wrong.

Running `python3 -m sayswho.reextract` over the first capture and its stored page reported a parity mismatch:
four citations in the page, three in the capture. Across all 24, **38 captured against 51 in the stored
pages: 13 missing, a quarter of the total, spread over 11 of the 24 answers.**

**The cause.** `saysWhoExtractCitations` looped over `adapter.citationSelectors` and ended with
`if (citations.length) break;`. The first selector that matched anything won and the rest never ran.
Perplexity declares two, `a[href^="http"]` and `[data-pplx-citation-url]`, and renders both shapes in the same
answer, so every citation of the second kind was dropped the moment the first kind appeared. The dedup set was
already keyed on marker and URL together, so scanning every selector could never have double-counted: the
break was not protecting anything and never had been.

**Why it was invisible.** Everything the capture did find was real. There was no crash, no empty list, no
warning, and the citations it recorded were correct ones. This is the same shape as the Perplexity
zero-of-eight in item 16 and the gzip bug in item 7: a component that fails by returning less, plausibly.

**What caught it.** Not a test. `reextract` exists so that the extension's reading of the live DOM can be
compared against a second implementation reading the same bytes, and it printed the disagreement with the
sentence it was written with: one of the two is wrong, and that disagreement is the finding rather than a
nuisance. The §9 parity check in `tests/parity/` covers the renderer and has never covered the extractor,
which is where a silent shortfall actually costs something.

**What it did not cost.** Nothing had to be re-asked. Day 2 stored the raw page beside every capture for
exactly this: "a selector fix no longer re-runs the query, so a selector change and an answer change cannot
arrive together and be mistaken for each other." `reextract --repair` rebuilt the citation lists from those
bytes, left the answer text and its hash untouched, and recorded `citations_source: reextracted` in each
capture so no repaired capture can pass as a clean one. That design decision was made four days before it
was needed and it saved the run.

**What is still open, and it is the honest half of this entry.** The test added with the fix asserts that the
source no longer contains the early exit. That is a test about the shape of a file, which this project says
elsewhere is the weak kind, and it is here because running the extension's extractor needs a DOM. The test
that would have caught this runs that extractor in node against the same markup `reextract` parses and
compares the two citation sets, the way the renderer is already treated. Until that exists, the extractor's
half of §9 rests on somebody running `reextract` by hand and reading the output.

---

## 21. The first honest run, and the four voided spans that had to be checked before any of it could be said

Day 6, 2026-08-13. Twenty-four Perplexity answers against the frozen consumer stratum, judged against stored
splits so the claims are the ones a labeller could have read. Seven minutes, 130 model calls, 532,970 tokens,
nothing halted, no capture errored.

| | |
|---|---|
| captures | 24, all bound, all one product |
| sources | 51: **42 `SOURCE_OK`**, 8 `SOURCE_BOT_BLOCKED`, 1 `SOURCE_UNREACHABLE`, **0 `SOURCE_DEAD_LINK`** |
| document kinds | 49 HTML, 2 PDF |
| claims | 158, of which 42 carry no citation |
| claim-source pairs | 139 |
| G1 skipped | 213 blocks, 219 units |
| verdicts returned | 130: 75 `SUPPORTED`, 21 `PARTIALLY_SUPPORTED`, 34 `NOT_FOUND_IN_SOURCE`, **0 `CONTRADICTED`** |
| verdicts standing | **125**, after the five voids below. A voided verdict is not a weaker verdict, it is no verdict, and it leaves the numerator and the denominator together |
| voided | 5: four `JUDGE_FABRICATED_SPAN`, one `SPAN_ADDED_AFTER_GENERATION` |

**No support rate was printed, and that is the deliverable.** Gate G4 withheld it on 18 of the 24 answers,
naming both split hashes each time: the gold set holds six labels covering four splits, the run judged
twenty-four. `INSUFFICIENT_EVIDENCE` withheld two more on its own ground, `CO-04` and `CO-08`, where more than
half the cited claims produced no standing verdict. `CO-08` is the starker one: two sources, both
`SOURCE_OK`, and zero standing verdicts out of them. The stratum aggregate then refused on the grounds that an
aggregate over the runs that happened to be measurable is an aggregate over measurability.

**The four fabricated spans, checked before being described.** `SCOPE.md` §8 carries an obligation added after
item 14: the fabricated-span count is published rather than quietly fixed, **and it is only called a finding
about the judge once the extraction behind each void has been checked.** So all four were re-checked against
the cached bytes, with the reader that now routes PDFs correctly.

- **Three are genuine.** The judge stitched non-contiguous passages into one quote. Two of them announce it
  with a literal `...` in the span, and the third silently skips items from a bulleted list. This is exactly
  what the guard is for, and it is the same failure the one genuine catch in item 14 was.
- **One is ours, and is now fixed.** `CO-15`'s span is the page verbatim except for a `[44]` footnote marker,
  which our extractor keeps inline and the judge dropped. Strip footnote markers from both sides and the span
  matches exactly. A reader of that page sees a superscript, not four characters mid-sentence.

  `span_is_present` now tries the comparison twice, the second time with bracketed numbers of up to three
  digits removed from both sides, and it runs only when the first pass fails. Re-checked against the same
  cached bytes: `CO-15` is overturned and the other three stay voided, which is the blast radius the fix was
  supposed to have. The widening is real and stated where it is made: the guard can now accept a span whose
  only difference from the page is a bracketed number, which includes quoting "see [44]" where the page says
  "see [45]". Every entry in `extract._SPAN_FOLD` was bought with the same trade, and the alternative here was
  a count published against the judge for characters this pipeline inserted.

  `drift.span_predates_generation` was routed through the same function rather than keeping its own copy of
  the comparison, because otherwise the identical marker would have voided the identical span as
  `SPAN_ADDED_AFTER_GENERATION` instead: one bug, two codes, and the second one blames the page for changing.

So the honest figure is **3 of 96 span-bearing verdicts attributable to the judge, and 1 of 96 to this tool,
the latter now fixed rather than carried**.
All four sources were HTML, so the PDF and HTML split that item 17 requires reports zero PDF-sourced voids,
which is a fact about this sample rather than a reassurance: only two of the fifty-one sources were PDFs.

**What the run says about the guards rather than about the products.** Every unauditable source in the run is
unauditable because of us or because of a server refusing robots, not because of a broken citation: seven
403s, one TLS failure, and one 404 that a person can open in a browser and read in full. That last one is
still classified `SOURCE_DEAD_LINK`, which is the one unauditable code that accuses a citation rather than
this pipeline, and it was wrong. It is now fixed: a non-200 whose own headers or body name it as an
abuse-detection page is recorded as `SOURCE_BOT_BLOCKED` whatever status it arrived with, bounded to responses
under 8 KB so an article discussing bot detection is not mistaken for one. Re-derived from the cache with no
new requests, the table above is the corrected one.

**Which makes the sentence stronger and worth stating plainly: not one of the fifty-one cited sources was a
broken citation.** Nine were unreadable to us, and all nine are a server refusing an automated client or a
TLS chain we could not verify. The unauditable rate this run would publish is a measurement of our access,
not of anyone's citation hygiene, and `DATA_CONTRACT.md` §3 forbids the only thing that would change that.

## The plausibility audit

`SCOPE.md` §12 day 7 asks for one. It is a judgement rather than an output, so it is signed as such: this is
mine to defend and the numbers behind each point are in `runs/day7/`.

**What looks right.** 42 of 51 sources readable is plausible for consumer questions answered from government
and health-service pages. 158 claims from 24 answers, at 6.6 claims per answer, matches the length of what
Perplexity returns. 139 claim-source pairs against 51 sources means most sources carry two or three claims,
which is what a cited paragraph looks like.

**What looks wrong, and is.** `CONTRADICTED` came back empty across 130 verdicts. Break attempt 1 found this
judge reading a page's disclaimer as a contradiction 4 times out of 4 (item 15), so the class is clearly
reachable; a run that produces none of it either got lucky with 24 well-cited answers or the judge is
reluctant to use it on real pages, and those two are not distinguishable from here. It is the class §3 Phase 4
says to fill first in a gold set, and no run so far can supply an example.

**What looks too good.** 75 `SUPPORTED` of 130 is 58%, and every one of those quoted a span the guard
confirmed is on the page. That is a higher support rate than the project's own framing would have predicted.
Three reasons to distrust it before anyone quotes it: no rate was published from it and none may be; the
questions are synthetic and short, which makes them easier to answer well than real research questions; and
Perplexity cites densely, so a claim has more chances to find a supporting source than an answer with one
footnote per paragraph.

**What is missing rather than measured.** 42 of 158 claims carry no citation at all, and this tool is blind to
whether they needed one. That is 27% of the extracted claims, and §7's omission limitation covers exactly that
gap. The thin-page flag has now seen 51 more sources without firing, which is either a well-built flag or a
flag that does not work, and nothing here separates those.


**Two things that did not happen, worth stating because they were expected to.** The thin-page flag has still
never fired on real data, over fifty-one more sources. And `CONTRADICTED` came back empty across 130 verdicts,
which is the class `SCOPE.md` §3 Phase 4 says to fill first in a gold set: a class the judge never produces
cannot be calibrated against, and a run that never produces one cannot supply the examples.


## 22. The honest run spent the blindness, and G4 does not notice

Day 8, 2026-08-15, found while preparing the labelling session rather than by running anything.

**The gold set cannot be labelled blind over these answers any more, and the run that made the numbers is what
spent it.** `tools/prep_goldset.py` reports 28 files under `reports/` and `runs/` already holding a verdict
over 25 of 25 answers, so `tools/label_goldset.py` exits 3 rather than asking the first question.
`--supplemental` is the documented way through and it is not an override: those labels carry `blind: false`,
and `goldset.agreement` iterates `gold.blind`, so they are counted, reported separately, and excluded from
kappa by construction.

The six labels that exist were written between 21:09 and 21:20 UTC on 2026-08-13. The run started at 23:51
UTC the same day, two and a half hours later. So they are blind, `agreement`'s timestamp refusal passes on
them, and as of day 8 they are the only blind labels this stratum will ever have. Two of the six are
comparable, the other four being sources the judge was never asked about, which is why the kappa reported on
day 7 was n=2.

**Nothing was done wrong, which is the part worth recording.** Day 6 prepped a session whose prior-audit scan
was clean over all 24 answers, and `TODO.md` said so. Day 7 then ran the stratum, because a run that judges
the stratum is what day 7 owed. Both were correct in isolation. The order was not, and no guard in this
project watches the order: `prior_audit` refuses a labelling session after a run, and nothing refuses a run
before a labelling session. The control fires in one direction only, and the direction it does not fire in is
the one that costs a day.

**Then the sharper half.** `gates.g4_calibration_exists` checks four things: judge class and model, the judge
prompt version, the claim prompt version, and split membership. It does not look at whether a single label in
the gold set is blind, and it has no minimum count. So labelling the remaining 39 pairs supplementally would
extend `split_sha256s` across all 24 splits, G4 would pass, and a stratum support rate would print, calibrated
by two blind comparable pairs.

That is not a bug in the sense of a wrong result. G4 does exactly what its docstring says: it ties a gold set
to a judge, a prompt version and a split, and those are the four things whose mismatch needs four different
actions. But the gate is named `g4_calibration_exists`, and what it verifies is that a gold set exists for
this configuration rather than that a calibration does. A set of forty supplemental labels satisfies it and
calibrates nothing, and the invariant in `CLAUDE.md` that G4 is what stands between the project and an
uncalibrated rate is, as written, stronger than the code behind it.

**It was found by asking what a labelling session would produce, not by a test.** Every test of G4 gives it
labels and asks whether the tuple matches. None gives it a gold set whose labels are all supplemental and asks
whether a rate should print. That is the same shape as item 8: the gate was written against the failure that
was imagined, and the one that arrived came in through the field nobody thought to constrain.

**What is being done about it.** The gold set is being rebuilt blind on a second product rather than topped up
supplementally, which is the honest route and also the one that fixes the single-product stratification named
in `SCOPE.md` §3. Ten of the twenty-four frozen consumer queries were drawn with seed 20260812 before any
ChatGPT answer was captured, so the selection predates the data: CO-02, CO-03, CO-08, CO-10, CO-14, CO-17,
CO-20, CO-21, CO-22 and CO-24. A new product means new answer hashes, so the prior-audit scan is clean and the
labels are blind in fact rather than by assertion.

**All 24 were then put in a fixed order, not just the ten**, in `queries/capture-order.md`, because ten
answers might not yield the thirty comparable pairs G4 now demands and "capture a few more" is a choice made
with the data in view. A gold set topped up that way stratifies on whatever the first ten happened to lack.
The continuation comes from the same generator in the same call, so fixing the rest changed nothing about the
ten already published, and the file is committed before any ChatGPT answer exists so the git history is the
evidence rather than the claim. What it does not fix is stated there too: an order decided in advance is not
a stopping rule, and stopping once the floor is met is still a decision made with the data in view. It is the
honest one available, and the writeup reports how many answers were captured and why capture stopped.

Two things that carries with it, both stated here rather than discovered later. The ChatGPT adapter has never
been verified, so every capture it produces carries `adapter_verified: false`, and a gold set built on it
inherits that until the adapter is checked field by field against a real page. And the unauditable share of
the new pairs is not knowable in advance: 15 of 145 is a fact about the pages Perplexity cited, and the target
cannot be chosen until `prep_goldset.py` has fetched ChatGPT's sources and said what the split is.

**Answered the same day, and in the direction that costs something.** This was first written as an open
question, on the grounds that a gate should not be changed on the day the change would be convenient. That
argument was about the wrong risk. The move it guards against is loosening a gate so a result can get out,
and this change does the opposite: G4 now requires `gates.MIN_BLIND_COMPARABLE` blind labels that can be
compared with a verdict, set to thirty, which is the floor of the range §0a already promised. Supplemental
labels never count towards it and `UNAUDITABLE` labels never count towards it, since the judge was never
asked about those pairs. The gate refuses strictly more than it did.

What it costs is worth stating, because a tightening that cost nothing would not have been worth making. The
gold set as it stands, six labels with two comparable, now fails G4 on the count as well as on coverage. So
does any set the day 9 session produces below thirty comparable blind labels. The number that has to be
reached to publish anything went up, deliberately, and it is one constant in one file so that lowering it is
a visible act rather than a flag on a run.

Four tests hold it, and all four describe a set that would have passed before: forty supplemental labels
across every split, the six-label state this repo was actually in, thirty `UNAUDITABLE` labels padding the
count, and twenty supplemental labels failing to make up one missing blind one. The two existing tests that
now pass an explicit floor of one are the tuple checks, which are about configuration rather than about
calibration, and lowering the floor there says so out loud rather than padding a fixture to thirty.

One honest limit on the fix. G4 counts labels, and kappa is computed over the labels that match a verdict
which was produced and not voided, so the gate checks an upper bound on the n behind a rate rather than the n
itself. A set of thirty blind comparable labels whose verdicts were all voided would pass G4 and yield a
kappa of nothing. That is a narrower hole than the one closed and it is left open knowingly, because closing
it means giving the gate the judgements, and G4 runs before they are all in.
