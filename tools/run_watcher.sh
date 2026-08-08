#!/bin/zsh
# What launchd actually executes.
#
# It exists for one reason: launchd does not source your shell profile, and the judge key lives in
# ~/.zshrc. Putting the key in the launchd plist instead would write it to disk inside a file this project
# created, which DATA_CONTRACT.md §8 rules out. So the key stays exactly where you already put it, and this
# script reads it the same way an interactive shell would.
#
# Output goes to the log launchd is configured with, so a failed run leaves a trace rather than vanishing.

set -u

REPO="$(cd "$(dirname "$0")/.." && pwd)"

# Interactive-shell config, sourced deliberately. Failures here are not fatal: a missing key produces a
# clear error from the pipeline, which is more useful than this script exiting with nothing said.
[[ -f "$HOME/.zshrc" ]] && source "$HOME/.zshrc" >/dev/null 2>&1

PYTHON="$REPO/.venv/bin/python"
[[ -x "$PYTHON" ]] || PYTHON="$(command -v python3)"

echo "--- $(date -u +%Y-%m-%dT%H:%M:%SZ) watcher starting"

# -u because this log is the only window into a run nobody is watching. Python block-buffers stdout when it
# is a file, so without this the log stays empty for the ten minutes the run takes and then arrives all at
# once, which is exactly when you would want to look at it.
exec "$PYTHON" -u "$REPO/tools/watch_captures.py" "$@"
