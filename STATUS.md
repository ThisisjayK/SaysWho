# Status table

`SCOPE.md` §0a promises this table: every core and stretch item marked done or not-done, with a reason, and
nothing quietly dropped. It is the honesty overlay's fourth item in §8.

Last updated 2026-08-14, day 8 of ten, where day 5 was 2026-08-11. 783 tests, and `tests/test_documents.py`
now checks that this number is true rather than leaving it to rot. This file carried the header "day 7" on
2026-08-14 while its own anchor made that date day 8, which is corrected here and is the smaller half of what
day 8 found.

**Day 7's line has been crossed and the core is behind it, with one row still open.** Every day 7 item is
done: the honest run, the metric readout, the fabricated-span figure checked before being described, the
plausibility audit, the trace table. What is not done is day 5's own deliverable, the gold set, which stands
at 6 human labels of a planned 30 to 40 and is the reason the run published no support rate.

**And the gold set got harder on day 8 rather than closer.** The honest run put verdicts over all 24 consumer
answers, so a blind labelling session over them is refused: `label_goldset.py` exits 3 and `--supplemental`
is the only way in, and supplemental labels are excluded from kappa by construction. The 6 labels that exist
predate the run by two and a half hours and are blind; two of them are comparable, which is the n=2 kappa.
Topping the set up would produce forty labels and move that number not at all. So the set is being rebuilt
blind on ChatGPT over ten frozen queries drawn with seed 20260812 before any capture existed, which also
gives the second product that §3's stratification always needed. `FINDINGS.md` item 22 has it, including the
half worth more than the scheduling: G4 checks that a gold set exists for this configuration, not that a
calibration does, so a wholly supplemental set would have opened it.

**The stratum changed on day 6, and it changed by being given up rather than delivered.** The
professional-research set was to be transcribed from my own AI history and that history is gone. Retyping
from memory was available and is refused, because `queries/README.md` rules it out in two places written
before there was any reason to want an exception. So the core runs on the consumer stratum, which is written,
frozen since day 1, and synthetic. Every number the core publishes now describes how this tool behaves on
questions nobody asked. §10 carries the reasoning and §7 carries the limitation at the top of its list.

`SCOPE.md` §0a carries the same nine core-and-stretch rows in summary form, because a reader of the design
document needs them there. **This file is the detailed one and the two are updated in the same commit.**
`TODO.md` remains the working list. Three places recording state is one more than is comfortable, and the
rule that keeps them honest is that §0a says the state and this file says why.

**Read the first two rows first.** One of them was the blocker for six days and is now a withdrawal; the
other is what the critical path moved to.

---

## The blocker, and what replaced it

| Item | State | Reason |
|---|---|---|
| Professional stratum assembled | **not done, and not deferred** | Entries had to be real questions I asked an AI tool during PM work, scrubbed per `queries/README.md`. The sessions they were to be transcribed from are gone. Retyping from memory is the only route left and it is refused: recall cannot be pulled chronologically, so it selects on what stuck, which correlates with how the tool performed and is invisible from outside; and a retyped question is reconstructed rather than transcribed, which converts §7's authorship caveat from a coverage limitation into a validity one. `queries/professional.toml` stays empty. It is not topped up with inventions and it is not filled with reconstructions labelled `real_scrubbed` |
| Captured answers to audit and label | **done, and split, day 6** | The new critical path. The consumer stratum is frozen and ready, and nothing has been asked yet, so there is nothing to audit or to label against. Captured by hand on day 6: 24 Perplexity answers, one per conversation, bound to CO-01 through CO-24, 51 citations, none uncited. The first pass captured 38 of those 51, because the extension's extractor stopped at the first citation selector that matched and Perplexity renders two shapes; the missing 13 were rebuilt from the stored pages rather than by re-asking, which is what storing them is for. `FINDINGS.md` item 20. Phase 1 then ran over all 24 with `--split-only`, giving 24 stored splits and 24 run records: **162 claims, 145 claim-source pairs, 43 uncited claims, 240 skipped units, and 42 of 51 sources auditable.** So the gold set's 30 to 40 pairs can be drawn from 145 rather than scraped together, and the unauditable classes it fills first are real: 7 `SOURCE_BOT_BLOCKED`, 1 `SOURCE_DEAD_LINK`, 1 `SOURCE_UNREACHABLE`. A second product would be a second pass and is what would let the gold set stratify across products. Two other things came out of the attempt. The installed watcher has never run once, because its plist still points at the pre-rename path, and that is the only reason capturing 24 answers would not have auto-audited all 24 and made a blind gold set impossible for this stratum. And nothing connects a downloaded capture to the question that produced it except the order it was made in, since the extension never sets `query_id`. Both are on `TODO.md` |

