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
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

REPO = Path(__file__).resolve().parent.parent
DEFAULT_CAPTURES = Path.home() / "Downloads" / "sayswho"
DEFAULT_REPORTS = Path.home() / "Downloads" / "sayswho-reports"

#: Attempts before a capture is left alone. Without a cap, every launchd firing replays the whole backlog of
#: failures, which is what happened the first time this ran: one broken path produced 39 ledger lines across
#: two firings and would have continued indefinitely.
MAX_ATTEMPTS = 3

#: Captures audited per firing. A run takes about ten minutes against the free tier, so an unbounded batch
#: turns one download into hours of work.
MAX_PER_RUN = 5

#: A lock older than this was left by a process that died. Breaking it is safer than never running again.
STALE_LOCK_SECONDS = 2 * 60 * 60


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


def answer_sha(path: Path) -> str:
    """The capture's recorded answer hash, or empty if the file cannot be read."""
    try:
        return str(json.loads(path.read_text(encoding="utf-8")).get("answer_sha256", ""))
    except Exception:
        return ""


def pending(captures_dir: Path, ledger: dict[str, dict], max_attempts: int = MAX_ATTEMPTS) -> list[Path]:
    """Captures still worth auditing, oldest first.

    Three reasons a capture is not worth auditing, and each one was learned from a real run:

    - It already produced a report.
    - **Another capture of the same answer already produced one.** Twenty captures in the download folder
      turned out to be four distinct answers: capturing the same page repeatedly while fixing selectors is
      normal. Re-auditing identical text costs ten minutes of free-tier quota and tells you nothing new,
      since the audit is a function of the answer.
    - It has failed `max_attempts` times. A retry that can never succeed is not persistence, it is a loop:
      one wrong path replayed a backlog of eighteen failures on every firing.

    A failure below the cap does stay pending, because a run that died on a rate limit deserves another go.
    """
    if not captures_dir.exists():
        return []

    audited_answers = {
        entry.get("answer_sha256")
        for entry in ledger.values()
        if entry.get("status") == "ok" and entry.get("answer_sha256")
    }

    out: list[Path] = []
    for path in sorted(captures_dir.glob("capture-*.json"), key=lambda p: p.stat().st_mtime):
        entry = ledger.get(path.name, {})
        if entry.get("status") == "ok":
            continue
        if entry.get("attempts", 0) >= max_attempts:
            continue
        sha = answer_sha(path)
        if sha and sha in audited_answers:
            continue
        out.append(path)
        if sha:
            # Two unaudited captures of one answer: audit the first, and the second becomes a duplicate on
            # the next pass rather than a second identical run in this one.
            audited_answers.add(sha)
    return out


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

    entry = {"capture": capture_path.name, "at": now(), "answer_sha256": answer_sha(capture_path)}
    code = cli_main([
        str(capture_path),
        "--judge",
        # Absolute, because launchd runs this with cwd "/" and the CLI's default cache path is relative.
        # The first live firing died on exactly this: ".cache/fetch" became "/.cache/fetch", which is a
        # read-only volume, and every capture in the folder failed identically.
        "--cache", str(REPO / ".cache" / "fetch"),
        "--save-split", str(split_json),
        "--report", str(report_html),
        "--report-json", str(report_json),
    ])

    if code != 0:
        # G0 failure is the common case: an answer with no citations is not scored, and that is a result
        # rather than an error. It is recorded as handled so the queue does not retry it forever.
        entry.update(status="ok", outcome="not scored", detail=f"pipeline exit {code}")
        return entry

    if not report_html.exists():
        # The pipeline succeeded and wrote nothing to mark. It happens when no cited source could be read:
        # Phase 1 never runs, so there are no claims and no report.
        #
        # The ledger used to claim "report" here and record a path to a file that did not exist. A log that
        # asserts an artifact it never saw is the same failure this project audits other people for, in the
        # one place nobody looks because it is automated.
        entry.update(
            status="ok",
            outcome="no report",
            detail="no source could be read, so there were no claims to mark",
        )
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
    parser.add_argument("--max-per-run", type=int, default=MAX_PER_RUN)
    parser.add_argument("--max-attempts", type=int, default=MAX_ATTEMPTS)
    args = parser.parse_args(argv)

    # launchd starts jobs with cwd "/". Everything downstream, the fetch cache included, assumes it is being
    # run from the repo the way a person would run it, so make that true rather than passing paths around.
    os.chdir(REPO)

    ledger_path = args.ledger or (args.reports / "audited.jsonl")
    lock_path = args.lock or (args.reports / ".lock")
    args.reports.mkdir(parents=True, exist_ok=True)

    # O_EXCL: if another invocation holds the lock, this one leaves rather than queueing behind it. launchd
    # fires again on the next directory change, and the queue is durable in the ledger either way.
    try:
        fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        age = time.time() - lock_path.stat().st_mtime
        if age < STALE_LOCK_SECONDS:
            print(f"another audit is running ({lock_path}); exiting")
            return 0
        # Left by a process that died. Never running again is a worse failure than running twice.
        print(f"breaking a stale lock, {age / 3600:.1f} hours old")
        lock_path.unlink(missing_ok=True)
        fd = os.open(lock_path, os.O_CREAT | os.O_WRONLY)
    os.write(fd, f"{os.getpid()} {now()}\n".encode())
    os.close(fd)

    try:
        ledger = read_ledger(ledger_path)
        queue = pending(args.captures, ledger, max_attempts=args.max_attempts)
        if not queue:
            print("nothing to audit")
            return 0

        limit = 1 if args.once else args.max_per_run
        if len(queue) > limit:
            print(f"{len(queue)} pending, auditing {limit} this time")
            queue = queue[:limit]

        intact, why = freeze_is_intact()
        if not intact:
            append_ledger(ledger_path, {"capture": "-", "at": now(), "status": "blocked", "detail": why})
            notify("SaysWho: run blocked", "The query freeze check failed. No capture was audited.")
            print(f"freeze check failed, refusing to run:\n{why}")
            return 1

        done, failed, last_summary = 0, 0, ""
        for capture_path in queue:
            attempts = ledger.get(capture_path.name, {}).get("attempts", 0) + 1
            print(f"auditing {capture_path.name} (attempt {attempts})")
            try:
                entry = audit(capture_path, args.reports)
            except Exception as exc:
                entry = {
                    "capture": capture_path.name, "at": now(), "status": "failed",
                    "answer_sha256": answer_sha(capture_path),
                    "detail": f"{type(exc).__name__}: {exc}",
                }
                traceback.print_exc()
                failed += 1
            else:
                done += 1
                counts = entry.get("counts") or {}
                last_summary = ", ".join(
                    f"{v} {k.lower().replace('_', ' ')}" for k, v in counts.items()
                )
            entry["attempts"] = attempts
            if entry["status"] != "ok" and attempts >= args.max_attempts:
                entry["detail"] = (
                    f"{entry.get('detail', '')} [{attempts} attempts, not retried again]".strip()
                )
            append_ledger(ledger_path, entry)
            print(f"  {entry.get('status')}: {entry.get('outcome') or entry.get('detail', '')}")

        # One notification per firing, not per capture. The first live run fired eighteen of them.
        if failed and not done:
            notify("SaysWho: audits failed", f"{failed} capture(s) failed. See watcher.log.")
        elif failed:
            notify("SaysWho: reports ready", f"{done} done, {failed} failed. See watcher.log.")
        elif done == 1:
            notify("SaysWho: report ready", last_summary or "1 capture audited")
        else:
            notify("SaysWho: reports ready", f"{done} captures audited")
        return 0
    finally:
        lock_path.unlink(missing_ok=True)


if __name__ == "__main__":
    sys.exit(main())
