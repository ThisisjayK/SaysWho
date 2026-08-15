# ChatGPT capture order, pre-registered

Written 2026-08-15, day 8, **before a single ChatGPT answer had been captured**. The git commit that adds
this file is the evidence for that, which is the only reason it is a file rather than a decision made at the
keyboard tomorrow.

## Why this exists

The consumer gold set is being rebuilt on ChatGPT, because the day 7 run put verdicts over all 24 Perplexity
answers and a blind labelling session over them is refused. `FINDINGS.md` item 22.

Ten queries were drawn for that on day 8. G4 now requires 30 blind labels that can be compared with a
verdict, and whether ten ChatGPT answers yield 30 comparable pairs is not knowable until their sources are
fetched: 15 of 145 unauditable is a fact about the pages Perplexity cited, not a constant.

So the ten might not be enough. **"Capture a few more" after seeing the first ten is a choice made with the
data in view**, and a gold set assembled that way stratifies on whatever the first ten happened to lack. The
order below removes the choice: if more are needed, take the next id, then the next.

## The order

Positions 1 to 10 are the draw already published in `FINDINGS.md` item 22 and `TODO.md`. Positions 11 to 24
are the continuation, derived from the same generator in the same call, so nothing about the first ten
changed when the rest were fixed.

| # | Query | Question |
|---|---|---|
| 1 | CO-02 | At what age should someone whose parent had colon cancer start getting sc... |
| 2 | CO-03 | What is the maximum daily dose of acetaminophen for an adult, and does it... |
| 3 | CO-08 | If I leave my job with an outstanding 401k loan, how long do I have to re... |
| 4 | CO-10 | What is the deadline to file a federal tax extension, and does an extensi... |
| 5 | CO-14 | Can I travel outside the US while my change of status petition is pending... |
| 6 | CO-17 | How many hours per week can an F-1 student work on campus during the acad... |
| 7 | CO-20 | Does replacing a residential electrical panel in Boston require a permit,... |
| 8 | CO-21 | How much notice does a Massachusetts landlord have to give before raising... |
| 9 | CO-22 | Can a utility company shut off heat for nonpayment during winter in Massa... |
| 10 | CO-24 | What is the deadline for a Massachusetts landlord to return a security de... |
| 11 | CO-06 | Can I get the shingles vaccine before age 50 if I am immunocompromised, a... |
| 12 | CO-19 | In Massachusetts, how much notice does a landlord have to give before ent... |
| 13 | CO-13 | How long is the STEM OPT extension, and what happens to my work authoriza... |
| 14 | CO-01 | Is it safe to take ibuprofen regularly if I am on lisinopril for blood pr... |
| 15 | CO-11 | Does closing an old credit card hurt my credit score, and how long does t... |
| 16 | CO-07 | What is the Roth IRA contribution limit this year, and at what income doe... |
| 17 | CO-04 | Does St. Johns Wort reduce the effectiveness of hormonal birth control? |
| 18 | CO-23 | How do I check whether a home improvement contractor is registered in Mas... |
| 19 | CO-09 | How much of my money is FDIC insured if I have a checking account and a s... |
| 20 | CO-15 | How many days is the grace period after an F-1 program end date before I ... |
| 21 | CO-12 | Can I withdraw money from a Roth IRA before retirement age without a pena... |
| 22 | CO-16 | Do I qualify for an interview waiver on an H-1B visa renewal, and how rec... |
| 23 | CO-18 | If my I-140 is approved and I change employers, do I keep my priority date? |
| 24 | CO-05 | What blood pressure reading is high enough that I should go to an emergen... |

Positions 1 to 10 are the ten already published. 11 onward is where to go next.

## How to re-derive it

Stdlib, no state beyond the seed and `queries/consumer.toml`, which
`python3 tools/freeze_queries.py check` confirms is unchanged.

```python
import tomllib, random

ids = [q["id"] for q in tomllib.load(open("queries/consumer.toml", "rb"))["query"]]
r = random.Random(20260812)
first = sorted(r.sample(ids, 10))        # the ten published on day 8
rest = [i for i in ids if i not in first]
r.shuffle(rest)                          # same generator, continued
order = first + rest
```

The seed is the one `tools/prep_goldset.py` and `tools/label_goldset.py` already default to, so the sampling
in this project has one seed rather than a new one per decision.

## What this does not fix

Capturing in this order is not the same as labelling in it. The labelling sampler draws its own pairs and
takes unauditable ones first, per `SCOPE.md` §3 Phase 4. This file governs which questions get asked of
ChatGPT and in what order, nothing else.

And an order fixed in advance does not make a stopping rule. Deciding to stop once 30 comparable pairs exist
is still a decision made with the data in view, and it is the honest one available: the alternative is
capturing all 24 regardless, which the remaining days do not hold. Whichever number is reached, the writeup
reports how many answers were captured and that capture stopped when the gate's floor was met.
