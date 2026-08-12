"""The verified-inferred boundary, as data rather than as a table somebody typed.

`SCOPE.md` §4 is the heart of the attestation: every field this tool emits, classified by where it came from.
A reader deciding how much weight to put on a number needs to know whether it was observed, computed,
fetched from somewhere else, produced by a model, or supplied by a person.

**Why it lives here and not only in the document.** A hand-written table describes the fields that existed on
the day it was written. This project already found three prose claims that had drifted false, which is why
`tests/test_documents.py` exists, and a classification table is exactly the kind of prose that rots: a field
gets added to a payload and no one revisits §4. So the classification is a Python object, §4's table is
rendered from it, and a test compares the document against the render and fails on drift.

**The seven labels, and why `record` and `local-evidence` are different.** The distinction that took the most
thought. A `record` is a primary observation: what the product emitted, what the server returned, when. A
`local-evidence` field is something this project stored and later reads back as evidence, and the difference
matters because a re-audit over cached bytes and a re-fetch answer different questions. `tools/reaudit_spans.py`
runs over the cache on purpose, since re-checking a span against a page fetched today would silently
substitute today's page for the one the answer was written against. Collapsing the two labels would hide that.
"""

from __future__ import annotations

from dataclasses import dataclass

#: The seven classifications, each with the question it answers for a reader.
LABELS: dict[str, str] = {
    "record": (
        "A primary observation, written down as it arrived: what the product emitted, what a server "
        "returned, and when. Nothing was inferred to produce it"
    ),
    "local-evidence": (
        "An artefact this project stored and reads back as evidence, chiefly the fetch cache and the stored "
        "page. Distinct from a record because a rerun over stored bytes answers a different question than a "
        "fresh fetch, and several findings depend on the difference"
    ),
    "external-source": (
        "Content fetched from a third party that is not the audited product: the cited page itself, and the "
        "Wayback snapshot. Its accuracy is that third party's, not this tool's"
    ),
    "script-output": (
        "Computed by deterministic code from records, local evidence or external sources. Reproducible from "
        "the same inputs, and carrying no judgement"
    ),
    "model-inference": (
        "Produced by a language model. Rendered with an explicit judgement marker in every output surface "
        "and never printed bare beside a record-derived number"
    ),
    "your-input": (
        "Supplied by a person, and the only class this tool cannot generate or check. The gold set labels "
        "and the pre-registered cost of error"
    ),
    "missing": (
        "Not produced at all, and named here so its absence is visible. A field a reader might expect and "
        "will not find, with the reason"
    ),
}


@dataclass(frozen=True)
class Row:
    field: str
    label: str
    note: str = ""

    def __post_init__(self):
        if self.label not in LABELS:
            raise ValueError(f"{self.field}: {self.label!r} is not one of the seven classifications")


