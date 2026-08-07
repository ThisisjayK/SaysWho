"""Append-only fetch cache.

DATA_CONTRACT.md §7: every response is written to disk before anything reads it, a rerun reads the cache
instead of re-requesting, and nothing overwrites a fetch that already happened.

The append-only part is the one that matters. If a refetch could replace an earlier record, a rerun could
quietly audit different bytes than the run being reported, and the verdicts would stop being reproducible
without anything looking wrong.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .records import sha256


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class FetchCache:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _dir(self, url: str) -> Path:
        return self.root / sha256(url)[:16]

    def put(self, url: str, status: int, headers: dict, body: bytes, fetched_at: str | None = None) -> dict:
        """Record one fetch. Never overwrites an earlier one."""
        fetched_at = fetched_at or now_iso()
        d = self._dir(url)
        d.mkdir(parents=True, exist_ok=True)

        stamp = fetched_at.replace(":", "").replace("-", "")
        body_path = d / f"{stamp}.body"
        meta_path = d / f"{stamp}.json"

        if meta_path.exists():
            # Same URL twice within one second. Keep both rather than clobbering.
            n = 1
            while (d / f"{stamp}-{n}.json").exists():
                n += 1
            body_path = d / f"{stamp}-{n}.body"
            meta_path = d / f"{stamp}-{n}.json"

        body_path.write_bytes(body)
        meta = {
            "url": url,
            "status": status,
            "headers": {k.lower(): v for k, v in headers.items()},
            "fetched_at": fetched_at,
            "content_sha256": sha256(body),
            "body_file": body_path.name,
            "body_bytes": len(body),
        }
        meta_path.write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n")
        return meta

    def latest(self, url: str) -> tuple[dict, bytes] | None:
        """Most recent cached fetch for this URL, or None."""
        d = self._dir(url)
        if not d.is_dir():
            return None
        metas = sorted(d.glob("*.json"))
        if not metas:
            return None
        meta = json.loads(metas[-1].read_text())
        body = (d / meta["body_file"]).read_bytes()
        return meta, body

    def count(self, url: str) -> int:
        d = self._dir(url)
        return len(list(d.glob("*.json"))) if d.is_dir() else 0
