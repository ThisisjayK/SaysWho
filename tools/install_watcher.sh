#!/bin/zsh
# Install (or remove) the launchd agent that audits new captures.
#
#     tools/install_watcher.sh            install and start watching
#     tools/install_watcher.sh --uninstall
#
# WatchPaths, not a timer and not a daemon. launchd starts the job when ~/Downloads/sayswho changes and the
# job exits when its queue is empty, so nothing of this project is resident between captures.
#
# The plist is generated here rather than committed, because it has to carry absolute paths for this machine
# and a committed one would be wrong on any other. It contains no key and no secret: see run_watcher.sh.

set -eu

LABEL="com.sayswho.watch"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
REPO="$(cd "$(dirname "$0")/.." && pwd)"
CAPTURES="$HOME/Downloads/sayswho"
REPORTS="$HOME/Downloads/sayswho-reports"

if [[ "${1:-}" == "--uninstall" ]]; then
  launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || launchctl unload "$PLIST" 2>/dev/null || true
  rm -f "$PLIST"
  echo "removed $LABEL. Nothing of it remains loaded."
  exit 0
fi

mkdir -p "$CAPTURES" "$REPORTS" "$HOME/Library/LaunchAgents"
chmod +x "$REPO/tools/run_watcher.sh"

cat > "$PLIST" <<PLIST_END
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>$LABEL</string>

  <key>ProgramArguments</key>
  <array>
    <string>$REPO/tools/run_watcher.sh</string>
    <string>--captures</string>
    <string>$CAPTURES</string>
    <string>--reports</string>
    <string>$REPORTS</string>
  </array>

  <!-- The whole point: start on a change to this directory, then exit. No timer, no resident process. -->
  <key>WatchPaths</key>
  <array>
    <string>$CAPTURES</string>
  </array>

  <!-- Chrome writes a .crdownload first and renames it, so a single capture touches the directory more than
       once. The lock in watch_captures.py makes a duplicate launch exit immediately; this just makes them
       rarer. -->
  <key>ThrottleInterval</key>
  <integer>30</integer>

  <key>RunAtLoad</key>
  <false/>

  <key>StandardOutPath</key>
  <string>$REPORTS/watcher.log</string>
  <key>StandardErrorPath</key>
  <string>$REPORTS/watcher.log</string>
</dict>
</plist>
PLIST_END

launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"

echo "installed $LABEL"
echo "  watching  $CAPTURES"
echo "  reports   $REPORTS"
echo "  log       $REPORTS/watcher.log"
echo
echo "Capture an answer in the browser and a report appears in the reports directory."
echo "Remove it with: tools/install_watcher.sh --uninstall"
