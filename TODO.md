# SaysWho build checklist (TODO)

Everything the project owes, in the order it has to happen. Derived from `SCOPE.md` §0a (the core and stretch
split), §8 (the rubric), and §12 (the schedule).

Two rules for keeping this file honest. Nothing gets ticked because it was started. And a stretch item that
does not happen gets marked not-done with a reason rather than deleted, because §0a promises the writeup
reports it either way.

## Start here next session

Written 2026-08-15, mid day 9, with the calibration built and the run not yet executed.

**The gold set is done and it is the first real one this project has had.** 45 blind labels over ten ChatGPT
captures, 0 supplemental, 36 comparable against a floor of 30. The prior-audit scan was clean over all ten
answers before the session opened, so these are blind in fact. `goldset/chatgpt-consumer.gold.json`.

**What is left, in order.**

1. **Run the stratum.** It has not happened. `runs/day9/` does not exist, so there is no readout, no support
   rate, and no refusal. This is the one remaining step between the project and a number it is entitled to
   print. It needs `GEMINI_API_KEY`, so it runs in Jayanth's shell:

   ```
   CAPS=""; for f in captures/capture-chatgpt-2026-08-15T*.json; do CAPS="$CAPS --captures $f"; done
   SPL=""; for s in splits/chatgpt/*.split.json; do SPL="$SPL --split $s"; done
   .venv/bin/python tools/run_stratum.py $CAPS $SPL --judge --goldset goldset/chatgpt-consumer.gold.json --out runs/day9
   ```

   The captures are passed explicitly rather than as `--captures captures/`, which would sweep in the 24
   Perplexity answers and make it a different run.

2. **Whatever the readout says, the rate is over inline-rendered citations.** Not over ChatGPT's citations.
   At least 20 of 53 claim-attached citations were behind "+N" controls and never in the captures, and a
   claim whose supporting source was one of them is judged against the source that did render and comes back
   `NOT_FOUND_IN_SOURCE`, the verdict with no span and no G3 check. 22 of the 36 comparable human labels are
   `NOT_FOUND_IN_SOURCE`, so this caveat is load-bearing rather than decorative. `FINDINGS.md` item 23
3. **The ChatGPT adapter is still unverified.** `verifiedSelectors` is empty in `extension/src/adapters.js`,
   so all ten captures carry `adapter_verified: false` and the gold set inherits it. Row L260
4. **The PR description.** Still blocked on the same two answers only Jayanth has: which repo
   `contrib/jayanth-says-who` targets, and which chapters SaysWho satisfies
5. **The video.** `VIDEO.md` is written and its gold set paragraph is now wrong: it says six labels and no
   calibration. That paragraph has to be rewritten against whatever the run prints before recording

Superseded plan from the end of day 8 follows, kept because the corrections in it are the point.

Written 2026-08-14 at the end of day 8, so day 9 does not begin by rereading the file.

**Everything the code can do on its own is done, and one human afternoon is what the project is waiting on.**
The captures happened on day 6, the honest run on day 7, and it published no support rate because the gold
set holds 6 human labels against 24 judged splits. G4 is not going to calibrate its way out of that. No
amount of further building changes it.

**Corrected on day 8, and the correction is the point.** The plan written here that morning said to pick a
target and label the existing answers. That plan is dead: the day 7 run put verdicts over all 24 of them, so
`label_goldset.py` exits 3 and `--supplemental` is the only way in, and supplemental labels carry
`blind: false` and never enter kappa. Topping up the existing set would produce forty labels and leave the
blind kappa at n=2. `FINDINGS.md` item 22.

Day 9's queue, in order:

1. **Capture ChatGPT answers in the order in `queries/capture-order.md`**, which fixes all 24 rather than
   just the first ten, and was committed before a single ChatGPT answer existed. The first ten are CO-02,
   CO-03, CO-08, CO-10, CO-14, CO-17, CO-20, CO-21, CO-22, CO-24, and if those do not yield 30 comparable
   pairs the next ones are CO-06, then CO-19, then CO-13. Taking the next id is not the same as picking one
   after seeing which codes the first ten happened to be short of. A new product means new answer hashes, so
   the prior-audit scan comes back clean and the labels are blind in fact. This also gives the second product
   §3's stratification always needed, since one product means the gold set stratifies on G2 codes alone
2. **Verify the ChatGPT adapter while in there.** `verifiedSelectors` is empty, so every capture it makes
   carries `adapter_verified: false`, and a gold set built on those captures inherits it. Read one captured
   answer end to end against the screen and confirm the citation set matches what the extension stored. This
   is row L238 and it is the same browser session
3. **Bind, split, then prep with fetching on.** `tools/bind_capture.py captures/*.json --in-order --stratum
   consumer`, then `--split-only --save-split`, then `tools/prep_goldset.py` **without** `--no-fetch`, since
   ChatGPT's sources have never been fetched and nothing about them is cached
4. **Only then pick the target.** 15 of 145 unauditable is a fact about the pages Perplexity cited, not a
   constant. Whether ChatGPT's sources are more or less bot-blocked is unknown until step 3 reports it, and
   the target is a decision with numbers behind it or it is a guess
5. **Label.** `LABELLING.md` is the decision guide and discusses vocabulary rather than claims, deliberately.
   `UNAUDITABLE` pairs are the quick ones and buy no kappa, so the target has to exceed the comparable n
   wanted. The PDF extraction check works during the session as of day 7
6. **Run the stratum with the gold set attached**, over the ChatGPT captures. First moment the project is
   entitled to print a support rate, and still entitled to refuse
7. **The PR description.** Still blocked on the same two answers only I have: which repo
   `contrib/jayanth-says-who` targets, and which chapters SaysWho satisfies. `PR_DESCRIPTION.md` is drafted
   around both blanks

Do not run the judge over the ChatGPT captures before the labels exist. That is the mistake day 7 made
without noticing, and the guard only fires in the other direction.

After that, days 9 and 10 are the video, an outsider trying the install, and whichever stretch rows fit.
The stretch rows that do not fit get a state and a reason here rather than being dropped, per §0a.

Landed on day 8, none of it measurable: the README rewritten for somebody arriving at the repo, which found
a verdict name in it the judge never emits and two gold set commands missing required arguments; the
`--judge` help string still naming the key from before Gemini became the default; and an audit of all 49
unticked rows against the repo, which found one describing a bug fixed the day before. The other 48 are
correctly open. `STATUS.md` has the detail under "What changed on day 8".

## Where things actually stand

Day 8 of ten, where day 5 was 2026-08-11. **Every day 7 row is done and the gold set is the only core item
left open.** The honest run, the readout, the fabricated-span figure checked before being described, the
plausibility audit and the trace table all landed on day 7. Day 8 added no measurement: it rewrote the README
for a reader arriving cold, fixed a help string naming the wrong API key, and audited these rows against the
repo, which found one describing a bug that had been fixed the day before. 48 rows are open and all 48 were
verified as genuinely open. `STATUS.md` has the detail.

