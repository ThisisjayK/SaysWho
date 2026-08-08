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
