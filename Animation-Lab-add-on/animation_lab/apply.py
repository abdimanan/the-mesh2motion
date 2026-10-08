"""Bringing rigs and animations from the library into the user's scene.

Everything is appended (copied) from the library's .blend files, never linked, so the user's
file keeps working without the add-on. Appended rigs and actions have their asset mark
cleared, so the user's file does not turn into an asset library.
"""

import re

import bpy

from . import library

# custom properties on every action Animation Lab puts in a file
ID_PROPERTY = "animation_lab_id"
FPS_PROPERTY = "animation_lab_fps"
MIRRORED_PROPERTY = "animation_lab_mirrored"

NLA_TRACK_NAME = "Animation Lab"

# an armature counts as the skeleton when it has its position bone and at least this share of
# its bones. Rigs with simplified hands (fingers removed) still qualify; the missing bones
# simply are not animated.
MIN_MATCHING_BONES = 0.5

# left/right naming patterns of the Mesh2Motion rigs: thigh_l, Back_Leg_Foot_1_L, hand.L
_SIDE_PATTERNS = [
    (re.compile(r"_l$"), "_r"), (re.compile(r"_r$"), "_l"),
    (re.compile(r"_L$"), "_R"), (re.compile(r"_R$"), "_L"),
    (re.compile(r"\.l$"), ".r"), (re.compile(r"\.r$"), ".l"),
    (re.compile(r"\.L$"), ".R"), (re.compile(r"\.R$"), ".L"),
    (re.compile(r"_l_"), "_r_"), (re.compile(r"_r_"), "_l_"),
    (re.compile(r"_L_"), "_R_"), (re.compile(r"_R_"), "_L_"),
]


class Compatibility:
    def __init__(self, matching, total, has_position_bone):
        self.matching = matching
        self.total = total
        self.has_position_bone = has_position_bone

    @property
    def ok(self):
        return self.has_position_bone and self.total > 0 and self.matching / self.total >= MIN_MATCHING_BONES

    def describe(self):
        if self.ok:
            return f"{self.matching}/{self.total} bones match"
        if not self.has_position_bone:
            return "Not a Mesh2Motion rig for this skeleton"
        return f"Only {self.matching}/{self.total} bones match"


def compatibility(armature_object, skeleton_entry):
    """How well an armature matches a library skeleton, by bone names."""
    if armature_object is None or armature_object.type != "ARMATURE" or skeleton_entry is None:
        return Compatibility(0, 0, False)
    names = set(armature_object.data.bones.keys())
    expected = skeleton_entry["bone_names"]
    position_bone = skeleton_entry["position_bone"].lower()
    return Compatibility(
        matching=sum(1 for name in expected if name in names),
        total=len(expected),
        has_position_bone=any(name.lower() == position_bone for name in names),
    )


def _append(blend_file, collection_name, name):
    with bpy.data.libraries.load(library.file_path(blend_file), link=False) as (_source, target):
        setattr(target, collection_name, [name])
    appended = getattr(target, collection_name)[0]
    if appended is None:
        raise RuntimeError(f"{name!r} is missing from {blend_file}")
    if appended.asset_data is not None:
        appended.asset_clear()
    return appended


def import_rig(context, skeleton_entry):
    """Appends the skeleton's rig at the 3D cursor and makes it the active, selected object."""
    rig = _append(skeleton_entry["blend_file"], "objects", skeleton_entry["rig"])
    context.collection.objects.link(rig)
    rig.location = context.scene.cursor.location

    for obj in context.view_layer.objects.selected:
        obj.select_set(False)
    rig.select_set(True)
    context.view_layer.objects.active = rig
    return rig


def _action_fcurves(action):
    return [curve for layer in action.layers for strip in layer.strips
            for channelbag in strip.channelbags for curve in channelbag.fcurves]