Day 7 of ten, where day 5 was 2026-08-11. **The honest run happened on day 6 and printed no support rate,
which is what it was built to do when there is no calibration behind one.** What day 7 owes now is the
writeup's obligations rather than the pipeline's: labelling every rate single-stratum and synthetic, and the
plausibility audit. `FINDINGS.md` item 21 has the numbers.

Day 6 of ten, where day 5 was 2026-08-11. Day 6's own deliverable, the two core break attempts and the parity
check, was already complete before day 6 began. Day 5's own deliverable is the gold set, which was blocked for
two days on a stratum that has now been given up rather than delivered: the core runs on the frozen consumer
set instead, and the gold set waits on captures. Days 2, 3, 4 and 6 are done. Day 1 is done apart from the
professional stratum, which is reported not-done with its reason. Days 5 and 7 are a day's work away rather
than blocked, and day 7 is tomorrow.

**What is still open is browser work and one afternoon of labelling.** That is a different sentence from the
one that stood here for six days, and it is not better news than it sounds: the thing that made the old
sentence true, a stratum only I could produce, was given up rather than done. Items below still marked
**mine to do** are the ones no amount of building moves forward.

Day 1, partially done.

- [x] Consumer stratum written, 24 questions across four domains, each with a cost of error
- [x] Consumer stratum frozen, hash manifest in `queries/FREEZE.json`
- [x] Freeze tooling built, and all three failure paths tested rather than assumed
- [x] Repo created, scope document and query set committed
- [ ] **Professional stratum assembled. Not-done and withdrawn, day 6.** The sessions are gone, so there is
      nothing to transcribe, and retyping from memory is refused: recall selects on what stuck, which
      correlates with how the tool performed, and a retyped question is reconstructed rather than
      transcribed. Reported not-done with this reason rather than deferred. `SCOPE.md` §10
- [ ] `SCRUB_LOG.md` filled in and the drop count recorded. **Not possible and withdrawn:** there was no
      intake, so there is no drop rate. The writeup says that rather than printing a zero
- [x] `DATA_CONTRACT.md` written, before any fetch has happened
- [ ] Reply sent to Prof. Brown with `SCOPE.md` attached. Parked for now, deliberately

## What blocked the schedule for six days, and how it ended

Kept rather than deleted, because §0a promises an item is reported either way and because the reason this
list stopped mattering is itself the finding. `FINDINGS.md` item 18.

- [ ] ~~Pull the queries~~ **Impossible.** The population was answers in my own AI history that came back with
      citations attached. The sessions are gone
- [ ] ~~Scrub each one per `queries/README.md`~~ **Nothing to scrub.** The procedure stays in that file, since
      it is the standard any future professional set has to meet, and `tools/validate_queries.py` still
      enforces it on anything claiming `real_scrubbed`
- [ ] ~~Log every query that entered intake~~ **No intake happened**
- [ ] ~~Write `cost_of_error` for each survivor~~ **No survivors**
- [ ] ~~Flip `professional.toml` status to `ready` and freeze it~~ **Stays `draft` and stays empty.** Not
      topped up with inventions, and not filled with reconstructions labelled `real_scrubbed`
- [ ] ~~Publish the drop rate~~ **Withdrawn, and it was a promised number.** A rate needs a denominator and
      there was no intake to have one

## What blocks the schedule now

- [x] Capture answers against the frozen consumer stratum. Done by hand on day 6: 24 Perplexity answers, one
      conversation each, bound to CO-01 through CO-24 by `bind_capture.py --in-order`, whose pairing table was
      read before confirming. 51 citations, no uncited answer, so G0 halts none of them
- [x] Make the split. 24 stored splits in `splits/`, 24 run records in `runs/consumer/`, from `--split-only`
      so no verdict exists for any of these claims. 162 claims, 145 claim-source pairs, 43 uncited claims, 240
      skipped units, 42 of 51 sources auditable. The gold set draws its 30 to 40 pairs from 145, and the
      classes §3 Phase 4 says to fill first exist for once: 7 `SOURCE_BOT_BLOCKED`, 1 `SOURCE_DEAD_LINK`, 1
      `SOURCE_UNREACHABLE`
- [x] **A malformed response was ending the run rather than becoming an outcome.** One server returned a
      chunked body whose size line `http.client` could not parse, which surfaces as a `ValueError` from inside
      urlopen rather than a `URLError`, so it escaped the fetcher's handler and killed the whole capture,
      costing CO-23 its run record. The rerun succeeded, which is the worst version of a bug: transient, so it
      reads as nothing. A stratum run fetches every cited URL of every answer, so betting on no server
      misbehaving is not a bet. It is now caught like a timeout, retried under the same policy, and recorded
      as `SOURCE_UNREACHABLE` with the exception in its detail. One bad response costs one source, and says so
- [x] Prep the labelling session. `tools/prep_goldset.py` over all 24 splits: 0 requests sent, because the
      split pass warmed the cache, 35 pairs over 25 pages, 725,539 characters to read, and the prior-audit
      scan clean over all 24 answers. So the labels can be blind in fact rather than by assertion, which is
      the first time that has been true in this repo
- [x] `LABELLING.md`, a decision guide for the session. The vocabulary rather than the answers, since a guide
      that discussed a claim would anchor the label it is meant to steady. The four boundaries it draws are
      the ones with a known failure behind them: silence is not contradiction, which is the direction the
      judge is already known to drift in from break attempt 1; never round `P` up to `S`; `U` rather than `N`
      when the page could not be read, since the alternative turns our fetch failure into somebody's citation
      failure; and `?` is a real answer rather than a tired one
- [x] **Decided 2026-08-15, for the ChatGPT pool rather than the Perplexity one: target 45.** The reasoning
      below was written about Perplexity and it is why the decision waited for data. ChatGPT's pool is also
      145 pairs but only 2 sources are unauditable rather than 15, so `prep_goldset.py --target 45` reported 6
      unauditable and 39 comparable, against 30 needed. The 6 extra over the floor were deliberate slack for
      voided verdicts. Original reasoning follows. The pool is 145 pairs, of which only
      15 are unauditable, and the sampler takes all 15 first. `goldset.agreement` excludes those from kappa,
      since the judge was never asked about them, so `--target 35` yields 20 comparable pairs and a kappa at
      n=20 rather than the 30 to 40 §0a asks for. `--target 45` gives 30 comparable, `--target 55` gives 40.
      The choice is an hour of labelling against the width of the interval, and whichever is chosen the
      writeup reports the comparable n rather than the label count
