## Run 2026-08-16T00:22:10+00:00

- stratum: consumer
- judge: GeminiJudge gemini-3.5-flash-lite, judge-v2, claims-v1
- gold set: goldset/chatgpt-consumer.gold.json
- user agent: SaysWho/0.1 (citation audit research; +https://github.com/ThisisjayK/SaysWho; kappagantula.j@northeastern.edu)
- captures: 10
- finished: 2026-08-16T00:30:19+00:00

### Metric readout

```
================================================================================================
SaysWho run: consumer   started 2026-08-16T00:22:10+00:00
judge        GeminiJudge gemini-3.5-flash-lite
versions     judge-v2, claims-v1
gold set     goldset/chatgpt-consumer.gold.json
reads as        single-stratum and SYNTHETIC. These questions were written, not asked, so no rate here describes real use by anyone
================================================================================================

captures     10
  capture-chatgpt-2026-08-15T2252000000.json chatgpt      ok
  capture-chatgpt-2026-08-15T2252100000.json chatgpt      ok
  capture-chatgpt-2026-08-15T2252150000.json chatgpt      ok
  capture-chatgpt-2026-08-15T2252190000.json chatgpt      ok
  capture-chatgpt-2026-08-15T2252240000.json chatgpt      ok
  capture-chatgpt-2026-08-15T2252280000.json chatgpt      ok
  capture-chatgpt-2026-08-15T2252330000.json chatgpt      ok
  capture-chatgpt-2026-08-15T2252370000.json chatgpt      ok
  capture-chatgpt-2026-08-15T2252460000.json chatgpt      ok
  capture-chatgpt-2026-08-15T2252500000.json chatgpt      ok

STRATUM RATE  withheld
  one or more runs withheld their support rate, so an aggregate over them would be an aggregate over the runs that happened to be measurable: INSUFFICIENT_EVIDENCE: more than half this answer's cited claims produced no verdict that stands, so a support rate over the remainder would be a rate over whatever happened to be readable rather than over the answer.

PER DOMAIN
  mass.gov: citation support rate, mass.gov: 19 of 54 claim-source pairs (35.2%, 95% CI 23.8% to 48.5%, n=54, over 1 split)
      not read: JUDGE_FABRICATED_SPAN 1, SPAN_ADDED_AFTER_GENERATION 1
  irs.gov: citation support rate, irs.gov: 23 of 47 claim-source pairs (48.9%, 95% CI 35.3% to 62.8%, n=47, over 1 split)
  boston.gov: citation support rate, boston.gov: 3 of 10 claim-source pairs (30.0%, 95% CI 10.8% to 60.3%, n=10, over 1 split)
  uscis.gov: citation support rate, uscis.gov: 1 of 7 claim-source pairs (14.3%, 95% CI 2.6% to 51.3%, n=7, over 1 split)
      not read: SOURCE_DEAD_LINK 3
  malegislature.gov: citation support rate, malegislature.gov: 9 of 9 claim-source pairs (100.0%, 95% CI 70.1% to 100.0%, n=9, over 1 split)
  gi.org: citation support rate, gi.org: 2 of 3 claim-source pairs (66.7%, 95% CI 20.8% to 93.9%, n=3, over 1 split)
      not read: SOURCE_DEAD_LINK 3
  fda.gov: citation support rate, fda.gov: 2 of 4 claim-source pairs (50.0%, 95% CI 15.0% to 85.0%, n=4, over 1 split)
  dhs.gov: citation support rate, dhs.gov: 0 of 2 claim-source pairs (0.0%, 95% CI 0.0% to 65.8%, n=2, over 1 split)
  masslegalhelp.org: 1 of 1 claim-source pairs readable, no rate (only 1 readable pair(s))
  A low rate for one publisher is a hypothesis about this pipeline first: a paywall pattern it misreads, a layout its extractor mangles, a format it cannot open.

PER ANSWER
  CO-02  chatgpt  split d1a3f0154b6b
    judge-fabricated-span rate: 0 of 2 span-bearing verdicts (0.0%, 95% CI 0.0% to 65.8%, n=2, over 1 split)
    source drift rate: 0 of 1 sources (0.0%, 95% CI 0.0% to 79.3%, n=1)
    unauditable rate: 3 of 6 claim-source pairs (50.0%, 95% CI 18.8% to 81.2%, n=6, over 1 split)
    withheld: INSUFFICIENT_EVIDENCE: more than half this answer's cited claims produced no verdict that stands, so a support rate over the remainder would be a rate over whatever happened to be readable rather than over the answer.
    verdicts: {'SUPPORTED': 2, 'NOT_FOUND_IN_SOURCE': 1, 'SOURCE_DEAD_LINK': 3}
  CO-03  chatgpt  split ff068afec018
    judge-fabricated-span rate: 0 of 4 span-bearing verdicts (0.0%, 95% CI 0.0% to 49.0%, n=4, over 1 split)
    source drift rate: 0 of 2 sources (0.0%, 95% CI 0.0% to 65.8%, n=2)
    unauditable rate: 0 of 4 claim-source pairs (0.0%, 95% CI 0.0% to 49.0%, n=4, over 1 split)
    citation support rate: 2 of 4 claim-source pairs (50.0%, 95% CI 15.0% to 85.0%, n=4, over 1 split)
    citation support rate, counted in claims: 1 of 2 claims (50.0%, 95% CI 9.5% to 90.5%, n=2, over 1 split)
    verdicts: {'PARTIALLY_SUPPORTED': 2, 'SUPPORTED': 2}
  CO-08  chatgpt  split a72d510667cc
    judge-fabricated-span rate: 0 of 18 span-bearing verdicts (0.0%, 95% CI 0.0% to 17.6%, n=18, over 1 split)
    source drift rate: 1 of 5 sources (20.0%, 95% CI 3.6% to 62.4%, n=5)
    unauditable rate: 0 of 35 claim-source pairs (0.0%, 95% CI 0.0% to 9.9%, n=35, over 1 split)
    citation support rate: 16 of 35 claim-source pairs (45.7%, 95% CI 30.5% to 61.8%, n=35, over 1 split)
    citation support rate, counted in claims: 6 of 7 claims (85.7%, 95% CI 48.7% to 97.4%, n=7, over 1 split)
    verdicts: {'NOT_FOUND_IN_SOURCE': 17, 'PARTIALLY_SUPPORTED': 1, 'SUPPORTED': 16, 'CONTRADICTED': 1}
  CO-10  chatgpt  split d69cca9c4538
    judge-fabricated-span rate: 0 of 10 span-bearing verdicts (0.0%, 95% CI 0.0% to 27.8%, n=10, over 1 split)
    source drift rate: 0 of 3 sources (0.0%, 95% CI 0.0% to 56.1%, n=3)
    unauditable rate: 0 of 12 claim-source pairs (0.0%, 95% CI 0.0% to 24.2%, n=12, over 1 split)
    citation support rate: 7 of 12 claim-source pairs (58.3%, 95% CI 32.0% to 80.7%, n=12, over 1 split)
    citation support rate, counted in claims: 4 of 4 claims (100.0%, 95% CI 51.0% to 100.0%, n=4, over 1 split)
    verdicts: {'SUPPORTED': 7, 'NOT_FOUND_IN_SOURCE': 2, 'PARTIALLY_SUPPORTED': 3}
  CO-14  chatgpt  split c440c7ff1a7d
    judge-fabricated-span rate: 0 of 1 span-bearing verdicts (0.0%, 95% CI 0.0% to 79.3%, n=1, over 1 split)
    source drift rate: no sources, so there is no rate
    unauditable rate: 3 of 6 claim-source pairs (50.0%, 95% CI 18.8% to 81.2%, n=6, over 1 split)
    citation support rate: 1 of 3 claim-source pairs (33.3%, 95% CI 6.1% to 79.2%, n=3, over 1 split)
    citation support rate, counted in claims: 1 of 3 claims (33.3%, 95% CI 6.1% to 79.2%, n=3, over 1 split)
    verdicts: {'SOURCE_DEAD_LINK': 3, 'NOT_FOUND_IN_SOURCE': 2, 'SUPPORTED': 1}
  CO-17  chatgpt  split effca12f40b7
    judge-fabricated-span rate: 0 of 1 span-bearing verdicts (0.0%, 95% CI 0.0% to 79.3%, n=1, over 1 split)
    source drift rate: 0 of 3 sources (0.0%, 95% CI 0.0% to 56.1%, n=3)
    unauditable rate: 0 of 6 claim-source pairs (0.0%, 95% CI 0.0% to 39.0%, n=6, over 1 split)
    citation support rate: 0 of 6 claim-source pairs (0.0%, 95% CI 0.0% to 39.0%, n=6, over 1 split)
    citation support rate, counted in claims: 0 of 4 claims (0.0%, 95% CI 0.0% to 49.0%, n=4, over 1 split)
    verdicts: {'NOT_FOUND_IN_SOURCE': 5, 'PARTIALLY_SUPPORTED': 1}
  CO-20  chatgpt  split cd9592deafbb
    judge-fabricated-span rate: 0 of 10 span-bearing verdicts (0.0%, 95% CI 0.0% to 27.8%, n=10, over 1 split)
    source drift rate: 0 of 2 sources (0.0%, 95% CI 0.0% to 65.8%, n=2)
    unauditable rate: 0 of 22 claim-source pairs (0.0%, 95% CI 0.0% to 14.9%, n=22, over 1 split)
    citation support rate: 6 of 22 claim-source pairs (27.3%, 95% CI 13.2% to 48.2%, n=22, over 1 split)
    citation support rate, counted in claims: 6 of 9 claims (66.7%, 95% CI 35.4% to 87.9%, n=9, over 1 split)
    verdicts: {'PARTIALLY_SUPPORTED': 3, 'NOT_FOUND_IN_SOURCE': 12, 'SUPPORTED': 6, 'CONTRADICTED': 1}
  CO-21  chatgpt  split fc789252f042
    judge-fabricated-span rate: 0 of 8 span-bearing verdicts (0.0%, 95% CI 0.0% to 32.4%, n=8, over 1 split)
    source drift rate: 1 of 4 sources (25.0%, 95% CI 4.6% to 69.9%, n=4)
    unauditable rate: 1 of 19 claim-source pairs (5.3%, 95% CI 0.9% to 24.6%, n=19, over 1 split)
    citation support rate: 7 of 18 claim-source pairs (38.9%, 95% CI 20.3% to 61.4%, n=18, over 1 split)
    citation support rate, counted in claims: 6 of 7 claims (85.7%, 95% CI 48.7% to 97.4%, n=7, over 1 split)
    verdicts: {'SUPPORTED': 7, 'NOT_FOUND_IN_SOURCE': 11, 'VOID:SPAN_ADDED_AFTER_GENERATION': 1}
  CO-22  chatgpt  split c1c5df3cf2eb
    judge-fabricated-span rate: 0 of 13 span-bearing verdicts (0.0%, 95% CI 0.0% to 22.8%, n=13, over 1 split)
    source drift rate: 0 of 4 sources (0.0%, 95% CI 0.0% to 49.0%, n=4)
    unauditable rate: 0 of 26 claim-source pairs (0.0%, 95% CI 0.0% to 12.9%, n=26, over 1 split)
    citation support rate: 11 of 26 claim-source pairs (42.3%, 95% CI 25.5% to 61.1%, n=26, over 1 split)
    citation support rate, counted in claims: 9 of 10 claims (90.0%, 95% CI 59.6% to 98.2%, n=10, over 1 split)
    verdicts: {'SUPPORTED': 11, 'NOT_FOUND_IN_SOURCE': 13, 'PARTIALLY_SUPPORTED': 2}
  CO-24  chatgpt  split b9f97d2274b1
    judge-fabricated-span rate: 1 of 9 span-bearing verdicts (11.1%, 95% CI 2.0% to 43.5%, n=9, over 1 split)
    source drift rate: 0 of 2 sources (0.0%, 95% CI 0.0% to 65.8%, n=2)
    unauditable rate: 1 of 9 claim-source pairs (11.1%, 95% CI 2.0% to 43.5%, n=9, over 1 split)
    citation support rate: 8 of 8 claim-source pairs (100.0%, 95% CI 67.6% to 100.0%, n=8, over 1 split)
    citation support rate, counted in claims: 8 of 8 claims (100.0%, 95% CI 67.6% to 100.0%, n=8, over 1 split)
    verdicts: {'SUPPORTED': 8, 'VOID:JUDGE_FABRICATED_SPAN': 1}

JUDGE AGAINST HUMAN
  gold set     35 blind labels compared against the judge
  kappa        0.304  95% CI 0.004 to 0.604, n=35. A wide-interval estimate, not a calibration
    SUPPORTED              precision 57.1% (n=7)   recall 44.4% (n=9)
    PARTIALLY_SUPPORTED    precision 16.7% (n=6)   recall 25.0% (n=4)
    NOT_FOUND_IN_SOURCE    precision 77.3% (n=22)   recall 77.3% (n=22)
    9 pair(s) the human marked UNAUDITABLE, excluded: the judge was never asked about them
    1 labelled pair(s) had no standing verdict in this run, excluded
  attribution   not run. 0 of 13 judge-human disagreement(s) could be checked against our extraction, so this says nothing about extract.py either way
                8 carried a pasted passage and none of them could be checked, which means the page was not in the fetch cache when it was labelled. Run tools/prep_goldset.py without --no-fetch before a session
  [attribution recomputed 2026-08-16 by the day 10 fix to goldset.attribution, over the gold set and
   judgements in run.json. Nothing else in this file was recomputed. FINDINGS.md item 24]

metering     {'calls': 139, 'total_tokens': 817995, 'estimated_cost_usd': 0.0, 'budget_tokens': 2000000, 'halted': False, 'halt_reason': ''}

Every rate above is single-stratum. It is not a rate for AI citations generally.
```

### Per-number trace

| Published figure | Value | n | Unit | Comes from | Over which records |
|---|---|---|---|---|---|
| judge-fabricated-span rate (CO-02) | 0.0% (0.0% to 65.8%) | 2 | span-bearing verdict | `rates.fabricated_span_rate` | capture-chatgpt-2026-08-15T2252000000.json, 2 source(s), split `d1a3f0154b6b` |
| source drift rate (CO-02) | 0.0% (0.0% to 79.3%) | 1 | source | `rates.drift_rate` | capture-chatgpt-2026-08-15T2252000000.json, 2 source(s), split `d1a3f0154b6b` |
| unauditable rate (CO-02) | 50.0% (18.8% to 81.2%) | 6 | claim-source pair | `rates.unauditable_rate` | capture-chatgpt-2026-08-15T2252000000.json, 2 source(s), split `d1a3f0154b6b` |
| judge-fabricated-span rate (CO-03) | 0.0% (0.0% to 49.0%) | 4 | span-bearing verdict | `rates.fabricated_span_rate` | capture-chatgpt-2026-08-15T2252100000.json, 2 source(s), split `ff068afec018` |
| source drift rate (CO-03) | 0.0% (0.0% to 65.8%) | 2 | source | `rates.drift_rate` | capture-chatgpt-2026-08-15T2252100000.json, 2 source(s), split `ff068afec018` |
| unauditable rate (CO-03) | 0.0% (0.0% to 49.0%) | 4 | claim-source pair | `rates.unauditable_rate` | capture-chatgpt-2026-08-15T2252100000.json, 2 source(s), split `ff068afec018` |
| citation support rate (CO-03) | 50.0% (15.0% to 85.0%) | 4 | claim-source pair | `rates.support_rate` | capture-chatgpt-2026-08-15T2252100000.json, 2 source(s), split `ff068afec018` |
| citation support rate, counted in claims (CO-03) | 50.0% (9.5% to 90.5%) | 2 | claim | `rates.claim_level_rate` | capture-chatgpt-2026-08-15T2252100000.json, 2 source(s), split `ff068afec018` |
| judge-fabricated-span rate (CO-08) | 0.0% (0.0% to 17.6%) | 18 | span-bearing verdict | `rates.fabricated_span_rate` | capture-chatgpt-2026-08-15T2252150000.json, 5 source(s), split `a72d510667cc` |
| source drift rate (CO-08) | 20.0% (3.6% to 62.4%) | 5 | source | `rates.drift_rate` | capture-chatgpt-2026-08-15T2252150000.json, 5 source(s), split `a72d510667cc` |
| unauditable rate (CO-08) | 0.0% (0.0% to 9.9%) | 35 | claim-source pair | `rates.unauditable_rate` | capture-chatgpt-2026-08-15T2252150000.json, 5 source(s), split `a72d510667cc` |
| citation support rate (CO-08) | 45.7% (30.5% to 61.8%) | 35 | claim-source pair | `rates.support_rate` | capture-chatgpt-2026-08-15T2252150000.json, 5 source(s), split `a72d510667cc` |
| citation support rate, counted in claims (CO-08) | 85.7% (48.7% to 97.4%) | 7 | claim | `rates.claim_level_rate` | capture-chatgpt-2026-08-15T2252150000.json, 5 source(s), split `a72d510667cc` |
| judge-fabricated-span rate (CO-10) | 0.0% (0.0% to 27.8%) | 10 | span-bearing verdict | `rates.fabricated_span_rate` | capture-chatgpt-2026-08-15T2252190000.json, 3 source(s), split `d69cca9c4538` |
| source drift rate (CO-10) | 0.0% (0.0% to 56.1%) | 3 | source | `rates.drift_rate` | capture-chatgpt-2026-08-15T2252190000.json, 3 source(s), split `d69cca9c4538` |
| unauditable rate (CO-10) | 0.0% (0.0% to 24.2%) | 12 | claim-source pair | `rates.unauditable_rate` | capture-chatgpt-2026-08-15T2252190000.json, 3 source(s), split `d69cca9c4538` |
| citation support rate (CO-10) | 58.3% (32.0% to 80.7%) | 12 | claim-source pair | `rates.support_rate` | capture-chatgpt-2026-08-15T2252190000.json, 3 source(s), split `d69cca9c4538` |
| citation support rate, counted in claims (CO-10) | 100.0% (51.0% to 100.0%) | 4 | claim | `rates.claim_level_rate` | capture-chatgpt-2026-08-15T2252190000.json, 3 source(s), split `d69cca9c4538` |
| judge-fabricated-span rate (CO-14) | 0.0% (0.0% to 79.3%) | 1 | span-bearing verdict | `rates.fabricated_span_rate` | capture-chatgpt-2026-08-15T2252240000.json, 2 source(s), split `c440c7ff1a7d` |
| source drift rate (CO-14) | withheld | 0 | source | `rates.drift_rate` | capture-chatgpt-2026-08-15T2252240000.json, 2 source(s), split `c440c7ff1a7d` |
| unauditable rate (CO-14) | 50.0% (18.8% to 81.2%) | 6 | claim-source pair | `rates.unauditable_rate` | capture-chatgpt-2026-08-15T2252240000.json, 2 source(s), split `c440c7ff1a7d` |
| citation support rate (CO-14) | 33.3% (6.1% to 79.2%) | 3 | claim-source pair | `rates.support_rate` | capture-chatgpt-2026-08-15T2252240000.json, 2 source(s), split `c440c7ff1a7d` |
| citation support rate, counted in claims (CO-14) | 33.3% (6.1% to 79.2%) | 3 | claim | `rates.claim_level_rate` | capture-chatgpt-2026-08-15T2252240000.json, 2 source(s), split `c440c7ff1a7d` |
| judge-fabricated-span rate (CO-17) | 0.0% (0.0% to 79.3%) | 1 | span-bearing verdict | `rates.fabricated_span_rate` | capture-chatgpt-2026-08-15T2252280000.json, 3 source(s), split `effca12f40b7` |
| source drift rate (CO-17) | 0.0% (0.0% to 56.1%) | 3 | source | `rates.drift_rate` | capture-chatgpt-2026-08-15T2252280000.json, 3 source(s), split `effca12f40b7` |
| unauditable rate (CO-17) | 0.0% (0.0% to 39.0%) | 6 | claim-source pair | `rates.unauditable_rate` | capture-chatgpt-2026-08-15T2252280000.json, 3 source(s), split `effca12f40b7` |
| citation support rate (CO-17) | 0.0% (0.0% to 39.0%) | 6 | claim-source pair | `rates.support_rate` | capture-chatgpt-2026-08-15T2252280000.json, 3 source(s), split `effca12f40b7` |
| citation support rate, counted in claims (CO-17) | 0.0% (0.0% to 49.0%) | 4 | claim | `rates.claim_level_rate` | capture-chatgpt-2026-08-15T2252280000.json, 3 source(s), split `effca12f40b7` |
| judge-fabricated-span rate (CO-20) | 0.0% (0.0% to 27.8%) | 10 | span-bearing verdict | `rates.fabricated_span_rate` | capture-chatgpt-2026-08-15T2252330000.json, 5 source(s), split `cd9592deafbb` |
| source drift rate (CO-20) | 0.0% (0.0% to 65.8%) | 2 | source | `rates.drift_rate` | capture-chatgpt-2026-08-15T2252330000.json, 5 source(s), split `cd9592deafbb` |
| unauditable rate (CO-20) | 0.0% (0.0% to 14.9%) | 22 | claim-source pair | `rates.unauditable_rate` | capture-chatgpt-2026-08-15T2252330000.json, 5 source(s), split `cd9592deafbb` |
| citation support rate (CO-20) | 27.3% (13.2% to 48.2%) | 22 | claim-source pair | `rates.support_rate` | capture-chatgpt-2026-08-15T2252330000.json, 5 source(s), split `cd9592deafbb` |
| citation support rate, counted in claims (CO-20) | 66.7% (35.4% to 87.9%) | 9 | claim | `rates.claim_level_rate` | capture-chatgpt-2026-08-15T2252330000.json, 5 source(s), split `cd9592deafbb` |
| judge-fabricated-span rate (CO-21) | 0.0% (0.0% to 32.4%) | 8 | span-bearing verdict | `rates.fabricated_span_rate` | capture-chatgpt-2026-08-15T2252370000.json, 4 source(s), split `fc789252f042` |
| source drift rate (CO-21) | 25.0% (4.6% to 69.9%) | 4 | source | `rates.drift_rate` | capture-chatgpt-2026-08-15T2252370000.json, 4 source(s), split `fc789252f042` |
| unauditable rate (CO-21) | 5.3% (0.9% to 24.6%) | 19 | claim-source pair | `rates.unauditable_rate` | capture-chatgpt-2026-08-15T2252370000.json, 4 source(s), split `fc789252f042` |
| citation support rate (CO-21) | 38.9% (20.3% to 61.4%) | 18 | claim-source pair | `rates.support_rate` | capture-chatgpt-2026-08-15T2252370000.json, 4 source(s), split `fc789252f042` |
| citation support rate, counted in claims (CO-21) | 85.7% (48.7% to 97.4%) | 7 | claim | `rates.claim_level_rate` | capture-chatgpt-2026-08-15T2252370000.json, 4 source(s), split `fc789252f042` |
| judge-fabricated-span rate (CO-22) | 0.0% (0.0% to 22.8%) | 13 | span-bearing verdict | `rates.fabricated_span_rate` | capture-chatgpt-2026-08-15T2252460000.json, 5 source(s), split `c1c5df3cf2eb` |
| source drift rate (CO-22) | 0.0% (0.0% to 49.0%) | 4 | source | `rates.drift_rate` | capture-chatgpt-2026-08-15T2252460000.json, 5 source(s), split `c1c5df3cf2eb` |
| unauditable rate (CO-22) | 0.0% (0.0% to 12.9%) | 26 | claim-source pair | `rates.unauditable_rate` | capture-chatgpt-2026-08-15T2252460000.json, 5 source(s), split `c1c5df3cf2eb` |
| citation support rate (CO-22) | 42.3% (25.5% to 61.1%) | 26 | claim-source pair | `rates.support_rate` | capture-chatgpt-2026-08-15T2252460000.json, 5 source(s), split `c1c5df3cf2eb` |
| citation support rate, counted in claims (CO-22) | 90.0% (59.6% to 98.2%) | 10 | claim | `rates.claim_level_rate` | capture-chatgpt-2026-08-15T2252460000.json, 5 source(s), split `c1c5df3cf2eb` |
| judge-fabricated-span rate (CO-24) | 11.1% (2.0% to 43.5%) | 9 | span-bearing verdict | `rates.fabricated_span_rate` | capture-chatgpt-2026-08-15T2252500000.json, 2 source(s), split `b9f97d2274b1` |
| source drift rate (CO-24) | 0.0% (0.0% to 65.8%) | 2 | source | `rates.drift_rate` | capture-chatgpt-2026-08-15T2252500000.json, 2 source(s), split `b9f97d2274b1` |
| unauditable rate (CO-24) | 11.1% (2.0% to 43.5%) | 9 | claim-source pair | `rates.unauditable_rate` | capture-chatgpt-2026-08-15T2252500000.json, 2 source(s), split `b9f97d2274b1` |
| citation support rate (CO-24) | 100.0% (67.6% to 100.0%) | 8 | claim-source pair | `rates.support_rate` | capture-chatgpt-2026-08-15T2252500000.json, 2 source(s), split `b9f97d2274b1` |
| citation support rate, counted in claims (CO-24) | 100.0% (67.6% to 100.0%) | 8 | claim | `rates.claim_level_rate` | capture-chatgpt-2026-08-15T2252500000.json, 2 source(s), split `b9f97d2274b1` |
| Judge-human agreement (kappa) | 0.304 (0.004 to 0.604) | 35 | blind label | `goldset.cohens_kappa` | goldset/chatgpt-consumer.gold.json |