Everything below is either done, or waiting on the second row, or explicitly out of scope.

## Core, due day 7

Day 6's own row in §12 is items 4 and 5 below, and all three of them are done and written up. That is worth
saying plainly rather than leaving to be inferred from three ticks, and it is worth saying next to the reason
it is not reassuring: those were the items that depend on nothing but code.

| # | Item | State | Note |
|---|---|---|---|
| 1 | The full pipeline: splitting, fetch, judge, span check, three-way verdict | **done** | Runs end to end on a real capture. `sayswho/pipeline.py` is the single orchestration; the CLI and the harness both drive it |
| 1 | No confidence score anywhere | **done** | Two checks per surface: the key gate over every payload, and a vocabulary scan of every rendered file. The word "score" survives in four sentences, all refusing to produce one, allowlisted in the test |
| 1 | Unauditable claims excluded from every denominator by a hard contract check | **done** | Two levels, sources and claim-source pairs, plus voided verdicts. All three raise rather than warn |
| 2 | One stratum, now the consumer set | **changed on day 6** | The professional set cannot be assembled and is reported not-done above rather than deferred. The consumer set is frozen since day 1 and synthetic, and it carries the core. Reported as a downgrade in what the numbers describe, not as a substitution |
| 3 | Gold set of 30 to 40 hand-labelled claims | **not done, tooling now actually usable** | Format, four refusals, arithmetic and labelling tool were built and tested, and walking the workflow end to end on 2026-08-11 found two faults that would each have wasted the session: there was no way to produce a stored split without a judged run printing every verdict on the way past, and a gold set spanning more than one answer bound to no split at all, so G4 would have refused every capture it covered. `--split-only` and a list of split hashes checked by membership. `FINDINGS.md` item 16. A third and a fourth fault came out of the same walk: launched without a terminal the tool raised `EOFError` at the first prompt, and an answer audited earlier left verdicts that would anchor a labeller while tripping neither the timestamp refusal nor G4. `sayswho/prior_audit.py` scans `reports/` and `runs/` for a verdict over the same `answer_sha256` and refuses a blind session, with `--supplemental` as the way through rather than an override. Run against this repository it refuses, which is the correct answer. `tools/prep_goldset.py` now runs before a session: it draws the same sample the session will, warms the cache for any page missing from it, and reports what the afternoon will be. Building it found a fifth fault, which is that the stratification across G2 codes degrades silently to product-only when no run record is passed. The labelling itself is human work, and as of day 6 it needs captured answers rather than a stratum |
| 3 | n and confidence intervals reported honestly | **done** | `Rate` carries its n, a Wilson interval and its split count, and `Rate.render` is the only formatter, so no surface can print a bare percentage |
| 4 | Break attempt 5, prompt injection through a fetched page | **done** | Narrowed a published claim rather than confirming it. `BREAK_ATTEMPTS.md` |
| 4 | Break attempt 6, denominator contamination | **done** | Fires at both levels, and writing it found a third contamination path |
| 5 | Parity check between the extension and the headless pipeline | **done** | The real `render.js` runs in node over a payload the real Python built, compared state by state |

### Core items whose machinery exists and which have never run on real data

Listed separately rather than ticked, because "the code path exists" and "we have seen it work on a real
answer" are different claims and only one of them is currently true.