- [x] A second product. **Done 2026-08-15: ten ChatGPT answers over the frozen consumer stratum**, captured
      in the order pre-registered in `queries/capture-order.md` before any of them existed. 71 claims, 145
      claim-source pairs, 33 sources, 31 `SOURCE_OK` and 2 `SOURCE_DEAD_LINK`. Bound one query at a time with
      an explicit `--query` rather than with `--in-order`, which pairs by capture time against ids in **id
      order** and would have bound the pre-registered draw to CO-01 through CO-10: the wrong questions, with
      every hash still verifying. All ten answers were read against their questions before writing. The
      original note follows. One product means the gold set stratifies on G2 codes alone,
      since product is the other axis and there is only one value of it. ChatGPT cites these questions;
      Claude mostly does not, which is an observation on a handful of tries rather than a finding
- [ ] **ChatGPT hides at least 37.7 per cent of its citations from DOM capture, and it is not fixed.** The ten
      captures hold 33 citations with at least 20 more behind "+N" controls, one answer of the ten complete
      and CO-22 missing half. Unlike the day 6 Perplexity loss this cannot be repaired from the stored pages,
      because those sources are never rendered rather than missed by a selector: the stored CO-22 page is
      655,970 characters and holds the same five URLs the capture already had. Three routes exist and none was
      taken under the day 9 clock: drive the expanders before capture, which needs testing rather than
      assuming because the probe suggests the sources land in a transient container; capture the share view,
      which audits a different artefact from the one a person reads and §1 forbids; or run the API comparison
      that `sayswho/apicapture.py` and `tools/compare_capture.py` were built for. `FINDINGS.md` item 23
- [x] **The extractor was dropping a quarter of the citations, and the stored pages paid for themselves.**
      `saysWhoExtractCitations` ended its selector loop with `if (citations.length) break;`, so the first
      selector that matched anything won. Perplexity declares two and renders both, so 13 of 51 inline
      citations were behind a selector that never ran. Found by `reextract` reporting a parity mismatch on the
      first capture. Fixed in the extension, and the 24 captures were repaired from their stored pages with
      `python3 -m sayswho.reextract PAGE --capture CAPTURE --repair` rather than by re-asking, which is
      exactly what day 2 stored those pages for. `FINDINGS.md` item 20
- [ ] Real parity on the extractor, not a source scan. The test added with that fix asserts the source no
      longer contains the early exit, which is a test about the shape of a file and the project says elsewhere
      that those are the weak kind. The one that would have caught this runs the extension's extractor in node
      against the same markup `reextract` parses, and compares the two citation sets. The renderer already has
      that treatment in `tests/parity/`, and the extractor, which is where the money is, has never had it
- [ ] **The installed watcher is broken, and leaving it broken is deliberate until the gold set is labelled.**
      `~/Library/LaunchAgents/com.sayswho.watch.plist` points at `/Users/jayanthadityak/Finall Project/`, two
      Ls, from before this repo was renamed. `launchctl` reports last exit 78, a config error, and no log has
      ever been written, so the agent has never run once. Two things follow. It has to be reinstalled with
      `tools/install_watcher.sh` to work at all, and the plist embeds an absolute path, so any future rename
      silently breaks it again the same way. And it must **not** be reinstalled before the labelling session:
      it audits every new capture, so a working watcher would have judged all 24 consumer answers within
      thirty seconds of capturing them and made a blind gold set impossible for this stratum. That is the
      prior-audit guard's exact failure case, arriving automatically and with nobody at the keyboard
- [x] Bind 24 captures without misbinding one. `bind_capture.py --in-order --stratum consumer` pairs captures
      by capture time with a stratum's ids in id order, and refuses to trust that pairing: it writes nothing
      without `--confirm`, and first prints each query beside the opening sentence of the answer it proposes to
      bind. That table is the check, because a misbound capture is a rate over the wrong question and every
      hash still verifies. It refuses outright when there are more captures than queries, since that means a
      question was asked twice and order cannot say which, and a short run needs `--allow-partial` so that
      stopping early is stated rather than silent. Both modes write through one `bind_one`
- [ ] Teach the extension to carry a query id. `saysWhoBuildCapture` takes `queryId` and no caller passes one,
      which is why order is load-bearing at all. The fix is a field in the popup, and it would make the
      pairing above a checksum rather than the only link
- [x] Decide how many of the 24 frozen consumer queries the day-7 run covers, and say so. **24 of 24.** Every
      frozen consumer query was asked, captured, bound and judged, so the run is over the whole stratum rather
      than a subset of it and no selection question arises. Superseded note follows.
- [x] ~~A run over a subset of a frozen set~~ is legitimate and it is not the same claim as a run over the set, so whichever it is
      gets stated next to the n rather than left to be inferred

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
      worker. Hashes the answer and downloads JSON the harness reads. **This line said "captures the last
      answer" until day 6 and that was never what the code does:** `saysWhoFindAnswer` ranks every matching
      container on the page by citation count and returns the highest, falling back to the longest text. On a
      single-answer page those are the same thing, which is why nobody noticed. In a multi-turn thread they are
      not, and the consequence is practical rather than cosmetic: capturing the seventh question in a thread
      returns whichever earlier answer cited most. One question per conversation is therefore a rule for the
      capture run and not a preference
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
- [x] Perplexity: probed, and it was worse than the note said. Not "roughly a third" of its citations are
      missing from the DOM as links: **none** of them are links. Every inline citation is
      `<span class="citation inline" data-pplx-citation-url="https://...">` and a live answer page contained
      no `<a href>` at all, so the anchors-only rule found zero citations and produced a clean capture that
      G0 would read as an uncited answer. Fixed in three places at once, because the counter that ranks
      containers, the extractor, and the Python re-extractor all have to agree about what a citation is
- [ ] Perplexity, the rest of verification: read a captured answer end to end against the screen on a
      logged-in page, and find out what the "+N" chip does when one sentence cites several sources. Until
      both, captures from this adapter stay labelled unverified. **Mine to do**
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
- [x] The popup, so clicking the extension shows what is useful instead of firing a capture blind. Server
      state in three colours rather than two, since running-without-a-judge is up and cannot produce a
      verdict. The current page's adapter and whether it has ever been checked. The last capture's summary,
      which until now lived in a toast that disappeared. Both actions. And a toggle to hide the in-page
      buttons, live, without a reload
- [x] Draw the line the popup is built on: control surface, not result surface. A popup closes on blur, so
      an audit could never have lived in it
- [ ] Exercise the browser leg. The server, the popup states and the dock layout are all tested or rendered,
      but none of it has been run inside a real extension on claude.ai. **Mine to do**
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
- [x] **Read the formats instead of refusing them.** PDF, plain text, XML and RSS, and `.docx`, all stdlib:
      a PDF's content streams are Flate-compressed and `zlib` is stdlib, a `.docx` is a zip of XML and
      `zipfile` is stdlib. `sayswho/pdf.py` walks the text-showing operators. The extraction layer keeps its
      dependency-free property, which was the argument against reaching for pypdf or trafilatura
