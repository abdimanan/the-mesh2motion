"""Thumbnail icons for the UI, loaded from the library's PNGs the first time they are shown."""

import os

import bpy.utils.previews

_collection = None


def register():
    global _collection
    _collection = bpy.utils.previews.new()


def unregister():
    global _collection
    if _collection is not None:
        bpy.utils.previews.remove(_collection)
        _collection = None


def clear():
    """Forget loaded icons, for example after the library was rebuilt."""
    if _collection is not None:
        _collection.clear()


def icon_id(path):
    """Icon id for an image file, or 0 when there is no such file."""
    if _collection is None or not path or not os.path.isfile(path):
        return 0
    if path not in _collection:
        _collection.load(path, path, "IMAGE")
    return _collection[path].icon_id
