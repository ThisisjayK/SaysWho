# SaysWho: building a tool that refuses to give you a number

A case study for a technical reader. What the problem was, which decisions were load bearing, what they cost,
and what is still unmeasured. Written on day 7 of a ten-day build, so the last section is
still longer than the results section, which remains the accurate shape.

Repo: https://github.com/ThisisjayK/SaysWho

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

So unauditable claims are excluded from every denominator, by a contract check that raises rather than warns,
and when more than half an answer is unauditable the tool prints `INSUFFICIENT_EVIDENCE` and no number at
all.

**What it cost.** The thing every reviewer asks for first. There is no headline percentage to put on a slide,
and "73% of citations check out" is a far better demo than a refusal.

### 3. The interface computes nothing

Every state a reader sees is decided in Python, and the extension's renderer draws what it is handed.

This exists because the alternative is two implementations of the same verdict logic, one in JavaScript for
speed of iteration and one in Python for the audit, drifting apart under maintenance until the interface is
telling users something the audited pipeline never said. The check is a test that runs the real renderer in
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
every span. 781 tests, each gate with a test that makes it fire on the bug it exists to catch.

What has actually been observed, all at n=1 and reported as such: a Claude research report that named fifteen
sources and linked one. A drift check that flagged churning reference lists as drift until it was asked the
right question, which is not "did this page change" but "was the sentence this verdict rests on there when
the answer was written". A gzip bug that made every archived comparison report drift, producing a clean,
consistent, entirely artefactual result. And an extraction guard that fired twice and was wrong both times,
because the permissive parser it depended on had been written, tested, and never wired in.

**No measured rate exists yet, and the run that could have produced one refused to print it.** Twenty-four
answers, 51 sources, 130 verdicts, and no support rate: gate G4 withholds every rate that depends on a
calibrated judge, the gold set covers four of the twenty-four splits, and two more answers were withheld on
`INSUFFICIENT_EVIDENCE` before G4 got to them. The refusal is the system behaving correctly. It is also the
reason there is no results section here, and watching it happen on real data is the closest thing to a result
this project has.

`STATUS.md` lists every core and stretch item as done or not-done with a reason, including the ones that
would be more flattering to leave out.

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
