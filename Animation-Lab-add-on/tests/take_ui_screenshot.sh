#!/usr/bin/env bash
# Manual UI check: installs the add-on into a throwaway Blender user folder, opens Blender
# with a window, shows the Animation Lab tab, saves a screenshot and quits. A Blender
# window appears for a few seconds. Your own Blender settings are not touched.
#
#   tests/take_ui_screenshot.sh screenshot.png            # the browser as it opens
#   tests/take_ui_screenshot.sh screenshot.png "walk"     # with a search
#   tests/take_ui_screenshot.sh screenshot.png "walk" apply  # also import the rig and apply Walk
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ADDON_ROOT="$(cd "$HERE/.." && pwd)"
OUT="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
SEARCH="${2:-}"
MODE="${3:-}"

if [[ -n "${BLENDER:-}" ]]; then
  BLENDER_BIN="$BLENDER"
elif command -v blender >/dev/null 2>&1; then
  BLENDER_BIN="$(command -v blender)"
else
  BLENDER_BIN="/Applications/Blender.app/Contents/MacOS/Blender"
fi
export BLENDER="$BLENDER_BIN"

SKIP_LIBRARY_BUILD="${SKIP_LIBRARY_BUILD:-1}" "$ADDON_ROOT/tools/package_addon.sh" >/dev/null
ZIP="$(ls -t "$ADDON_ROOT"/dist/animation_lab-*.zip | head -n 1)"

USER_FOLDER="$(mktemp -d -t animation-lab-ui)"
trap 'rm -rf "$USER_FOLDER"' EXIT
export BLENDER_USER_RESOURCES="$USER_FOLDER"

"$BLENDER_BIN" --command extension install-file --repo user_default --enable "$ZIP" >/dev/null
# watchdog: Blender is stopped after 120 s whatever happens (macOS has no `timeout`)
perl -e 'alarm 120; exec @ARGV' "$BLENDER_BIN" --python "$HERE/ui_screenshot.py" -- "$OUT" "$SEARCH" "$MODE" 2>&1 | grep -E "SCREENSHOT|FAILED|Error|Traceback|line [0-9]" || true
