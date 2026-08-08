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

Day 2 of ten, done. The pipeline can tell you whether a cited source can be read at all. It cannot yet tell
you whether the source supports the claim, because the judge and the span guard are day 3.

So the refusing half of this tool works and the checking half does not.

**In the browser.** A Manifest V3 extension captures an answer from claude.ai, chatgpt.com, perplexity.ai or
Google AI Overviews. It scrolls the answer into existence first, since a long answer is not fully in the DOM
until it has been on screen. It extracts the answer text and citation URLs, hashes the text, and downloads
both a capture record and the page it came from. When it cannot reach everything, it says so instead of
handing back a plausible number.

**In the terminal.** `python3 -m sayswho.cli <capture.json>` re-verifies the hash, refuses answers with no
citations, fetches every cited URL under `DATA_CONTRACT.md`, and assigns one of six outcomes: `SOURCE_OK`,
`SOURCE_UNREACHABLE`, `SOURCE_EMPTY`, `SOURCE_PAYWALLED`, `SOURCE_ROBOTS_EXCLUDED`, `SOURCE_DRIFTED`. It
compares each readable page against the Wayback Machine for drift, counts sources named in prose with no
link, and enforces that unauditable claims never reach a denominator.

`python3 -m sayswho.reextract <page.html> --capture <capture.json>` re-runs extraction over the stored bytes
and compares the result to what the extension produced. Two implementations, one in JavaScript against a
live DOM and one in Python against saved markup, and they have to agree.

81 tests. Each gate has a test that makes it fire on the bug it exists to catch.

**Not built yet:** claim splitting, the judge, the span guard, the marking UI, the gold set. The
professional query stratum is empty by design until real queries are scrubbed into it.

No number this project produces is a measurement yet. `FINDINGS.md` records what has been observed so far,
and every entry there is n=1.

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