- [x] Two new outcome codes, because a refusal has to say whose failure it is. `SOURCE_NO_TEXT_LAYER` for a
      scan or a page whose content is a chart image, where the words are on screen and OCR is out of scope.
      `SOURCE_UNREADABLE_ENCODING` for a PDF whose fonts use a custom encoding, where the bytes are glyph
      numbers and the recoverable "text" is plausible-looking rubbish. Neither ever passes text to the judge:
      a garbled read produces `NOT_FOUND_IN_SOURCE`, the one verdict with no span and no G3 check, and the
      one that accuses the product. `FINDINGS.md` item 11 found that once already
- [x] Tables extract as rows, cells separated rather than one per line. A row label and its value used to
      become two unrelated lines, so a claim about a measure's rate could not be found in a page stating it
- [ ] Measure which way the PDF garbled test errs. Two ratios, printable characters and spaces, neither
      measured, both set to refuse in the ambiguous case. The day 5 gold set is the only thing that can say
      how much coverage that costs, same as `EXTRACTION_SUSPECT`
- [x] Exercise the PDF reader on live data. Done, and this row was the one place the three state files
      disagreed: `STATUS.md` has had it struck through as run since the first live PDF audit and this list
      still said not yet. It read the boston.gov PDF cited by a real Perplexity answer, `SOURCE_OK`, 54,811
      characters as of 2026-08-12. Every extraction bug in `FINDINGS.md` items 14 and 17 came out of that one
      document and none of them came from a test, which is the argument for exercising a reader on live data
      rather than the argument for having done it
- [ ] Exercise the thin-page flag on live data. Still has never fired on a real capture
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
Note, not a task: the open items above all came from reading that run's output rather than from the plan.
It carried a checkbox until day 8 and could never satisfy one, so it was counted as outstanding work every
time this file was totalled.

Re-run on 2026-08-07, same capture, after the drift fix. 9 sources, 7 auditable, 20 claims, 15 judgements.
PubMed survived. One verdict voided as `JUDGE_FABRICATED_SPAN`, 1 of 9 span-bearing, against 0 of 7 on day 3.
That is 1 of 16 across both runs and it is not a rate, but the guard has now fired on ordinary output rather
than only on the test built to trip it. `FINDINGS.md` item 10.

**Superseded on day 5, kept because deleting it would hide the correction.** That 1 of 16 was mostly this
tool. Re-auditing the voided spans found three of four caused by SaysWho: two by a PDF reader inserting a
space between every digit, one by a span comparison that read a curly quote and a straight quote as different
characters. One was a genuine catch. Both bugs are fixed, the third cause is known and unfixed, and the figure
is withdrawn rather than restated. `FINDINGS.md` item 14.

## Day 5 additions, from reading a spec against the build

- [x] **`missing_qualifiers` on every verdict.** What the cited page attaches that the claim does not, in
      the page's own terms: "observational, not causal", "US subgroup only", "2019 figure, claim says 2023".
      A list of strings, never a number. It is what makes `PARTIALLY_SUPPORTED` actionable, since "supports
      part of this" without saying which part hands the checking work back to the reader
- [x] A partial verdict arriving with an empty list is counted as `partial_without_qualifiers` and published
      rather than voided. The verdict may well be right and voiding it would lose real signal
- [x] Score-shaped qualifiers are dropped and recorded. The no-confidence gate walks keys, and it cannot walk
      string values without failing on this project's own prose, so the check lives where the strings come
      from a model rather than from us
- [x] `JUDGE_PROMPT_VERSION` bumped to `judge-v2`, deliberately now. G4 keys the gold set to judge and prompt
      version, so this is free before day 5 labelling and expensive after it. Leaving it at v1 with a changed
      prompt underneath would have been the actual violation
- [x] **`PARTIALLY_SUPPORTED` is its own claim state.** It used to roll up into `SUPPORTED`, so a claim whose
      only verdict was "supports part of this" was marked green and labelled "Supported by the cited source".
      `missing_qualifiers` made that indefensible on screen: the card read "Supported by the cited source"
      above a list saying "association, claim says reduction". Six states now, and the rollup never rounds up
- [x] `report.py` uses `rates.py` for the pair count rather than growing its own. A second denominator one
      file away from `standing_denominator` is exactly what that function exists to prevent

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
- [x] **Make it possible to label blind at all.** Found by walking the workflow before labelling rather than
      during it. The labels have to predate the judge, and `goldset.agreement` enforces that, but the only
      route to a stored split was `--judge --save-split`, which runs Phase 3 and prints every verdict on the
      way past. Three refusals guarded blindness and the one mandatory step handed you the answers.
      `--split-only` runs Phase 1 and stops, and refuses `--judge`, `--goldset`, `--report` and
      `--report-json` rather than quietly ignoring them. `tests/test_cli.py`, which counts what the model was
      asked for rather than reading the output
- [x] **Make a gold set able to cover more than one answer.** Same walk. A `GoldSet` carried one
      `split_sha256` and G4 compared it for equality, but one answer yields roughly twenty labellable pairs
      against a target of thirty to forty, and the sampler stratifies across products, so a real set spans
      two or three answers. Given more than one split the labelling tool wrote `split_sha256 = ""`, which
      matches nothing: an afternoon of labelling would have calibrated not one capture. Now a list, checked
      by membership, and it records the splits its labels actually came from rather than the ones the sampler
      was handed, since quitting early must not claim an answer never reached
- [x] **Catch a prior audit of the same answer.** Built as `sayswho/prior_audit.py`, and it was the weakest
      control in the project until it was: neither existing guard could see this case, because
      `goldset.agreement` compares label times against the run they are compared with, so labels written today
      pass against a run made tomorrow, and G4 ties to the split, which differs because Phase 1 does not repeat
      itself. The scan matches on `answer_sha256` across `reports/` and `runs/`, so a report renamed or moved
      is still found, and the tool exits 3 before asking its first question rather than after three claims have
      been read. Three things it is careful about: it reads files full of verdicts and never carries one out,
      it reports not-checked rather than clean when there is no artefact directory to look in, and there is no
      flag to skip it. The way through is `--supplemental`, which is a different and clearly labelled thing
      rather than a weaker blind. Run against this repo it refuses immediately, which is correct and not
      comfortable: the one real split on disk has two audits behind it. `FINDINGS.md` item 16
- [x] **Prepare the session before it starts.** `tools/prep_goldset.py`. It draws the same sample the
      labelling tool will, by importing `choose_sample` rather than reimplementing it, warms the cache for any
      page in that sample it does not already have, and reports what the afternoon will be: pages, characters
      to read, how many pairs are unauditable and how many can have a pasted passage checked against our own
      extraction. It fetches only cache misses on purpose, because a fresh copy of a page we already have
      moves the extraction check onto bytes the judge never read, and it says which pages that caveat applies
      to. It runs the prior-audit scan too, so `--supplemental` is a decision made before the terminal is open
