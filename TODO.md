# SaysWho build checklist (TODO)

Everything the project owes, in the order it has to happen. Derived from `SCOPE.md` §0a (the core and stretch
split), §8 (the rubric), and §12 (the schedule).

Two rules for keeping this file honest. Nothing gets ticked because it was started. And a stretch item that
does not happen gets marked not-done with a reason rather than deleted, because §0a promises the writeup
reports it either way.

## Where things actually stand

Day 5 of ten. Days 2, 3, 4 and 6 are done; days 1, 5 and 7 are blocked on the same thing.

**Everything still open is either mine to do by hand or waits on something that is.** The professional
stratum has to be transcribed out of my own AI history and scrubbed, and it is the input to the gold set,
the honest run and every published number. Items below marked **mine to do** are the ones no amount of
building moves forward.

Day 1, partially done.

- [x] Consumer stratum written, 24 questions across four domains, each with a cost of error
- [x] Consumer stratum frozen, hash manifest in `queries/FREEZE.json`
- [x] Freeze tooling built, and all three failure paths tested rather than assumed
- [x] Repo created, scope document and query set committed
- [ ] Professional stratum assembled. Blocked on pulling real queries out of my own AI history
- [ ] `SCRUB_LOG.md` filled in and the drop count recorded
- [x] `DATA_CONTRACT.md` written, before any fetch has happened
- [ ] Reply sent to Prof. Brown with `SCOPE.md` attached. Parked for now, deliberately

## Blocking the whole schedule

- [ ] Pull the queries. Search Claude, ChatGPT and Perplexity history for answers that came back with
      citations attached. Those are the population. Answers with no footnotes produce nothing to audit
- [ ] Scrub each one per `queries/README.md`. Employer names, project codenames, colleague names, identifying
      figures, markets narrow enough to identify the company
- [ ] Log every query that entered intake in `SCRUB_LOG.md`, kept or dropped, with a reason code
- [ ] Write `cost_of_error` for each survivor. This is pre-registration and it enters the freeze hash
- [ ] Flip `professional.toml` status to `ready` and freeze it
- [ ] Publish the drop rate. A suspiciously low one is itself evidence the intake was pre-filtered

## Day 1: the data contract

- [x] `DATA_CONTRACT.md`: respect `robots.txt`, one request per second per domain, identifying User-Agent with
      a contact address, every fetch cached to disk so reruns audit the same bytes
- [x] No authenticated fetches and no paywall circumvention. A paywall is a legitimate `UNAUDITABLE` outcome
      and routing around it would corrupt the measurement
- [x] Write down the model call metering and logging policy before any calls are made
- [x] `SOURCE_ROBOTS_EXCLUDED` added to the G2 outcome table in `SCOPE.md` §3. Writing the contract surfaced
      it: unreachable means we tried and could not, robots-excluded means we chose not to try
- [x] Implement the contract in the fetch layer, and write the tests that prove the enforced half of §10 is
      actually enforced rather than merely written down. `tests/test_fetch.py` runs against a real local HTTP
      server, so the politeness rules are asserted on what went over the wire

## Day 2: capture and fetch

Python side done. Browser side captures, and now audits in place through the local server, but the selectors
for three of the four products have never been checked field by field against a real page.

- [x] Fetch layer implementing the data contract. `sayswho/fetch.py`, stdlib only
- [x] Phase 0 gate G0: zero inline citations returns `NO_CITATIONS` and halts. An uncited answer is a
      different object, not a zero percent answer
- [x] Phase 2 gate G2 returning `SOURCE_OK`, `SOURCE_UNREACHABLE`, `SOURCE_EMPTY`, `SOURCE_PAYWALLED` and
      `SOURCE_ROBOTS_EXCLUDED`
- [x] Capture record with a verbatim answer hash. A capture edited after the fact is rejected on load
- [x] Append-only fetch cache, so a rerun audits the same bytes
- [x] The denominator contract, and the test that forces the violation and confirms it raises
- [x] The no-confidence-number check, and the tests that confirm it rejects nested confidence fields
- [x] 31 tests, run against a real local HTTP server rather than a mocked `urlopen`, because the politeness
      rules are about what actually goes over the wire
- [x] End to end run over a fixture capture, three cited URLs, three different G2 codes
- [x] `SOURCE_DRIFTED` and the Wayback lookup. Containment rather than Jaccard, so a page that only grew is
      not called drift. Both similarity numbers are recorded, so the 0.80 threshold is inspectable rather
      than load bearing on its own
