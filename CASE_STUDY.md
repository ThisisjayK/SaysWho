# SaysWho: building a tool that refuses to give you a number

A case study for a technical reader. What the problem was, which decisions were load bearing, what they cost,
and what is still unmeasured. Written on day 7 and updated on day 10, when the one measured result arrived.
It is one calibration at n=35, and the section reporting it spends more words on its limits than on the
figure itself. On a ten-day build that is the accurate shape.

Repo: https://github.com/ThisisjayK/SaysWho
Demo: [thisisjayk.github.io/SaysWho](https://thisisjayk.github.io/SaysWho/), including a five minute film
that runs the whole thing on one real answer, both refusals included.

---

## The problem

AI search tools cite sources. The citation is doing rhetorical work: it signals verification while performing
none. The reader sees a footnote and stops asking.

I am the user. Most of my research as a PM starts with an AI tool, and before anything from an answer goes
into a document other people act on, I have to open the sources and check they say what the answer says they
say. Six citations is fifteen minutes. So I skip it more often than I should.

The job is narrow, and keeping it narrow is most of the design: **tell me which two of these six footnotes I
need to open.** Not a trust score. Not a verdict on the product. A pointer at the two sentences that do not
check out.

The gap is documented and other people found it first. Liu, Zhang and Liang (EMNLP 2023) found 51.5% of
generated sentences fully supported by their citations across four generative search engines. The Tow Center
reported error rates above 60% across eight chatbots in 2025. What is missing is not the measurement. It is a
way for a reader to find out which sentence to distrust while they are reading it.

## The hard part is not the checking

The obvious build is: ask a language model whether the source supports the claim. That takes an afternoon and
produces finding-shaped output with nothing behind it. A model asked to verify another model will confidently
agree, disagree, and invent a justification for either.

So the whole project is organised around one question: **what stops this tool from being wrong in a way that
looks right?**

Four decisions came out of that, and each cost something.

### 1. The judge has to quote, and a script checks the quote

To return `SUPPORTED`, the judge must return a verbatim span from the fetched document. A normalised
substring match then confirms the span is really there. If it is not, the verdict is voided and logged as
`JUDGE_FABRICATED_SPAN`, and how often that happens is published as a finding about the judge.

A deterministic check on a probabilistic component. The model cannot talk its way past `str.find`.

**What it cost.** Coverage. A judge that cannot find a quotable passage must return `NOT_FOUND_IN_SOURCE`,
so genuinely-supported claims whose support is spread across three paragraphs come back unsupported.

**What it does not do, which took a break attempt to find out.** It rules out evidence the page does not
contain. Against an adversarial page those are different sentences: an injected instruction that dictates its
own span puts that span on the page, so presence is satisfied and the guard passes. No substring check
survives that. The published claim was narrowed to match, and the failing case is kept as a passing test.

### 2. No confidence score, anywhere

Not in the extension, not in the harness, not in the writeup. A test enforces it across every output surface.

The reasoning is specific rather than aesthetic. A confidence number attached to a page that could not be
fetched is invented. The dead link becomes "low confidence", and the reader loses the ability to tell "we
checked and it is not supported" from "we could not check". Those are the two most different outcomes in the
system and a single number collapses them.

Unauditable claims are excluded from every denominator, by a contract check that raises rather than warns.
When more than half an answer is unauditable, the tool prints `INSUFFICIENT_EVIDENCE` and no number at all.

**What it cost.** The thing every reviewer asks for first. There is no headline percentage to put on a slide,
and "73% of citations check out" is a far better demo than a refusal.

### 3. The interface computes nothing

Every state a reader sees is decided in Python, and the extension's renderer draws what it is handed.

The alternative would be two implementations of the same verdict logic, one in JavaScript for speed of
iteration and one in Python for the audit, drifting apart under maintenance until the interface is telling
users something the audited pipeline never said. The check is a test that runs the real renderer in
node over a payload the real Python built and compares what appeared on screen, state by state, against what
Python decided.

**What it cost.** The extension cannot mark claims on the product page itself yet. Doing that needs a local
server the extension can talk to, because the gates and the span guard are Python. The scope document
promised one click and was corrected to say capture and render, which is a worse demo and a true sentence.

### 4. The query set is frozen with hashes

Queries are written before any capture, hashed, and committed. A check runs before every capture run and
fails on any addition, removal or edit. Breaking a freeze takes an explicit flag and a written reason, and
the reason is recorded permanently.

The failure this prevents is not somebody else tampering. It is me, on day 9, with a result I do not like and
a query I have started to feel was unfair.

**What it cost, and it cost the thing the project was about.** The professional stratum was to be transcribed
from my own AI history and scrubbed, and it was the single blocker on the schedule for six days. On day 6 the
sessions turned out to be gone. The tempting version, writing twenty plausible PM questions in an hour, would
have made a published sentence false; the subtler version, retyping them from memory, would have broken two
selection rules I had written on day 1 and would have looked identical from the outside. So the core runs on
the frozen consumer stratum, which is synthetic and says so, and the claim that the query set is real is gone
from the core rather than weakened in it. `FINDINGS.md` item 18.

The freeze is what made that decision cheap to make and impossible to disguise. The consumer set was written
and hashed on day 1, before anything was known about what the professional set would produce, so promoting it
on day 6 could not have been a choice about results.

## Two decisions that turned out to matter more than expected

**The unit of the rate.** The scope document said `SUPPORTED / auditable claims` from day one. It never said
whether a claim citing three sources is one item or three. A real claim in the first live run came back
supported by one source and not-found by two: 1 of 3 counted in claim-source pairs, 1 of 1 counted in claims.
Same evidence, opposite readings. An ambiguous denominator sits in a specification looking like a definition
until someone computes it, and by then there is a number attached that nobody wants to change.

**The stratification that was impossible.** The plan asked for the gold set to be stratified across verdict
classes and labelled before seeing judge output. Those requirements are in direct conflict: the verdict
classes are the judge's output. The half that is knowable in advance is implemented; the other half is a
supplement, labelled afterwards, excluded from the agreement number and reported separately. The failure this
avoids is concrete: fill the rare class from the judge's own output, and report an agreement figure measured
on a sample the judge chose.

## Where it stands

Runs end to end on a real captured answer: capture, hash, fetch every cited URL under a written data
contract, check drift against the Wayback archive, split into claims, judge each against its source, verify
every span. 840 tests, each gate with a test that makes it fire on the bug it exists to catch.

What has actually been observed, all at n=1 and reported as such: a Claude research report that named fifteen
sources and linked one. A drift check that flagged churning reference lists as drift until it was asked the
right question, which is not "did this page change" but "was the sentence this verdict rests on there when
the answer was written". A gzip bug that made every archived comparison report drift, producing a clean,
consistent, entirely artefactual result. And an extraction guard that fired twice and was wrong both times,
because the permissive parser it depended on had been written, tested, and never wired in.

`STATUS.md` lists every core and stretch item as done or not-done with a reason, including the ones that
would be more flattering to leave out.

## The one measurable improvement, and why it is smaller than it sounds

**On day 7 this tool could not print a support rate at all. On day 9 it printed several, and the thing that
changed is a number that does not flatter it.**

Day 7 was twenty-four answers, 51 sources, 130 verdicts and no rate anywhere. Gate G4 withholds every rate
that depends on a calibrated judge, and there was no calibration, so there was nothing to publish. The
refusal was the system working, and it was also a dead end: a tool that always refuses is not a useful tool,
it is a tool with the wrong gate.

Day 9 supplied the missing input by hand. Forty-five claims labelled blind, before the judge saw any of them,
with a prior-audit scan proving blindness rather than asserting it. Thirty-six were comparable with a
standing verdict. Against those:

**Cohen's kappa 0.304, 95% CI 0.004 to 0.604, n=35.**

G4 opened, and per-answer and per-domain support rates printed for the first time in the project's history,
each with its own n and interval. The stratum rate stayed withheld, because one answer of the ten tripped
`INSUFFICIENT_EVIDENCE`, so the two gates are visibly doing different jobs rather than one standing in for
the other.

**Now the part that matters more than the headline.** The lower bound is 0.004. At this sample size the run
cannot rule out that the agreement between the judge and me is chance. The figure is reported as a
wide-interval estimate, never as a calibration, and it is in the film, the readout and this paragraph
carrying its interval every time, because kappa 0.30 quoted bare would be doing precisely what the tool
exists to prevent.

Per class it is uneven in a way the aggregate hides. `NOT_FOUND_IN_SOURCE`, the verdict that accuses the
audited product, has precision and recall both 77.3% (n=22): the tool is at its most reliable exactly where
being wrong is most expensive. `PARTIALLY_SUPPORTED` has precision 16.7% (n=6), which is a class the judge
and I do not agree on and which no aggregate should be allowed to smooth over.

So the honest version of the improvement is narrow: the system moved from publishing nothing to publishing
per-answer rates with a stated agreement figure whose interval nearly spans chance. That is one calibration
at n=35 on one stratum against one judge, and every sentence above says so.

## What is verified and what is inferred

Every field the tool emits is classified, and the classification is a Python object rather than a paragraph,
because a table of provenance is exactly the kind of prose that rots when a payload gains a field.
`sayswho/boundary.py` holds the seven classes, `SCOPE.md` §4 is generated from it, and
`tests/test_documents.py` fails if the document and the code disagree or if a run record emits a field no row
covers.

| Class | What it means for a reader |
|---|---|
| `record` | A primary observation, written as it arrived: what the product emitted, what a server returned, when |
| `local-evidence` | An artefact this project stored and reads back, chiefly the fetch cache and the stored page |
| `external-source` | Fetched from a third party that is not the audited product: the cited page, the Wayback snapshot |
| `script-output` | Computed by deterministic code from the three above. Reproducible, carrying no judgement |
| `model-inference` | Produced by a language model. Marked as a judgement in every surface, never printed bare beside a record-derived number |
| `your-input` | Supplied by a person. The gold set labels and the pre-registered cost of error, and the only class this tool can neither generate nor check |
| `missing` | Not produced at all, named so its absence is visible |

The line that matters: **claim splitting and every verdict are `model-inference`. Source outcomes, span
presence and every rate are `script-output`.** So "this page does not say that" is a judgement, and "this
page could not be fetched" and "this quoted span is really on the page" are not. The panel, the readout and
the film all keep that boundary visible, and `runs/day9/TRACE.md` traces every number in the run back to the
record it came from.

## What I would do differently

**Decide the denominator before building the thing that produces it.** The unit of the rate should have been
a line in the scope document with a worked example, not a discovery on day 4.

**Try to draw the sample before specifying how it is stratified.** Ten minutes writing the sampler on day 1
would have caught the blind-stratification conflict before it was written down as a requirement.

**Extraction quality is not a detail.** It is a stdlib HTML-to-text pass, and every way it fails produces
`NOT_FOUND_IN_SOURCE`, which is the one verdict that accuses the product being audited and the one verdict
carrying no span to check. Four mitigations are in and none of them are a real extractor. Keeping the layer
dependency-free was a deliberate constraint and I would take that decision again more slowly.

## What it cannot do

It checks whether a cited page says what the answer attributes to it. It cannot tell you whether the claim is
true, whether the source is any good, or what the answer left out. Those three limits are in the scope
document, in the tool's own output, and in this paragraph, because a tool that reads as more capable than it
is fails in exactly the way this project exists to catch.