- [x] The fifth workflow fault, found by building that. Without `--capture` no G2 code is known, every pair
      buckets as `UNKNOWN`, and the stratification quietly becomes product-only, so §3 Phase 4's "unauditable
      first" does not happen. Demonstrated rather than reasoned: on the real split the sample changed when the
      run record was supplied, from six pages with no unauditable pair to seven including the paywalled and
      the no-text-layer ones. The prep tool says NOT STRATIFIED when it happens, and reports the unauditable
      count as not-known rather than as zero
- [x] Label 30 to 40 claims by hand, before looking at any judge output. **Done 2026-08-15 over ChatGPT, 45
      labels, all blind, 36 comparable.** The prior-audit scan reported 723 files under `reports/` and `runs/`
      carrying no verdict over any of the ten answers, so blindness is a checked fact rather than an
      assertion. Target 45 was chosen after `prep_goldset.py` reported 6 unauditable pairs of 45, not before:
      the pool was 145 claim-source pairs over 33 sources, 31 `SOURCE_OK` and 2 `SOURCE_DEAD_LINK`, which is a
      much cleaner split than Perplexity's 15-of-145 unauditable and is why 45 yields 39 comparable rather
      than 30. The labeller returned 9 `UNAUDITABLE` rather than the predicted 6, so 36 comparable is the real
      number. Distribution: 22 `NOT_FOUND_IN_SOURCE`, 10 `SUPPORTED`, 4 `PARTIALLY_SUPPORTED`, 9
      `UNAUDITABLE`, 0 `CONTRADICTED`. The original note follows, because the reason this could not be done on
      Perplexity is the finding rather than the scheduling. **No longer possible over the Perplexity
      answers.** 6 blind labels exist, written 2026-08-13 between 21:09 and
      21:20 UTC, which is two and a half hours before the day 7 run started at 23:51 and is why they are
      blind and why `agreement`'s timestamp refusal passes on them. Two of the six are comparable, so the
      kappa behind everything is n=2. The run then put verdicts over all 24 answers, so `label_goldset.py`
      exits 3 on a blind session and `--supplemental` is the only way in, and those labels never enter kappa.
      **So the set is being rebuilt blind on ChatGPT rather than topped up**, over ten frozen queries drawn
      with seed 20260812 before any capture existed. `FINDINGS.md` item 22
- [x] **G4 verified that a gold set existed for this configuration, not that a calibration did.** It checked
      judge class, judge model, both prompt versions and split membership, and looked at no label: no minimum
      count, no blindness check, so forty supplemental labels across all 24 splits would have opened it and
      printed a stratum rate calibrated by two blind pairs. Fixed on day 8 rather than deferred, once it was
      clear the change tightens the gate rather than loosening one: `gates.MIN_BLIND_COMPARABLE` blind
      comparable labels are now required, set to thirty because that is the floor §0a already promised.
      Supplemental labels never count, and `UNAUDITABLE` never counts, since the judge was never asked about
      those pairs. Four tests, each describing a set that would have passed before. **It costs something and
      that is the point: the current six-label set now fails G4 on the count as well as on coverage.**
      `FINDINGS.md` item 22
- [ ] G4 counts labels and kappa is computed over labels that match a verdict which stands, so the gate
      checks an upper bound on the n behind a rate rather than the n itself. Thirty blind comparable labels
      whose verdicts were all voided would pass G4 and produce a kappa of nothing. Narrower than the hole
      closed on day 8 and left open knowingly, because closing it means handing the gate the judgements and
      G4 runs before they are all in
- [ ] **No guard refuses a judge run that would spend a labelling session's blindness.** `prior_audit` fires
      one way only: it refuses a labelling session after a run, and nothing refuses a run before a labelling
      session. Day 6 prepped a clean session and day 7 ran the stratum, both correct alone and wrong in that
      order, and the cost was the whole blind gold set for that stratum. The cheap version is
      `run_stratum.py` warning when it is about to judge an answer that a prepped-but-unlabelled session
      covers
- [x] Stratification, as far as blind labelling permits. Products and G2 codes are knowable before any model
      runs and are stratified on, with `UNAUDITABLE` reached first. Verdict classes are the judge's output,
      so a blind sample cannot stratify on them and a sample that did would not be blind. If `CONTRADICTED`
      comes back empty the answer is a supplement labelled afterwards, excluded from kappa and reported
      separately. This is a correction to §3 Phase 4 as written, not a shortcut around it
- [x] Commit the labels with a timestamp that precedes the judge run. Enforced: `goldset.agreement` raises
      if any blind label postdates the run it is being compared against
- [x] Per-class precision and recall, plus Cohen's kappa with its confidence interval. Each class carries
      its own n, and perfect agreement on a single class reports no interval rather than a flattering one
- [x] A second rater, non-human and declared as such. All 45 pairs labelled independently by Claude as
      `labeller: claude-opus-5`, in `goldset/second-rater-claude.gold.json`, a separate file that never merges
      with the human set and never enters a human kappa. Done after the human labelling started and without
      showing the human any of it, because presenting model labels first and inviting adjustment is anchoring
      that no guard in this repo can see: the file would still say `blind: true` and `prior_audit` would still
      report clean. Coverage: 21 S, 7 P, 2 N, 0 C, 15 U. The 15 U are structural, since the model only ever
      had the block page for those sources while the human could open them in a browser
- [ ] Report the two raters separately and never pooled. The comparison is a finding about how mechanical this
      task is, not a calibration: **the first six overlapping pairs agree on 0 of 6.** Four of those six are
      the access difference above. The other two are real disagreement on the same document, where the human
      read the page as silent and the model quoted a passage from our own extraction. That is the number the
      writeup reports, with its n, and it is why the human labels could not be replaced
- [x] **`extracted_pair` in `tools/label_goldset.py` ran the HTML extractor over raw bytes**, so for a PDF
      source it compared the labeller's passage against `endstream endobj` noise and always recorded the pair
      as unchecked rather than as a real comparison. `tools/reaudit_spans.py` fixed exactly this once and
      carries a docstring warning about it, which made it the second time the assumption shipped. Two of the
      45 sampled pairs are IRS PDFs, so the extraction check could never have fired on either. Fixed in
      `c52a808` on day 7, and fixed once rather than twice: both tools now read cached bytes through
      `fetch.text_pair`, which is the read-only half of `Fetcher._classify` and routes by document kind. Two
      tests hold it, one asserting a PDF is read as a PDF rather than as markup, and one running the same
      bytes through the helper and the fetcher and asserting they agree. This row stayed unticked after the
      work landed, which is the failure `TODO.md` exists to prevent
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

- [x] Honest run over the frozen consumer stratum. Run 2026-08-13 over the 24 bound captures with the 24
      stored splits, so the judge saw the claims a labeller could have read. Seven minutes, 130 model calls,
      532,970 tokens, nothing halted, no capture errored. Four artefacts in `runs/day7/`: the run record, the
      readout, `RUN_LOG.md` and the trace table. `FINDINGS.md` item 21
