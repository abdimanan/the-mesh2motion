"""Animation Lab operators."""

import bpy
from bpy.props import EnumProperty, IntProperty, StringProperty
from bpy.types import Operator

from . import apply, library, preferences, preview, previews, properties


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
        state = context.window_manager.animation_lab
        state.selected = self.animation_id
        if preview.is_active():
            # clicking another animation while previewing plays that one instead
            preview.switch(context, library.animation(self.animation_id), state.mirror,
                           preferences.get(context).match_scene_fps)
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


class ANIMLAB_OT_import_rig(Operator):
    """Add the Mesh2Motion rig of this skeleton to the scene, at the 3D cursor"""

    bl_idname = "animation_lab.import_rig"
    bl_label = "Import Rig"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return library.skeleton(context.window_manager.animation_lab.skeleton) is not None and context.mode == "OBJECT"

    def execute(self, context):
        skeleton = library.skeleton(context.window_manager.animation_lab.skeleton)
        rig = apply.import_rig(context, skeleton)
        self.report({"INFO"}, f"Added {rig.name}")
        return {"FINISHED"}


class ANIMLAB_OT_apply_animation(Operator):
    """Apply the selected animation to the active armature"""

    bl_idname = "animation_lab.apply_animation"
    bl_label = "Apply Animation"
    bl_options = {"REGISTER", "UNDO"}

    mode: EnumProperty(
        name="Apply As",
        items=(
            ("ACTION", "Active Action", "Set it as the armature's action, replacing the current one"),
            ("NLA", "NLA Strip", "Add it as a strip in the NLA Editor, starting at the current frame"),
        ),
        default="ACTION",
    )

    @classmethod
    def description(cls, _context, properties_):
        if properties_.mode == "NLA":
            return "Add the selected animation to the active armature's NLA tracks, at the current frame"
        return "Set the selected animation as the active armature's action"

    @classmethod
    def poll(cls, context):
        if library.animation(context.window_manager.animation_lab.selected) is None:
            cls.poll_message_set("Select an animation first")
            return False
        obj = context.active_object
        if obj is None or obj.type != "ARMATURE":
            cls.poll_message_set("Select an armature, or import the rig")
            return False
        return True

    def execute(self, context):
        state = context.window_manager.animation_lab
        entry = library.animation(state.selected)

        # the preview would put the armature's old action back over this one when it stops
        preview.stop(context)
        armature = context.active_object

        match = apply.compatibility(armature, library.skeleton(entry["skeleton"]))
        if not match.ok:
            self.report({"ERROR"}, f"{armature.name}: {match.describe()}. Import the "
                                   f"{library.skeleton(entry['skeleton'])['display_name']} rig to use this animation.")
            return {"CANCELLED"}

        scene = context.scene
        scene_fps = round(scene.render.fps / scene.render.fps_base)
        action = apply.get_action(entry, scene_fps, preferences.get(context).match_scene_fps, state.mirror)

        if self.mode == "NLA":
            apply.push_to_nla(armature, action, scene.frame_current)
            where = f"NLA of {armature.name} at frame {scene.frame_current}"
        else:
            apply.assign(armature, action)
            where = armature.name
        self.report({"INFO"}, f"Applied {action.name} to {where}")
        return {"FINISHED"}


class ANIMLAB_OT_preview_start(Operator):
    """Play the selected animation in the viewport: on the active armature when it matches,
    otherwise on a temporary rig at the 3D cursor"""

    bl_idname = "animation_lab.preview_start"
    bl_label = "Preview"
    bl_options = {"INTERNAL"}

    @classmethod
    def poll(cls, context):
        if library.animation(context.window_manager.animation_lab.selected) is None:
            cls.poll_message_set("Select an animation first")
            return False
        return context.mode == "OBJECT"

    def execute(self, context):
        state = context.window_manager.animation_lab
        armature = preview.start(context, library.animation(state.selected), state.mirror,
                                 preferences.get(context).match_scene_fps)
        where = "a temporary rig" if preview.is_temporary_rig() else armature.name
        self.report({"INFO"}, f"Previewing on {where}. Stop Preview puts everything back.")
        return {"FINISHED"}


class ANIMLAB_OT_preview_stop(Operator):
    """Stop the preview and put back what it changed"""

    bl_idname = "animation_lab.preview_stop"
    bl_label = "Stop Preview"
    bl_options = {"INTERNAL"}

    @classmethod
    def poll(cls, context):
        return preview.is_active()

    def execute(self, context):
        preview.stop(context)
        return {"FINISHED"}


CLASSES = (
    ANIMLAB_OT_reload_library,
    ANIMLAB_OT_select_animation,
    ANIMLAB_OT_change_page,
    ANIMLAB_OT_import_rig,
    ANIMLAB_OT_apply_animation,
    ANIMLAB_OT_preview_start,
    ANIMLAB_OT_preview_stop,
)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
