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

**And `U` means *you* could not read it, not that this pipeline could not.** Try the link before reaching for
it. The two unauditable codes you are most likely to meet are not the same situation:

- `SOURCE_DEAD_LINK` is a 404. You will see what we saw, and `U` is the honest label.
- `SOURCE_BOT_BLOCKED` is a 403 aimed at an automated client. A person clicking that link will very often see
  the page normally.

When a blocked page loads for you, **label the claim as you find it and say in the notes that the page opened
in a browser.** Those labels are excluded from kappa either way, since there is no verdict to compare them
against, so nothing is lost by labelling them properly and something real is gained: the split between "this
citation is broken" and "this citation is unreadable to anything automated" is the difference between a
finding about a product and a limitation of this tool. `SOURCE_BOT_BLOCKED` exists as a separate code for
exactly that reason (`FINDINGS.md` item 3), and nothing has ever measured how far apart the two are.

Day 9 did not get the chance to. Its pool was 31 `SOURCE_OK` and 2 `SOURCE_DEAD_LINK` and contained no
blocked source at all, so all nine of its `U` labels came from four dead links and the distinction above went
untested. The day 6 Perplexity pool ran the other way, 7 blocked against 1 dead and 1 unreachable, which is
where the paragraph came from. Which codes a session meets is a fact about the product it captured, so check
what is in front of you rather than expecting either shape.

**`?` is a real answer.** A forced label on an ambiguous pair is noise entered as signal. `?` is recorded,
excluded from kappa, and its count is published. Use it when the honest answer is that the page is unclear or
the claim is too vague to check, not when you are tired.

## The passage

For `S`, `P` and `C` the tool asks for the passage you found. **Paste it from the page**, not from memory and
not from the claim.

It is not paperwork. `goldset.attribution` checks your passage against what `extract.py` produced from the
same page: if your passage is on the page and missing from our extraction, that disagreement is the
extractor's fault rather than the judge's, and it gets reported that way. Without a pasted passage the pair
cannot be attributed at all and any disagreement lands on the judge whether it belongs there or not.

Blank is allowed and costs that check, and the day 9 session is the evidence for how much it costs. 14 of its
45 labels carried a passage. Only 8 of its 13 judge-human disagreements did, and the comparison ran on none
of them: `extraction_missed` came back non-null once in 45, on a pair where judge and human agreed. So that
session measured nothing at all about whether `extract.py` explains any of its disagreements, and the run
record's 0 attributed to the extractor is 0 checked rather than 0 found.

**And the passage alone is not what makes the check run.** The page has to be in the fetch cache when you
label, or `extraction_missed` stays `None` and your passage buys nothing. That is what happened to 13 of the
14. Run `tools/prep_goldset.py` **without** `--no-fetch` before a session, which warms the cache for exactly
this reason, and paste the passage anyway.

## Consistency, which is the thing kappa is actually measuring

Your `P` at pair 5 has to mean what your `P` at pair 40 means. If you find your sense of a boundary moving,
write it in the notes field and carry on with the new reading; do not go back and revise earlier labels. The
file is written after every single label, and the tool skips pairs already labelled when you resume, which is
deliberate: revising the early ones once you know what the late ones look like is its own selection effect.

Stopping is free. `q` saves and quits, the count is reported, and resuming continues where you left off.

## While you are labelling

- **Do not start the server and do not press the audit button.** One audit of one of the answers you are
  labelling ends the blindness for it, and there is no way to restore it afterwards.
- Do not open a previous report, and do not run `sayswho.cli --judge` in another window.
- The tool opens no file containing a verdict, and neither does the prep pass.

**Blindness is a fact about the answers in front of you, not a property of this guide.** Run
`sayswho/prior_audit.py` before every session and read what it says, because the answer changes. It came back
clean before the day 9 ChatGPT session, which is why those 45 labels are blind in fact. It refuses over the 24
Perplexity consumer answers and has since the day 7 honest run put a verdict on all of them, so a blind
session over those is no longer available at any price: `--supplemental` is the only way in and supplemental
labels are excluded from kappa by construction, which is the whole reason day 9 captured a second product
instead of topping the old set up.

## Afterwards

The tool writes the set wherever `--out` pointed. Judging the same claims is the run a rate may come from,
and day 9's was:

```bash
python3 tools/run_stratum.py --captures captures/ --judge --goldset goldset/chatgpt-consumer.gold.json --out runs/day9
```

Gate G4 ties the set to the judge, the judge prompt version, the claim prompt version and the split hashes, so
the run has to judge the same claims you read. `goldset.agreement` refuses if any blind label postdates the
run it is compared against, which is why the labelling happens first and not the other way round.