def retime(action, frame_start, from_fps, to_fps):
    """Spaces the keys out (or in) so the clip plays at its real speed at another frame rate."""
    factor = to_fps / from_fps
    for curve in _action_fcurves(action):
        for point in curve.keyframe_points:
            for coordinate in (point.co, point.handle_left, point.handle_right):
                coordinate.x = frame_start + (coordinate.x - frame_start) * factor
        curve.update()


def mirror_bone_name(name):
    for pattern, replacement in _SIDE_PATTERNS:
        if pattern.search(name):
            return pattern.sub(replacement, name, count=1)
    return name  # a bone on the centre line mirrors onto itself


def mirror(action):
    """Swaps left and right: keys move to the opposite side's bone and are reflected across X.

    Uses Blender's X-mirror convention (the same as Paste Flipped Pose): location X and the Y
    and Z parts of rotations change sign. The Mesh2Motion rigs are symmetric, which is what
    makes this exact; tests check it against reflected joint positions.
    """
    for curve in _action_fcurves(action):
        match = re.match(r'pose\.bones\["(.+)"\]\.(\w+)$', curve.data_path)
        if not match:
            continue
        bone, channel = match.groups()
        partner = mirror_bone_name(bone)
        if partner != bone:
            curve.data_path = f'pose.bones["{partner}"].{channel}'

        flip = (channel == "location" and curve.array_index == 0) or \
               (channel == "rotation_quaternion" and curve.array_index in (2, 3)) or \
               (channel == "rotation_euler" and curve.array_index in (1, 2))
        if flip:
            for point in curve.keyframe_points:
                for coordinate in (point.co, point.handle_left, point.handle_right):
                    coordinate.y = -coordinate.y
        curve.update()


def get_action(entry, scene_fps, match_scene_fps=True, mirrored=False):
    """The animation as an action in this file: reused when it was already brought in with the
    same frame rate and mirroring, otherwise appended from the library and prepared."""
    target_fps = scene_fps if match_scene_fps else entry["fps"]
    for action in bpy.data.actions:
        if action.get(ID_PROPERTY) == entry["id"] and action.get(FPS_PROPERTY) == target_fps \
                and bool(action.get(MIRRORED_PROPERTY, False)) == mirrored:
            return action

    skeleton = library.skeleton(entry["skeleton"])
    action = _append(skeleton["blend_file"], "actions", entry["action"])
    action.use_fake_user = False  # the object or NLA strip using it keeps it in the file
    action[ID_PROPERTY] = entry["id"]
    action[MIRRORED_PROPERTY] = mirrored

    if target_fps != entry["fps"]:
        retime(action, entry["frame_start"], entry["fps"], target_fps)
    action[FPS_PROPERTY] = target_fps

    if mirrored:
        mirror(action)
        action.name = f"{entry['name']} (mirrored)"
    return action


def assign(armature_object, action):
    """Sets the action as the armature's active action."""
    animation_data = armature_object.animation_data_create()
    animation_data.action = action
    if animation_data.action_slot is None and len(action.slots):
        # the slot is named after the library rig; another armature name needs it set by hand
        animation_data.action_slot = action.slots[0]


def push_to_nla(armature_object, action, frame):
    """Adds the action as an NLA strip starting at a frame, on the Animation Lab track, or on a
    new track when that spot is taken."""
    animation_data = armature_object.animation_data_create()
    start = int(frame)
    length = action.frame_range[1] - action.frame_range[0]

    track = None
    for candidate in animation_data.nla_tracks:
        if candidate.name.startswith(NLA_TRACK_NAME) and not any(
                strip.frame_start < start + length and start < strip.frame_end for strip in candidate.strips):
            track = candidate
            break
    if track is None:
        track = animation_data.nla_tracks.new()
        track.name = NLA_TRACK_NAME

    strip = track.strips.new(action.name, start, action)
    if len(action.slots) and strip.action_slot is None:
        strip.action_slot = action.slots[0]
    return strip
