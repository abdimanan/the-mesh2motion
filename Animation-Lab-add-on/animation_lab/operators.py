"""Animation Lab operators. Importing rigs and applying animations come in AL5."""

import bpy
from bpy.props import IntProperty, StringProperty
from bpy.types import Operator

from . import library, preferences, previews, properties


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


class ANIMLAB_OT_select_animation(Operator):
    """Select this animation"""

    bl_idname = "animation_lab.select_animation"
    bl_label = "Select Animation"
    bl_options = {"INTERNAL"}

    animation_id: StringProperty(name="Animation", options={"SKIP_SAVE"})

    @classmethod
    def description(cls, _context, properties_):
        entry = library.animation(properties_.animation_id)
        if entry is None:
            return cls.__doc__
        return f"{entry['name']}: {entry['category']}, {entry['duration']:.1f} s"

    def execute(self, context):
        if library.animation(self.animation_id) is None:
            self.report({"WARNING"}, f"Unknown animation {self.animation_id!r}")
            return {"CANCELLED"}
        context.window_manager.animation_lab.selected = self.animation_id
        return {"FINISHED"}


class ANIMLAB_OT_change_page(Operator):
    """Show the previous or next page of animations"""

    bl_idname = "animation_lab.change_page"
    bl_label = "Change Page"
    bl_options = {"INTERNAL"}

    step: IntProperty(name="Step", default=1, options={"SKIP_SAVE"})

    def execute(self, context):
        state = context.window_manager.animation_lab
        last_page = library.page_count(len(properties.filtered_animations(state)), preferences.get(context).page_size) - 1
        state.page = min(max(state.page + self.step, 0), last_page)
        return {"FINISHED"}


CLASSES = (
    ANIMLAB_OT_reload_library,
    ANIMLAB_OT_select_animation,
    ANIMLAB_OT_change_page,
)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
