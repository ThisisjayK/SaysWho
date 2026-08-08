# Data contract

Written on day 1, before any fetch has happened. That ordering is the point. A fetch policy written after a
run is a description of what I did, and this needs to be a constraint on what I am allowed to do.

Everything here governs the harness and the extension equally. §9 of `SCOPE.md` requires them to produce
identical verdicts on identical inputs, and they cannot do that if they fetch differently.

## 1. What may be fetched

Only URLs that appear as citations in a captured answer. No crawling, no link following, no fetching a
domain's other pages to get better context. One cited URL, one request.

## 2. Politeness

| Rule | Value |
|---|---|
| `robots.txt` | Fetched once per domain per run, cached, honoured |
| Rate limit | One request per second per domain, including the `robots.txt` request itself |
| Timeout | 20 seconds total. `urllib` does not separate connect from read, and splitting them would need a dependency, so the contract records what the code does rather than an intention it cannot keep |
| Retries | Two, on timeout and 5xx only, with 2s then 8s backoff |
| Retry on 4xx | Never. A 404 is an answer, not a failure to get one |
| Concurrency | Unlimited across domains, one at a time within a domain |

**User-Agent.** Identifying, with a working contact address, so anyone who sees this in their logs can reach a
person:

```
SaysWho/0.1 (citation audit research; +https://github.com/ThisisjayK/SaysWho; kappagantula.j@northeastern.edu)
```

The contact address is read from `SAYSWHO_CONTACT` and the value above is the documented default. An
anonymous User-Agent would make the politeness claims in this document unfalsifiable, which is why the
address is real.

## 3. What is never done

- **No authenticated fetches.** No cookies, no sessions, no logins, no API keys belonging to a publisher
- **No paywall circumvention.** Not through archive mirrors, not through referrer spoofing, not through
  reader-mode proxies, not through cached copies
- **No CAPTCHA solving, and no attempt to look like a browser to get past bot detection.** If a site does not
  want an automated client, it does not get one
- **No fetching a page that `robots.txt` disallows**

A paywall is a legitimate `UNAUDITABLE` outcome. Routing around one would replace an honest "we could not
check this" with a number obtained by pretending to be someone else, and the unauditable rate is the
measurement this whole project rests on. Corrupting it to make the sample bigger would be the exact failure
the project exists to catch.

**One consequence worth stating.** Wayback snapshots are used for drift comparison only, in §6 below. A
Wayback copy is never read as a substitute for a source that was paywalled or robots-disallowed. Using an
archive to obtain content the publisher declined to serve is circumvention with extra steps.

## 4. Fetch outcomes

Extends the G2 table in `SCOPE.md` §3 with one code that writing this document made necessary.

| Code | Condition |
|---|---|
| `SOURCE_OK` | 200, and extractable text above the threshold in §5 |
| `SOURCE_UNREACHABLE` | 4xx, 5xx after retries, timeout, DNS failure, TLS failure |
| `SOURCE_EMPTY` | 200, but extractable text below the threshold |
| `SOURCE_PAYWALLED` | Paywall or consent wall detected per §5 |
| `SOURCE_DRIFTED` | Content differs from the nearest snapshot per §6 |
| `SOURCE_ROBOTS_EXCLUDED` | `robots.txt` disallows the path, so no request was made |

`SOURCE_ROBOTS_EXCLUDED` is new. It is tempting to fold it into `SOURCE_UNREACHABLE`, and that would be
wrong: unreachable means we tried and could not, robots-excluded means we chose not to try. Both leave the
claim `UNAUDITABLE` and out of every denominator, so the arithmetic is identical, but the reason published
next to the number is not. A project whose entire argument is that reason codes must stay distinct does not
get to collapse two of them for tidiness.

Anything other than `SOURCE_OK` marks the claim `UNAUDITABLE` with its reason attached, and no judge call is
made. Judging a claim against a page we do not have would be inventing evidence.

## 5. Extraction

- Readability for HTML. PDFs parsed if a text layer exists, otherwise `SOURCE_EMPTY`. No OCR
- `SOURCE_EMPTY` threshold: fewer than 200 characters of extracted text
- Paywall and consent walls detected by heuristic: known interstitial markers, a `paywall` or `consent`
  container with the article body absent, or a body that is almost entirely boilerplate

