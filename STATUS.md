# Status table

`SCOPE.md` §0a promises this table: every core and stretch item marked done or not-done, with a reason, and
nothing quietly dropped. It is the honesty overlay's fourth item in §8.

Last updated 2026-08-11, day 5 of ten.

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
| `SOURCE_NOT_HTML` and the thin-page flag on live data | Tested, never fired on a real capture. This answer cites no PDFs; the Claude research report cites one |
| `EXTRACTION_SUSPECT`'s error direction | Only the gold set can measure it. Until then the writeup says the direction is chosen and the rate is unknown |

## Stretch, days 8 to 10

| # | Item | State | Reason |
|---|---|---|---|
| 6 | Competitor head-to-head (§5a) | **not done** | Day 8 at the earliest. Until it runs, the §1b differentiator is described as structural rather than measured, and incumbent behaviour is attributed to their marketing copy |
| 7 | Consumer stratum run | **not done** | Written and frozen on day 1 so it cannot have been shaped by professional results. Running it needs the core to land first |
| 8 | Break attempts 1 to 4 | **not done** | Itemised with expected failure directions in `BREAK_ATTEMPTS.md` rather than left as a blank |
| 9 | Per-domain reporting | **not done** | At the core's n the per-domain cells would be near-empty, which is why it was stretch |
| 9 | Gold set expansion beyond 40 | **not done** | Depends on the first 40 |
| (extra) | Crossref existence check for named citations | **not done** | Roughly half a day, and only if the core lands on time. The constraint if it is built: check existence, never support |
| (extra) | Split `SOURCE_UNREACHABLE` into dead-link and bot-blocked | **done** | `SOURCE_DEAD_LINK` and `SOURCE_BOT_BLOCKED`. Done ahead of the stretch window because §5a's dead-link stratum cannot report a dead-link rate until the code distinguishing one exists |
| (extra) | Widen `CITATION_NOT_LINKED` patterns and measure their recall | **not done** | The current count is a floor and the writeup keeps saying so |

## Extension surface

| Item | State | Note |
|---|---|---|
| Capture on claude.ai, chatgpt.com, perplexity.ai, Google | **done** | With auto-scroll, hash, stored page and incompleteness warnings |
| Claude `.bg-surface-3 .standard-markdown` verified | **done** | Read end to end against the screen, corroborated by a DOM probe |
| Claude `.font-claude-response` verified | **not done** | The chat path has never been exercised |
| ChatGPT selectors verified field by field | **not done** | The capture works; it has not been checked |
| Perplexity adapter trusted | **not done** | Four source chips carry no anchor at all, so roughly a third of its citations are not in the DOM as links |
| Google AI Overviews adapter verified | **not done** | And its results never enter a cross-product aggregate: the default judge is a Google model |
| Marking on the product page itself | **not done** | Needs a local server the extension can talk to. A JavaScript reimplementation of the gates would be the second implementation the parity check exists to compare. `SCOPE.md` §1a was corrected to say capture and render |

## What this table is for

If the core does not land by day 7, this table is what makes that a reported fact rather than an impression.
The rows above that say "not done" outnumber the ones that say "done" in the sections that produce numbers,
and that is the accurate picture on day 5.