- [x] No snapshot reports drift as unknown, never as unchanged. Tested, because converting missing data into
      a clean result is the exact move this project refuses
- [x] Content-Encoding decoding. Wayback replays archived pages gzipped, and undecoded they extracted as
      binary noise that passed the length threshold as `SOURCE_OK` and then matched nothing. Every archived
      comparison reported drift and every source became unauditable: a clean consistent result that was
      entirely an artefact. Regression test added
- [x] MV3 extension skeleton: manifest, per-product adapters, capture builder, content script, service
      worker. Captures the last answer, hashes it, downloads JSON the harness reads
- [x] Capture-side sha256 matches Python's, so both sides agree on what the input was. The beginning of the
      §9 parity check, not the whole of it
- [x] Adapter provenance travels with every capture, including whether the adapter has been verified
- [x] Claude selectors corrected against the real page. `.font-claude-message` never existed; it is
      `.font-claude-response`, and a Research report lives in `.bg-surface-3 .standard-markdown` rather than
      in the chat column at all
- [x] Container chosen by citation count rather than selector order. With the artifact panel open, both the
      chat summary and the report match, and only one has anything to audit
- [x] Page furniture excluded from citations, and the exclusion counted into the capture. A large
      `chrome_links_excluded` means the exclusion list is eating real citations
- [x] Claude `.bg-surface-3 .standard-markdown` verified: text read end to end against the screen, citation
      count corroborated by a DOM probe, and re-extraction from the stored page returns the same citation
      set. Verification is now recorded per selector rather than per adapter, since exercising one path says
      nothing about the other
- [x] Parity check demonstrated on a real page. The extension's JS extraction and the Python extraction from
      the stored markup agree on container and citations
- [ ] Claude `.font-claude-response` verified. The chat path has never been exercised. **Mine to do:** it needs a real answer on a real page
- [ ] ChatGPT selectors verified. The capture works but has not been checked field by field. **Mine to do**
- [ ] Perplexity: four source chips carry no anchor at all, so roughly a third of its citations are not in
      the DOM as links. Needs a probe of what those chips actually are before the adapter can be trusted.
      **Mine to do**
- [x] Auto-scroll before capture, and `rendered_chars` against `dom_chars` so unrendered text is reported
      rather than silently missing
- [x] `extension_version` stamped into every capture, so a stale content script announces itself
- [x] Raw page HTML stored with every capture, and `python3 -m sayswho.reextract` re-runs selection over the
      same bytes. A selector fix no longer re-runs the query, so a selector change and an answer change
      cannot arrive together and be mistaken for each other
- [x] Stored pages gitignored. A full claude.ai page carries the sidebar and therefore the titles of every
      other conversation
- [ ] Google AI Overviews adapter verified through the same code path, no separate asterisk. **Mine to do**
- [x] Remove the terminal step without running anything all day. `tools/install_watcher.sh` installs a
      launchd agent using `WatchPaths`, so the job starts on a change to the capture directory and exits
      when its queue is empty. No daemon, no polling, no port. The key is sourced from the shell profile
      rather than written into the plist, per `DATA_CONTRACT.md` §8
- [x] The local server, so the audit happens without leaving the page. `python3 -m sayswho.server`, and an
      "audit here" button that posts the capture and draws the result in a panel. The gates and the span
      guard stay in Python, which is the point: `audit.js` posts JSON and draws what comes back, and a test
      asserts it does not mention a verdict name. Loopback bind, origin allowlist, no wildcard CORS, freeze
      check at startup, citation cap. `DATA_CONTRACT.md` §9a
- [ ] Marking the product's own sentences in place. Still not done, and now for a narrower reason: the
      payload carries offsets into the answer text and mapping those onto a live DOM that re-renders as you
      scroll is separate work whose worst failure is a verdict beside the wrong sentence. The panel is next
      to the page rather than on it
- [ ] Exercise the browser leg. The server is tested and the package is checked as far as it can be without
      a browser, but whether the panel renders correctly on claude.ai has never been seen. **Mine to do**
- [x] Span display quality, as far as display can fix it. `report.span_focus` marks the sentence inside the
      span that bears on the claim, by content-word overlap, deterministically. The whole span still ships
      and still scrolls, because a shortened span is not evidence, so this says where to look rather than
      deciding what counts. Two parity tests: the focus is marked, and "Like us on Facebook" is still there.
      The underlying problem is still extraction quality and this does not touch it