| Item | Why it has not run |
|---|---|
| ~~Honest run over the frozen stratum~~ | **Run, 2026-08-13.** 24 captures, 51 sources, 158 claims, 130 verdicts of which 125 stand, 7 minutes, 130 model calls, nothing halted. It printed no support rate, which is the deliverable rather than a shortfall: G4 withheld on 18 answers and `INSUFFICIENT_EVIDENCE` on 2 more, each naming its reason and both split hashes. `FINDINGS.md` item 21 |
| ~~Metric readout with n and CIs over real data~~ | **Produced.** `runs/day7/` holds the run record, the readout, `RUN_LOG.md` and the per-number trace table. Every rate it is entitled to print carries its n; every rate it is not names the gate that stopped it |
| Judge-human agreement | **Computed, and n=2.** Six human labels exist and four are on sources the judge was never asked about, so two were comparable and kappa came out 0.0 over them. At that n it is an arithmetic result rather than a measurement, and it is reported as one |
| ~~The PDF reader on live data~~ | **Run.** It read the `boston.gov` PDF cited by a real Perplexity answer, `SOURCE_OK`, 54,811 characters as of 2026-08-12. The count is dated because it has moved twice: 57,067, then 56,352, then this, as each fix stopped the reader inventing characters. Two earlier figures were left standing here and in `tools/reaudit_spans.py` after they stopped being true, which is the rot a prose gate cannot catch, since a number is not a path. Three extraction bugs came out of this one document, none of them from a test. See "The first live PDF, and what it cost" below |
| The thin-page flag on live data | Tested, and still never fired on a real capture: 51 more sources in the day-6 run and not one |
| The fabricated-span count as a finding about the judge | **Recomputed 2026-08-13, after checking the extraction behind every void, which §8 requires before it may be called a finding about the judge: 3 of 96 span-bearing verdicts are the judge stitching non-contiguous passages, and 1 of 96 is this tool inlining a `[44]` footnote marker the judge dropped.** All four voids were HTML sources and only 2 of 51 sources were PDFs, so the PDF-versus-HTML split is a fact about the sample. What follows is the earlier figure this replaces. **Withdrawn, not pending.** The earlier 1-of-16 figure was mostly this tool: three of four voids were caused by SaysWho and one was a genuine catch. The symbol-font bullet behind two of them is fixed as of 2026-08-12 (`FINDINGS.md` item 17) and that does not restore the count: those spans were quoted from an extraction this tool no longer produces, so only judging the fixed document settles them. Recomputed after that run, and reported separately for PDF and HTML |
| `EXTRACTION_SUSPECT`'s error direction | Only the gold set can measure it. Until then the writeup says the direction is chosen and the rate is unknown |
| The PDF garbled test's error direction | Same shape, one layer down. Two ratios, printable characters and spaces, decide whether decoded text is language or glyph numbers. Neither threshold is measured. It is set to refuse in the ambiguous case, because refusing costs coverage and passing garbled text produces a verdict that accuses a source |

## Stretch, days 8 to 10