- [x] Metric readout. Produced, and **it printed no support rate, which is the deliverable rather than a
      shortfall.** G4 withheld on 18 of the 24 answers, naming both split hashes each time, because the gold
      set holds 6 labels over 4 splits and the run judged 24. `INSUFFICIENT_EVIDENCE` withheld 2 more on its
      own ground. The stratum aggregate then refused, on the grounds that an aggregate over the runs that
      happened to be measurable is an aggregate over measurability
- [x] The judge-fabricated-span figure, checked before being described, which is what §8 requires. All four
      voids re-checked against the cached bytes: 3 of 96 span-bearing verdicts are the judge stitching
      non-contiguous passages, two of them announcing it with a literal ellipsis, and **1 of 96 was this tool**
      inlining a `[44]` footnote marker the judge dropped. That one is now fixed, so a rerun of this stratum
      would report 3 of 96 rather than 4, and the writeup says the figure moved because the checker was
      corrected rather than because the judge improved
- [x] Label every rate as single-stratum **and as synthetic**. Made structural rather than promised:
      `harness.readout` prints the caveat in its header, from a table keyed by stratum, so a consumer run
      says the questions were written rather than asked and an unnamed stratum refuses to be characterised at
      all. An obligation on prose is one a tired person drops at 2am, which is the argument `rates.py` already
      makes by holding the no-API-rate rule in code
- [x] Plausibility audit of the numbers. Written into `FINDINGS.md` item 21 and signed as a judgement rather
      than an output. What looks right, what looks wrong (`CONTRADICTED` empty across 130 verdicts when break
      attempt 1 shows the class is reachable), what looks too good (58% supported, and three reasons to
      distrust it before anyone quotes it), and what is missing rather than measured (42 of 158 claims carry
      no citation and this tool is blind to whether they needed one)
- [x] Fix the footnote-marker void. Fixed in the guard rather than in the extractor, deliberately: the
      document keeps saying what we extracted, and the comparison learns that a bracketed number is not part
      of the sentence. `span_is_present` tries twice, the second pass stripping bracketed numbers of up to
      three digits from both sides, and only when the first fails. Re-checked against the same cached bytes:
      `CO-15` is overturned and the other three stay voided, which is the blast radius it was meant to have.
      `drift.span_predates_generation` routed through the same function so the identical marker cannot void
      the identical span under a different code. The widening is stated where it is made: a span differing
      from the page only in bracketed numbers is now accepted
- [x] The `SOURCE_DEAD_LINK` that is not one. Fixed: a non-200 whose own headers or body name it an
      abuse-detection page is `SOURCE_BOT_BLOCKED` whatever status it arrived with, bounded to responses under
      8 KB so an article about bot detection is not mistaken for one. Re-derived from the cache with no new
      requests: **the run's corrected table is 42 `SOURCE_OK`, 8 `SOURCE_BOT_BLOCKED`, 1 `SOURCE_UNREACHABLE`
      and zero dead links.** Not one of the fifty-one cited sources was a broken citation, which makes the
      unauditable rate a measurement of our access rather than of anyone's citation hygiene
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
- [x] ~~Consumer stratum run~~ Promoted into the core on day 6, so this is no longer a stretch item. Rates
      are still reported per stratum, which now means one stratum and a statement that there is only one
- [x] Break attempts 1 to 4 built as one runner, `tools/break_attempts.py`. Each declares the failure it is
      looking for before it runs, and the criterion is read mechanically rather than reinterpreted afterwards
- [x] Break attempt 2, paywall misread. **Held.** The only one of the four needing no judge, because holding
      means the judge is never called on a page recognised as withheld. One document, so it says the mechanism
      handled this wall, not that it catches walls
- [x] Break attempts 1, 3 and 4: run them. Done 2026-08-11 against the live Gemini judge on `judge-v2`,
      output in `runs/break/`. 3 and 4 held, and 3 held by the predicted route rather than by luck: the judge
      quoted the added sentence, the span was genuinely on the live page, and the drift layer voided it as
      `SPAN_ADDED_AFTER_GENERATION` anyway. 1 broke, and not into the failure it had declared
- [x] Attempt 1b, which did not exist when the run started. Attempt 1's fixture was confounded: it ended by
      denying that it reported any effect estimate, so it measured whether a disclaimer reads as a
      contradiction (it does, 4 of 4) rather than whether topical overlap reads as support. 1b removes the
      denial and gets the declared failure, `PARTIALLY_SUPPORTED` for a claim the page never states, 4 of 4,
      every span verbatim and on the page. `FINDINGS.md` item 15
- [x] Fix the runner's false sentence. `_assess` reported every non-`NOT_FOUND_IN_SOURCE` verdict as "the
      failure the attempt was looking for", which was untrue for attempt 1 and had already been written to
      `results.json`. Held and broke are still decided by `holds_if` alone, so the correction cannot flatter a
      result: a break now records which failure it found and says when that is not the declared one
- [ ] Decide what attempt 1's `CONTRADICTED` means for published verdict counts. Silence read as
      contradiction inflates the verdict that accuses a product most directly, and deflates the one that says
      the source does not address the claim. Two documents and eight calls is a hypothesis about the judge,
      so this waits on the gold set, which is now the only thing that can measure three separate biases
- [ ] Say in the writeup that `PARTIALLY_SUPPORTED` is the claim state with the weakest evidence behind it.
      `missing_qualifiers` named the missing figure correctly every time and the verdict was still wrong, so
      the qualifier list is not a substitute for the refusal the page warranted
- [x] Per-domain reporting. `sayswho/domains.py`, counted in claim-source pairs, grouped by registrable domain
      so www and bare are one publisher, and gated by G4 exactly as the aggregate is: a slice of a number that
      may not be printed is still that number. A single readable pair gets counts and no percentage, since
      "100.0%" over one observation is what gets quoted without its n. The table leads with the reason sources
      could not be read, because a low rate for one publisher is a hypothesis about this pipeline first
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

## Capture from an API rather than the DOM

- [x] `sayswho/apicapture.py`. Produces an ordinary capture with `source="api"`, so the CLI, the harness and
      the report all work on it unchanged. Stdlib only, no new dependency
- [x] No schema hardcoded. Four providers return citations in four shapes and the documentation for one of
      them described a structure that did not match what the file was first written to expect, so the walk
      finds citation-shaped objects, records the JSON path of each, and counts the URLs it did not take. That
      count is what made the Perplexity bare-list shape visible instead of reporting a clean zero
- [x] Live calls only for a provider whose request builder has actually been run. Gemini, because it is the
      only free tier here. Everything else replays a stored response through `--from`, which needs no
      knowledge of how the call was made
- [x] `tools/compare_capture.py`. The reason the API path is worth having: it measures how many citations the
      DOM capture missed, which is the largest unquantified risk in the project and a number that has never
      existed. Reported as a floor, with the prose overlap beside it, because same question is not same answer
