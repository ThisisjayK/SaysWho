# The frozen query set

Day 1 of §12. This directory holds the stimulus set for every SaysWho run, and the machinery that makes
"frozen" a checkable fact rather than a promise in a document.

Two strata, per §10 of `SCOPE.md`:

| File | Stratum | Runs in | Provenance |
|---|---|---|---|
| `professional.toml` | Professional research | Core, day 7 | Real queries from my own PM work, scrubbed |
| `consumer.toml` | Consumer high-stakes | Stretch item 7 | Synthetic |

**Both are authored and frozen now, even though only one runs in the core.** That ordering is the whole
point. If the consumer set were written on day 8, it would be written by someone who had already seen what
the professional set produced, and it would be impossible to prove it hadn't been shaped by that.

## What "frozen" means here

A freeze is a hash manifest, `FREEZE.json`, recording the sha256 of each query file and of each individual
query. After a stratum is frozen:

- no query is added
- no query is removed
- no query text is edited, and neither is its `cost_of_error`

`tools/freeze_queries.py check` recomputes the hashes and exits non-zero if any of that happened. It runs
before every capture run, so a tuned benchmark fails loudly instead of quietly producing a better number.

`cost_of_error` is inside the hash deliberately. It is the pre-registered reason the query is in the set at
all, and rewriting it after seeing a bad result would be a quieter kind of tuning than swapping the query.

```bash
python3 tools/validate_queries.py
```

```bash
python3 tools/freeze_queries.py status
```

```bash
python3 tools/freeze_queries.py freeze
```

```bash
python3 tools/freeze_queries.py check
```

`freeze` refuses to act on a stratum whose `status` is still `draft`, and refuses to re-freeze anything
already in the manifest. Breaking a freeze requires `--force --reason "..."`, which appends to a permanent
`unfreeze` record in the manifest rather than erasing the old entry. There is no way to break a freeze
silently, including for me.

## Schema

Each file has one `[stratum]` table and a list of `[[query]]` tables.

**`[stratum]`**

| Key | Meaning |
|---|---|
| `id` | Stratum identifier, e.g. `professional_research` |
| `id_prefix` | Prefix every query id in the file must carry, e.g. `PR` |
| `label` | Human name used in reports |
| `status` | `draft` until the stratum is complete, then `ready`. Only `ready` can be frozen |
| `provenance_policy` | `real_scrubbed` or `synthetic`. Every query in the file must match |
| `domains` | Allowed values for a query's `domain`. A query outside this list is an error |

**`[[query]]`**

| Key | Required | Meaning |
|---|---|---|
| `id` | yes | `PR-01`, `CO-07`. Unique across all files |
| `domain` | yes | One of the stratum's declared domains |
| `text` | yes | The question exactly as it will be pasted into each product |
| `cost_of_error` | yes | What it costs the asker to act on a wrong answer. §10 requires this on every query |
| `provenance` | yes | `synthetic` or `real_scrubbed` |
| `scrub_notes` | if `real_scrubbed` | What was removed and what that removal cost the question |
| `asked_approx` | if `real_scrubbed` | Rough month the original was asked, e.g. `2026-06` |

**Forbidden keys.** The validator rejects any key containing `expected`, `predicted`, `verdict`, `gold`,
`score`, `confidence`, or `hypothesis`. There is no field in this schema for what I think a query will
produce. A stimulus set that records its author's expectations is one edit away from being a set selected to
meet them.

## What belongs in the professional stratum

The population is not "everything I asked an AI during work." It is **the answers that came back with
citations attached**, because an answer with no footnotes produces nothing to audit. Anything else is a
`NO_CITATIONS_EXPECTED` drop.

**Domains, and what each one contributes to the measurement.**

| Domain | Shape | What it produces |
|---|---|---|
| `competitive` | Pricing tiers, rate limits, feature availability, funding, integration support | Vendor pages and trade press. Vendor pages change, so this is the main source of `SOURCE_DRIFTED` |
| `market_sizing` | TAM figures, growth rates, adoption percentages, segment share | Analyst content, often paywalled. Main source of `SOURCE_PAYWALLED`, and the numbers most often repeated without a source |
| `regulatory` | What a rule requires, thresholds, effective dates, who it binds | Government pages and legal PDFs. Highest cost of error, and PDFs are where `SOURCE_EMPTY` appears |
| `technical_background` | How a mechanism works, benchmark results, context limits, standards | Papers, docs, changelogs. Where vocabulary-overlap false positives are most likely |

