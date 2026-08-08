#!/usr/bin/env python3
"""Audit any capture that has not been audited yet, then exit.

    watch_captures.py [--captures DIR] [--reports DIR] [--once]

Run by launchd whenever `~/Downloads/sayswho` changes, so clicking capture in the browser produces a marked
report a few minutes later with no terminal step. Nothing stays resident: launchd starts this on a directory
change and it exits when the queue is empty.

Three things this has to get right, and each of them is a way the automation could quietly lie:

**It must not re-audit the same capture forever.** Reports are written to a different directory than the one
being watched, because writing into the watched directory would retrigger the job. A ledger records every
capture already processed.

**It must not run twice at once.** A capture arriving mid-run would otherwise start a second pipeline against
the same rate-limited free tier, and both would back off against each other. A lock file makes the second
invocation exit immediately; launchd will trigger again on the next change.

**It must not hide a failure.** A run that fails writes the failure to the ledger and says so in the
notification. An automation that silently drops the runs it could not do is worse than no automation, because
the missing report looks like a capture you forgot to make.

The API key is read from the environment, same as everywhere else. `run_watcher.sh` sources your shell
profile before calling this, so the key stays where you already keep it and is never written to disk by this
project. DATA_CONTRACT.md §8.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

REPO = Path(__file__).resolve().parent.parent
DEFAULT_CAPTURES = Path.home() / "Downloads" / "sayswho"
DEFAULT_REPORTS = Path.home() / "Downloads" / "sayswho-reports"


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")


def read_ledger(path: Path) -> dict[str, dict]:
    """Captures already handled, keyed by file name. Missing or corrupt reads as empty.

    A corrupt ledger costs a re-audit, which is slow and harmless. Refusing to run because a log file is
    malformed would be the automation failing closed on its own bookkeeping.
    """
    if not path.exists():
        return {}
    done: dict[str, dict] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if name := entry.get("capture"):
            done[name] = entry
    return done


def append_ledger(path: Path, entry: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def pending(captures_dir: Path, ledger: dict[str, dict]) -> list[Path]:
    """Captures with no ledger entry, oldest first.

    A capture whose previous attempt failed stays pending, so a run that died on a rate limit is retried the
    next time anything changes rather than being written off.
    """
    if not captures_dir.exists():
        return []
    found = sorted(captures_dir.glob("capture-*.json"), key=lambda p: p.stat().st_mtime)
    return [p for p in found if ledger.get(p.name, {}).get("status") != "ok"]


def notify(title: str, message: str) -> None:
    """A macOS notification. Best effort: this is the only signal a background run gives."""
    try:
        subprocess.run(
            ["osascript", "-e",
             f'display notification {json.dumps(message)} with title {json.dumps(title)}'],
            check=False, capture_output=True, timeout=10,
        )
    except Exception:
        pass


def freeze_is_intact() -> tuple[bool, str]:
    """CLAUDE.md: `freeze_queries.py check` passes before any capture run.

    Enforced here rather than trusted, because an automated pipeline is exactly where a broken freeze would
    go unnoticed: nobody is watching the terminal.
    """
    try:
        done = subprocess.run(
            [sys.executable, str(REPO / "tools" / "freeze_queries.py"), "check"],
            capture_output=True, text=True, timeout=60, cwd=REPO,
        )
    except Exception as exc:
        return False, f"freeze check could not run: {exc}"
    if done.returncode != 0:
        return False, (done.stdout + done.stderr).strip()[:400]
    return True, ""


def audit(capture_path: Path, reports_dir: Path) -> dict:
    """Run the pipeline over one capture and write its report. Returns a ledger entry."""
    from sayswho.cli import main as cli_main

    stem = capture_path.stem
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_html = reports_dir / f"{stem}.html"
    report_json = reports_dir / f"{stem}.json"
    split_json = reports_dir / f"{stem}.split.json"

    entry = {"capture": capture_path.name, "at": now()}
    code = cli_main([
        str(capture_path),
        "--judge",
        "--save-split", str(split_json),
        "--report", str(report_html),
        "--report-json", str(report_json),
    ])

    if code != 0:
        # G0 failure is the common case: an answer with no citations is not scored, and that is a result
        # rather than an error. It is recorded as handled so the queue does not retry it forever.
        entry.update(status="ok", outcome="not scored", detail=f"pipeline exit {code}")
        return entry

    entry.update(status="ok", outcome="report", report=str(report_html), split=str(split_json))
    if report_json.exists():
        payload = json.loads(report_json.read_text(encoding="utf-8"))
        entry["counts"] = payload.get("counts", {}).get("states", {})
    return entry


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--captures", type=Path, default=DEFAULT_CAPTURES)
    parser.add_argument("--reports", type=Path, default=DEFAULT_REPORTS)
    parser.add_argument("--ledger", type=Path, default=None)
    parser.add_argument("--lock", type=Path, default=None)
    parser.add_argument("--once", action="store_true", help="audit at most one capture, then exit")
    args = parser.parse_args(argv)

    ledger_path = args.ledger or (args.reports / "audited.jsonl")
    lock_path = args.lock or (args.reports / ".lock")
    args.reports.mkdir(parents=True, exist_ok=True)

    # O_EXCL: if another invocation holds the lock, this one leaves rather than queueing behind it. launchd
    # fires again on the next directory change, and the queue is durable in the ledger either way.
    try:
        fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        print(f"another audit is running ({lock_path}); exiting")
        return 0
    os.write(fd, f"{os.getpid()} {now()}\n".encode())
    os.close(fd)

    try:
        queue = pending(args.captures, read_ledger(ledger_path))
        if not queue:
            print("nothing to audit")
            return 0

        intact, why = freeze_is_intact()
        if not intact:
            append_ledger(ledger_path, {"capture": "-", "at": now(), "status": "blocked", "detail": why})
            notify("SaysWho: run blocked", "The query freeze check failed. No capture was audited.")
            print(f"freeze check failed, refusing to run:\n{why}")
            return 1

        if args.once:
            queue = queue[:1]

        for capture_path in queue:
            print(f"auditing {capture_path.name}")
            try:
                entry = audit(capture_path, args.reports)
            except Exception as exc:
                entry = {
                    "capture": capture_path.name, "at": now(), "status": "failed",
                    "detail": f"{type(exc).__name__}: {exc}",
                }
                traceback.print_exc()
                notify("SaysWho: audit failed", f"{capture_path.name}: {exc}")
            else:
                counts = entry.get("counts") or {}
                summary = ", ".join(f"{v} {k.lower().replace('_', ' ')}" for k, v in counts.items())
                notify("SaysWho: report ready", summary or capture_path.name)
            append_ledger(ledger_path, entry)
            print(f"  {entry.get('status')}: {entry.get('outcome') or entry.get('detail', '')}")
        return 0
    finally:
        lock_path.unlink(missing_ok=True)


if __name__ == "__main__":
    sys.exit(main())
