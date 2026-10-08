"""Animation Lab operators. AL3 has only Reload; importing and applying come in AL5."""

import bpy
from bpy.types import Operator

from . import library, previews


class ANIMLAB_OT_reload_library(Operator):
    """Read the animation library again, for example after rebuilding it"""

    bl_idname = "animation_lab.reload_library"
    bl_label = "Reload Library"
    bl_options = {"INTERNAL"}

    def execute(self, context):
        library.reload()
        previews.clear()

        error = library.load_error()
        if error:
            self.report({"WARNING"}, error)
            return {"CANCELLED"}

        self.report({"INFO"}, f"Animation Lab: {len(library.animations())} animations")
        for area in context.screen.areas if context.screen else []:
            area.tag_redraw()
        return {"FINISHED"}


CLASSES = (ANIMLAB_OT_reload_library,)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
