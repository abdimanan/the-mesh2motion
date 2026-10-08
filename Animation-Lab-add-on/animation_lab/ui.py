"""The Animation Lab tab in the 3D Viewport sidebar (N panel): the animation browser, the
selected animation and the skeleton."""

import bpy
from bpy.types import Panel

from . import apply, library, mixamo, preferences, preview, previews, properties
from .operators import (
    ANIMLAB_OT_apply_animation,
    ANIMLAB_OT_change_page,
    ANIMLAB_OT_import_rig,
    ANIMLAB_OT_preview_start,
    ANIMLAB_OT_preview_stop,
    ANIMLAB_OT_reload_library,
    ANIMLAB_OT_select_animation,
)

SIDEBAR_TAB = "Animation Lab"


class AnimationLabPanel:
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = SIDEBAR_TAB


def draw_thumbnail(layout, relative_path, scale):
    """The library thumbnail, or a plain placeholder when no icon can be shown (Blender only
    hands out icons when it has a UI)."""
    icon = previews.icon_id(library.file_path(relative_path))
    if icon:
        layout.template_icon(icon_value=icon, scale=scale)
    else:
        layout.label(text="", icon="ACTION")


class ANIMLAB_PT_library(AnimationLabPanel, Panel):
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
        settings = preferences.get(context)

        layout.prop(state, "skeleton", text="")
        # Blender draws its own clear button inside the search field
        layout.prop(state, "search", text="", icon="VIEWZOOM")
        layout.prop(state, "category", text="")

        results = properties.filtered_animations(state)
        if not results:
            layout.label(text="No animations match", icon="INFO")
            return

        pages = library.page_count(len(results), settings.page_size)
        page = min(state.page, pages - 1)
        row = layout.row(align=True)
        row.label(text=f"{len(results)} animations")
        previous_page = row.operator(ANIMLAB_OT_change_page.bl_idname, text="", icon="TRIA_LEFT")
        previous_page.step = -1
        row.label(text=f"{page + 1} / {pages}")
        next_page = row.operator(ANIMLAB_OT_change_page.bl_idname, text="", icon="TRIA_RIGHT")
        next_page.step = 1

        grid = layout.grid_flow(row_major=True, columns=0, even_columns=True, even_rows=True, align=False)
        for entry in library.page_of(results, page, settings.page_size):
            cell = grid.column(align=True)
            draw_thumbnail(cell, entry["thumbnail"], settings.thumbnail_scale)
            button = cell.operator(
                ANIMLAB_OT_select_animation.bl_idname,
                text=entry["name"],
                depress=entry["id"] == state.selected,
            )
            button.animation_id = entry["id"]


class ANIMLAB_PT_selection(AnimationLabPanel, Panel):
    bl_label = "Selected Animation"
    bl_parent_id = "ANIMLAB_PT_library"

    @classmethod
    def poll(cls, context):
        return library.is_available()

    def draw(self, context):
        layout = self.layout
        state = context.window_manager.animation_lab
        entry = library.animation(state.selected)
        if entry is None:
            layout.label(text="Click an animation to select it", icon="INFO")
            layout.operator(ANIMLAB_OT_import_rig.bl_idname, icon="ARMATURE_DATA")
            return

        draw_thumbnail(layout, entry["thumbnail"], preferences.get(context).thumbnail_scale * 1.5)
        column = layout.column(align=True)
        column.label(text=entry["name"], icon="ACTION")
        column.label(text=f"{entry['category']} · {entry['pack']} pack")
        frames = entry["frame_end"] - entry["frame_start"] + 1
        column.label(text=f"{entry['duration']:.2f} s · {frames} frames at {entry['fps']} fps")
        if entry["root_motion"]:
            column.label(text="Moves through the scene (root motion)", icon="CON_LOCLIKE")
        if entry["tags"]:
            column.label(text="Tags: " + ", ".join(entry["tags"]))

        draw_apply_controls(layout, context, entry, state)


def draw_preview_controls(layout):
    if preview.is_active():
        playing_on = "a temporary rig" if preview.is_temporary_rig() else preview.target().name
        layout.label(text=f"Previewing on {playing_on}", icon="PLAY")
        layout.operator(ANIMLAB_OT_preview_stop.bl_idname, icon="CANCEL")
    else:
        layout.operator(ANIMLAB_OT_preview_start.bl_idname, icon="PLAY")


def draw_apply_controls(layout, context, entry, state):
    draw_preview_controls(layout)
    box = layout.box()
    armature = context.active_object if context.active_object and context.active_object.type == "ARMATURE" else None
    if armature is None:
        box.label(text="Select an armature, or import the rig", icon="INFO")
    elif mixamo.uses_mixamo_mode(entry, armature):
        box.label(text=f"{armature.name}: {mixamo.describe(armature)}", icon="CHECKMARK")
    else:
        match = apply.compatibility(armature, library.skeleton(entry["skeleton"]))
        box.label(text=f"{armature.name}: {match.describe()}", icon="CHECKMARK" if match.ok else "ERROR")

    box.operator(ANIMLAB_OT_import_rig.bl_idname, icon="ARMATURE_DATA")
    box.prop(state, "mirror", icon="MOD_MIRROR")
    row = box.row(align=True)
    row.operator(ANIMLAB_OT_apply_animation.bl_idname, text="Apply", icon="ACTION").mode = "ACTION"
    row.operator(ANIMLAB_OT_apply_animation.bl_idname, text="Push to NLA", icon="NLA").mode = "NLA"


class ANIMLAB_PT_skeleton(AnimationLabPanel, Panel):
    bl_label = "Skeleton"
    bl_parent_id = "ANIMLAB_PT_library"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        return library.is_available()

    def draw(self, context):
        layout = self.layout
        skeleton = library.skeleton(context.window_manager.animation_lab.skeleton)
        if skeleton is None:
            return

        draw_thumbnail(layout, skeleton.get("thumbnail"), preferences.get(context).thumbnail_scale * 1.5)
        column = layout.column(align=True)
        column.label(text=f"{skeleton['animations']} animations", icon="ACTION")
        column.label(text=f"{skeleton['rig']}, {skeleton['bones']} bones", icon="ARMATURE_DATA")
        layout.operator(ANIMLAB_OT_import_rig.bl_idname, icon="ARMATURE_DATA")
        layout.operator(ANIMLAB_OT_reload_library.bl_idname, icon="FILE_REFRESH")


CLASSES = (ANIMLAB_PT_library, ANIMLAB_PT_selection, ANIMLAB_PT_skeleton)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
