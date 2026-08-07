# SaysWho build checklist

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
- [ ] `DATA_CONTRACT.md` written
- [ ] Reply sent to Prof. Brown with `SCOPE.md` attached

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

- [ ] `DATA_CONTRACT.md`: respect `robots.txt`, one request per second per domain, identifying User-Agent with
      a contact address, every fetch cached to disk so reruns audit the same bytes
- [ ] No authenticated fetches and no paywall circumvention. A paywall is a legitimate `UNAUDITABLE` outcome
      and routing around it would corrupt the measurement
- [ ] Write down the model call metering and logging policy before any calls are made

## Day 2: capture and fetch

- [ ] DOM capture on claude.ai, chatgpt.com, perplexity.ai. Answer text and citation markers stored verbatim
      and hashed
- [ ] Google AI Overviews through the same code path, no separate asterisk
- [ ] Fetch layer implementing the data contract
- [ ] Phase 0 gate G0: zero inline citations returns `NO_CITATIONS` and halts. An uncited answer is a
      different object, not a zero percent answer
- [ ] Phase 2 gate G2 returning all five outcomes: `SOURCE_OK`, `SOURCE_UNREACHABLE`, `SOURCE_EMPTY`,
      `SOURCE_PAYWALLED`, `SOURCE_DRIFTED`
- [ ] Wayback CDX lookup for drift detection against the generation timestamp

Done means an answer captured, hashed, and every cited URL fetched with a G2 code attached.

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