| # | Item | State | Reason |
|---|---|---|---|
| 6 | Competitor head-to-head (§5a) | **not done** | Day 8 at the earliest. Until it runs, the §1b differentiator is described as structural rather than measured, and incumbent behaviour is attributed to their documentation. What the documentation check established: three of the four attach a confidence number to a verdict, and none of the four says what it does with a source it could not fetch. That is a fact about their pages, not their behaviour |
| (extra) | No API-sourced rate is published, enforced | **done** | Decided 2026-08-11 and held in `sayswho/rates.py` rather than in prose: `for_run` withholds every rate for a capture whose `source` is `api`, including the ones needing no gold set, and `aggregate` raises. No override parameter, because unlike a conflicted product there is no legitimate reason to want one. The per-domain slice is closed too, since a slice is still a rate |
| (extra) | Capture from a provider API | **done** | `sayswho/apicapture.py` and `tools/api_capture.py`. Produces an ordinary capture with `source="api"` so the whole pipeline works on it unchanged, stdlib only, no schema hardcoded. No rate derived from one is published, enforced in `rates.py` rather than promised in prose. `tools/compare_capture.py` measures how many citations a DOM capture missed, which is the number this path exists for |
| (extra) | A gate for prose | **done** | `tests/test_documents.py`. Paths and modules named in any document must exist, load-bearing claims are checked against the code, and the test count in this file is checked against the suite. Verified by reintroducing all three of day 5's real prose failures and confirming each one fires |
| (extra) | Prior art checked rather than asserted | **done** | All four tools in §1b verified against their own documentation, 2026-08-11. Two claims did not survive and both were tilted this project's way. `FINDINGS.md` item 12. Every row in the new §1b table is dated, and re-checking before submission is on `TODO.md` |
| 7 | ~~Consumer stratum run~~ Professional stratum run | **promoted, and swapped** | The consumer stratum stopped being stretch on day 6 and now carries the core, and being written and frozen on day 1 is exactly what makes that usable: it was authored before anything was known about what the professional set would produce. What sits in this row now is the professional stratum, not-done for the reason in the blocker table |
| 8 | Break attempts 1 to 4 | **all run, 3 held and 1 broke** | Run against the live judge 2026-08-11, `tools/break_attempts.py`, each declaring the failure it looks for before it runs. 2 held with no judge needed, because holding means the judge is never called. 3 held by the predicted route: the span was really on the live page and the drift layer voided it as `SPAN_ADDED_AFTER_GENERATION` anyway. 4 held, reading polarity rather than vocabulary. 1 broke, and not into the failure it declared, because its fixture ended by denying it reported any estimate and the judge read that denial as `CONTRADICTED`. 1b removes the denial and produces the declared failure: `PARTIALLY_SUPPORTED` for a claim the page never states, 4 of 4 calls, every span verbatim and on the page. `FINDINGS.md` item 15 |
| 9 | Per-domain reporting | **done** | `sayswho/domains.py`, built on `rates.py` so a slice and the aggregate cannot disagree about a denominator. G4 applies: a per-domain rate is still a rate. One readable pair gets counts and no percentage. The table leads with why sources could not be read, because at the core's n a low cell is a hypothesis about this pipeline before it is anything about a publisher |
| 9 | Gold set expansion beyond 40 | **not done** | Depends on the first 40 |
| (extra) | Crossref existence check for named citations | **done** | Built ahead of its window because the core is blocked on transcription rather than on build time. The constraint is enforced rather than intended: no document text in any record, `rates.py` does not import it, and a test asserts the word does not appear there |
| (extra) | Split `SOURCE_UNREACHABLE` into dead-link and bot-blocked | **done** | `SOURCE_DEAD_LINK` and `SOURCE_BOT_BLOCKED`. Done ahead of the stretch window because §5a's dead-link stratum cannot report a dead-link rate until the code distinguishing one exists |
| (extra) | Widen `CITATION_NOT_LINKED` patterns and measure their recall | **half done** | Patterns widened as far as is safe without knowing recall (PMID, PMC, arXiv). The measurement harness is built; marking an answer by hand is mine to do, and until then the count is a floor of unknown depth |

## Extension surface

| Item | State | Note |
|---|---|---|
| Capture on claude.ai, chatgpt.com, perplexity.ai, Google | **done, with one rule attached** | With auto-scroll, hash, stored page and incompleteness warnings. **One question per conversation**, because `saysWhoFindAnswer` returns the highest-citation container on the page rather than the newest answer. On a single-answer page they are the same and on a thread they are not, so a capture taken mid-thread can be an earlier answer wearing the current question's id. `TODO.md` claimed this captured the last answer since day 2 and the code has never done that. One correction today worth naming: the rendered-versus-DOM character counts were measuring different things, so a table in an answer made `innerText` longer than `textContent` and a capture reported more characters rendered than the DOM contained. The display bug was the small half. An inflated rendered count eats the gap the check exists to find, so an answer half of which was never laid out could have reported as complete |
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

