# SaysWho build checklist (TODO)

Everything the project owes, in the order it has to happen. Derived from `SCOPE.md` §0a (the core and stretch
split), §8 (the rubric), and §12 (the schedule).

Two rules for keeping this file honest. Nothing gets ticked because it was started. And a stretch item that
does not happen gets marked not-done with a reason rather than deleted, because §0a promises the writeup
reports it either way.

## Where things actually stand

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
- [ ] Implement the contract in the fetch layer on day 2, and write the tests that prove the enforced half of
      §10 is actually enforced rather than merely written down

## Day 2: capture and fetch

Python side done, browser side not started.

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
- [ ] **Compare a capture field by field against the screen, then flip `verified`.** Selectors now match, but
      matching is not the same as capturing the right thing. Still `verified: false` for every product
- [ ] ChatGPT and Perplexity selectors checked against their real pages. Only Claude has been looked at
- [ ] Google AI Overviews adapter verified through the same code path, no separate asterisk
- [ ] Marking UI. Deliberately not built yet: there are no verdicts until day 3, and marking claims before
      there is anything behind it would be finding-shaped output

Done means an answer captured, hashed, and every cited URL fetched with a G2 code attached. That works today
against a handwritten fixture. It does not yet work against a real answer, because nothing captures one.

## Day 3: claim splitting and the judge

- [ ] Phase 1 claim extraction, bound to citation markers, labelled model-inference in every output surface
- [ ] Gate G1: opinions, hedges, instructions and transitions return `NOT_A_FACTUAL_CLAIM` and are skipped.
      The skip count is published, never silently dropped
- [ ] Phase 3 judge returning `SUPPORTED`, `PARTIALLY_SUPPORTED`, `NOT_FOUND_IN_SOURCE`, `CONTRADICTED`
- [ ] Gate G3, the span guard. Normalised substring check against the fetched document. Absent or fabricated
      span voids the verdict and logs `JUDGE_FABRICATED_SPAN`
- [ ] Judge running on a free tier with a user-supplied key, calls metered per run

Done means a run producing per-claim verdicts with the fabricated-span rate counted.

## Day 4: gates and the contract check

- [ ] Unauditable claims excluded from every denominator, enforced by a hard contract check
- [ ] `INSUFFICIENT_EVIDENCE` when more than half an answer's claims are unauditable, and no number printed
- [ ] Gate G4: refuse to print aggregate rates when no gold set exists for the current judge and prompt
      version. Per-claim verdicts still emit
- [ ] Test asserting no confidence number appears anywhere in any output surface
- [ ] Headless harness runnable end to end over the frozen query set
- [ ] `freeze_queries.py check` wired to run before every capture, so a tuned set fails the run

Done means pytest with each gate failing on its target bug, not merely present.

## Day 5: the gold set

- [ ] Label 30 to 40 claims by hand, before looking at any judge output
- [ ] Stratify across products and across verdict classes. Fill `UNAUDITABLE` and `CONTRADICTED` first, since
      a class the set never contains cannot be calibrated
- [ ] Commit the labels with a timestamp that precedes the judge run
- [ ] Per-class precision and recall, plus Cohen's kappa with its confidence interval
- [ ] Try to recruit a classmate to double-label 10 to 15 claims. If nobody is available, say so plainly and
      treat my labels as a single-rater ceiling rather than ground truth

## Day 6: break attempts and parity

- [ ] Break attempt 5, prompt injection through a fetched page. Report at the resolution the guard actually
      provides. An injected page can still supply a real on-page span, so the guard rules out a verdict with
      no textual basis, which is not the same as defeating injection
- [ ] Break attempt 6, denominator contamination. Force unauditable claims into the denominator and confirm
      the contract check fires
- [ ] Parity check: the extension and the headless harness produce identical verdicts on identical inputs,
      verified by test. If the interface disagrees with the audited pipeline, the interface is lying

## Day 7: the core is done

- [ ] Honest run over the frozen professional stratum, terminal transcript pasted
- [ ] Metric readout: citation support rate, unauditable rate, judge-fabricated-span rate, judge-human
      agreement, source drift rate. Every one with its n and a confidence interval
- [ ] Label every rate as single-stratum. Not a rate for AI citations generally
- [ ] Plausibility audit of the numbers
- [ ] §0a status table filled in, every stretch item marked done or not-done
- [ ] Per-number trace table: every published figure traced to the record it came from

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
- [ ] **Existence check for named citations, via Crossref.** Does "LeClair et al., Supportive Care in Cancer,
      2022" correspond to a real paper? Free API, no key, so it fits the budget. Catches fabricated
      references, which is a real and well-documented failure mode

      The line that makes this safe, and it is not negotiable if it gets built: **check existence, never
      check support.** Judging a claim against a paper we selected ourselves would be inventing the evidence,
      which is the exact failure this project exists to catch. Three outcomes, no scores:
      `CITATION_RESOLVED`, `CITATION_NOT_FOUND`, `CITATION_AMBIGUOUS`. A resolved citation still never enters
      a support-rate denominator, because "this paper exists" and "this paper backs this sentence" are
      different facts and collapsing them would repeat the mistake this whole project is about

      Roughly half a day. Build only if the core lands on time
- [ ] Widen the `CITATION_NOT_LINKED` patterns and measure their recall against a hand-marked answer. The
      current count is a floor and the writeup has to keep saying so until that is measured

## Deliverables, by rubric row

- [ ] Contribution works, 60 points. Installable MV3 extension, headless harness, pytest proving each gate
      fails on its target bug, parity check
- [ ] Two-customer pair, 30 points. `recipes/audit-citations.md` in nine sections, plus a `.card.md` covering
      six failure modes
- [ ] Verified-data attestation, 35 points. The §4 boundary table, the per-number trace table, the privacy and
      honesty gate output
- [ ] The honest run, 35 points. Terminal output, plausibility audit, the two core break attempts, metric
      readout, §7 limitations
- [ ] GitHub PR, 25 points. `contrib/jayanth-says-who` branch with a maintainer-ready description. Confirm
      which repo this targets before writing it
- [ ] Portfolio piece, 35 points. Case study for a technical hiring manager, plus an extension a reader can
      install in about thirty seconds
- [ ] Explainer video, 20 points. Three to six minutes, one uncut segment showing a real answer marked live,
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
