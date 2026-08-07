# SaysWho

A browser extension that checks whether AI answers' citations actually support the claims attached to them.
Graduate capstone, Northeastern, for a course on computational skepticism. Repo:
https://github.com/ThisisjayK/SaysWho

`SCOPE.md` is the design document. Read §0a before proposing work, since it defines what is core (due day 7)
and what is stretch (days 8 to 10).

## Status tracking

`CHECKLIST.md` is the single source of truth for what is done and what is not. There is no second task list.

- Tick an item only when it is finished, not when it is started
- A stretch item that does not happen gets marked not-done with a reason. It does not get deleted, because
  §0a promises the writeup reports it either way
- Update `CHECKLIST.md` in the same commit as the work it describes

At the start of a session, read `CHECKLIST.md` to find the current state rather than asking.

## Invariants that are not up for negotiation

These are the project. Breaking one silently is worse than missing a deadline.

**Never invent a professional-stratum query.** Entries in `queries/professional.toml` must be real questions
Jayanth actually asked an AI tool during PM work, scrubbed per `queries/README.md`. `SCOPE.md` §10 claims they
are real, and §7's whole limitations argument depends on that being literally true. A plausible invented
question would make a published sentence false. If the file is empty, it stays empty until real queries
arrive.

**Never edit a frozen query.** `python3 tools/freeze_queries.py check` must pass before any capture run. It
fails on additions, removals and edits, including edits to `cost_of_error`. Breaking a freeze requires
`--force --reason`, which is recorded permanently in the manifest.

**No confidence score, anywhere.** Not in the extension, not in the harness, not in the writeup. An
unreachable source makes a claim `UNAUDITABLE`, and unauditable claims never enter the denominator of any
published rate.

**No verdict without a verbatim span.** `SUPPORTED` requires a quoted span that a script confirms is present
in the fetched document. Failures log `JUDGE_FABRICATED_SPAN` and the rate gets published rather than fixed
quietly.

**Do not weaken a claim's caveats to make a result read better.** Every rate carries its n and a confidence
interval. Until the §5a head-to-head actually runs, the differentiator is described as structural, not
measured, and incumbent behaviour is attributed to their marketing copy.

## Repo conventions

- `email-to-professor.md` and `reply-to-professor.md` are gitignored on purpose. Correspondence stays local
- `email-to-professor.md` is a record of what was already sent. Do not edit it, including to fix the old
  project name. It said RECEIPTS because that is what went out
- Prose in this project contains no em dashes. Check before committing anything written
- Tooling is stdlib only. Python 3.11 or newer for `tomllib`. Do not add dependencies without asking
