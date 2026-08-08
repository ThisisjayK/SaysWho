"""Phase 1, claim extraction, and gate G1.

Splits an answer into atomic factual claims, each bound to the citations attached to it. This is
model-inference and is labelled as such in every output surface, per `SCOPE.md` §4.

Gate G1 skips anything that is not a factual claim: opinions, hedges, instructions, definitions, transitional
sentences, and the interface furniture that rides along in a DOM capture ("Give feedback", a maps card's
phone number). Skipped claims are **counted and reported, never dropped silently** — a system that quietly
discards what it cannot handle is lying by omission, and the skip count is a published number.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from .model import JudgeClient, ModelRefused
from .records import Capture, normalise_url

#: Bumping this invalidates the gold set, same as the judge prompt. `SCOPE.md` §3 gate G4.
CLAIM_PROMPT_VERSION = "claims-v1"

NOT_A_FACTUAL_CLAIM = "NOT_A_FACTUAL_CLAIM"

SYSTEM = """You split an AI-generated answer into the individual factual claims it makes, so each one can be
checked against the source it cites.

A factual claim asserts something about the world that could turn out to be true or false: a number, a date,
an event, a property of a named thing, a rule or requirement. Split compound sentences into separate claims
when they assert separate checkable things.

Skip anything that is not a factual claim, and say why. Skip opinions and recommendations, hedges and
framing, instructions to the reader, definitions of terms, transitions and headings, and interface text that
was captured along with the answer (feedback links, ratings, phone numbers, navigation labels).

For each claim, list the citation markers attached to it or to the sentence it came from, exactly as they
appear in the answer. A claim with no citation marker gets an empty list; do not guess which source it
belongs to.

Quote each claim's text from the answer rather than paraphrasing it, so a reader can find it."""

SCHEMA = {
    "type": "object",
    "properties": {
        "claims": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "markers": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["text", "markers"],
                "additionalProperties": False,
            },
        },
        "skipped": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "reason": {"type": "string"},
                },
                "required": ["text", "reason"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["claims", "skipped"],
    "additionalProperties": False,
}


@dataclass
class Claim:
    """One factual claim, bound to the citations attached to it. Model inference."""

    id: str
    text: str
    markers: list[str] = field(default_factory=list)
    urls: list[str] = field(default_factory=list)

    @property
    def is_cited(self) -> bool:
        return bool(self.urls)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["source"] = "model-inference"
        return d


@dataclass
class Skipped:
    text: str
    reason: str
    code: str = NOT_A_FACTUAL_CLAIM

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ClaimSet:
    claims: list[Claim]
    skipped: list[Skipped]

    @property
    def uncited_count(self) -> int:
        """Claims the splitter found with no citation attached.

        Not the same as `NO_CITATIONS`: the answer had citations, this particular sentence did not. It is
        the omission blindness in `SCOPE.md` §7, counted where it can be seen.
        """
        return sum(1 for c in self.claims if not c.is_cited)

    def to_dict(self) -> dict:
        return {
            "claims": [c.to_dict() for c in self.claims],
            "skipped": [s.to_dict() for s in self.skipped],
            "claim_count": len(self.claims),
            "skipped_count": len(self.skipped),
            "uncited_claim_count": self.uncited_count,
        }


def _marker_index(capture: Capture) -> dict[str, list[str]]:
    """Marker text to the URLs it points at, normalised for fetching."""
    index: dict[str, list[str]] = {}
    for citation in capture.citations:
        key = " ".join(citation.marker.split()).casefold()
        url = normalise_url(citation.url)
        index.setdefault(key, [])
        if url not in index[key]:
            index[key].append(url)
    return index


def split_claims(capture: Capture, client: JudgeClient) -> ClaimSet:
    """Split a captured answer into claims and bind each to its cited URLs."""
    try:
        reply = client.complete_json(
            system=SYSTEM,
            cached_context=f"<answer product=\"{capture.product}\">\n{capture.answer_text}\n</answer>",
            question=(
                "Citation markers present in this answer: "
                + ", ".join(sorted({c.marker for c in capture.citations}))
                + "\n\nSplit the answer above into factual claims."
            ),
            schema=SCHEMA,
            purpose="split",
            prompt_version=CLAIM_PROMPT_VERSION,
            subject=capture.query_id,
        )
    except ModelRefused as exc:
        raise RuntimeError(f"claim splitting refused for {capture.query_id}: {exc}") from exc

    index = _marker_index(capture)
    claims: list[Claim] = []

    for i, raw in enumerate(reply.get("claims", []), start=1):
        markers = [m for m in raw.get("markers", []) if m]
        urls: list[str] = []
        for marker in markers:
            for url in index.get(" ".join(marker.split()).casefold(), []):
                if url not in urls:
                    urls.append(url)
        claims.append(
            Claim(id=f"{capture.query_id}#{i:03d}", text=raw.get("text", ""), markers=markers, urls=urls)
        )

    skipped = [
        Skipped(text=s.get("text", ""), reason=s.get("reason", ""))
        for s in reply.get("skipped", [])
    ]

    return ClaimSet(claims=claims, skipped=skipped)
