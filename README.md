# SaysWho

AI search tools cite their sources. Nothing in the pipeline checks whether those sources say what the answer
claims they say.

SaysWho is a browser extension that does the checking. When Claude, ChatGPT or Perplexity answers with
citations, it splits the answer into individual factual claims, fetches every cited page, and marks each
claim where it sits as one of three things:

- `SUPPORTED`, shown with the exact sentence from the source that backs it
- `NOT_FOUND_IN_SOURCE`, meaning the citation is there but the support isn't
- `UNAUDITABLE`, meaning a dead link, a paywall, or a page that changed since the answer was written

## Status

Day 5 of ten. The pipeline runs end to end on a real answer: it captures, fetches, splits into claims, judges
each one against its source, and refuses to print an aggregate rate because no gold set exists yet.

`STATUS.md` is the honest version of this section, item by item, and `TODO.md` is the working list. The one
row that matters: the professional query stratum is still empty, and it is the input to everything that
produces a number, so several parts below are built and have never run on real data. They are marked as such
rather than counted as working.

**In the browser.** A Manifest V3 extension captures an answer from claude.ai, chatgpt.com, perplexity.ai or
Google AI Overviews. It scrolls the answer into existence first, since a long answer is not fully in the DOM
until it has been on screen. It extracts the answer text and citation URLs, hashes the text, and downloads
both a capture record and the page it came from. When it cannot reach everything, it says so instead of
handing back a plausible number.

**In the terminal.** `python3 -m sayswho.cli <capture.json>` re-verifies the hash, refuses answers with no
citations, fetches every cited URL under `DATA_CONTRACT.md`, and assigns one of six outcomes. Add `--judge`
and it splits the answer into claims, judges each against its cited source, and checks every span.

The judge runs on Gemini's free tier by default, so a run costs nothing. `--judge-provider anthropic`
switches. Both satisfy the same protocol, so the pipeline and the gates never know which is running.

**The span guard.** To return `SUPPORTED` the judge must quote the source verbatim, and a script confirms by
substring match that the span is in the document that was actually retrieved. A span that is not there voids
the verdict and logs `JUDGE_FABRICATED_SPAN`, and that rate is published as a finding about the judge. On the
first live run it voided nothing across seven span-bearing verdicts, and on the re-run after the drift fix it
voided one of nine. That is 1 of 16 across both runs. It is not a rate and it is reported as not being one.

`python3 -m sayswho.reextract <page.html> --capture <capture.json>` re-runs extraction over the stored bytes
and compares it to what the extension produced. Two implementations, one in JavaScript against a live DOM and
one in Python against saved markup, and they have to agree.

**The refusals.** Five gates, and each one has a test that makes it fire on the bug it exists to catch. G4
withholds every rate that depends on a calibrated judge until a gold set exists for this judge, this prompt
version and this split. `INSUFFICIENT_EVIDENCE` withholds a rate when more than half an answer's claims
produced no verdict that stands. An unbound capture is audited and excluded from every aggregate. And Google
AI Overviews results never enter a cross-product aggregate, because the default judge is a Google model, a
refusal enforced in `rates.aggregate` rather than in a paragraph.

**The popup.** Clicking the toolbar icon shows whether the audit server is running, in three states rather
than two, since a server running without a judge is up and cannot produce a verdict. It also shows whether
the current page's adapter has ever been checked against a real page, and what the last capture found,
including whether that capture held the whole answer. Both actions can be driven from there, and the in-page
buttons can be turned off for people who would rather not have an overlay on someone else's product.

**Without the terminal.** `python3 -m sayswho.server --judge` opens a loopback-only audit server, and the
extension's second button posts the capture to it and draws the result in a panel over the page. The gates
and the span guard stay in Python: the panel's script posts JSON and renders what comes back, and a test
asserts it never mentions a verdict name. It does not mark the product's own sentences in place, and the
reason is in `extension/README.md`.