- [ ] Run one live Gemini grounded call and check the walk against the stored response. **Mine to do,** the
      key is in your shell and not mine. `python3 tools/api_capture.py --provider gemini --prompt "..."`
- [ ] Run the fidelity comparison on a real pair, DOM and API, for one frozen query. This is the number that
      belongs in §7 beside the support rate
- [x] **Decided 2026-08-11: no API-sourced rate is published.** An API answer is a different object from the
      one a person sees, and §1 says this tool audits products. So the API path exists to measure the scraper
      and never to produce a published support rate, unauditable rate, drift rate or agreement figure. A
      capture with `source="api"` may be audited, and its per-claim verdicts may be read and quoted, because
      those are statements about one document and one sentence rather than rates about a product
- [x] Prose gate: `tests/test_documents.py`. Every path and module a document names must exist, the
      load-bearing claims are checked against the code (the extension's language, the two-dependency promise,
      the stdlib-only layers, the dated prior-art table, no document promising a confidence score), and the
      test count in `STATUS.md` is checked against the suite. Built by reintroducing all three of day 5's real
      prose failures and confirming each fires. Two bugs in the gate itself while writing it, one of them
      comparing an unnormalised window so that "no\n confidence score" did not match "no confidence", which is
      the third time today the same fault appeared. Previously: check the claims documents make about files. Three prose claims were found false on day 5,
      the extension's language, two about competitors, and one where a commit message said §7 said something
      §7 did not contain. All three were found by being asked. `test_extension_manifest.py` already asserts
      that source files contain given strings, so the mechanism exists and is pointed at code rather than at
      documentation. `FINDINGS.md` item 13
- [x] No-API-rates enforced in `sayswho/rates.py`. `UNPUBLISHABLE_SOURCES`, checked in `for_run` before any
      rate is computed and in `aggregate`, with no override parameter: unlike a conflicted product, which is
      still worth reporting per-product, there is no legitimate reason to want a rate from an API capture. The
      per-domain path excludes them and reports the exclusion, because a slice is still a rate. Per-claim
      verdicts are untouched, since those are statements about one document and one sentence Every other rule of this kind is a gate:
      `CONFLICTED_PRODUCTS` refuses a Google surface in an aggregate, `standing_denominator` raises on a
      contaminated denominator, G4 refuses an uncalibrated rate. A decision that lives only in a TODO is one
      a tired person overrides at 2am on day 7 without noticing they did

## Spans, after the re-audit

- [x] Fold typography in the span guard. Quotes, dashes, soft hyphens, zero-widths, and NFKC per character
      for ligatures and full-width forms. Three of five variants used to void a span the page really contained
- [x] Separate the claim-id normalisation from the span guard's. `canonical_for_id` is frozen and documented
      as such: G4 ties a gold set to claim ids, so a span-guard change would otherwise have relabelled
      everything silently
- [x] Re-audit the voided spans. `tools/reaudit_spans.py`, over cached bytes rather than the live web, since
      re-checking against a page fetched today answers a different question. One of four voids overturned by
      the PDF fix, two traced to a symbol-font bullet, one is a genuine catch. `FINDINGS.md` item 14
- [x] Fix the PDF `Td` line-break bug that broke "(61.1%)" into "(6 1 . 1 %)" and voided a correct verdict
- [x] Symbol-font bullets in PDFs. Fixed, and the sentence that said it could not be was the reason it stayed
      broken: "needs font-encoding support a stdlib reader does not have" was true of the general case and
      false of this document, which carried the reverse table inside it as an ordinary Flate stream. Two bugs,
      not one. The symbol bullet was a two-byte code in an embedded SymbolMT subset, now read through the
      document's own `/ToUnicode` CMaps, pooled, with a code two fonts disagree about dropped rather than
      guessed. The second bullet was WinAnsi 0x95, decoded into a control code and then stripped as
      never-content, which deleted the evidence rather than corrupting it, and that half needed no font at all.
      Measured on the real boston.gov PDF: 54,811 characters before and after, 23 bullets where there were
      none. `FINDINGS.md` item 17
- [ ] The fabricated-span count over PDF sources. Still reported separately from HTML, and still withdrawn
      rather than restated, because the two voided spans are not overturned by the fix: they were quoted from
      an extraction this tool no longer produces, so only judging the fixed document settles them. That is the
      re-run below, not a re-check
- [x] Precomposed against decomposed accents in the span guard. The blocker was a belief rather than a
      constraint: composing cannot be done per character, and decomposing can, and decomposing reaches the same
      place from both sides. `fold_for_span` now strips the Combining Diacritical Marks block after an NFD
      pass, so a precomposed accent and a decomposed one match and the per-character index in `report.py`
      still lands on the right characters, which is what a test now pins. The line is the block, not the `Mn`
      category: a Devanagari virama and a Hebrew point are also `Mn`, and dropping either changes the word
      rather than its typography. The cost is stated rather than hidden, since the guard can no longer tell
      "resume" from an accented one
- [ ] Re-run the fabricated-span figure once there is a run to compute it over, and say in the writeup that
      the earlier one was mostly an artefact of the checker rather than a finding about the judge

## The ethics gate

- [x] **Privacy and honesty, shown passing rather than promised.** `sayswho/ethics.py` and
      `python3 tools/ethics_gate.py`. The attestation row asks for the gate passing, and a paragraph saying
      the contract holds is not evidence that it does, which is the argument this whole project rests on
- [x] Privacy checked against git, not against the `.gitignore` text. Four checks: nothing private staged,
      nothing private already tracked (ignoring a directory does not untrack what is in it), every private
      rule actually matches when git is asked, and no key-shaped string in any tracked file. The key patterns
      are built by concatenation, because written as single literals the scanner finds itself and the gate
      can never pass
- [x] One reviewed exception, `runs/span-reaudit.json`, named in the output with its reason rather than
      silently skipped. It is the evidence behind `FINDINGS.md` item 14 and it holds public consumer-stratum
      page spans. An exception with a reason can be argued with; a check relaxed to pass cannot
- [x] Honesty is the suite's honesty tests, run rather than cited. A gate reporting on tests it did not run
      is the thing the gate exists to prevent, so `--fast-ethics-gate` says which half it did not check
- [x] Wired into `tools/run_stratum.py` ahead of any fetch, so "if either fails, the run does not happen" is
      enforced on the one path where nobody watches every line
- [x] Fifteen tests, each forcing a failure against a throwaway repository: a force-added capture,
      correspondence staged, a private file already committed, an ignore rule that does not match, a leaked
      key, and a directory that is not a repository at all, which reports not-checked rather than pass

## Deliverables, by rubric row

- [x] Contribution works, 60 points. Installable MV3 extension loaded and run on real pages, headless harness
      that has now produced a real run, a test per gate that makes it fire on the bug it exists to catch, and
      the parity check running the real renderer in node against a payload the real Python built
