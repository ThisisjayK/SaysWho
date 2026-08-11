"""Per-domain reporting. `SCOPE.md` §0a item 9, stretch.

The question it answers is whether the tool's results vary by the kind of site being cited. A support rate
that is much lower for one publisher than another is more likely to be a fact about this pipeline than about
that publisher: a paywall pattern it misreads, a layout its extractor mangles, a PDF library it does not
have. So this is a diagnostic aimed at SaysWho first and at the products second, and the writeup has to say
so, because "citations to this site are less supported" is a sentence a reader will take as being about the
site.

**Everything here obeys the same rules as the aggregate**, which is the whole reason it is built on
`rates.py` rather than counting on its own:

- The unit is the claim-source pair.
- Unauditable pairs never enter a denominator. `standing_denominator` raises rather than letting them.
- No rate is printed unless G4 has passed, and the refusal reason travels with the refusal.
- Every rate carries its n and an interval, and at these sample sizes almost every per-domain n is small
  enough that the interval is the finding.

**Registrable domain, not hostname.** `www.bmc.org` and `bmc.org` are one publisher, and counting them apart
would split an already small n in half. The suffix handling is deliberately simple and its limits are stated
in `registrable_domain`.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit

from .rates import Pair, Rate, UNIT_PAIR, standing_denominator
from .judge import CONTRADICTED, NOT_FOUND_IN_SOURCE, PARTIALLY_SUPPORTED, SUPPORTED
from .records import AUDITABLE_CODES

#: Two-part public suffixes common in this corpus, where the registrable domain is three labels rather than
#: two. Not a full public suffix list: pulling one in would be a dependency, and this is a reporting
#: convenience rather than a security boundary. A domain that lands wrong here is grouped oddly in a table,
#: which is visible, rather than silently mis-scored.
_TWO_PART_SUFFIXES = frozenset(
    {
        "ac.uk", "co.uk", "gov.uk", "org.uk", "nhs.uk", "sch.uk",
        "com.au", "gov.au", "edu.au", "org.au",
        "co.nz", "govt.nz", "co.jp", "go.jp", "ac.jp",
        "com.br", "gov.br", "co.in", "gov.in", "nic.in", "ac.in",
        "com.cn", "gov.cn", "edu.cn", "co.za", "gov.za",
    }
)


def registrable_domain(url: str) -> str:
    """The publisher-level domain of a URL, lowercased. Empty string when there is not one.

    `www.` and other leading subdomains are dropped, so `www.bmc.org`, `bmc.org` and `patients.bmc.org` are
    one publisher. Known two-part suffixes are handled, so `nhs.uk` does not collapse a hospital trust and a
    government department into the same row.

    Limits, stated because a wrong grouping is a wrong row in a published table: this is not a public suffix
    list, so an unusual multi-part suffix will group one label too high. It is a reporting convenience.
    """
    try:
        host = (urlsplit(url).hostname or "").lower().strip(".")
    except ValueError:
        return ""
    if not host or host.replace(".", "").isdigit():
        # An IP address has no registrable domain. Returned as-is so it is visible rather than dropped.
        return host

    labels = host.split(".")
    if len(labels) < 2:
        return host
    if ".".join(labels[-2:]) in _TWO_PART_SUFFIXES and len(labels) >= 3:
        return ".".join(labels[-3:])
    return ".".join(labels[-2:])


@dataclass(frozen=True)
class DomainRow:
    """One publisher's row. Counts always; a rate only when a gate allowed one."""

    domain: str
    pairs: int
    standing: int
    unauditable: int
    verdicts: dict[str, int]
    #: Why pairs from this domain could not be read, by G2 code. This is the column that makes the table a
    #: diagnostic about the tool rather than a league table of publishers.
    source_codes: dict[str, int]
    rate: Rate | None = None
    rate_refused: str = ""

    def to_dict(self) -> dict:
        return {
            "domain": self.domain,
            "pairs": self.pairs,
            "standing": self.standing,
            "unauditable": self.unauditable,
            "verdicts": dict(sorted(self.verdicts.items())),
            "source_codes": dict(sorted(self.source_codes.items())),
            "rate": self.rate.to_dict() if self.rate else None,
            "rate_refused": self.rate_refused,
        }

    def render(self) -> str:
        if self.rate is not None:
            return f"{self.domain}: {self.rate.render()}"
        reason = self.rate_refused or "no rate"
        return (
            f"{self.domain}: {self.standing} of {self.pairs} {UNIT_PAIR}s readable, no rate ({reason})"
        )


