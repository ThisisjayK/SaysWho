# Status table

`SCOPE.md` §0a promises this table: every core and stretch item marked done or not-done, with a reason, and
nothing quietly dropped. It is the honesty overlay's fourth item in §8.

Last updated 2026-08-11, day 5 of ten. 643 tests, and `tests/test_documents.py` now checks that this number is true rather than leaving it to rot.

`SCOPE.md` §0a carries the same nine core-and-stretch rows in summary form, because a reader of the design
document needs them there. **This file is the detailed one and the two are updated in the same commit.**
`TODO.md` remains the working list. Three places recording state is one more than is comfortable, and the
rule that keeps them honest is that §0a says the state and this file says why.

**Read the first row first.** The professional stratum is empty, and it is the input to everything that
produces a number. Every "built and unexercised" below traces back to it.

---

## The blocker

| Item | State | Reason |
|---|---|---|
| Professional stratum assembled | **not done** | Entries must be real questions I asked an AI tool during PM work, scrubbed per `queries/README.md`. §10 claims that and §7's limitations argument depends on it being literally true, so the file stays empty until real queries are transcribed. It cannot be unblocked by anyone but me and it cannot be topped up with inventions |

Everything below is either done, or blocked on that row, or explicitly out of scope.

## Core, due day 7

| # | Item | State | Note |
|---|---|---|---|
| 1 | The full pipeline: splitting, fetch, judge, span check, three-way verdict | **done** | Runs end to end on a real capture. `sayswho/pipeline.py` is the single orchestration; the CLI and the harness both drive it |
| 1 | No confidence score anywhere | **done** | Two checks per surface: the key gate over every payload, and a vocabulary scan of every rendered file. The word "score" survives in four sentences, all refusing to produce one, allowlisted in the test |
| 1 | Unauditable claims excluded from every denominator by a hard contract check | **done** | Two levels, sources and claim-source pairs, plus voided verdicts. All three raise rather than warn |
| 2 | One stratum: professional-research queries, scrubbed | **not done** | See the blocker |
| 3 | Gold set of 30 to 40 hand-labelled claims | **not done, tooling ready** | Format, four refusals, arithmetic and labelling tool are built and tested. The labelling itself is human work and needs the stratum |
| 3 | n and confidence intervals reported honestly | **done** | `Rate` carries its n, a Wilson interval and its split count, and `Rate.render` is the only formatter, so no surface can print a bare percentage |
| 4 | Break attempt 5, prompt injection through a fetched page | **done** | Narrowed a published claim rather than confirming it. `BREAK_ATTEMPTS.md` |
| 4 | Break attempt 6, denominator contamination | **done** | Fires at both levels, and writing it found a third contamination path |
| 5 | Parity check between the extension and the headless pipeline | **done** | The real `render.js` runs in node over a payload the real Python built, compared state by state |

### Core items whose machinery exists and which have never run on real data

Listed separately rather than ticked, because "the code path exists" and "we have seen it work on a real
answer" are different claims and only one of them is currently true.

| Item | Why it has not run |
|---|---|
| Honest run over the frozen professional stratum | No stratum. `tools/run_stratum.py` runs today and correctly prints nothing, naming which kind of nothing |
| Metric readout with n and CIs over real data | Same. The readout is exercised by tests against a scripted judge |
| Judge-human agreement | No gold set, which needs the stratum |
| ~~The PDF reader on live data~~ | **Run.** It read the `boston.gov` PDF cited by a real Perplexity answer: 56,352 characters, `SOURCE_OK`. Two extraction bugs came straight out of that, both found by re-auditing voided spans rather than by any test. See the day 5 note below |
| The thin-page flag on live data | Tested, never fired on a real capture |
| `EXTRACTION_SUSPECT`'s error direction | Only the gold set can measure it. Until then the writeup says the direction is chosen and the rate is unknown |
| The PDF garbled test's error direction | Same shape, one layer down. Two ratios, printable characters and spaces, decide whether decoded text is language or glyph numbers. Neither threshold is measured. It is set to refuse in the ambiguous case, because refusing costs coverage and passing garbled text produces a verdict that accuses a source |

## Stretch, days 8 to 10