#: Every field the tool emits. Ordered by how far each one sits from a primary observation, because that is
#: the order a reader should weigh them in.
CLASSIFICATION: tuple[Row, ...] = (
    Row("Query, answer text, model ID, generation timestamp", "record",
        "as captured from the product, hashed. An edited capture is rejected on load"),
    Row("Cited URL, HTTP status, fetch timestamp, content hash", "record",
        "what the server returned, before anything read it"),
    Row("`extension_version`, adapter name, whether the adapter was verified", "record",
        "provenance of the capture itself, so a stale content script announces itself"),

    Row("Cached page bytes in `.cache/fetch/`", "local-evidence",
        "append-only, so a rerun audits the same bytes rather than today's page"),
    Row("Stored page HTML saved beside a capture", "local-evidence",
        "re-extraction runs over this, so a selector fix does not re-run the query"),
    Row("Stored split (`splits/`), and its `split_sha256`", "local-evidence",
        "the claims a human labelled. Phase 1 does not return the same split twice, so the file is the "
        "evidence rather than the process"),
    Row("Gold set file, its `labels_sha256` and split binding", "local-evidence",
        "the container. The labels inside it are your-input"),

    Row("Fetched page content", "external-source",
        "the cited page, from whoever publishes it"),
    Row("Wayback snapshot content and date", "external-source",
        "a third party's copy, and its absence is reported as unknown rather than as unchanged"),
    Row("Crossref resolution of a named citation", "external-source",
        "existence only, never support. It enters no denominator"),

    Row("Extracted source text, text length, document kind", "script-output",
        "deterministic given the bytes. The layer most likely to be wrong, per `FINDINGS.md` item 11"),
    Row("G2 outcome code", "script-output",
        "eleven codes, derived from status, headers and extracted length"),
    Row("Span-present check (`JUDGE_FABRICATED_SPAN`)", "script-output",
        "deterministic. It checks presence, never relevance"),
    Row("Drift containment and Jaccard, `SPAN_ADDED_AFTER_GENERATION`", "script-output",
        "computed against the archived copy, per claim rather than per page"),
    Row("Counts, rates, denominators, Wilson intervals", "script-output",
        "one function computes each denominator and everything calls it"),
    Row("Judge precision, recall, Cohen's kappa", "script-output",
        "arithmetic over your-input. Both halves are named wherever it is printed, because the number is "
        "only as good as the labels under it"),
    Row("Extraction attribution (`extraction_missed`)", "script-output",
        "a script's answer about the passage a labeller pasted, so its input is your-input"),

    Row("Claim boundaries (Phase 1 splitting)", "model-inference",
        "labelled as such in every surface. The spread across runs is measured, not assumed"),
    Row("Support verdict (Phase 3)", "model-inference",
        "the judge's answer, admissible only with a verbatim span a script confirmed"),
    Row("`missing_qualifiers` on a verdict", "model-inference",
        "a list of strings in the page's own terms, never a number"),

    Row("Gold set labels", "your-input",
        "the one field this tool cannot generate. Blind, and refused if they postdate the judge run"),
    Row("`cost_of_error` on a frozen query", "your-input",
        "pre-registered before any capture, and inside the freeze hash"),

    Row("Whether the cited source is *true*", "missing",
        "out of scope. It checks whether the page says what the answer says it says. See §7"),
    Row("Whether the source is any good", "missing",
        "a blog post and a randomised trial are the same object to this tool"),
    Row("What the answer left out", "missing",
        "omission is invisible. The uncited count is a floor with a measured gap under it"),
    Row("A confidence score, anywhere", "missing",
        "refused by design, not unimplemented. An unreachable source makes a claim `UNAUDITABLE` and it "
        "leaves every denominator rather than being scored low"),
)

#: Top-level keys of the CLI run record, mapped to the row that covers them. The test uses this to assert
#: nothing the tool emits is unclassified, which is the failure a typed table cannot catch.
PAYLOAD_KEYS: dict[str, str] = {
    "capture": "record",
    "binding": "script-output",
    "fetches": "record",
    "drift": "external-source",
    "named_citations": "script-output",
    "named_citation_existence": "external-source",
    "auditable": "script-output",
    "unauditable": "script-output",
    "claims": "model-inference",
    "split_sha256": "local-evidence",
    "skips": "script-output",
    "uncited": "script-output",
    "rates": "script-output",
}


def render_table() -> str:
    """The §4 table, generated. `tests/test_documents.py` compares the document against this."""
    lines = ["| Field | Classification | Note |", "|---|---|---|"]
    for row in CLASSIFICATION:
        # The three a reader has to weigh differently are bolded, which is how §4 has always drawn them.
        emphasis = row.label in ("model-inference", "your-input", "missing")
        label = f"**{row.label}**" if emphasis else f"`{row.label}`"
        lines.append(f"| {row.field} | {label} | {row.note} |")
    return "\n".join(lines)


def render_labels() -> str:
    """The seven classifications and what each one tells a reader."""
    lines = ["| Classification | What it means |", "|---|---|"]
    for name, meaning in LABELS.items():
        lines.append(f"| `{name}` | {meaning} |")
    return "\n".join(lines)


def unclassified(payload: dict) -> list[str]:
    """Top-level keys in a run record that no row covers.

    The check a typed table cannot perform: a field added to the payload and never carried into §4.
    """
    return sorted(k for k in payload if k not in PAYLOAD_KEYS)