- [x] Marking UI. Built once there were verdicts behind it. `sayswho/report.py` computes every state,
      `extension/src/render.js` draws it, and the harness embeds that same file in a standalone HTML report
      via `--report`, so the extension and the harness cannot show different things. Five states, because
      three would have had to collapse "we could not read the source" into "unsupported": supported, not
      supported by the cited source, sources disagree, could not verify, no citation to check. Hovering a
      marked sentence gives the cited page's own words, the ones the span guard confirmed are on the page

Done means an answer captured, hashed, and every cited URL fetched with a G2 code attached. That works today
against a handwritten fixture. It does not yet work against a real answer, because nothing captures one.

## Day 3: claim splitting and the judge

- [x] Phase 1 claim extraction, bound to citation markers by matching marker text to normalised URLs,
      labelled model-inference in every output surface
- [x] Gate G1: skipped lines carry a reason and are counted. `skipped_count` and `uncited_claim_count` are
      both published
- [x] Phase 3 judge returning `SUPPORTED`, `PARTIALLY_SUPPORTED`, `NOT_FOUND_IN_SOURCE`, `CONTRADICTED`,
      via structured outputs so a malformed verdict is not a parse failure
- [x] Gate G3, the span guard, with the test that hands it a fabricated span and asserts the void
- [x] The judge is never called on a source that is not `SOURCE_OK`, asserted by a test that checks the
      model was not called at all
- [x] Break attempt 5 built and tested, and it revised §6: an injection that dictates its own span defeats
      the guard, because dictating the span puts it on the page. Kept as a passing test of the failure
- [x] Metering per call, budget cap that halts and records the halt, cost estimated only for known models
- [x] Source document sent as a cached prefix, so several claims citing one page pay for it once
- [x] Gemini free-tier judge, chosen so the run costs nothing. Same `JudgeClient` protocol, so the pipeline,
      the gates and the span guard are untouched by the swap
- [x] Free-tier rate limits waited out with backoff rather than dropping the claim, and the waiting time
      recorded. A claim skipped for quota is a hole in the denominator
- [x] Refusals, truncated answers and empty answers all void rather than half-parse
- [x] Ran end to end against a real ChatGPT capture on `gemini-3.5-flash-lite`. 20 claims, 13 judgements,
      0 fabricated spans out of 7 span-bearing verdicts. Model pinned rather than aliased, because
      `gemini-flash-latest` would move underneath the gold set and G4 would never notice
- [x] **Define the unit of the support rate.** The claim-source pair, decided and pinned by a test in
      `sayswho/rates.py`. It is the question the tool asks (does this cited page say what this sentence
      says) and the unit a human labels in, so the gold set and the rate count the same objects. The cost is
      that a claim citing five sources weighs five times as much, so `claim_level_rate` publishes the other
      unit beside it. Claim #009 is 1/3 in pairs and 1/1 in claims, and both numbers ship. §5 rewritten
- [x] **Look at the 139 skipped lines.** Dumped and read. `--dump-skipped` added, because the run had been
      publishing the skip count and discarding the text, so the check was impossible rather than merely
      undone. The split is now carried in the `--json` record too. Three things came out of reading them,
      written up as `FINDINGS.md` items 8 and 9: the re-run returned 119 rather than 139 on the identical
      capture, tables are skipped whole so one skipped line held about ninety checkable cells, and four
      uncited factual lines were skipped as framing, which makes `uncited_claim_count` a floor
- [x] Drift false positive fixed. Page-level containment is no longer a gate: it now only answers "is this
      still the same document" at a threshold near zero. Whether a change mattered is decided per claim, by
      checking the judge's span against the archived version. A span that postdates the answer voids the
      verdict as `SPAN_ADDED_AFTER_GENERATION`; a reference list that churned no longer excludes anything
- [x] Re-run the ChatGPT capture and confirm the PubMed source now survives as auditable. Done. PubMed came
      back `DRIFT_PAGE_CHANGED` at containment 0.6210, the same number that used to exclude it, and stayed
      auditable. Auditable sources went from 6 of 9 to 7 of 9
- [x] Bind captures to the frozen query set. `sayswho/queryset.py` plus `tools/bind_capture.py`. An unbound
      capture is still audited and its per-claim verdicts still stand; it is excluded from every aggregate,
      because a rate has to be able to say what it is a rate over. Three refusals rather than one, since
      unbound, added-after-the-freeze and never-heard-of-it need three different actions
