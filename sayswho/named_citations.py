"""Named citations: sources an answer names in prose without linking.

Found on day 2, in a real Claude Research report about breast cancer screening. The report ran to 20,288
characters, named at least fifteen sources, and hyperlinked exactly one. Everything else was of the form
"LeClair et al., Supportive Care in Cancer, 2022", attached to numbers a reader would act on: a 78% mortality
difference, an adjusted odds ratio of 2.06, a cost of $979 to $1,759 per patient.

Without this module the pipeline would have passed G0 on that report, audited its single link, and reported
on n=1 as though it had looked at the whole thing.

`SCOPE.md` §7 anticipates omission, meaning sentences with no citation at all. This is a different failure:
the sentence *is* cited, in a form a person can follow and a script cannot. A named citation does more
rhetorical work than a footnote, because it carries an author and a journal and a year, and less of it can
be checked, because there is nothing to fetch.

**What this module does not do.** It does not look the source up, and it never judges support. Resolving
"LeClair et al., 2022" to a paper would mean *choosing* a paper nobody pointed at, and judging a claim
against a source we selected ourselves would be inventing the evidence. That boundary is the whole reason
this is safe to build. Existence checking against Crossref is recorded as a stretch item in `TODO.md`, and
even if it lands, a resolved citation still never enters a support-rate denominator.

**Precision over recall, deliberately.** The count of unverifiable citations is a number that gets published,
so a false positive inflates a finding. The patterns below are narrow. They will miss real named citations,
and the writeup says the count is a floor rather than a total.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass

#: A claim whose source is named in prose but carries no resolvable URL.
CITATION_NOT_LINKED = "CITATION_NOT_LINKED"

AUTHOR_ETAL_YEAR = "AUTHOR_ETAL_YEAR"
TRIAL_ID = "TRIAL_ID"
DOI = "DOI"
PUBLISHED_IN = "PUBLISHED_IN"
YEAR_JOURNAL_STUDY = "YEAR_JOURNAL_STUDY"

_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    # "LeClair et al., Supportive Care in Cancer, 2022"
    # "Yala, Mikhael, Lehman, Barzilay et al., Science Translational Medicine, 2021"
    # "Rajabiun et al., Cancer, 2025;131(1):e35671"
    (
        AUTHOR_ETAL_YEAR,
        re.compile(
            r"\b[A-Z][A-Za-z'’\-]+"
            r"(?:,\s+[A-Z][A-Za-z'’\-]+){0,5}"
            r"\s+et\s+al\.?,?\s*"
            r"[^.;)\n]{0,80}?"
            r"\b(?:19|20)\d{2}\b"
        ),
    ),
    # The same thing with the year first: "AACR Abstract A039, 2023, Battaglia et al."
    # "et al" is doing the work here, which is why a bare year in prose cannot trigger this.
    (
        AUTHOR_ETAL_YEAR,
        re.compile(
            r"\b(?:19|20)\d{2}\b"
            r"[^.;)\n]{0,60}?"
            r"\b[A-Z][A-Za-z'’\-]+"
            r"(?:,\s+[A-Z][A-Za-z'’\-]+){0,5}"
            r"\s+et\s+al\.?"
        ),
    ),
    # "clinicaltrials.gov NCT03514433". Unambiguous, so it is matched on the identifier alone.
    (TRIAL_ID, re.compile(r"\bNCT\d{8}\b")),
    # A bare DOI. Also unambiguous.
    (DOI, re.compile(r"\b10\.\d{4,9}/[^\s,;)\]]+")),
    # "published in Nature Health (Nov 2025)"
    (
        PUBLISHED_IN,
        re.compile(
            r"\bpublished\s+in\s+"
            r"[A-Z][A-Za-z&\-]+(?:\s+[A-Z][A-Za-z&\-]+){0,4}"
            r"[^.\n]{0,30}?\b(?:19|20)\d{2}\b"
        ),
    ),
    # "a 2014 Cancer Epidemiology study"
    (
        YEAR_JOURNAL_STUDY,
        re.compile(
            r"\b(?:19|20)\d{2}\s+"
            r"[A-Z][A-Za-z&\-]+(?:\s+[A-Z][A-Za-z&\-]+){0,3}\s+"
            r"(?:study|paper|trial|analysis|report|review)\b"
        ),
    ),
]


@dataclass(frozen=True)
class NamedCitation:
    """A source named in the text, with no URL attached."""

    text: str
    start: int
    end: int
    kind: str

    def to_dict(self) -> dict:
        return asdict(self)


def find_named_citations(text: str) -> list[NamedCitation]:
    """Named sources in prose, in document order, with overlaps resolved in favour of the longer match."""
    found: list[NamedCitation] = []

    for kind, pattern in _PATTERNS:
        for match in pattern.finditer(text):
            found.append(
                NamedCitation(
                    text=" ".join(match.group(0).split()),
                    start=match.start(),
                    end=match.end(),
                    kind=kind,
                )
            )

    # Overlapping matches are the same citation seen by two patterns. Keep the longer one, so a single
    # source is never counted twice into a published number.
    found.sort(key=lambda c: (c.start, -(c.end - c.start)))
    kept: list[NamedCitation] = []
    for citation in found:
        if kept and citation.start < kept[-1].end:
            continue
        kept.append(citation)

    return kept


@dataclass
class NamedCitationReport:
    linked_citations: int
    named_citations: list[NamedCitation]

    @property
    def named_count(self) -> int:
        return len(self.named_citations)

    @property
    def by_kind(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for citation in self.named_citations:
            counts[citation.kind] = counts.get(citation.kind, 0) + 1
        return counts

    def to_dict(self) -> dict:
        return {
            "linked_citations": self.linked_citations,
            "named_citations_found": self.named_count,
            "by_kind": self.by_kind,
            # A floor, not a total. The patterns are narrow on purpose, because this number is published.
            "count_is_a_floor": True,
            "named_citations": [c.to_dict() for c in self.named_citations],
        }


def analyse(capture) -> NamedCitationReport:
    """Named citations in a capture, alongside how many real links it carried."""
    return NamedCitationReport(
        linked_citations=len(capture.citations),
        named_citations=find_named_citations(capture.answer_text),
    )
