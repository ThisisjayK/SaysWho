"""Phase 5, the report payload, and the marking view built from it.

The reader's question is narrow: does the cited source actually say this. So the view shows three things
per claim and keeps everything else one level down. What it must never do is answer that question when the
pipeline did not, which is why `COULD_NOT_VERIFY` is a first-class state rather than a quiet absence.

**One payload, two surfaces.** This module computes every state the view displays. The extension does not
recompute anything: it loads this JSON and calls the same `render.js`. `SCOPE.md` §9 requires the extension
and the harness to produce identical verdicts, and the cheapest way to satisfy that for the view is to have
one implementation of it and no second opinion.

**The claim-level state does not decide the unit of the support rate.** A claim citing three sources can
come back supported by one and not-found by two, and which of those the rate counts is still open
(`TODO.md`, due before day 5). So a disagreement renders as `MIXED` with the per-source rows visible, rather
than being collapsed into whichever answer a rate would eventually want.
"""

from __future__ import annotations

import html
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .extract import normalise_for_span
from .judge import PARTIALLY_SUPPORTED, SUPPORTED

#: What the reader sees. Three answers to "does the source say this", plus the two ways there is no answer.
SUPPORTED_STATE = "SUPPORTED"
NOT_SUPPORTED = "NOT_SUPPORTED"
MIXED = "MIXED"
COULD_NOT_VERIFY = "COULD_NOT_VERIFY"
NOT_CHECKED = "NOT_CHECKED"

#: Text shown for each state. Wording is load bearing. "Not supported by the cited source" is a statement
#: about the citation, not about the world: the claim may be perfectly true and cited to the wrong page.
STATE_LABELS = {
    SUPPORTED_STATE: "Supported by the cited source",
    NOT_SUPPORTED: "Not supported by the cited source",
    MIXED: "Sources disagree",
    COULD_NOT_VERIFY: "Could not verify",
    NOT_CHECKED: "No citation to check",
}

STATE_HELP = {
    SUPPORTED_STATE: "A passage from the cited page was quoted, and a script confirmed it is really there.",
    NOT_SUPPORTED: "The page was read and does not state this, or states something incompatible with it.",
    MIXED: "One cited source supports this and another does not. Both are shown; neither is averaged.",
    COULD_NOT_VERIFY: (
        "No verdict stands. The source could not be read, or the verdict was thrown out. This is not "
        "evidence for or against the claim."
    ),
    NOT_CHECKED: "The answer attached no citation to this sentence, so there was nothing to check.",
}


def locate(answer: str, claim_text: str) -> tuple[int, int] | None:
    """Character offsets of a claim inside the answer, tolerating whitespace differences.

    Computed here rather than in the renderer so both surfaces mark the same characters. Returns None when
    the claim cannot be found, which happens for claims lifted out of a table: the DOM flattens a table into
    one block and the splitter quotes across cells. That is counted and shown, never silently dropped.
    """
    if not claim_text.strip():
        return None
    if not (hit := _find_collapsed(answer, claim_text)):
        return None
    return hit


def _find_collapsed(answer: str, needle: str) -> tuple[int, int] | None:
    """Find `needle` in `answer` comparing whitespace-collapsed, case-folded text, but return real offsets."""
    flat: list[str] = []
    index: list[int] = []
    previous_space = True
    for i, ch in enumerate(answer):
        if ch.isspace():
            if previous_space:
                continue
            flat.append(" ")
            index.append(i)
            previous_space = True
        else:
            flat.append(ch.casefold())
            index.append(i)
            previous_space = False

    hay = "".join(flat)
    pin = normalise_for_span(needle)
    if not pin:
        return None

    at = hay.find(pin)
    if at < 0:
        return None
    start = index[at]
    end_char = index[min(at + len(pin) - 1, len(index) - 1)]
    return start, end_char + 1


def claim_state(rows: list[dict], has_citation: bool) -> str:
    """The single label shown against a claim, derived from its per-source rows.

    A voided verdict is not a weaker verdict, it is no verdict, so it contributes nothing here and the claim
    falls to COULD_NOT_VERIFY if nothing else stands.
    """
    if not has_citation:
        return NOT_CHECKED

    standing = [r for r in rows if not r["voided"] and r["verdict"]]
    if not standing:
        return COULD_NOT_VERIFY

    supportive = {SUPPORTED, PARTIALLY_SUPPORTED}
    yes = [r for r in standing if r["verdict"] in supportive]
    no = [r for r in standing if r["verdict"] not in supportive]

    if yes and no:
        return MIXED
    if yes:
        return SUPPORTED_STATE
    return NOT_SUPPORTED


@dataclass
class Report:
    payload: dict[str, Any]

    def to_json(self) -> str:
        return json.dumps(self.payload, indent=2, ensure_ascii=False)

    def to_html(self) -> str:
        return _page(self.payload)

    def save(self, path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_html(), encoding="utf-8")
        return path


