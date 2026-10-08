"""Playing an animation in the viewport before applying it.

The preview plays on the active armature when it matches the skeleton, so the user sees the
motion on their own character; otherwise on a temporary rig at the 3D cursor. Everything the
preview changes is remembered and put back when it stops: the armature's action and pose, the
scene's preview range and current frame. A temporary rig is removed again.

The preview also stops before the file is saved or another file is opened, and when the
add-on is disabled, so it never ends up in the user's file.
"""

import bpy
from bpy.app.handlers import persistent
from mathutils import Matrix

from . import apply, library

PREVIEW_PROPERTY = "animation_lab_preview"

# what the running preview changed, so it can be put back. None when no preview is running.
_session = None


class _Session:
    def __init__(self):
        self.object_name = ""
        self.temporary_rig = False
        self.had_animation_data = False
        self.previous_action = None
        self.previous_slot_handle = None
        self.previous_pose = {}
        self.scene_name = ""
        self.use_preview_range = False
        self.preview_range = (0, 0)
        self.frame = 1
        self.animation_id = ""


def is_active():
    return _session is not None


def animation_id():
    return _session.animation_id if _session else ""


def target():
    """The armature the preview plays on, or None."""
    return bpy.data.objects.get(_session.object_name) if _session else None


def is_temporary_rig():
    return bool(_session and _session.temporary_rig)


def start(context, entry, mirrored=False, match_scene_fps=True):
    """Starts previewing an animation (stopping any preview already running)."""
    global _session
    stop(context)

    skeleton = library.skeleton(entry["skeleton"])
    scene = context.scene
    session = _Session()

    armature = context.active_object
    if armature is None or not apply.compatibility(armature, skeleton).ok:
        armature = _temporary_rig(context, skeleton)
        session.temporary_rig = True
    else:
        session.had_animation_data = armature.animation_data is not None
        if armature.animation_data:
            session.previous_action = armature.animation_data.action
            slot = armature.animation_data.action_slot
            session.previous_slot_handle = slot.handle if slot else None
        session.previous_pose = {bone.name: bone.matrix_basis.copy() for bone in armature.pose.bones}

    session.object_name = armature.name
    session.scene_name = scene.name
    session.use_preview_range = scene.use_preview_range
    session.preview_range = (scene.frame_preview_start, scene.frame_preview_end)
    session.frame = scene.frame_current
    _session = session

    _play(context, entry, mirrored, match_scene_fps)
    return armature


def switch(context, entry, mirrored=False, match_scene_fps=True):
    """Plays another animation in the running preview. Starts one when the skeleton differs."""
    if _session is None:
        return
    current = library.animation(_session.animation_id)
    if current is None or current["skeleton"] != entry["skeleton"]:
        start(context, entry, mirrored, match_scene_fps)
        return
    _play(context, entry, mirrored, match_scene_fps)


def stop(context):
    """Stops the preview and puts back everything it changed."""
    global _session
    if _session is None:
        return
    session = _session
    _session = None

    screen = context.screen
    if screen is not None and screen.is_animation_playing:
        bpy.ops.screen.animation_cancel(restore_frame=False)

    scene = bpy.data.scenes.get(session.scene_name)
    if scene is not None:
        # While the preview range is switched off, Blender lets setting its start and end
        # disturb each other, so set them with it on. Start is set twice in case the saved
        # range begins after the current end.
        scene.use_preview_range = True
        start, end = session.preview_range
        scene.frame_preview_start = start
        scene.frame_preview_end = end
        scene.frame_preview_start = start
        scene.use_preview_range = session.use_preview_range
        scene.frame_set(session.frame)

    armature = bpy.data.objects.get(session.object_name)
    if armature is None:
        return

    if session.temporary_rig:
        armature_data = armature.data
        bpy.data.objects.remove(armature)
        if armature_data.users == 0:
            bpy.data.armatures.remove(armature_data)
        return

    if not session.had_animation_data:
        armature.animation_data_clear()
    else:
        armature.animation_data.action = session.previous_action
        if session.previous_action is not None and session.previous_slot_handle is not None:
            for slot in session.previous_action.slots:
                if slot.handle == session.previous_slot_handle:
                    armature.animation_data.action_slot = slot
    for bone in armature.pose.bones:
        bone.matrix_basis = session.previous_pose.get(bone.name, Matrix.Identity(4))
    if scene is not None:
        scene.frame_set(session.frame)


def _temporary_rig(context, skeleton):
    rig = apply._append(skeleton["blend_file"], "objects", skeleton["rig"])
    context.collection.objects.link(rig)
    rig.location = context.scene.cursor.location
    rig.show_in_front = True
    rig[PREVIEW_PROPERTY] = True
    return rig


def _play(context, entry, mirrored, match_scene_fps):
    scene = context.scene
    scene_fps = round(scene.render.fps / scene.render.fps_base)
    action = apply.get_action(entry, scene_fps, match_scene_fps, mirrored)
    apply.assign(target(), action)
    _session.animation_id = entry["id"]

    # loop just this clip
    start_frame, end_frame = (round(value) for value in action.frame_range)
    scene.use_preview_range = True
    scene.frame_preview_start = start_frame
    scene.frame_preview_end = max(end_frame, start_frame + 1)
    scene.frame_set(start_frame)

    screen = context.screen
    if screen is not None and not screen.is_animation_playing:
        bpy.ops.screen.animation_play()


@persistent
def _stop_before_save(_dummy=None, _dummy2=None):
    if _session is not None:
        stop(bpy.context)


@persistent
def _forget_on_load(_dummy=None, _dummy2=None):
    # the objects belong to the file being closed; there is nothing to put back
    global _session
    _session = None


def register():
    bpy.app.handlers.save_pre.append(_stop_before_save)
    bpy.app.handlers.load_pre.append(_forget_on_load)


def unregister():
    if _session is not None:
        stop(bpy.context)
    if _stop_before_save in bpy.app.handlers.save_pre:
        bpy.app.handlers.save_pre.remove(_stop_before_save)
    if _forget_on_load in bpy.app.handlers.load_pre:
        bpy.app.handlers.load_pre.remove(_forget_on_load)