| # | Item | State | Reason |
|---|---|---|---|
| 6 | Competitor head-to-head (§5a) | **not done** | Day 8 at the earliest. Until it runs, the §1b differentiator is described as structural rather than measured, and incumbent behaviour is attributed to their documentation. What the documentation check established: three of the four attach a confidence number to a verdict, and none of the four says what it does with a source it could not fetch. That is a fact about their pages, not their behaviour |
| (extra) | No API-sourced rate is published, enforced | **done** | Decided 2026-08-11 and held in `sayswho/rates.py` rather than in prose: `for_run` withholds every rate for a capture whose `source` is `api`, including the ones needing no gold set, and `aggregate` raises. No override parameter, because unlike a conflicted product there is no legitimate reason to want one. The per-domain slice is closed too, since a slice is still a rate |
| (extra) | A gate for prose | **done** | `tests/test_documents.py`. Paths and modules named in any document must exist, load-bearing claims are checked against the code, and the test count in this file is checked against the suite. Verified by reintroducing all three of day 5's real prose failures and confirming each one fires |
| (extra) | Prior art checked rather than asserted | **done** | All four tools in §1b verified against their own documentation, 2026-08-11. Two claims did not survive and both were tilted this project's way. `FINDINGS.md` item 12. Every row in the new §1b table is dated, and re-checking before submission is on `TODO.md` |
| 7 | Consumer stratum run | **not done** | Written and frozen on day 1 so it cannot have been shaped by professional results. Running it needs the core to land first |
| 8 | Break attempts 1 to 4 | **1 of 4 has a result** | `tools/break_attempts.py`, one command for all four, each declaring the failure it looks for before it runs. Attempt 2, paywall misread, **held** and needed no judge: holding means the judge is never called, because it refuses a source that is not `SOURCE_OK`. Attempts 1, 3 and 4 ask whether the judge can be fooled, which a scripted judge cannot answer, so they report **no result** rather than a pass and the runner counts those separately |
| 9 | Per-domain reporting | **done** | `sayswho/domains.py`, built on `rates.py` so a slice and the aggregate cannot disagree about a denominator. G4 applies: a per-domain rate is still a rate. One readable pair gets counts and no percentage. The table leads with why sources could not be read, because at the core's n a low cell is a hypothesis about this pipeline before it is anything about a publisher |
| 9 | Gold set expansion beyond 40 | **not done** | Depends on the first 40 |
| (extra) | Crossref existence check for named citations | **done** | Built ahead of its window because the core is blocked on transcription rather than on build time. The constraint is enforced rather than intended: no document text in any record, `rates.py` does not import it, and a test asserts the word does not appear there |
| (extra) | Split `SOURCE_UNREACHABLE` into dead-link and bot-blocked | **done** | `SOURCE_DEAD_LINK` and `SOURCE_BOT_BLOCKED`. Done ahead of the stretch window because §5a's dead-link stratum cannot report a dead-link rate until the code distinguishing one exists |
| (extra) | Widen `CITATION_NOT_LINKED` patterns and measure their recall | **half done** | Patterns widened as far as is safe without knowing recall (PMID, PMC, arXiv). The measurement harness is built; marking an answer by hand is mine to do, and until then the count is a floor of unknown depth |

## Extension surface

