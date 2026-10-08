#!/usr/bin/env bash
# Builds the installable Animation Lab add-on: dist/animation_lab-<version>.zip
#
#   tools/package_addon.sh                          # build the library, then the zip
#   SKIP_LIBRARY_BUILD=1 tools/package_addon.sh     # reuse the library already built
#
# Uses Blender's own extension tools to build and validate the zip. Blender is found from
# $BLENDER, then `blender` on the PATH, then the default macOS location.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ADDON_ROOT="$(cd "$HERE/.." && pwd)"
SOURCE_DIR="$ADDON_ROOT/animation_lab"
DIST_DIR="$ADDON_ROOT/dist"

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

if [[ "${SKIP_LIBRARY_BUILD:-0}" != "1" ]]; then
  "$HERE/build_library/build.sh"
fi

if [[ ! -f "$SOURCE_DIR/library/catalog.json" ]]; then
  echo "The library is missing. Run tools/build_library/build.sh first." >&2
  exit 1
fi

VERSION="$(sed -n 's/^version = "\(.*\)"/\1/p' "$SOURCE_DIR/blender_manifest.toml")"
ZIP="$DIST_DIR/animation_lab-$VERSION.zip"
mkdir -p "$DIST_DIR"
rm -f "$ZIP"

"$BLENDER_BIN" --factory-startup --command extension build --source-dir "$SOURCE_DIR" --output-dir "$DIST_DIR"
"$BLENDER_BIN" --factory-startup --command extension validate "$ZIP"

echo "Add-on: $ZIP ($(du -h "$ZIP" | cut -f1))"