The second was recorded as unfixed and was fixed on 2026-08-12, which is `FINDINGS.md` item 17 and is worth
reading as a finding about the note rather than about the PDF. This document renders bullets through a symbol
font whose glyphs sit at letter code points, so a line reading "\u2022 Adults who..." extracted as "x Adults
who...", and the note here said that following font encodings is beyond a stdlib reader. The document carried
its own reverse table, as an ordinary Flate stream, inside a compressed object stream. Two two-byte fonts,
nineteen codes, no conflicts, and a second bullet bug nobody had noticed: WinAnsi 0x95, decoded into a control
code and stripped as never-content, which deleted evidence rather than corrupting it.

Of the four voids re-audited: one was the `Td` bug, two are the bullet, and one is a genuine catch, where the
judge stitched two passages together with an ellipsis rather than quoting contiguously. Three of four were
this tool's fault. **The two bullet voids are still not overturned**, and the fix is why: re-checked against
the corrected extraction they now get 305 of 549 characters through, where the bullet used to stop them at
about 170, and then fail on `non-Boston`, because the judge quoted `nonBoston` from an extraction that had
dropped an en dash. A span quoted from text this tool no longer produces cannot be settled by re-checking. So
the fabricated-span count over PDF sources stays separate from one over HTML, and stays withdrawn.

## What changed on day 8, and what it means

Nothing measurable. No run, no labels, no new rate. What day 8 did was check the documents against the code
they describe, and then check what tomorrow's session would actually produce, which turned out to be the
larger of the two.

**The blind gold set for the consumer stratum is gone, spent by the run that produced the numbers.** Written
up as `FINDINGS.md` item 22 and summarised at the top of this file. Two things in it are worth repeating
here, because they are about the controls rather than the schedule. `prior_audit` fires in one direction
only, refusing a labelling session after a run and never a run before a session, so the order that costs a
day is the one nothing watches. And `gates.g4_calibration_exists` verifies that a gold set exists for this
judge, prompt version and split, without looking at whether any label in it is blind or how many there are,
so forty supplemental labels would open the gate on a kappa of two. The invariant in `CLAUDE.md` that G4 is
what stands between this project and an uncalibrated rate is, as written, stronger than the code behind it.
That is recorded rather than patched, because a gate should not be changed on the day the change would be
convenient.

**The working list was reporting work that had already shipped.** `TODO.md` carried a row saying
`extracted_pair` in `tools/label_goldset.py` ran the HTML extractor over raw bytes, so a cited PDF was
compared against `endstream endobj` noise and every passage recorded as unchecked. That was fixed on day 7 in
`c52a808`, routed through `fetch.text_pair` for both tools that need it, with a test asserting a PDF is read
as a PDF and a second running the same bytes through the helper and the fetcher to check they agree. The row
stayed unticked, so the file spent a day describing a bug that no longer existed, and the fix was nearly done
twice. This is the shape `FINDINGS.md` item 17 named: a written limitation outliving the thing it limits.
Item 17 counted two instances of it. This is the same pattern pointing the other way, since here the document
overstated what was broken rather than what was impossible.

**So the other 48 open rows were audited against the repo rather than reread.** All 48 are correctly open.
Checked directly: `tests/parity/` holds only `render_in_node.mjs`, so there is still no node parity test for
the extractor; the installed watcher plist still names `/Users/jayanthadityak/Finall Project/` with two Ls;
`content.js` still calls `saysWhoBuildCapture` without a `queryId`, so `query_id` defaults to `UNASSIGNED`;
`extract.py` still imports only `re`, `unicodedata` and `html.parser`; `verifiedSelectors` is empty for
ChatGPT, Perplexity and Google, and Claude holds only the Research artifact selector, not the chat one; the
thin-page flag appears nowhere in `runs/day7/run.json`; and no head-to-head artefact, hand-marked answer,
grounded API call or `contrib/jayanth-says-who` branch exists anywhere.

