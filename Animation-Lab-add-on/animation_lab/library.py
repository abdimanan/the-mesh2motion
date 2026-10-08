"""The bundled animation library: catalog.json, the .blend files and the thumbnails.

Plain Python (no bpy), so it can be tested outside Blender. The catalog is read once and
cached; reload() drops the cache.
"""

import json
import os

LIBRARY_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "library")
CATALOG_FILE = "catalog.json"
SUPPORTED_FORMAT_VERSION = 1

_catalog = None
_load_error = None


def catalog_path():
    return os.path.join(LIBRARY_DIR, CATALOG_FILE)


def reload():
    global _catalog, _load_error
    _catalog = None
    _load_error = None


def catalog():
    """The parsed catalog, or None when the library is missing or unreadable (see load_error())."""
    global _catalog, _load_error
    if _catalog is not None or _load_error is not None:
        return _catalog

    try:
        with open(catalog_path(), encoding="utf-8") as catalog_file:
            data = json.load(catalog_file)
        if data.get("format_version") != SUPPORTED_FORMAT_VERSION:
            raise ValueError(f"catalog format {data.get('format_version')} is not supported")
        _catalog = data
    except FileNotFoundError:
        _load_error = "The animation library is not built. Run tools/build_library/build.sh."
    except (OSError, ValueError) as error:
        _load_error = f"The animation library could not be read: {error}"
    return _catalog


def load_error():
    catalog()
    return _load_error


def is_available():
    return catalog() is not None


def skeletons():
    data = catalog()
    return data["skeletons"] if data else []


def skeleton(key):
    return next((entry for entry in skeletons() if entry["key"] == key), None)


def animations(skeleton_key=None, category=None):
    data = catalog()
    if not data:
        return []
    return [
        entry for entry in data["animations"]
        if (skeleton_key is None or entry["skeleton"] == skeleton_key)
        and (category is None or entry["category"] == category)
    ]


def categories(skeleton_key):
    """(category, number of animations) for a skeleton, most animations first."""
    counts = {}
    for entry in animations(skeleton_key):
        counts[entry["category"]] = counts.get(entry["category"], 0) + 1
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))


def file_path(relative_path):
    """Absolute path of a file inside the library (a .blend or a thumbnail)."""
    return os.path.join(LIBRARY_DIR, relative_path) if relative_path else None