- [x] **Decide whether Google AI Overviews stays in the audited set.** It stays, reported per-product with
      the conflict stated, and `rates.aggregate` raises rather than folding it into a cross-product number.
      The refusal is in the code because a disclosure in a paragraph does not survive being copied into a
      slide. The clean fix, judging those captures with the Anthropic client, needs a second gold set under
      G4 and was costed and not taken. §7 rewritten
- [x] **Fix the unit G1 skips in.** Taken the second way: `sayswho/skips.py` counts skipped content in
      table rows, list items and sentences, and both rates are printed together, always. The answer text is
      hashed and verbatim, so re-splitting it before the splitter sees it was never available. The gap
      between the two numbers is the finding, so it is shown rather than closed. `FINDINGS.md` item 9
- [x] **Pin the gold set to a stored split.** `sayswho/splits.py`, plus `--split` and `--save-split`. A
      stored split carries the `answer_sha256` it came from, the claim prompt version and a `split_sha256`
      over its own claims, and binding it to a different answer, a different prompt version or an edited
      file all raise rather than falling back to re-splitting. Claim ids are now content-addressed, so an id
      means one sentence rather than one position: under the old positional ids a gold set would have
      silently relabelled rather than merely lost claims. G4's tuple is now judge, prompt version and split
- [x] Measure the spread rather than guessing at it. `tools/split_spread.py`, Phase 1 only, five runs for
      nothing on the free tier. claims 15 to 21, skipped 104 to 156, uncited 0 to 9
- [x] Every published rate derived from a split states how many splits it is over. `Rate.splits` is a field
      rather than a convention, and `Rate.render` is the only formatter, so no surface can print a bare
      percentage without it
- [x] Count the uncited factual lines currently landing in the skip list. `skips.uncited_floor` reports the
      published count and, beside it, the skipped units carrying a number or two proper nouns. Still a
      floor, and now with a measured distance under it instead of an unknown one
- [x] **Stop publishing extraction failures as citation failures.** Every way the tool fails to read a page
      came out as `NOT_FOUND_IN_SOURCE`, the one verdict with no span and therefore no G3 check, and the one
      that accuses the product. Four stdlib mitigations: `SOURCE_NOT_HTML` with a `%PDF-` sniff, SVG and
      `img alt` extracted, a thin-page flag, and the extraction check that voids a not-found as
      `EXTRACTION_SUSPECT` when the claim's own numbers are in the markup but not in the extracted text.
      `FINDINGS.md` item 11
- [x] `DATA_CONTRACT.md` §5 corrected. It claimed Readability and PDF parsing, and the code had neither
- [ ] Measure which way `EXTRACTION_SUSPECT` errs. It is biased on purpose, towards losing coverage rather
      than towards accusing a product, but neither its false positive nor its false negative rate is known.
      The day 5 gold set is the only thing that can measure it, and the writeup says so until it does
- [ ] Extend the extraction check to qualitative claims, or accept that it cannot cover them and say so.
      It fired on none of the six `NOT_FOUND_IN_SOURCE` verdicts in the guards re-run, and checking by hand
      showed none of the six carried a number or a dropped proper noun. Recorded in `SCOPE.md` §7
- [x] Fix the extraction check's first two live firings, both false positives. `extract.raw_text` was
      written for the comparison and never wired in, so the guard was matching claim tokens against raw
      markup: "Case" hit a `switch` statement and "Transportation" hit a nav link. The raw pass now excludes
      site furniture as well as scripts, and both cases are regression tests. `FINDINGS.md` item 11
- [ ] Exercise `SOURCE_NOT_HTML` and the thin-page flag on live data. Both are tested and neither has fired
      on a real capture, because this answer cites no PDFs. The Claude research report cites one
- [x] Label extraction failures separately in the gold set. Solved with a deterministic check rather than a
      second opinion: the labeller pastes the passage they found, and if it is on the page and missing from
      what `extract.py` produced, `goldset.attribution` assigns that disagreement to the extractor and
      reports a second kappa with those pairs removed. A floor on both counts, and it says so
- [ ] Decide on a real extractor. `sayswho/extract.py` is behind a function boundary so trafilatura or
      readability-lxml is a one-line swap, and it would fix tables, images and article-body detection at
      once. Cost is the stdlib-only property of the extraction layer. Not taken yet

