# Scrub log

Every real query that entered the intake process appears here exactly once, whether it survived or not.

§10 of `SCOPE.md`: *"if a query can't be scrubbed without destroying what made it a real question, it is
dropped and the drop is counted."* This file is the count. It exists so the drop rate is a published number
rather than an invisible one, because a stratum assembled by silently discarding the inconvenient queries
would look identical to one assembled honestly.

The consumer stratum is synthetic and does not pass through here.

## Totals

| | Count |
|---|---|
| Raw queries reviewed | 0 |
| Kept after scrubbing | 0 |
| Dropped as unscrubbable | 0 |
| Dropped for other reasons | 0 |

Drop rate: not yet computed. Filled in when intake closes, and reported in the writeup alongside the support
rates rather than in an appendix.

## Kept

Queries that survived scrubbing. The redactions are summarized here and repeated in each query's
`scrub_notes` field in `professional.toml`.

| Query id | What was removed | Did the removal change the question |
|---|---|---|
| | | |

## Dropped

| Original topic, generically described | Reason for the drop |
|---|---|
| | | 

Reasons use one of these codes:

- `UNSCRUBBABLE`: the identifying detail was the question. Removing it left a generic question I would not
  actually have asked.
- `NO_CITATIONS_EXPECTED`: a question the tools answer without citing anything, so it produces no claim to
  audit. Not a failure of the query, just out of scope for a citation auditor.
- `DUPLICATE`: substantively the same question as one already kept.
- `THIRD_PARTY_DATA`: the question contained information belonging to someone other than me. Dropped
  regardless of whether scrubbing was technically possible.

## Note on what this log cannot prove

It records the queries I put into intake. It cannot demonstrate that I put *all* of my relevant history into
intake, and nothing here would catch a query quietly skipped before it was ever reviewed. That is a real gap
and it is not closeable by me, since the raw history is private and cannot be published for comparison. What
I can do is state the gap and note that the scrub log's own drop rate is the only visible signal of it. A
suspiciously low drop rate would itself be evidence that the intake was pre-filtered.