**The headless run.** `python3 tools/run_stratum.py --captures captures/ --judge --out runs/today` audits
every capture bound to a frozen query and writes four files: the run record, the metric readout with an n and
an interval on every rate, `RUN_LOG.md`, and a per-number trace table generated from the run rather than
typed alongside it.

453 tests, all offline except a node process for the parity check. Two of them pin failures rather than
fixes: an injection that dictates its own span defeats the guard, and a judge can quote a real but irrelevant
sentence. Deleting either test would delete the finding. `BREAK_ATTEMPTS.md` writes both up.

**Not built yet:** marking the product's own sentences in place, the gold set labels, and the head-to-head. The
professional query stratum is empty by design until real queries are scrubbed into it, and that is what
everything producing a number is waiting on.

No number this project produces is a measurement yet. `FINDINGS.md` records what has been observed so far,
and every entry there is n=1.

Start here if you want to use it: [`recipes/audit-citations.md`](recipes/audit-citations.md), and the
one-page card of [six ways it goes wrong](recipes/audit-citations.card.md).

## Why bother

The gap is documented and other people found it first. Liu, Zhang and Liang (Stanford, EMNLP 2023) audited
four generative search engines and found 51.5% of generated sentences fully supported by their citations, and
74.5% of citations supporting the sentence they were attached to. The Tow Center ran a similar exercise
across eight chatbots in March 2025 and reported error rates above 60%. SourceCheckup, in Nature
Communications in April 2025, found the same pattern in medical answers.

What is still missing is a way for a reader to find out which sentence to distrust while they are reading it.

So the job is narrow. If an answer has six footnotes, tell me which two I need to open, so I spend fifteen
minutes there instead of spreading it across all six. I am the user here. Most of my research as a PM starts
with an AI tool, and checking the citations by hand is tedious enough that I skip it more often than I should.

## The part I actually care about

Ask a language model whether a source supports a claim and it will happily tell you. That answer has nothing
behind it.

So the judge is constrained. To return `SUPPORTED` it has to quote the exact span from the fetched page that
justifies the verdict, and a script then checks by string match that the span is really in the document that
was retrieved. If it isn't, the verdict is voided and logged as `JUDGE_FABRICATED_SPAN`. How often that
happens gets published as a finding about the judge rather than quietly fixed. It is a deterministic check on
a probabilistic component, and the model cannot talk its way past `str.find()`.

The second constraint is that SaysWho emits no confidence score anywhere, and a test enforces that. A
confidence number attached to a page that could not be fetched is invented. The dead link becomes "low
confidence" and the reader loses the ability to tell "we checked and it isn't supported" apart from "we
couldn't check". Unauditable claims stay out of the denominator of every rate published here, because
treating a network timeout as weak evidence against a citation would manufacture a scandal out of nothing.

## Prior art

There are already tools in this space. CiteGuardian breaks text into claims and reviews the cited sources, in
the browser, on AI answers. GPTZero ships an AI source checker. CiteTrue and FactSentinel are adjacent. The
general idea is not novel and this repo will not pretend otherwise.

The narrower claim is about what those tools do when the evidence cannot be reached, and it gets measured
rather than asserted. If they refuse cleanly on dead links then the differentiator collapses, and the writeup
will say so as prominently as it would have reported the flattering version. That failure condition is
written down now, before there is any data to be tempted by.

## What it cannot do

It checks whether a source says what the answer claims it says. It cannot check whether the source is true,
so a well cited falsehood passes clean. That is the biggest limit and it is not fixable inside this design.

It is also blind to omission. An answer can score perfectly by citing only its safe sentences and leaving the
risky ones bare. And it cannot tell a peer reviewed paper from a blog post. Both are a page with text on it
as far as the fetcher is concerned.

Sample sizes will be small. Every rate ships with its n, and the writeup says which differences the sample
cannot resolve rather than ranking things it has no power to rank.

## Context

A graduate capstone at Northeastern University, for a course on computational skepticism, which is the
practice of checking whether a system does the thing it says it does. Applying that to my own tool is the
whole assignment, which is why the failure conditions above are in the README rather than in a footnote at
the end.
