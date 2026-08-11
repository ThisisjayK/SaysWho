"""The frozen query set, and the binding between a capture and the query that produced it.

Two jobs, both refusals.

**The freeze check, run from inside the pipeline rather than beside it.** `CLAUDE.md` requires
`tools/freeze_queries.py check` to pass before any capture run. The watcher already enforced it; the
interactive path did not, which meant the one path a person uses by hand was the one path with no gate on
it. The check is shelled out to the existing tool rather than reimplemented, because a second implementation
of "has the query set moved" could disagree with the first and the disagreement would favour whichever one
was more convenient.

**The binding.** Every capture so far carried `query_id: "UNASSIGNED"`, so a verdict could not be traced
back to the question that produced it. An unbound capture is fine to audit and is not fine to publish a
rate from: a rate over "some answers I happened to capture" is a different measurement from a rate over a
frozen stratum, and nothing in the output distinguished them. `binding` returns the reason, and the harness
refuses.
"""

from __future__ import annotations

import subprocess
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
QUERIES_DIR = REPO / "queries"
MANIFEST = QUERIES_DIR / "FREEZE.json"

#: What the extension stamps on a capture before anybody has said which query it answers.
UNASSIGNED = "UNASSIGNED"

#: Binding failure codes. Distinct because they need different actions: bind it, freeze the stratum, or
#: find out where a capture carrying an unknown id came from.
CAPTURE_UNBOUND = "CAPTURE_UNBOUND"
QUERY_NOT_FROZEN = "QUERY_NOT_FROZEN"
QUERY_UNKNOWN = "QUERY_UNKNOWN"


@dataclass(frozen=True)
class Binding:
    ok: bool
    code: str = ""
    detail: str = ""


def freeze_intact(timeout: float = 60) -> tuple[bool, str]:
    """True when the query set on disk still matches what was frozen.

    Shells out to `tools/freeze_queries.py check`, which is the one implementation of this question.
    """
    try:
        done = subprocess.run(
            [sys.executable, str(REPO / "tools" / "freeze_queries.py"), "check"],
            capture_output=True, text=True, timeout=timeout, cwd=REPO,
        )
    except Exception as exc:
        return False, f"freeze check could not run: {exc}"
    if done.returncode != 0:
        return False, (done.stdout + done.stderr).strip()
    return True, ""


def load_strata(queries_dir: Path | None = None) -> dict[str, dict]:
    # Resolved at call time rather than bound as a default argument. A default is evaluated once, when the
    # module is imported, which makes the paths untestable and makes any later reconfiguration silently
    # ineffective: the call would keep reading the original directory and report happily on it.
    queries_dir = queries_dir or QUERIES_DIR
    out: dict[str, dict] = {}
    for path in sorted(queries_dir.glob("*.toml")):
        with open(path, "rb") as fh:
            out[path.name] = tomllib.load(fh)
    return out


def frozen_query_ids(queries_dir: Path | None = None, manifest_path: Path | None = None) -> set[str]:
    """Ids that are both present on disk and recorded in the freeze manifest.

    The intersection rather than either side alone. An id in the manifest and missing from disk is a
    tampered set, which `freeze_queries.py check` is what catches; an id on disk and missing from the
    manifest is a query added after the freeze, which is the same thing from the other direction. Neither
    should bind a capture.
    """
    import json

    queries_dir = queries_dir or QUERIES_DIR
    manifest_path = manifest_path or MANIFEST
    if not manifest_path.exists():
        return set()
    manifest = json.loads(manifest_path.read_text())
    strata = load_strata(queries_dir)

    ids: set[str] = set()
    for filename, entry in manifest.get("frozen", {}).items():
        doc = strata.get(filename)
        if doc is None:
            continue
        on_disk = {q["id"] for q in doc.get("query", [])}
        ids |= on_disk & set(entry.get("query_hashes", {}))
    return ids


def all_query_ids(queries_dir: Path | None = None) -> set[str]:
    """Every id on disk, frozen or not. Used only to tell "not frozen" from "does not exist"."""
    return {
        q["id"]
        for doc in load_strata(queries_dir).values()
        for q in doc.get("query", [])
    }


def binding(capture, queries_dir: Path | None = None, manifest_path: Path | None = None) -> Binding:
    """Whether this capture can be traced back to a frozen query.

    Not a gate on auditing. A capture with no query id can be audited perfectly well and its per-claim
    verdicts are worth exactly what they were worth before. It is a gate on publishing a rate, because a
    rate needs to say what it is a rate over.
    """
    qid = (capture.query_id or "").strip()
    if not qid or qid == UNASSIGNED:
        return Binding(
            False, CAPTURE_UNBOUND,
            "this capture is not bound to a query. Per-claim verdicts stand; no rate may be published from "
            "it, because a rate has to say what it is a rate over. Bind it with tools/bind_capture.py",
        )

    frozen = frozen_query_ids(queries_dir, manifest_path)
    if qid in frozen:
        return Binding(True)

    if qid in all_query_ids(queries_dir):
        return Binding(
            False, QUERY_NOT_FROZEN,
            f"{qid} exists on disk and is not in the freeze manifest, so it was added after the freeze or "
            "its stratum was never frozen. A rate over it would be a rate over a set that can still move",
        )

    return Binding(
        False, QUERY_UNKNOWN,
        f"{qid} is not a query in this repo. Either the capture came from somewhere else or the id was "
        "typed by hand",
    )


def query_text(qid: str, queries_dir: Path | None = None) -> str:
    for doc in load_strata(queries_dir).values():
        for q in doc.get("query", []):
            if q["id"] == qid:
                return q.get("text", "").strip()
    return ""


def stratum_of(qid: str, queries_dir: Path | None = None) -> str:
    for doc in load_strata(queries_dir).values():
        for q in doc.get("query", []):
            if q["id"] == qid:
                return doc.get("stratum", {}).get("id", "")
    return ""
