"""The Animation Lab tab in the 3D Viewport sidebar (N panel)."""

import bpy
from bpy.types import Panel

from . import library, preferences, previews
from .operators import ANIMLAB_OT_reload_library

SIDEBAR_TAB = "Animation Lab"


class ANIMLAB_PT_library(Panel):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = SIDEBAR_TAB
    bl_label = "Animation Lab"

    def draw(self, context):
        layout = self.layout

        if not library.is_available():
            box = layout.box()
            box.label(text="Animation library not found", icon="ERROR")
            box.label(text=library.load_error())
            layout.operator(ANIMLAB_OT_reload_library.bl_idname, icon="FILE_REFRESH")
            return

        state = context.window_manager.animation_lab
        layout.prop(state, "skeleton", text="")

        skeleton = library.skeleton(state.skeleton)
        if skeleton is None:
            return

        icon = previews.icon_id(library.file_path(skeleton.get("thumbnail")))
        if icon:
            layout.template_icon(icon_value=icon, scale=preferences.get(context).thumbnail_scale)

        column = layout.column(align=True)
        column.label(text=f"{skeleton['animations']} animations", icon="ACTION")
        column.label(text=f"{skeleton['rig']}, {skeleton['bones']} bones", icon="ARMATURE_DATA")

        layout.prop(state, "category", text="")

        box = layout.box()
        box.label(text="Browsing and applying animations", icon="INFO")
        box.label(text="arrive in the next update.")

        layout.operator(ANIMLAB_OT_reload_library.bl_idname, icon="FILE_REFRESH")


CLASSES = (ANIMLAB_PT_library,)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
