#!/usr/bin/env bash
# Runs the Animation Lab tests inside Blender (headless).
#
#   tests/run_tests.sh
#
# Blender is found from $BLENDER, then `blender` on the PATH, then the default macOS location.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

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

"$BLENDER_BIN" -b --factory-startup --python-exit-code 1 --python "$HERE/test_library.py"