def build(capture, records, claim_set, judgements, drifts=None, split_sha256="") -> Report:
    """Assemble everything the view needs, with every state already decided."""
    by_url = {r.url: r for r in records}
    drift_by_url = {d.url: d for d in (drifts or [])}
    judged: dict[str, list] = {}
    for j in judgements or []:
        judged.setdefault(j.claim_id, []).append(j)

    claims = []
    unlocatable = 0
    for claim in claim_set.claims:
        rows = []
        for url in claim.urls:
            record = by_url.get(url)
            match = next((j for j in judged.get(claim.id, []) if j.url == url), None)
            drift = drift_by_url.get(url)
            rows.append(
                {
                    "url": url,
                    "source_code": record.code if record else "",
                    "source_detail": record.detail if record else "",
                    "verdict": match.verdict if match else "",
                    "span": match.span if match else "",
                    "voided": bool(match.voided) if match else False,
                    "void_reason": match.void_reason if match else "",
                    # None means no archived snapshot, and stays None: unknown is not the same as fine.
                    "span_predates_generation": match.span_predates_generation if match else None,
                    "drift": drift.status if drift else "",
                    "judged": match is not None,
                }
            )

        where = locate(capture.answer_text, claim.text)
        if where is None and claim.text.strip():
            unlocatable += 1

        claims.append(
            {
                "id": claim.id,
                "text": claim.text,
                "markers": claim.markers,
                "start": where[0] if where else None,
                "end": where[1] if where else None,
                "state": claim_state(rows, has_citation=bool(claim.urls)),
                "sources": rows,
            }
        )

    counts: dict[str, int] = {}
    for c in claims:
        counts[c["state"]] = counts.get(c["state"], 0) + 1

    return Report(
        {
            "generated_by": "SaysWho",
            "answer": capture.answer_text,
            "meta": {
                "product": capture.product,
                "query_id": capture.query_id,
                "generated_at": capture.generated_at,
                "captured_at": capture.captured_at,
                "answer_sha256": capture.answer_sha256,
                "split_sha256": split_sha256,
                "adapter": capture.adapter,
                "adapter_verified": capture.adapter_verified,
                "extension_version": capture.extension_version,
                "capture_is_known_incomplete": capture.capture_is_known_incomplete,
            },
            "claims": claims,
            "skipped": [s.to_dict() for s in claim_set.skipped],
            "counts": {
                "claims": len(claims),
                "skipped": len(claim_set.skipped),
                "unlocatable": unlocatable,
                "sources": len(records),
                "sources_auditable": sum(1 for r in records if r.auditable),
                "states": counts,
            },
            "sources": [
                {
                    "url": r.url,
                    "code": r.code,
                    "detail": r.detail,
                    "text_length": r.text_length,
                    "extraction_thin": r.extraction_thin,
                }
                for r in records
            ],
            # Gate G4. The view states this rather than leaving a reader to wonder why there is no headline
            # percentage, because an absent number invites the reader to compute one.
            "no_aggregate_rate": (
                "No support rate is shown. Gate G4: there is no gold set for this judge and prompt version, "
                "so per-claim verdicts are all this run is entitled to report."
            ),
            "labels": STATE_LABELS,
            "help": STATE_HELP,
        }
    )


_ASSETS = Path(__file__).resolve().parent.parent / "extension" / "src"


def _asset(name: str) -> str:
    """Read a renderer asset. The same files the extension loads, so the two views cannot drift apart."""
    return (_ASSETS / name).read_text(encoding="utf-8")


def _page(payload: dict) -> str:
    """A standalone report: no network, no build step, opens in any browser."""
    title = f"SaysWho: {html.escape(str(payload['meta'].get('product', '')))} answer"
    # </script> inside the JSON would close the tag early. The payload contains fetched page spans, so this
    # is a real possibility rather than a theoretical one.
    data = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
{_asset("render.css")}
</style>
</head>
<body>
<div id="sayswho-report"></div>
<script>
{_asset("render.js")}
</script>
<script>
window.saysWhoRender(document.getElementById("sayswho-report"), {data});
</script>
</body>
</html>
"""


def strip_for_gate_check(payload: dict) -> dict:
    """The payload with quoted spans removed, for the no-confidence-number gate.

    A fetched span can contain the word "score" in ordinary prose, and the gate walks keys rather than
    values, so this exists for tests that walk the whole structure.
    """
    clone = json.loads(json.dumps(payload))
    # Tolerant of both shapes it gets handed: the report payload, whose `claims` is a list, and the CLI's
    # run record, whose `claims` is the ClaimSet dict. Raising here would mean the gate is skipped in
    # whichever surface got the shape wrong, which is the opposite of what a gate is for.
    claims = clone.get("claims")
    if isinstance(claims, dict):
        claims = claims.get("claims", [])
    for claim in claims or []:
        for row in (claim.get("sources") or []) if isinstance(claim, dict) else []:
            row.pop("span", None)
    return clone