| Item | State | Note |
|---|---|---|
| Capture on claude.ai, chatgpt.com, perplexity.ai, Google | **done** | With auto-scroll, hash, stored page and incompleteness warnings. One correction today worth naming: the rendered-versus-DOM character counts were measuring different things, so a table in an answer made `innerText` longer than `textContent` and a capture reported more characters rendered than the DOM contained. The display bug was the small half. An inflated rendered count eats the gap the check exists to find, so an answer half of which was never laid out could have reported as complete |
| Claude `.bg-surface-3 .standard-markdown` verified | **done** | Read end to end against the screen, corroborated by a DOM probe |
| Claude `.font-claude-response` verified | **not done** | The chat path has never been exercised |
| ChatGPT selectors verified field by field | **not done** | The capture works; it has not been checked |
| Perplexity adapter trusted | **citations fixed and seen working, capture not verified** | The mechanism is established by probe: every citation is a span carrying `data-pplx-citation-url` and the page carries no anchors at all, so the anchors-only rule found none of them. A real capture then returned 8 citations where it used to return zero. Two things still outstanding: reading a captured answer end to end against the screen, which is what flips `verified`, and the `+N` chips, which on that capture hid at least 2 more citations and made the 8 a subset the capture now says it is |
| Google AI Overviews adapter verified | **not done** | And its results never enter a cross-product aggregate: the default judge is a Google model |
| Popup: server state, adapter provenance, last capture, both actions, hide-the-dock toggle | **done, and run for real** | No longer just a shim. Loaded as a real extension on a real Perplexity answer: green light, adapter provenance, last capture with its warnings. The size bug that fixing this exposed is worth recording, because it was invisible in the shim: Chrome sizes a popup from the root element, and the width was set on `body`, so a 340px panel rendered in a 780px window |
| Audit without a terminal step | **done, and run for real** | The panel has rendered over a live page on both claude.ai and perplexity.ai. Three bugs came out of doing it that no test had caught: a hardcoded text colour that vanished when the panel followed the dark colour scheme, long URLs widening the panel until the page scrolled sideways, and five counters reading zero on a fetch-only run, which reads as "nothing checked out" rather than "nothing was checked". What has not happened is a clean run with verdicts since the last round of fixes |
| The audit and the capture are written to disk | **done** | `captures/` and `reports/`, both never overwritten, both gitignored because they hold answer text and quoted spans from fetched pages. Until today an audit existed only in the panel and closing it was the end of it, which was wrong for the same reason the capture is saved: an audit records what a set of pages said at one minute, and several will read differently next week |
| The server fails before it claims to be ready | **done** | It builds a judge and throws it away before it starts listening, so a missing package or a missing key stops it there with the fix printed, rather than surfacing two minutes into the first audit while the popup shows green. A taken port is explained the same way, including asking whatever holds it whether it is an older SaysWho server, which is the case that actually happens |
| Marking the product's own sentences in place | **not done** | Narrower reason than before: mapping payload offsets onto a live DOM that re-renders is separate work whose worst failure is a verdict beside the wrong sentence. The panel sits next to the page |

### The first live PDF, and what it cost

The PDF reader read a real cited PDF on its first outing. It also produced two bugs that no unit test could
have caught, because both are about how a real generator lays out a page rather than about how a
hand-built fixture does.

`Td` was treated as a line break. It is a text-position operator, and many generators emit it between
individual glyphs to kern them, so a newline went between every character and "(61.1%)" came out as
"(6 1 . 1 %)". The span guard then voided a correct verdict as `JUDGE_FABRICATED_SPAN`, which is the one code
published as a finding about the judge. The tool was about to accuse a model of inventing a quote its own PDF
reader had broken. Fixed by reading the operands: only a vertical move is a line break. Calibrated by sweeping
the horizontal threshold from 0 to 8 against the real document, where only inserting nothing gave the right
answer.

The second is unfixed and recorded rather than hidden. This document renders bullets through a symbol font
whose glyphs sit at letter code points, so a line reading "\u2022 Adults who..." extracts as "x Adults
who...". Two of the four voided spans are that. Following font encodings is beyond a stdlib reader, so a
fabricated-span count over PDF sources is inflated by an unknown amount and must be reported separately from
one over HTML until it is fixed. `FINDINGS.md` item 14.

Of the four voids re-audited: one was the `Td` bug, two are the bullet, and one is a genuine catch, where the
judge stitched two passages together with an ellipsis rather than quoting contiguously. Three of four were
this tool's fault.

## What changed on day 5, and what it means

Most of today went on the browser surface, and the pattern is worth recording because it bears on how much
the "done" rows above are worth. Seven bugs were found by loading the extension and looking at it, and the
test suite had caught none of them: a popup sized from the wrong element, invisible text on a dark panel,
long URLs pushing the page sideways, two character counts that measured different things, a warning naming
the wrong problem, a stale server holding a port, and an audit that existed nowhere but on screen.

Two of them, the language claim and a commit message describing a section that did not exist, were prose
rather than code, and prose had no gate at all. It has one now, and it was built the same way the other gates
were: by reintroducing each failure and watching it fire, rather than by trusting that it would.

Every one was in a row this file already called done. They were done in the sense that the code path existed
and was tested, which is exactly the distinction the "machinery exists and has never run" section above was
written to make, and the lesson is that the section should have been longer. A test suite over surfaces I
build and check myself confirms the thing behaves as I modelled it. It cannot tell me the model was wrong.

The Perplexity adapter is the clearest case in the other direction. Its citation extraction was not
subtly wrong, it found **zero of eight** citations, and it had passed every test since day 2 because the
tests asserted the anchors-only rule the adapter implemented. A probe of a real page took ten minutes and
settled it.

## What this table is for

If the core does not land by day 7, this table is what makes that a reported fact rather than an impression.
The rows above that say "not done" outnumber the ones that say "done" in the sections that produce numbers,
and that is the accurate picture on day 5. The blocker at the top has not moved all day.