**Two rows misreported themselves and were reworded.** One was a sentence carrying a checkbox it could never
satisfy, which counted as outstanding work every time the file was totalled. The other was labelled "the case
study half" while `CASE_STUDY.md` is written and ticked two rows above it; what is actually open there is
that nobody but the author has ever run the install steps, so the thirty-second claim is a guess by the one
person who already knows which folder to pick.

**The README was rewritten for somebody arriving at the repo rather than somebody who built it**, and
checking it against the code found two things it had wrong. Its verdict list mixed the judge's internal
classes with the six states `report.py` renders, so it advertised a `NOT_SUPPORTED` verdict the judge never
emits, the real one being `NOT_FOUND_IN_SOURCE`. And the gold set tools were listed without the `--split` and
`--out` arguments they require, so the commands as printed would have failed. Both are fixed. The limits and
the withheld-rate section stayed, shortened rather than dropped, because a README that cut them to read
better is the move §8 forbids. Separately, `--judge`'s help string still named `ANTHROPIC_API_KEY` from
before Gemini became the default, which would have sent a reader looking for a paid key to run the free path.

## What changed on day 6, and what it means

Three items landed, and the reason they are worth a section is that all three had been recorded here or in
`TODO.md` as blocked, and none of them was.

**The prior-audit guard**, which was the weakest control in the project. Two refusals already stood between a
gold set and the judge's answers and neither could see the case: `goldset.agreement` compares a label's
timestamp against the run it is compared with, so labels written today pass against a run made yesterday, and
G4 ties to the split, which differs for a second audit because Phase 1 does not repeat itself. An answer judged
last week therefore left verdicts that would anchor a labeller and trip nothing at all, and for a day the only
control was a sentence in a banner asking the labeller to remember. `sayswho/prior_audit.py` now scans
`reports/` and `runs/` for a verdict over the same `answer_sha256`, and the tool exits before asking its first
question. Run against this repository it refuses, which is the correct answer and not a comfortable one: the
only real split on disk has two audits behind it, so the rehearsal needs `--supplemental`.

**Precomposed against decomposed accents in the span guard**, recorded as blocked on the per-character index
`report.py` builds. It was blocked on a belief about that index rather than on the index. Composing cannot be
done one character at a time; decomposing can, and it reaches the same place from both sides.

**Symbol-font bullets in PDFs**, recorded here as unfixed with a reason attached: following font encodings is
beyond a stdlib reader. True of the general case, false of the document in hand, which carried its own reverse
table inside it. `FINDINGS.md` item 17.

**What the three have in common is the shape of the mistake, and it is a new one for this file.** Day 5's
lesson was that a tested code path is not a run. This is different: each of these was a limitation stated with
a reason, and a reason makes a limitation read as settled. Nothing in the suite can check the word "beyond",
and two of the three sentences had been copied into three or four documents each, which is how a guess acquires
the authority of a decision. The day 5 section below says a test suite over surfaces I build myself cannot tell
me the model was wrong. This says the same thing about prose: the limitations section is exactly as unaudited
as the results section used to be, and it is read more charitably.

**And then the blocker was not moved but withdrawn.** Late on day 6 the professional stratum turned out to be
unassemblable rather than untranscribed: the sessions are gone. Retyping from memory was refused, for two
reasons `queries/README.md` had already written down, and the core moved onto the frozen consumer stratum
instead. That is a smaller project than the one §0 describes, and the honest framing is not that a blocker
cleared. It is that the thing the blocker was protecting has been given up, and the numbers that follow
describe a tool rather than anyone's research.

What it does change is what stands between here and a number. It is no longer transcription, which only I
could do. It is captured answers, which is browser work, and then the labelling hour.

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
and that is the accurate picture on day 6 as it was on day 5. The blocker at the top has not moved in two days.

Day 7 is tomorrow, and after the day 6 decision the core can plausibly be complete on it: the stratum exists,
capturing answers against it is an afternoon in a browser, and the gold set is an hour after that. What it
will not be is the core §0 describes. Item 2 is reported changed and item 7 reports what was lost, which is
the §0a promise being kept in the one case it was written for: an item that did not happen is named, with the
reason, rather than quietly becoming an item that did.