## Where day 3 left things

- [x] Pipeline runs end to end on a real capture: 9 sources, 6 auditable, 20 claims, 13 judgements
- [x] 0 fabricated spans out of 7 span-bearing verdicts. Small sample, reported as one
- [x] G4 held: the run refused to print an aggregate support rate, with the reason
- [ ] The open items above are all from reading that run's output rather than from the plan

Re-run on 2026-08-07, same capture, after the drift fix. 9 sources, 7 auditable, 20 claims, 15 judgements.
PubMed survived. One verdict voided as `JUDGE_FABRICATED_SPAN`, 1 of 9 span-bearing, against 0 of 7 on day 3.
That is 1 of 16 across both runs and it is not a rate, but the guard has now fired on ordinary output rather
than only on the test built to trip it. `FINDINGS.md` item 10.

## Day 4: gates and the contract check

- [x] Unauditable claims excluded from every denominator, enforced by a hard contract check. Two levels now:
      `gates.auditable_denominator` counts sources, `rates.standing_denominator` counts claim-source pairs,
      and both raise rather than warn. A voided verdict leaves the numerator and the denominator together,
      so a fabricated span cannot become evidence against a product
- [x] `INSUFFICIENT_EVIDENCE` when more than half an answer's claims are unauditable, and no number printed.
      Counted in claims rather than pairs, because the question is how much of the answer could be checked
      and a reader thinks in sentences. The boundary is inclusive: exactly half is still insufficient
- [x] Gate G4: refuse to print aggregate rates when no gold set exists for the current judge and prompt
      version. Per-claim verdicts still emit. The tuple is judge, judge prompt, claim prompt and
      `split_sha256`, and each mismatch is reported separately because the four need four different actions
- [x] Rates carry what §5 promises: n, a Wilson interval, the unit, and how many splits they are over. The
      interval field is `interval_95` rather than `confidence_interval`, because the no-confidence-number
      gate walks keys and it is not getting an exception list
- [x] Test asserting no confidence number appears anywhere in any output surface. Two checks per surface,
      because either alone has a hole: the key gate over every structured payload, and a vocabulary scan of
      every rendered surface. The word "score" survives in four sentences, all of which refuse to produce
      one, and the allowlist is in the test so a fifth use has to be added on purpose
- [x] Headless harness runnable end to end over the frozen query set. `sayswho/harness.py` and
      `tools/run_stratum.py`, writing four artefacts: the run record, the metric readout, `RUN_LOG.md` and
      the per-number trace table. Run today it prints an honest nothing and says which kind of nothing
- [x] One pipeline, not two. `sayswho/pipeline.py` holds the loops and both the CLI and the harness drive
      it, so the harness could not become a second orchestration that quietly disagrees about which sources
      reach the judge
- [x] `freeze_queries.py check` wired to run before every capture, so a tuned set fails the run. Now on all
      three paths: the watcher, the interactive `sayswho.cli`, and the harness. `--skip-freeze-check` exists
      for captures outside the frozen set and the run says so in its output

Done means pytest with each gate failing on its target bug, not merely present.

## Day 5: the gold set

The machinery is built and tested. What is left on this list is the labelling itself, which is mine to do.

- [x] Gold set file format, its four refusals, and the arithmetic. `sayswho/goldset.py`: bound to one
      `split_sha256`, tamper-evident over every field of every label, blind labels refused if they postdate
      the judge run, and labels outside the vocabulary rejected on load
- [x] The labelling tool. `tools/label_goldset.py`, which refuses to open a file carrying judge output,
      draws a reproducible seeded sample stratified across products and G2 codes, and saves after every
      single label
- [x] Ask the labeller for the passage they found, and check it against our own extraction. A passage that
      is on the page and missing from `extract.py`'s output makes the resulting disagreement the extractor's
      rather than the judge's, which is the one way to separate two problems with the same symptom
- [ ] Label 30 to 40 claims by hand, before looking at any judge output. **Mine to do.** Blocked on the
      professional stratum existing
- [x] Stratification, as far as blind labelling permits. Products and G2 codes are knowable before any model
      runs and are stratified on, with `UNAUDITABLE` reached first. Verdict classes are the judge's output,
      so a blind sample cannot stratify on them and a sample that did would not be blind. If `CONTRADICTED`
      comes back empty the answer is a supplement labelled afterwards, excluded from kappa and reported
      separately. This is a correction to §3 Phase 4 as written, not a shortcut around it