def by_domain(
    pairs: list[Pair],
    calibration=None,
    splits: int = 1,
    split_sha256: str = "",
    min_standing: int = 2,
) -> list[DomainRow]:
    """Group pairs by publisher and rate each group, or say why not.

    `calibration` is the G4 result. When it has not passed, every row reports counts and no rate, carrying
    the same refusal the aggregate carries: a per-domain rate is still a rate, and slicing a number that may
    not be printed does not make it printable.

    `min_standing` defaults to 2 because a rate over a single observation is not a rate, it is the
    observation with a percent sign on it: "100.0%" over one pair is the number that gets quoted without its
    n. The row is still returned with all of its counts and the reason, so nothing is hidden. Only the
    percentage is withheld.

    Sorted by pair count, descending, then by name. The busiest publisher first is what a reader scans for.
    """
    grouped: dict[str, list[Pair]] = {}
    for pair in pairs:
        grouped.setdefault(registrable_domain(pair.url), []).append(pair)

    rows: list[DomainRow] = []
    for domain, group in grouped.items():
        # Raises if an unauditable pair is being counted as standing. Called per group as well as over the
        # whole run, so a contaminated denominator cannot slip in through a slice.
        standing = standing_denominator(group)

        verdicts: dict[str, int] = {}
        codes: dict[str, int] = {}
        for pair in group:
            if pair.standing:
                verdicts[pair.verdict] = verdicts.get(pair.verdict, 0) + 1
            else:
                key = pair.void_reason or pair.source_code or "not judged"
                codes[key] = codes.get(key, 0) + 1

        rate = None
        refused = ""
        # Gate first, then the presentation threshold. G4 not passing is a fact about the whole run and
        # holds however many pairs there are, so reporting "only 1 readable pair" instead would name the
        # smaller reason and imply the larger one had been satisfied.
        if calibration is None:
            refused = "no calibration supplied, so no rate is printed"
        elif not getattr(calibration, "passed", False):
            refused = getattr(calibration, "detail", "") or "gate G4: no gold set for this judge"
        elif standing < min_standing:
            refused = f"only {standing} readable pair(s)"
        else:
            rate = Rate(
                name=f"citation support rate, {domain}",
                hits=sum(1 for p in group if p.standing and p.verdict == SUPPORTED),
                n=standing,
                unit=UNIT_PAIR,
                splits=splits,
                split_sha256=split_sha256,
                note=(
                    f"SUPPORTED over claim-source pairs citing {domain} whose verdict stands. A low rate "
                    "here is more likely to be a fact about this pipeline than about the publisher: check "
                    "the source_codes column before reading it any other way."
                ),
            )

        rows.append(
            DomainRow(
                domain=domain or "(no domain)",
                pairs=len(group),
                standing=standing,
                unauditable=len(group) - standing,
                verdicts=verdicts,
                source_codes=codes,
                rate=rate,
                rate_refused=refused,
            )
        )

    rows.sort(key=lambda r: (-r.pairs, r.domain))
    return rows


def render(rows: list[DomainRow]) -> str:
    """The table, as text, with the caveat attached rather than left to the reader to remember."""
    if not rows:
        return "per-domain: no cited sources"

    lines = [f"per-domain, {UNIT_PAIR}s, {len(rows)} publisher(s):"]
    for row in rows:
        lines.append(f"  {row.render()}")
        if row.source_codes:
            unread = ", ".join(f"{k} {v}" for k, v in sorted(row.source_codes.items()))
            lines.append(f"      not read: {unread}")
    lines.append(
        "  A low rate for one publisher is a hypothesis about this pipeline first: a paywall pattern it "
        "misreads, a layout its extractor mangles, a format it cannot open."
    )
    return "\n".join(lines)
