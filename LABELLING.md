# Labelling guide

Open this beside the session. It is about the vocabulary, not about the answers: nothing here says anything
about a particular claim or page, because a guide that did would be anchoring the labels it is meant to
steady.

Every definition below comes from `sayswho/goldset.py`, which is what the arithmetic actually uses.

## The one question

**Does this page say what this sentence says?**

Not whether the sentence is true. Not whether the page is any good. A well-cited falsehood gets `SUPPORTED`,
and `SCOPE.md` §7 says so as the largest limitation in the design. A true sentence cited to a page that does
not state it gets `NOT_FOUND_IN_SOURCE`, and that is a statement about the citation rather than about the
world.

## The six labels

| Key | Label | It means |
|---|---|---|
| `S` | `SUPPORTED` | The page states this claim. You can quote the passage |
| `P` | `PARTIALLY_SUPPORTED` | The page supports part of it, or a weaker version of it |
| `N` | `NOT_FOUND_IN_SOURCE` | You read the page and it does not state this |
| `C` | `CONTRADICTED` | The page states something incompatible with this |
| `U` | `UNAUDITABLE` | You could not read the source at all |
| `?` | `UNDECIDABLE` | You read it and genuinely cannot decide |

## The four boundaries that matter, and what each one protects

**`N` against `C`. Silence is not contradiction.** A page that simply does not mention the claim is `N`. `C`
is for a page that states something incompatible: a different number, the opposite direction, an exclusion
that the claim asserts. This boundary is the one to be most careful about, because the judge is known to get
it wrong in a specific direction: break attempt 1 found it reading a page's disclaimer as a contradiction,
4 of 4 (`FINDINGS.md` item 15). If you drift the same way, the kappa measures the two of you making the same
mistake and reports it as agreement.

**`S` against `P`. Never round up.** If the page attaches something the claim drops, it is `P`. The usual
shapes: the page says "associated with" and the claim says "reduces"; the page scopes a figure to one group
or one year and the claim states it flat; the page says "may" and the claim says "does". If you find yourself
thinking "close enough", that is exactly the case `P` exists for.

**`U` against `N`.** If you could not read the page, `U`, whatever you suspect the page would have said.
Marking `N` because a page was slow, blocked or gone converts this pipeline's fetch failure into a finding
about somebody's citation, which is the specific dishonesty this whole project is built against. `U` is a
label about the source, not about the claim: the judge was never asked about those pairs, so they carry no
agreement information and are excluded from kappa and reported on their own.

**`?` is a real answer.** A forced label on an ambiguous pair is noise entered as signal. `?` is recorded,
excluded from kappa, and its count is published. Use it when the honest answer is that the page is unclear or
the claim is too vague to check, not when you are tired.

## The passage

For `S`, `P` and `C` the tool asks for the passage you found. **Paste it from the page**, not from memory and
not from the claim.

It is not paperwork. `goldset.attribution` checks your passage against what `extract.py` produced from the
same page: if your passage is on the page and missing from our extraction, that disagreement is the
extractor's fault rather than the judge's, and it gets reported that way. Without a pasted passage the pair
cannot be attributed at all and any disagreement lands on the judge whether it belongs there or not. In this
sample, 20 of the 45 pairs can be attributed this way.

Blank is allowed and costs that check.

## Consistency, which is the thing kappa is actually measuring

Your `P` at pair 5 has to mean what your `P` at pair 40 means. If you find your sense of a boundary moving,
write it in the notes field and carry on with the new reading; do not go back and revise earlier labels. The
file is written after every single label, and the tool skips pairs already labelled when you resume, which is
deliberate: revising the early ones once you know what the late ones look like is its own selection effect.

Stopping is free. `q` saves and quits, the count is reported, and resuming continues where you left off.

## While you are labelling

- **Do not start the server and do not press the audit button.** Nothing on disk currently holds a verdict for
  any of these 24 answers, and `sayswho/prior_audit.py` confirmed that before the session. One audit of one of
  these answers ends the blindness for it.
- Do not open a previous report, and do not run `sayswho.cli --judge` in another window.
- The tool has opened no file containing a verdict, and neither has the prep pass.

## Afterwards

The set is at `goldset/consumer.gold.json`. Judging the same claims is the run a rate may come from:

```bash
python3 tools/run_stratum.py --captures captures/ --split splits/CO-01.split.json --judge --goldset goldset/consumer.gold.json --out runs/day7
```

Gate G4 ties the set to the judge, the judge prompt version, the claim prompt version and the split hashes, so
the run has to judge the same claims you read. `goldset.agreement` refuses if any blind label postdates the
run it is compared against, which is why the labelling happens first and not the other way round.
