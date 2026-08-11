"""Existence checking for named citations. Never support checking.

`SCOPE.md` §0a stretch item, and `FINDINGS.md` item 1 is the reason it is worth having: a Claude Research
report named at least fifteen sources and hyperlinked one. "LeClair et al., Supportive Care in Cancer, 2022"
is a citation a person can follow and a script cannot fetch, and the claims attached to those names were the
checkable kind. Fabricated references are a well documented failure mode, and this is the cheapest way to
find one: does the paper exist at all.

**The line, and it is not negotiable.** Check existence, never check support. Resolving a name to a paper
means *choosing* a paper nobody pointed at, and then judging a claim against a source we selected ourselves
would be inventing the evidence, which is the exact failure this whole project exists to catch. So:

- three outcomes, no scores: `CITATION_RESOLVED`, `CITATION_NOT_FOUND`, `CITATION_AMBIGUOUS`
- a resolved citation never enters a support-rate denominator, because "this paper exists" and "this paper
  backs this sentence" are different facts and collapsing them would repeat the mistake
- nothing here returns abstracts or full text, and there is a test asserting the record carries none. If the
  document text is never in the record, no later version of this can quietly start judging against it

Crossref is free and needs no key, so it fits the budget. It is queried with the same identifying User-Agent
the fetch layer uses, at one request per second, per `DATA_CONTRACT.md` §2.

**What a `CITATION_NOT_FOUND` does and does not mean.** It means this query did not resolve. Crossref does
not index everything: conference abstracts, government reports, preprints outside arXiv and anything from a
non-participating publisher can be perfectly real and absent. So not-found is a prompt to look by hand, not
a finding that the citation is fabricated, and the writeup says that next to the number rather than under it.
"""

from __future__ import annotations

import json
import re
import time
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from typing import Any

from .fetch import DEFAULT_CONTACT, user_agent

API = "https://api.crossref.org/works"

#: A work matching the name was found, and only one candidate matched.
CITATION_RESOLVED = "CITATION_RESOLVED"

#: Nothing matched. Not a finding that the citation is fabricated: Crossref does not index everything.
CITATION_NOT_FOUND = "CITATION_NOT_FOUND"

#: More than one candidate matched, so naming one of them would be a choice rather than a resolution.
CITATION_AMBIGUOUS = "CITATION_AMBIGUOUS"

#: The lookup could not be made at all: no network, an API error, a timeout. Distinct from not-found on the
#: same grounds SOURCE_ROBOTS_EXCLUDED is distinct from SOURCE_UNREACHABLE. Not-found means we asked and
#: nothing matched; this means we never got an answer, and reporting it as not-found would turn our own
#: outage into a finding about somebody's citation.
CITATION_LOOKUP_FAILED = "CITATION_LOOKUP_FAILED"

_YEAR = re.compile(r"\b(19|20)\d{2}\b")
_SURNAME = re.compile(r"\b([A-Z][A-Za-z'’\-]{2,})\s+et\s+al")
_DOI = re.compile(r"\b10\.\d{4,9}/[^\s,;)\]]+")


@dataclass
class Resolution:
    """What a lookup found. A record, never a judgement about support."""

    query: str
    outcome: str
    #: The DOI of the single matching work, when there is exactly one. Empty otherwise, including for
    #: ambiguous, where naming one candidate would be the choice this module refuses to make.
    doi: str = ""
    title: str = ""
    year: int | None = None
    candidates: int = 0
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["source"] = "external-source"
        d["note"] = (
            "Existence only. This says a work with this name exists, and says nothing whatever about "
            "whether it supports the claim it was cited for. It enters no support-rate denominator."
        )
        return d


def _surname_of(text: str) -> str:
    match = _SURNAME.search(text)
    if match:
        return match.group(1).casefold()
    # "Smith, Journal of Things, 2020" with no "et al": take the first capitalised word.
    words = re.findall(r"\b[A-Z][A-Za-z'’\-]{2,}\b", text)
    return words[0].casefold() if words else ""


def _year_of(text: str) -> int | None:
    match = _YEAR.search(text)
    return int(match.group(0)) if match else None


def _fetch_json(url: str, timeout: float = 20.0) -> dict:
    request = urllib.request.Request(
        url, headers={"User-Agent": user_agent(DEFAULT_CONTACT), "Accept": "application/json"}
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read())


def _work_year(work: dict) -> int | None:
    for key in ("published-print", "published-online", "issued", "created"):
        parts = (work.get(key) or {}).get("date-parts") or []
        if parts and parts[0] and parts[0][0]:
            return int(parts[0][0])
    return None


def _work_surnames(work: dict) -> set[str]:
    return {
        str(a.get("family", "")).casefold()
        for a in (work.get("author") or [])
        if a.get("family")
    }


