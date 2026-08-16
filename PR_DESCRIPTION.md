# PR description

**No blanks left, and one thing to check before sending.** The target repository is
`ThisisjayK/SaysWho`, a self-contained contribution rather than one to another project. The chapters are
named against the module list in `INFO-7375-Computational-Skepticism-and-AI`, whose README calls itself a
book-style structure, so "chapter" is read as "module" there. **If the assignment means something else by
chapter, that section is the one to redo**, and it is the only inference in this document rather than a
lookup. Every number here is checkable against this repo.

Branch: `contrib/jayanth-says-who`

---

## Title

SaysWho: a citation auditor that refuses to score what it cannot check

## Body

### What this adds

A browser extension and a headless harness that check whether an AI answer's citations actually support the
sentences they are attached to. It splits an answer into claims, binds each claim to its citation markers,
fetches every cited page under a written data contract, and asks a judge one narrow question per pair: does
this page say what this sentence says.

The judge cannot answer `SUPPORTED` without quoting a span, and a script then confirms by substring match that
the span is really in the document that was retrieved. A span that is not there voids the verdict. That is a
deterministic check on a probabilistic component, and it is the part worth reviewing first.

### Which chapters this satisfies

Named against the module list in `INFO-7375-Computational-Skepticism-and-AI`, which its own README calls a
book-style structure. Eight of the fifteen, each with the artefact that demonstrates it. The seven not claimed
are listed after, because a coverage claim that names only its hits is the kind of claim this project exists
to check.

| Module | What demonstrates it |
|---|---|
| 1, Foundations of AI Skepticism and Botspeak Fluency | The six-state verdict vocabulary, which keeps "we checked and it is not supported" separate from "we could not check". `recipes/audit-citations.md` §9 names the two steps an agent must not take unattended, which is the Automation and Agency boundary drawn in code rather than described |
| 2, Logic, Probability, and Uncertainty | `sayswho/rates.py`. Every rate carries its n and a Wilson interval, `Rate.render` is the only formatter so no surface can print a bare percentage, and `tests/test_no_confidence_anywhere.py` enforces that no confidence number exists anywhere in the system |
| 3, Cognitive Bias, Model Bias, and the Human-AI Feedback Loop | Three measured judge biases rather than asserted ones: `PARTIALLY_SUPPORTED` at 16.7% precision (n=6), silence read as contradiction 4 of 4 in break attempt 1, and category conflation in both `CONTRADICTED` verdicts. `FINDINGS.md` items 15, 24 and 25 |
| 4, Data Validation Techniques for AI Systems | The frozen query set with hashes (`tools/freeze_queries.py`, checked before every run) and the answer-hash capture record. And the module's own question, is your dataset what you think it is, answered no: `FINDINGS.md` item 23 measures a 37.7% floor of citations the capture never saw |
| 7, Robustness, Adversarial Attacks, and Model Fragility | `BREAK_ATTEMPTS.md` and `tools/break_attempts.py`. Six attempts, each declaring the failure it looks for before it runs. Two are kept as passing tests of a failure rather than as fixes, including an injection that defeats the span guard by dictating a span that is genuinely on the page |
| 9, Human-AI Collaboration, Delegation, and Trust Calibration | The gold set is trust calibration in the module's own sense. 45 blind hand labels, `gates.MIN_BLIND_COMPARABLE` refusing an aggregate rate without 30 comparable ones, and a resulting kappa of 0.304 with a 95% CI of 0.004 to 0.604, a lower bound that does not exclude chance. The calibration's finding is that the tool's own verdicts should not be overtrusted |
| 11, Communicating AI Findings, and Presentation of Uncertainty | `sayswho/harness.py`'s readout and `harness.trace_table`, which traces every published figure to the record it came from and is generated rather than typed. The readout prints its synthetic-stratum caveat from a table keyed by stratum, so the caveat cannot be dropped by a tired author at 2am |
| 14, Rapid Prototyping and Build to Disprove | Every gate has a test that fails on the bug it exists to catch, not merely a test that it exists. The parity check runs the real renderer in node over a payload the real Python built and compares state by state |

**Not claimed, and why.** Module 5, explainability: the span requirement is adjacent to interpretability but
this project does no SHAP, LIME or counterfactual work. Module 6, fairness metrics and debiasing: no
quantitative fairness metric is computed. Module 8, reinforcement learning: nothing here is RL. Module 10,
visualization: the extension renders verdicts but there is no visualization pipeline and no critique of one.
Module 12, governance: `tools/ethics_gate.py` checks privacy and honesty against git rather than against a
governance framework, which is a smaller thing. Module 13, philosophical limits: `SCOPE.md` §7 states ten
limits including two that are unfixable inside this design, which is close, but the module is about meaning
and intentionality and this project is not. Module 15 is the capstone this submission is for rather than a
chapter it satisfies.

### How to review it in ten minutes