- [x] Commit the labels with a timestamp that precedes the judge run. Enforced: `goldset.agreement` raises
      if any blind label postdates the run it is being compared against
- [x] Per-class precision and recall, plus Cohen's kappa with its confidence interval. Each class carries
      its own n, and perfect agreement on a single class reports no interval rather than a flattering one
- [ ] Try to recruit a classmate to double-label 10 to 15 claims. **Mine to do.** If nobody is available, say so plainly and
      treat my labels as a single-rater ceiling rather than ground truth

## Day 6: break attempts and parity

- [x] Break attempt 5, prompt injection through a fetched page, written up at the resolution the guard
      actually provides. `BREAK_ATTEMPTS.md`. An injected page can still supply a real on-page span, so the
      guard rules out a verdict with no textual basis, which is not the same as defeating injection, and the
      published claim says the second thing
- [x] Break attempt 6, denominator contamination. Forced at both levels, sources and claim-source pairs,
      and both raise. A third variant added while writing it: a voided verdict counted as standing, which
      is the same contamination arriving through the judge rather than through the fetcher
- [x] Parity check: the extension and the headless harness produce identical verdicts on identical inputs,
      verified by test. `tests/test_parity.py` runs the real `render.js` in node over a payload the real
      Python built and compares what appeared on screen, state by state, against what Python decided. Not a
      test that the file contains no verdict logic, which would be a test about the shape of a file

## Day 7: the core is done

- [ ] Honest run over the frozen professional stratum, terminal transcript pasted. The command is
      `python3 tools/run_stratum.py --captures captures/ --judge --goldset <set> --out runs/day7`, and it
      writes the transcript, the readout, `RUN_LOG.md` and the trace table. **Blocked on the stratum**
- [ ] Metric readout: citation support rate, unauditable rate, judge-fabricated-span rate, judge-human
      agreement, source drift rate. Every one with its n and a confidence interval
- [ ] Label every rate as single-stratum. Not a rate for AI citations generally
- [ ] Plausibility audit of the numbers
- [x] §0a status table. `STATUS.md`, filled in for day 5 and updated as things land. Core items whose
      machinery exists but has never run on real data are listed separately rather than ticked, because
      "the code path exists" and "we have seen it work" are different claims
- [x] Per-number trace table: every published figure traced to the record it came from. Generated by
      `harness.trace_table` rather than typed, because a hand-written one describes the numbers that existed
      on the day it was written

## Days 8 to 10: stretch, in this order

- [ ] Head-to-head, dead-link and paywall stratum first, against one tool before adding a second
- [ ] Coverage table for every competitor named in §1b: compared, unreachable with a reason, out of scope
      with a reason, or not attempted
- [ ] If the incumbents refuse cleanly on unreachable sources, say the differentiator collapsed, as
      prominently as the flattering result would have been reported
- [ ] Consumer stratum run, rates reported per stratum rather than only in aggregate
- [ ] Break attempt 1, topical-match false positive
- [ ] Break attempt 2, paywall misread
- [ ] Break attempt 3, post-hoc drift
- [ ] Break attempt 4, shared-vocabulary contradiction
- [ ] Per-domain reporting
- [ ] Gold set expansion beyond 40
- [x] **Existence check for named citations, via Crossref.** `sayswho/crossref.py`, behind
      `--check-existence`, off by default because it makes requests to a third party. Four outcomes, not
      three: `CITATION_LOOKUP_FAILED` was added because reporting our own network failure as
      `CITATION_NOT_FOUND` would turn our outage into a finding about somebody's citation.

      Built before the core landed, which §0a said not to do, and the reason is that the core is blocked on
      transcription rather than on build time. It cannot corrupt anything: a resolution enters no
      denominator, `rates.py` does not import it, and there is a test asserting `rates.py` does not contain
      the word

      Matching requires both the first-author surname and the year within one. Two matches is
      `CITATION_AMBIGUOUS` and neither is named, because naming one would be a choice rather than a
      resolution. Not-found says in its own detail that Crossref does not index everything, so it is a
      prompt to look by hand rather than a finding that a citation was fabricated

      The line that makes this safe, and it is not negotiable if it gets built: **check existence, never
      check support.** Judging a claim against a paper we selected ourselves would be inventing the evidence,
      which is the exact failure this project exists to catch. Three outcomes, no scores:
      `CITATION_RESOLVED`, `CITATION_NOT_FOUND`, `CITATION_AMBIGUOUS`. A resolved citation still never enters
      a support-rate denominator, because "this paper exists" and "this paper backs this sentence" are
      different facts and collapsing them would repeat the mistake this whole project is about

      Roughly half a day. Build only if the core lands on time
