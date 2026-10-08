"""What the user picked in the Animation Lab panel. Lives on the window manager, so it is
not saved into the user's .blend files."""

import bpy
from bpy.props import EnumProperty, PointerProperty
from bpy.types import PropertyGroup

from . import library

ALL_CATEGORIES = "ALL"

# Blender only keeps the strings of dynamic enum items alive while Python does, so the
# item lists returned to it are kept here
_skeleton_items = []
_category_items = []


def skeleton_items(_self, _context):
    _skeleton_items.clear()
    for index, entry in enumerate(library.skeletons()):
        _skeleton_items.append((entry["key"], entry["display_name"], f"{entry['animations']} animations", index))
    if not _skeleton_items:
        _skeleton_items.append(("NONE", "No library", "The animation library is not built", 0))
    return _skeleton_items


def category_items(self, _context):
    _category_items.clear()
    total = len(library.animations(self.skeleton))
    _category_items.append((ALL_CATEGORIES, f"All categories ({total})", "Every animation of this skeleton", 0))
    for index, (category, count) in enumerate(library.categories(self.skeleton), start=1):
        _category_items.append((category, f"{category} ({count})", f"{count} {category} animations", index))
    return _category_items


def on_skeleton_changed(self, _context):
    # the categories differ per skeleton
    self.category = ALL_CATEGORIES


class ANIMLAB_PG_state(PropertyGroup):
    skeleton: EnumProperty(
        name="Skeleton",
        description="Which Mesh2Motion skeleton's animations to show",
        items=skeleton_items,
        update=on_skeleton_changed,
    )
    category: EnumProperty(
        name="Category",
        description="Only show animations of this kind",
        items=category_items,
    )


def register():
    bpy.utils.register_class(ANIMLAB_PG_state)
    bpy.types.WindowManager.animation_lab = PointerProperty(type=ANIMLAB_PG_state)


def unregister():
    del bpy.types.WindowManager.animation_lab
    bpy.utils.unregister_class(ANIMLAB_PG_state)