```bash
git clone https://github.com/ThisisjayK/SaysWho.git && cd SaysWho
python3 -m venv .venv && .venv/bin/pip install google-genai
.venv/bin/python -m pytest -q          # 816 tests, offline except one node process
.venv/bin/python tools/ethics_gate.py  # privacy and honesty, checked rather than promised
```

Then read three files in this order:

1. `FINDINGS.md` item 21, the first honest run. Twenty-four answers, 51 sources, 130 verdicts, and no support
   rate, because the gold set covered four of the twenty-four splits and gate G4 will not publish a rate it
   cannot calibrate. Then item 22, where that run is shown to have spent the blindness a gold set needs, and
   item 23, where the second product's captures are shown to be missing a third of their citations. Then item
   24, the run where the gate finally opened: 35 blind labels compared, Cohen's kappa 0.304 with a 95% CI of
   0.004 to 0.604, which is a lower bound that does not exclude chance. The gate held, the schedule did not,
   and the calibration, when it finally arrived, said not to trust the verdicts much. All three are reported.
2. `STATUS.md`, which lists every core and stretch item done or not-done with a reason, including the ones
   that would be more flattering to leave out.
3. `BREAK_ATTEMPTS.md`, where two attempts are kept as passing tests of a failure rather than as fixes.

### What it does not do, stated here rather than discovered in review

- It cannot tell you whether a source is **true**. A well-cited falsehood passes clean. This is the largest
  limitation and it is not fixable inside this design.
- It is blind to **omission**. An answer can score well by citing only its safe sentences.
- It cannot tell a peer-reviewed paper from a blog post.
- The professional query stratum, which was to be drawn from real research questions, **does not run**. The
  sessions it was to be transcribed from are gone, and inventing or retyping the questions would have made a
  published sentence false. The core runs on a synthetic consumer stratum which says so wherever it appears.
- **The citation capture is incomplete on ChatGPT, by a measured floor of 37.7 per cent.** ChatGPT collapses
  part of its citation list behind "+N" controls that the DOM never renders, so ten captured answers hold 33
  citations with at least 20 more missing. Unlike an earlier Perplexity loss of the same shape, this cannot be
  repaired from the stored pages. Any support rate over this stratum is a rate over inline-rendered citations
  rather than over the product's citations, and those are different claims. `FINDINGS.md` item 23.
- **A claim whose hidden source supported it is judged against the source that did render**, and comes back
  `NOT_FOUND_IN_SOURCE`: the one verdict with no span, therefore no span check, and the one that reads as an
  accusation. The direction of that bias is known and it is against the product.

### The design decisions most worth arguing with

**No confidence score, anywhere, enforced by a test.** A confidence number attached to a page that could not
be fetched is invented, and it destroys the distinction between "we checked and it is not supported" and "we
could not check". Unauditable claims are excluded from every denominator by a contract check that raises
rather than warns.

**One implementation of every verdict.** The extension's renderer draws what Python decided and computes
nothing. A test runs the real renderer in node over a payload the real Python built and compares the two,
state by state.

**The query set is frozen with hashes** before any capture, and a check fails on any addition, removal or
edit, including an edit to a query's stated cost of error. Breaking a freeze needs an explicit flag and a
written reason that is recorded permanently.

### What reviewing this found out about itself

Six bugs in the last two days, and **every one was found by running the tool rather than by the test suite**:

| Bug | What it would have published |
|---|---|
| Extractor stopped at the first citation selector | A quarter of Perplexity's citations silently missing |
| HTML extractor run over PDF bytes | A labeller's passage compared against `endstream endobj` |
| A 404 that was really an Akamai bot block | "This product cited a page that does not exist" |
| A footnote marker kept inline | A fabricated-span count charged to the judge |
| A malformed chunked response | An entire run lost after every model call was spent |
| A missing dataclass field | The same, on the first run that had anything to aggregate |

Four of the six would have put a wrong number in front of a reader, and three of those four would have blamed
a product or a model for something this pipeline did. That pattern is the argument for the project, so it is
in the PR rather than buried.

---

## Notes for you before sending

- **Check the chapter mapping.** It reads "chapter" as "module" from the course repo's own book-style
  outline, and claims eight of fifteen with the seven it does not claim listed and reasoned. If the
  assignment names chapters from a set text instead, redo that section; nothing else depends on it.
- **The gold set numbers, current as of 2026-08-16.** 45 blind labels, 36 comparable, 35 with a standing
  verdict to compare against. G4 opened and per-answer and per-domain rates printed. Cohen's kappa is 0.304,
  95% CI 0.004 to 0.604, so the lower bound does not exclude chance and the figure is a wide-interval estimate
  rather than a calibration. The stratum rate is still withheld, because one answer of the ten tripped
  `INSUFFICIENT_EVIDENCE`. `FINDINGS.md` item 24. Never quote the kappa without its interval.
- `queries/professional.toml` is committed empty on purpose. If a reviewer reads that as unfinished work
  rather than a refusal, the second bullet under "what it does not do" is the sentence to point at.