- [x] Split `SOURCE_UNREACHABLE` into `SOURCE_DEAD_LINK` (404, 410) and `SOURCE_BOT_BLOCKED` (401, 403,
      429), with the general code kept for everything else rather than forcing every status into one of the
      two. Same class of distinction as `SOURCE_ROBOTS_EXCLUDED`, and all three stay `UNAUDITABLE`, so the
      arithmetic is unchanged and only the sentence beside the number moves. Done early because it is small
      and because the dead-link stratum in §5a needs the distinction to exist before it can report one
- [x] Widen the `CITATION_NOT_LINKED` patterns, as far as widening is safe before recall is known. PMID,
      PMC and arXiv identifiers: all three are identifiers and nothing else, so they cost no precision, and
      prose mentioning the systems by name is tested not to match. Anything looser than that trades away the
      precision the published count depends on, on a guess
- [x] Build the recall measurement. `tools/measure_named_recall.py` compares the patterns against a
      hand-marked answer and reports recall and precision with intervals, matching a short hand-written form
      against a long matched one by identifying tokens rather than by substring
- [ ] Mark an answer by hand and run it. **Mine to do.** `--template` will start the file, and the tool says
      out loud that starting from its own answers will anchor the marking. Until this runs the count stays a
      floor of unknown depth

## Deliverables, by rubric row

- [ ] Contribution works, 60 points. Installable MV3 extension, headless harness, pytest proving each gate
      fails on its target bug, parity check
- [x] Two-customer pair, 30 points. `recipes/audit-citations.md` in nine sections, plus
      `recipes/audit-citations.card.md` covering six failure modes. Five of the six look like "the citation
      failed" and only one of them is, which is the card's organising idea
- [ ] Verified-data attestation, 35 points. The §4 boundary table, the per-number trace table, the privacy and
      honesty gate output
- [ ] The honest run, 35 points. Terminal output, plausibility audit, the two core break attempts, metric
      readout, §7 limitations
- [ ] GitHub PR, 25 points. `contrib/jayanth-says-who` branch with a maintainer-ready description.
      **Mine to do first:** confirm which repo this targets. Nothing else about it can be written until
      that is known, since a maintainer-ready description is addressed to a specific maintainer
- [x] Portfolio piece, 35 points: the case study. `CASE_STUDY.md`, for a technical reader, with the four
      load-bearing decisions and what each cost. The "what I would do differently" section is longer than
      the results section, which is the accurate shape on day 5
- [ ] Portfolio piece, the other half: an extension a reader can install in about thirty seconds. The
      install works today; the thirty-second claim needs someone who is not me to try it
- [ ] Explainer video, 20 points. **Mine to do.** Three to six minutes, one uncut segment showing a real answer marked live,
      including a claim it refuses to score
- [ ] Honesty overlay, 10 points. Calibrated verbs throughout, prior art named, the §5a failure condition
      declared before the data existed, the §0a status table

## Honesty obligations, regardless of how the numbers come out

These are not tasks that can be traded away for time. They are the reason the project is worth doing.

- [ ] Every rate ships with its n and a confidence interval, and the writeup says which differences the
      sample cannot resolve rather than ranking things it has no power to rank
- [ ] Kappa at n between 30 and 40 is reported as a wide-interval estimate, not as a calibration
- [ ] Products are named, and every sentence about them is calibrated. "We could not reproduce support for N
      of M claims, of which K were source-unreachable", never "Product X fabricates citations"
- [ ] Prior art named plainly. CiteGuardian, GPTZero, CiteTrue, FactSentinel. The general idea is not novel
- [ ] Until the head-to-head runs, the differentiator is described as structural rather than measured, and
      incumbent behaviour is attributed to their marketing copy
- [ ] The frozen query set is published in full so a reader can judge the sample instead of taking my word
      for it
- [ ] The scrub drop count is published alongside the support rates, not in an appendix
- [ ] The judge-fabricated-span rate is published as a finding about the judge, not quietly fixed
- [ ] §7 stays in: it cannot check whether a source is true, it is blind to omission, and it cannot tell a
      peer reviewed paper from a blog post