def resolve(text: str, fetch_json=_fetch_json, rows: int = 5) -> Resolution:
    """Look one named citation up. Existence only.

    A candidate counts as a match when the first-author surname appears in its author list and its year is
    within one of the year in the citation. Both are required. Surname alone matches half the literature,
    and year alone matches a twentieth of it.

    `fetch_json` is injectable so the tests do not depend on Crossref being up, which would make the suite
    fail for a reason that has nothing to do with this repo.
    """
    query = " ".join(text.split())

    doi_match = _DOI.search(query)
    if doi_match:
        doi = doi_match.group(0).rstrip(".,;)")
        try:
            payload = fetch_json(f"{API}/{urllib.parse.quote(doi)}")
        except Exception as exc:
            return Resolution(query=query, outcome=CITATION_LOOKUP_FAILED, detail=str(exc))
        work = payload.get("message") or {}
        if not work:
            return Resolution(query=query, outcome=CITATION_NOT_FOUND, detail="DOI not registered")
        return Resolution(
            query=query,
            outcome=CITATION_RESOLVED,
            doi=str(work.get("DOI", doi)),
            title=(work.get("title") or [""])[0],
            year=_work_year(work),
            candidates=1,
            detail="resolved by DOI, which is unambiguous",
        )

    surname = _surname_of(query)
    year = _year_of(query)
    if not surname:
        return Resolution(
            query=query, outcome=CITATION_LOOKUP_FAILED,
            detail="no author surname could be read out of this citation, so there is nothing to match on",
        )

    url = f"{API}?{urllib.parse.urlencode({'query.bibliographic': query, 'rows': rows})}"
    try:
        payload = fetch_json(url)
    except Exception as exc:
        return Resolution(query=query, outcome=CITATION_LOOKUP_FAILED, detail=str(exc))

    works = ((payload.get("message") or {}).get("items")) or []
    matches = []
    for work in works:
        if surname not in _work_surnames(work):
            continue
        work_year = _work_year(work)
        if year is not None and (work_year is None or abs(work_year - year) > 1):
            continue
        matches.append(work)

    if not matches:
        return Resolution(
            query=query, outcome=CITATION_NOT_FOUND, candidates=0,
            detail=(
                f"{len(works)} result(s) searched, none with author {surname!r}"
                + (f" and year {year}" if year else "")
                + ". Crossref does not index everything, so this is a prompt to look by hand rather than "
                "a finding that the citation is fabricated"
            ),
        )

    if len(matches) > 1:
        return Resolution(
            query=query, outcome=CITATION_AMBIGUOUS, candidates=len(matches),
            detail=(
                f"{len(matches)} works match this name. Naming one of them would be a choice rather than "
                "a resolution, so none is named"
            ),
        )

    work = matches[0]
    return Resolution(
        query=query,
        outcome=CITATION_RESOLVED,
        doi=str(work.get("DOI", "")),
        title=(work.get("title") or [""])[0],
        year=_work_year(work),
        candidates=1,
    )


@dataclass
class ExistenceReport:
    """Existence outcomes for the named citations in one answer."""

    resolutions: list[Resolution] = field(default_factory=list)

    def counts(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for r in self.resolutions:
            out[r.outcome] = out.get(r.outcome, 0) + 1
        return out

    def to_dict(self) -> dict[str, Any]:
        return {
            "resolutions": [r.to_dict() for r in self.resolutions],
            "counts": self.counts(),
            "note": (
                "Existence checking only. No resolution here enters any support-rate denominator, and no "
                "claim was judged against any of these works. CITATION_NOT_FOUND means this lookup did not "
                "resolve, not that the citation is fabricated."
            ),
        }

    def render(self) -> str:
        if not self.resolutions:
            return "crossref     no named citations to look up"
        lines = [f"crossref     {self.counts()}"]
        for r in self.resolutions:
            lines.append(f"  {r.outcome:<24} {r.query[:70]}")
            if r.outcome == CITATION_RESOLVED and r.doi:
                lines.append(f"    {r.doi}  {r.title[:80]}")
            elif r.detail:
                lines.append(f"    {r.detail[:110]}")
        lines.append(
            "  Existence only. None of this says whether any of these works supports the claim it was "
            "cited for."
        )
        return "\n".join(lines)


def check_named(capture, fetch_json=_fetch_json, rate_limit: float = 1.0, sleep=time.sleep) -> ExistenceReport:
    """Look up every named, unlinked citation in a capture. One request per second, per the data contract."""
    from .named_citations import find_named_citations

    report = ExistenceReport()
    for n, citation in enumerate(find_named_citations(capture.answer_text)):
        if n and rate_limit:
            sleep(rate_limit)
        report.resolutions.append(resolve(citation.text, fetch_json=fetch_json))
    return report
