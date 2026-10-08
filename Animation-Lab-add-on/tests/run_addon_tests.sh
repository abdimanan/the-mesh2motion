#!/usr/bin/env bash
# Packages the add-on, installs the zip into a throwaway Blender user folder and runs
# tests/test_addon.py against the installed copy. Your own Blender settings and add-ons are
# never touched.
#
#   tests/run_addon_tests.sh
#   SKIP_LIBRARY_BUILD=1 tests/run_addon_tests.sh   # reuse the library already built
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ADDON_ROOT="$(cd "$HERE/.." && pwd)"

if [[ -n "${BLENDER:-}" ]]; then
  BLENDER_BIN="$BLENDER"
elif command -v blender >/dev/null 2>&1; then
  BLENDER_BIN="$(command -v blender)"
elif [[ -x "/Applications/Blender.app/Contents/MacOS/Blender" ]]; then
  BLENDER_BIN="/Applications/Blender.app/Contents/MacOS/Blender"
else
  echo "Blender not found. Set BLENDER=/path/to/blender" >&2
  exit 1
fi
export BLENDER="$BLENDER_BIN"

"$ADDON_ROOT/tools/package_addon.sh"
ZIP="$(ls -t "$ADDON_ROOT"/dist/animation_lab-*.zip | head -n 1)"

USER_FOLDER="$(mktemp -d -t animation-lab-test-user)"
trap 'rm -rf "$USER_FOLDER"' EXIT
export BLENDER_USER_RESOURCES="$USER_FOLDER"

"$BLENDER_BIN" --command extension install-file --repo user_default --enable "$ZIP"
"$BLENDER_BIN" -b --python-exit-code 1 --python "$HERE/test_addon.py"