- [x] Two-customer pair, 30 points. `recipes/audit-citations.md` in nine sections, plus
      `recipes/audit-citations.card.md` covering six failure modes. Five of the six look like "the citation
      failed" and only one of them is, which is the card's organising idea
- [x] Verified-data attestation, 35 points. All three parts exist as of day 6, and the blocker named here was
      the trace table never having run over real data, which it now has: `runs/day7/TRACE.md` is generated
      from the run rather than typed. The §4 boundary table is generated from `sayswho/boundary.py` and
      `tests/test_documents.py` fails if the document and the code disagree. The gate output is
      `python3 tools/ethics_gate.py`. What this replaces, kept because deleting it would hide the change:
- [x] ~~Verified-data attestation, blocked on the trace table.~~ Two of the three parts were done. The §4 boundary table is
      generated from `sayswho/boundary.py` rather than typed, carries all seven classifications, and
      `tests/test_documents.py` fails if the document and the code disagree or if a run record emits a field
      no row covers. The privacy and honesty gate output is `python3 tools/ethics_gate.py`. The per-number
      trace table exists and is generated, but it has never run over real data, which is the blocker
- [x] The honest run, 35 points. All five parts exist: `runs/day7/` holds the transcript and the metric
      readout, the plausibility audit is written and signed as a judgement in `FINDINGS.md` item 21, break
      attempts 5 and 6 have written results in `BREAK_ATTEMPTS.md`, and §7 carries ten limitations including
      the ones this run added
- [ ] GitHub PR, 25 points. **Description drafted to the two open answers: `PR_DESCRIPTION.md`.** Title, the
      ten-minute review path, the limitations stated up front, the three design decisions worth arguing with,
      and the table of six bugs found by running the tool rather than by the suite. Two blanks marked in the
      file, and they are the same two as before: which repo this targets and which chapters it satisfies.
      Original note follows.
- [ ] ~~GitHub PR~~ `contrib/jayanth-says-who` branch with a maintainer-ready description.
      **Mine to do first, two answers:** which repo this targets, and which chapters SaysWho satisfies. The
      requirement asks for the chapters by name and nothing in this repo cites one, so that is a decision
      rather than a lookup. Nothing else about the description can be written until both are known, since a
      maintainer-ready description is addressed to a specific maintainer and claims specific coverage
- [x] Portfolio piece, 35 points: the case study. `CASE_STUDY.md`, for a technical reader, with the four
      load-bearing decisions and what each cost. The "what I would do differently" section is longer than
      the results section, which is the accurate shape on day 5
- [x] Portfolio piece, the install half. `README.md` now opens with it: clone, load unpacked, two buttons.
      Capture needs nothing running; the extra three lines for verdicts are separated out and labelled, so the
      thirty-second path is not padded with the five-minute one
- [ ] Portfolio piece, the install claim tried by somebody who is not me. Both halves of the row above are
      written and ticked: `CASE_STUDY.md` for the technical reader, and the `README.md` opening for the
      install. What is untested is the thirty seconds, since the only person who has ever run those steps is
      the person who wrote them and already knows which folder to pick. One outsider following the README
      cold, and whatever they trip on, is the whole of this row. It was worded as "the case study half"
      until day 8, which read as though `CASE_STUDY.md` were outstanding when it has existed since day 5
- [ ] Explainer video, 20 points. **Script and shot list written: `VIDEO.md`.** Six shots, the uncut segment
      specified step by step on `CO-22`, the three sentences to get exactly right, and what not to do on
      camera. Recording it is yours. The refusal is the middle of the demo rather than a caveat at the end,
      because a claim the tool declines to score is the argument
- [x] Honesty overlay, 10 points. Calibrated verbs throughout, prior art named and verified against its own
      documentation twice, the §5a failure condition declared before any data existed, and the §0a status
      table maintained rather than assembled at the end

## Honesty obligations, regardless of how the numbers come out

These are not tasks that can be traded away for time. They are the reason the project is worth doing.

- [ ] Every rate ships with its n and a confidence interval, and the writeup says which differences the
      sample cannot resolve rather than ranking things it has no power to rank
- [ ] Kappa at n between 30 and 40 is reported as a wide-interval estimate, not as a calibration
- [ ] Products are named, and every sentence about them is calibrated. "We could not reproduce support for N
      of M claims, of which K were source-unreachable", never "Product X fabricates citations"
- [x] Prior art named plainly, and checked rather than asserted. All four verified against their own
      documentation on 2026-08-11. Two claims in §1b did not survive: "every incumbent outputs a confidence
      score" is false for GPTZero and unfair to FactSentinel, whose own page warns that a single confidence
      number makes weak evidence feel settled, and two of the four are not doing this task at all. §1b now
      carries a table of what each says it does, plus the academic attribution work it never named, plus the
      one thing CiteGuardian does that SaysWho does not. `FINDINGS.md` item 12
- [x] Re-check §1b before submission. Done 2026-08-14 against all four pages. Every quoted phrase still
      appears where it is attributed, including FactSentinel's warning that a single confidence number makes
      weak evidence feel settled. One correction: "across several frontier models" was this document's phrase
      and not theirs, and it is removed. The claim that none of them documents what it does with an
      unfetchable source was asked directly of the two doing this task and holds. Original note follows.
- [x] ~~Marketing pages change, and every claim in that table is dated 2026-08-11 rather than timeless.~~ or worth one more pass if the writeup slips past a week
- [ ] Until the head-to-head runs, the differentiator is described as structural rather than measured, and
      incumbent behaviour is attributed to their marketing copy
- [x] The frozen query set is published in full so a reader can judge the sample instead of taking my word
      for it. `queries/consumer.toml` holds all 24 with their `cost_of_error`, and `queries/FREEZE.json` holds
      the hashes. Original note follows. Cheaper than it was and more important: the set that runs is synthetic, so a reader judging it
      is judging questions I wrote, and there is no provenance claim standing between them and that judgement
- [ ] ~~The scrub drop count is published alongside the support rates~~ **Withdrawn on day 6, and named as
      withdrawn.** There was no intake, so there is no drop rate. A promised number that cannot be
      produced is reported as absent rather than quietly dropped from the list
- [x] The judge-fabricated-span rate is published rather than quietly fixed, **and it is only described as a
      finding about the judge once the extraction behind each void has been checked.** Honoured twice now. On
      the day-6 run all four voids were re-checked before any of them were described: 3 of 96 are the judge
      stitching non-contiguous passages and 1 of 96 was this tool inlining a footnote marker, now fixed. The
      original wording follows. That precondition is new
      and it is here because the obligation as originally worded would have published the wrong thing: three
      of the first four voids were caused by this tool, and the honest phrasing separates a void caused by the
      model from one caused by the extractor. `FINDINGS.md` item 14
- [x] §7 stays in, and grew rather than shrank: ten limitations now, including the ones the honest run added.
      It cannot check whether a source is true, it is blind to omission, and it cannot tell a peer reviewed
      paper from a blog post
