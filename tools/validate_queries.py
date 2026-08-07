#!/usr/bin/env python3
"""Schema and policy checks for the query set.

Run before freezing, and again before any capture run. Exits non-zero on any error, so it can gate a run
rather than merely inform one.

Zero dependencies: tomllib is stdlib from Python 3.11.
"""

from __future__ import annotations

import hashlib
import sys
import tomllib
from pathlib import Path

QUERIES_DIR = Path(__file__).resolve().parent.parent / "queries"

STRATUM_KEYS = {"id", "id_prefix", "label", "status", "provenance_policy", "domains"}
QUERY_KEYS_REQUIRED = {"id", "domain", "text", "cost_of_error", "provenance"}
QUERY_KEYS_OPTIONAL = {"scrub_notes", "asked_approx"}

VALID_STATUS = {"draft", "ready"}
VALID_PROVENANCE = {"synthetic", "real_scrubbed"}

# No field in this schema may record what I think a query will produce. A stimulus set that carries its
# author's expectations is one edit away from being a set selected to meet them.
FORBIDDEN_KEY_SUBSTRINGS = (
    "expected",
    "predicted",
    "verdict",
    "gold",
    "score",
    "confidence",
    "hypothesis",
)

MIN_TEXT_CHARS = 25
MIN_COST_CHARS = 60


class Findings:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.notes: list[str] = []

    def error(self, where: str, msg: str) -> None:
        self.errors.append(f"{where}: {msg}")

    def note(self, msg: str) -> None:
        self.notes.append(msg)


def query_hash(q: dict) -> str:
    """Canonical hash of a query's pre-registered content.

    cost_of_error is included deliberately. It is the stated reason the query is in the set, and editing it
    after seeing results would be a quieter form of tuning than swapping the query out.
    """
    canonical = "\n".join(
        [
            q["id"].strip(),
            q["domain"].strip(),
            " ".join(q["text"].split()),
            " ".join(q["cost_of_error"].split()),
        ]
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def load_strata(queries_dir: Path = QUERIES_DIR) -> dict[str, dict]:
    """Load every *.toml in the queries directory. Raises on malformed TOML."""
    strata = {}
    for path in sorted(queries_dir.glob("*.toml")):
        with path.open("rb") as fh:
            strata[path.name] = tomllib.load(fh)
    return strata


def validate(strata: dict[str, dict]) -> Findings:
    f = Findings()
    seen_ids: dict[str, str] = {}

    if not strata:
        f.error("queries/", "no .toml files found")
        return f

    for filename, doc in strata.items():
        stratum = doc.get("stratum")
        if not isinstance(stratum, dict):
            f.error(filename, "missing [stratum] table")
            continue

        missing = STRATUM_KEYS - set(stratum)
        if missing:
            f.error(filename, f"[stratum] missing keys: {sorted(missing)}")
            continue

        if stratum["status"] not in VALID_STATUS:
            f.error(filename, f"status {stratum['status']!r} not in {sorted(VALID_STATUS)}")
        if stratum["provenance_policy"] not in VALID_PROVENANCE:
            f.error(
                filename,
                f"provenance_policy {stratum['provenance_policy']!r} not in {sorted(VALID_PROVENANCE)}",
            )

        prefix = stratum["id_prefix"]
        domains = set(stratum["domains"])
        queries = doc.get("query", [])

        if not queries and stratum["status"] == "ready":
            f.error(filename, "status is 'ready' but the file contains no queries")

        per_domain: dict[str, int] = {d: 0 for d in stratum["domains"]}

        for i, q in enumerate(queries):
            where = f"{filename}[{q.get('id', f'#{i}')}]"

            for key in q:
                lowered = key.lower()
                for bad in FORBIDDEN_KEY_SUBSTRINGS:
                    if bad in lowered:
                        f.error(where, f"forbidden key {key!r} (contains {bad!r})")

            missing = QUERY_KEYS_REQUIRED - set(q)
            if missing:
                f.error(where, f"missing required keys: {sorted(missing)}")
                continue

            unknown = set(q) - QUERY_KEYS_REQUIRED - QUERY_KEYS_OPTIONAL
            if unknown:
                f.error(where, f"unknown keys: {sorted(unknown)}")

            qid = q["id"]
            if qid in seen_ids:
                f.error(where, f"duplicate id, already used in {seen_ids[qid]}")
            seen_ids[qid] = filename

            if not qid.startswith(prefix + "-"):
                f.error(where, f"id must start with {prefix!r}-")

            if q["domain"] not in domains:
                f.error(where, f"domain {q['domain']!r} not in stratum domains {sorted(domains)}")
            else:
                per_domain[q["domain"]] += 1

            text = " ".join(q["text"].split())
            if len(text) < MIN_TEXT_CHARS:
                f.error(where, f"text is {len(text)} chars, minimum {MIN_TEXT_CHARS}")

            cost = " ".join(q["cost_of_error"].split())
            if len(cost) < MIN_COST_CHARS:
                f.error(
                    where,
                    f"cost_of_error is {len(cost)} chars, minimum {MIN_COST_CHARS}. "
                    "§10 requires a real statement of what a wrong answer costs the asker",
                )

            prov = q["provenance"]
            if prov not in VALID_PROVENANCE:
                f.error(where, f"provenance {prov!r} not in {sorted(VALID_PROVENANCE)}")
            elif prov != stratum["provenance_policy"]:
                f.error(
                    where,
                    f"provenance {prov!r} contradicts the stratum policy "
                    f"{stratum['provenance_policy']!r}",
                )

            if prov == "real_scrubbed":
                if not q.get("scrub_notes", "").strip():
                    f.error(where, "real_scrubbed requires non-empty scrub_notes")
                if not q.get("asked_approx", "").strip():
                    f.error(where, "real_scrubbed requires asked_approx")
            else:
                if q.get("scrub_notes"):
                    f.error(where, "synthetic queries must not carry scrub_notes")

        empty = [d for d, n in per_domain.items() if n == 0]
        if empty and stratum["status"] == "ready":
            f.note(
                f"{filename}: declared domains with no queries: {sorted(empty)}. "
                "An empty domain is reportable, not an error, but it must be reported."
            )

        counts = ", ".join(f"{d}={per_domain[d]}" for d in stratum["domains"])
        f.note(f"{filename}: {stratum['status']:>5}  n={len(queries):<3} {counts}")

    return f


def main() -> int:
    try:
        strata = load_strata()
    except tomllib.TOMLDecodeError as exc:
        print(f"FAIL  malformed TOML: {exc}", file=sys.stderr)
        return 2

    f = validate(strata)

    for note in f.notes:
        print(f"  {note}")

    if f.errors:
        print()
        for err in f.errors:
            print(f"FAIL  {err}", file=sys.stderr)
        print(f"\n{len(f.errors)} error(s).", file=sys.stderr)
        return 1

    total = sum(len(doc.get("query", [])) for doc in strata.values())
    print(f"\nOK  {len(strata)} stratum file(s), {total} queries, schema and policy checks pass.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
