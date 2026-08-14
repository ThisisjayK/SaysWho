# PR description, ready except for two answers

**Two blanks only you can fill, marked `<<< >>>` below.** Which repository this targets, and which chapters it
satisfies. Everything else is written and every number in it is checkable against this repo.

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

<<< NAME THE CHAPTERS HERE. The requirement asks for them by name and nothing in this repo cites one, so
this is a decision rather than a lookup. For each chapter, one sentence saying which artefact demonstrates
it, e.g. "gate G3 and tests/test_judge.py" rather than "the project demonstrates this." >>>

### How to review it in ten minutes

```bash
git clone <<< TARGET REPO >>> && cd SaysWho
python3 -m venv .venv && .venv/bin/pip install google-genai
.venv/bin/python -m pytest -q          # 783 tests, offline except one node process
.venv/bin/python tools/ethics_gate.py  # privacy and honesty, checked rather than promised
```

Then read three files in this order:

1. `FINDINGS.md` item 21, the first honest run. Twenty-four answers, 51 sources, 130 verdicts, and no support
   rate, because the gold set covers four of the twenty-four splits and gate G4 will not calibrate a rate it
   cannot calibrate.
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
- The gold set has **six labels of a planned thirty to forty**, which is exactly why the run above published
  nothing.

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

- Fill the two blanks. The chapters need naming individually with the artefact that demonstrates each.
- If the target repo has a `CONTRIBUTING.md`, read it before sending: this description assumes a maintainer
  who wants the limitations up front, and some projects want a shorter opening.
- `queries/professional.toml` is committed empty on purpose. If a reviewer reads that as unfinished work
  rather than a refusal, the second bullet under "what it does not do" is the sentence to point at.