The spread is load-bearing, not cosmetic. §10 fills the gold set's `UNAUDITABLE` and `CONTRADICTED` classes
first, and a class the query set never produces cannot be hand-labeled. A set that cites only stable
government pages would reach day 5 with no unauditable examples and no way to calibrate the single
distinction the project rests on.

**A query qualifies if:**

1. It contains **checkable assertions**: numbers, dates, named entities, thresholds. "Should we build this"
   produces reasoning. "What does this regulation require above this threshold" produces claims.
2. **Something downstream depended on the answer.** It went into a doc, a deck, or a recommendation. That
   dependency is what gets written into `cost_of_error`.
3. It is **one information need**. Sprawling multi-part prompts produce answers that resist atomic claim
   splitting, which pushes the difficulty into Phase 1 where it is a model-inference step rather than a
   measured one.

**Two selection rules that matter more than the rest.**

**Do not select on remembered outcome.** Not the queries where I remember the tool getting it wrong, and not
the ones where I remember it doing well. Selecting on the outcome tunes the benchmark before it exists, and
it is undetectable from the outside because the resulting set looks exactly like an honest one. Pull
chronologically or by domain and take what is there.

**Do not improve the phrasing.** These get transcribed roughly as typed, including the sloppy ones. §7 argues
that authorship here is a *coverage* limitation rather than a *validity* one, and that argument holds only
because a query is a stimulus rather than an attempt at optimal elicitation. Polishing the prompts converts
it into the validity version, which cannot be stated and bounded the way a coverage gap can.

**Target.** 20 to 30, roughly spread across the four domains. If the real history is thin in a domain, that
domain runs light and the imbalance is reported in the writeup. It is not topped up with inventions.

## Scrub procedure, professional stratum

These are real queries from real work, so they get reviewed one at a time before anything is committed.
Remove:

1. Employer names, and any former or client employer
2. Project and product codenames
3. Team, manager, and colleague names
4. Figures that identify a company: revenue, headcount, user counts, funding amounts, close dates
5. Any market so narrow that naming it identifies the company working in it
6. Dates specific enough to pin a query to an internal event

What lands in the repo is the question's shape, not its context. "Our" and "we" become the generic case.

**The drop rule.** If a query cannot survive scrubbing without losing what made it a real question, it is
dropped rather than watered down, and the drop is recorded in `SCRUB_LOG.md` with the reason. The drop count
is published. A scrub that quietly turns real questions into generic ones would give me a set that looks
real and isn't.

**Worked example. This is a format illustration and is not part of the set.**

```toml
[[query]]
id = "PR-00"
domain = "market_sizing"
text = """
How large is the US market for AI-assisted contract review software, and what is the growth rate?
"""
cost_of_error = """
A market size figure with a bad citation gets copied into a strategy doc and repeated by people who never
saw the source. Wrong by an order of magnitude changes whether a team is funded.
"""
provenance = "real_scrubbed"
scrub_notes = """
Original named the specific vertical we were sizing and the incumbent we were sizing against. Both removed.
The generic version keeps what made this a real question, which was needing a defensible number fast.
"""
asked_approx = "2026-06"
```

## Stated limitations of this set

- **One author.** Every query here is mine or written by me. §7 of `SCOPE.md` treats this as a coverage
  limitation, not a validity one, and the mitigation is that this set is published in full so a reader can
  judge the sample instead of taking my word for its representativeness.
- **The local-services domain is jurisdiction-bound to Massachusetts.** That is where I could write questions
  with a real cost of error attached. Support rates in that domain are about Massachusetts sources and are
  not evidence about local-services questions generally.
- **The consumer stratum is synthetic.** It is written to the same standard, but nobody actually asked these.
  It samples the shape of high-stakes consumer questions, not their real distribution.
- **Time-sensitivity is deliberate.** Many queries here have answers that changed recently or are bounded by
  a filing year. That is what makes source drift and dead links measurable, and it also means this set will
  age. Re-running it in a year measures a different web.
