#!/usr/bin/env bash
# Builds the Animation Lab library (.blend files + catalog.json) from the Mesh2Motion web app.
#
#   tools/build_library/build.sh            # all skeletons
#   tools/build_library/build.sh human,fox  # only these
#
# Blender is found from $BLENDER, then `blender` on the PATH, then the default macOS location.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ADDON_ROOT="$(cd "$HERE/../.." && pwd)"
STATIC_DIR="$(cd "$ADDON_ROOT/../mesh2motion-app/static" && pwd)"
OUT_DIR="$ADDON_ROOT/animation_lab/library"

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

"$BLENDER_BIN" -b --factory-startup --python-exit-code 1 \
  --python "$HERE/build_library.py" -- \
  --static "$STATIC_DIR" --out "$OUT_DIR" --only "${1:-}"