**The heuristic will be wrong sometimes.** Some paywalls will read as `SOURCE_EMPTY`, and some sites that
serve a stub to automated clients will read as `SOURCE_OK` with useless text. The false positive and false
negative rates for paywall detection are not measured, and the writeup says so rather than presenting the
paywall count as exact.

## 6. Drift

- Nearest Wayback snapshot to the answer's generation timestamp, fetched with the `id_` suffix so the
  archive's own toolbar is not counted as drift
- Compare extracted text, normalised for whitespace and casing. Both containment and Jaccard are recorded
- **Page level answers one question only: is this still the same document.** `SOURCE_DRIFTED` fires below
  containment 0.10, which means the URL is serving something else entirely: a redirect to a homepage, a
  consent wall in place of an article, a 404 body behind a 200. Between 0.10 and 0.80 the page changed and
  stays auditable, recorded as `DRIFT_PAGE_CHANGED`
- **Whether the change mattered is a per-claim question, answered in Phase 3.** After the span guard confirms
  the judge's span is on the live page, the span is checked against the archived version too. A span that was
  not there when the answer was written voids the verdict as `SPAN_ADDED_AFTER_GENERATION`: the model cannot
  have read it, so it is not evidence about that answer
- No snapshot available means drift is unknown, reported as unknown rather than as no-drift, and the span
  check returns unknown rather than passing

  **Why it works this way.** The first live run excluded a PubMed abstract at containment 0.62. The missing
  text was entirely the *Similar articles* and *Cited by* blocks; the abstract was unchanged. A whole-page
  threshold measures furniture, and a false `SOURCE_DRIFTED` deletes a real source from every denominator.
  Any page with a related-content block fails that way, so the fault was systematic. Asking about the span
  the verdict actually rests on is both narrower and correct, and costs no model calls.

  **What it still cannot see.** Support that was *removed* before the fetch. If a page once said something
  and no longer does, the judge returns `NOT_FOUND_IN_SOURCE` and that is indistinguishable from a citation
  that was always wrong. Catching it would mean judging every claim twice, against live and against archive.
  Stated as a limitation rather than paid for.

## 7. Caching

Every response is cached to disk before anything reads it: raw bytes, response headers, HTTP status, fetch
timestamp, and the sha256 of the body.

- A rerun reads the cache and does not re-request. Reruns audit the same bytes, so verdicts are reproducible
- The cache is append-only within a run. Nothing overwrites a fetch that already happened
- Cache entries are keyed by URL plus fetch timestamp, so a deliberate refetch later is a second record
  rather than a replacement for the first

## 8. Model calls

- Free tier, with a user-supplied key. The key is read from the environment and is never written to disk or
  committed
- Every call logged: timestamp, model id, prompt version, input and output token counts, estimated cost,
  and which claim it belongs to
- Per-run budget cap. On reaching it the run **halts and records that it halted**. It does not silently
  finish with fewer claims audited, because a truncated run reported as a complete one would put a wrong
  denominator under every rate
- Prompt version is part of the gold set's identity. Changing the prompt invalidates the calibration and
  gate G4 refuses aggregates until the gold set is relabelled

## 9. Privacy

- No third-party data enters the pipeline at any point
- Professional-stratum queries are scrubbed before commit per `queries/README.md`, and anything that cannot
  survive scrubbing is dropped and counted
- Fetched page content stays local. The repo publishes verdicts, reason codes, URLs and quoted spans, not
  copies of the pages
- Quoted spans in published output are single sentences used as evidence for a verdict. No page is
  reproduced at length

## 10. What is enforced by code, and what is not

Being honest about this is the point of the section.

**Enforced by code, and tested:**

- Rate limit, timeouts, retry policy
- `robots.txt` check before every request
- User-Agent on every request
- Cache write before read
- Unauditable claims excluded from every denominator
- No judge call on a non-`SOURCE_OK` source
- Budget cap halting the run
- Query set freeze verified before capture

**Enforced by discipline, not by code:**

- No paywall circumvention. Nothing in the codebase stops a future version of me from adding a header that
  gets past one. The protection is that this document says not to, and the fetch layer has no code path for it
- The drift threshold not being tuned after seeing results
- The scrub being applied to every query rather than to the convenient ones

The second list is the honest one. A contract that claims everything is automated when it is not is the same
category of error as a confidence score on a page nobody fetched.
