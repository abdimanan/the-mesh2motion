"""Mixamo mode: applying Mesh2Motion human animations to a Mixamo armature in the scene.

Mixamo bones have different rest axes from the Mesh2Motion bones, and Blender plays keys
relative to each bone's rest, so renaming the keys is not enough. Every frame is converted:
each Mixamo bone gets the same world rotation change as the Mesh2Motion bone it maps to, and
Hips carries the root motion, scaled by the ratio of the two hip heights.

    W_mixamo(bone, t) = W_m2m(source, t) * O,   O = W_m2m_rest(source)^-1 * W_mixamo_rest(bone)

The conversion uses the user's own armature as the target, whatever its proportions, so no
Mixamo data ships with the add-on. The Mesh2Motion side is evaluated by Blender itself on a
temporary copy of the library's human rig.
"""

import re

import bpy
from mathutils import Matrix, Quaternion

from . import apply, library

# Mesh2Motion human bone -> Mixamo bone (without the "mixamorig:" prefix).
# Generated from mesh2motion-app/src/retarget/bone-automap/MixamoMapper.ts
MIXAMO_FROM_M2M = {
    "pelvis": "Hips",
    "spine_01": "Spine",
    "spine_02": "Spine1",
    "spine_03": "Spine2",
    "neck_01": "Neck",
    "head": "Head",
    "head_leaf": "HeadTop_End",
    "clavicle_l": "LeftShoulder",
    "upperarm_l": "LeftArm",
    "lowerarm_l": "LeftForeArm",
    "hand_l": "LeftHand",
    "clavicle_r": "RightShoulder",
    "upperarm_r": "RightArm",
    "lowerarm_r": "RightForeArm",
    "hand_r": "RightHand",
    "thigh_l": "LeftUpLeg",
    "calf_l": "LeftLeg",
    "foot_l": "LeftFoot",
    "ball_l": "LeftToeBase",
    "ball_leaf_l": "LeftToe_End",
    "thigh_r": "RightUpLeg",
    "calf_r": "RightLeg",
    "foot_r": "RightFoot",
    "ball_r": "RightToeBase",
    "ball_leaf_r": "RightToe_End",
    "thumb_01_l": "LeftHandThumb1",
    "thumb_02_l": "LeftHandThumb2",
    "thumb_03_l": "LeftHandThumb3",
    "thumb_04_leaf_l": "LeftHandThumb4",
    "index_01_l": "LeftHandIndex1",
    "index_02_l": "LeftHandIndex2",
    "index_03_l": "LeftHandIndex3",
    "index_04_leaf_l": "LeftHandIndex4",
    "middle_01_l": "LeftHandMiddle1",
    "middle_02_l": "LeftHandMiddle2",
    "middle_03_l": "LeftHandMiddle3",
    "middle_04_leaf_l": "LeftHandMiddle4",
    "ring_01_l": "LeftHandRing1",
    "ring_02_l": "LeftHandRing2",
    "ring_03_l": "LeftHandRing3",
    "ring_04_leaf_l": "LeftHandRing4",
    "pinky_01_l": "LeftHandPinky1",
    "pinky_02_l": "LeftHandPinky2",
    "pinky_03_l": "LeftHandPinky3",
    "pinky_04_leaf_l": "LeftHandPinky4",
    "thumb_01_r": "RightHandThumb1",
    "thumb_02_r": "RightHandThumb2",
    "thumb_03_r": "RightHandThumb3",
    "thumb_04_leaf_r": "RightHandThumb4",
    "index_01_r": "RightHandIndex1",
    "index_02_r": "RightHandIndex2",
    "index_03_r": "RightHandIndex3",
    "index_04_leaf_r": "RightHandIndex4",
    "middle_01_r": "RightHandMiddle1",
    "middle_02_r": "RightHandMiddle2",
    "middle_03_r": "RightHandMiddle3",
    "middle_04_leaf_r": "RightHandMiddle4",
    "ring_01_r": "RightHandRing1",
    "ring_02_r": "RightHandRing2",
    "ring_03_r": "RightHandRing3",
    "ring_04_leaf_r": "RightHandRing4",
    "pinky_01_r": "RightHandPinky1",
    "pinky_02_r": "RightHandPinky2",
    "pinky_03_r": "RightHandPinky3",
    "pinky_04_leaf_r": "RightHandPinky4",
}

# the distinctive core of the Mixamo skeleton (MixamoMapper.CORE_BONES)
CORE_BONES = ["Hips", "Spine", "Neck", "Head", "LeftShoulder", "LeftArm", "LeftForeArm", "LeftHand", "RightShoulder", "RightArm", "RightForeArm", "RightHand", "LeftUpLeg", "LeftLeg", "LeftFoot", "RightUpLeg", "RightLeg", "RightFoot"]
# share of the core bones an armature needs to count as Mixamo (MixamoMapper.CORE_MATCH_THRESHOLD)
CORE_MATCH_THRESHOLD = 0.8

SKELETON = "human"
TARGET_PROPERTY = "animation_lab_mixamo_target"

_PREFIX = re.compile(r"^mixamorig\d*[:_]?")


def short_name(bone_name):
    """'mixamorig:LeftHand', 'mixamorigLeftHand', 'mixamorig1:LeftHand', 'mixamorig_LeftHand' -> 'LeftHand'."""
    return _PREFIX.sub("", bone_name)


def mixamo_bones(armature_object):
    """Mixamo short name -> the armature's own bone name."""
    bones = {}
    for bone in armature_object.data.bones:
        bones.setdefault(short_name(bone.name), bone.name)
    return bones


def is_mixamo(armature_object):
    if armature_object is None or armature_object.type != "ARMATURE":
        return False
    names = mixamo_bones(armature_object)
    return sum(1 for core in CORE_BONES if core in names) / len(CORE_BONES) >= CORE_MATCH_THRESHOLD


def matching_bones(armature_object):
    names = mixamo_bones(armature_object)
    return sum(1 for mixamo_name in MIXAMO_FROM_M2M.values() if mixamo_name in names), len(MIXAMO_FROM_M2M)


def _world_rotation(matrix):
    return matrix.to_3x3().normalized().to_quaternion()


def _depth(bone):
    return len(bone.parent_recursive)


def convert(context, entry, target, scene_fps, match_scene_fps=True, mirrored=False):
    """A new action that plays the Mesh2Motion animation on the Mixamo armature `target`."""
    if entry["skeleton"] != SKELETON:
        raise ValueError("Mixamo mode works with the Human animations only")

    source_action = apply.get_action(entry, scene_fps, match_scene_fps, mirrored)
    scene = context.scene
    frame_before = scene.frame_current

    # the Mesh2Motion side, evaluated by Blender on a temporary copy of the library rig
    skeleton = library.skeleton(SKELETON)
    source = apply._append(skeleton["blend_file"], "objects", skeleton["rig"])
    scene.collection.objects.link(source)
    try:
        return _convert(context, entry, source, source_action, target, mirrored)
    finally:
        armature_data = source.data
        bpy.data.objects.remove(source)
        if armature_data.users == 0:
            bpy.data.armatures.remove(armature_data)
        scene.frame_set(frame_before)


def _convert(context, entry, source, source_action, target, mirrored):
    scene = context.scene
    target_names = mixamo_bones(target)
    pairs = [(m2m, target_names[mixamo]) for m2m, mixamo in MIXAMO_FROM_M2M.items()
             if mixamo in target_names and m2m in source.data.bones]
    target_of = {target_bone: m2m for m2m, target_bone in pairs}
    hips = target_names["Hips"]

    # rest poses in world space
    source_rest = {m2m: source.matrix_world @ source.data.bones[m2m].matrix_local for m2m, _ in pairs}
    target_rest = {bone.name: target.matrix_world @ bone.matrix_local for bone in target.data.bones}
    offsets = {
        target_bone: _world_rotation(source_rest[m2m]).inverted() @ _world_rotation(target_rest[target_bone])
        for m2m, target_bone in pairs
    }

    # hips: root motion scaled by the ratio of the hip heights above each armature's origin
    source_hips_rest = source_rest[target_of[hips]].to_translation()
    target_hips_rest = target_rest[hips].to_translation()
    source_height = source_hips_rest.z - source.matrix_world.to_translation().z
    target_height = target_hips_rest.z - target.matrix_world.to_translation().z
    height_ratio = target_height / source_height if abs(source_height) > 1e-9 else 1.0

    to_target_space = target.matrix_world.inverted()
    target_space_rotation = _world_rotation(target.matrix_world).inverted()
    bones = sorted(target.data.bones, key=_depth)
    rest_relative = {
        bone.name: (bone.parent.matrix_local.inverted() @ bone.matrix_local) if bone.parent else bone.matrix_local.copy()
        for bone in bones
    }

    animation_data = source.animation_data_create()
    animation_data.action = source_action
    if len(source_action.slots):
        animation_data.action_slot = source_action.slots[0]

    start, end = (round(value) for value in source_action.frame_range)
    frames = list(range(start, end + 1))
    rotation_keys = {bone.name: [] for bone in bones if bone.name in target_of}
    location_keys = []

    for frame in frames:
        scene.frame_set(frame)
        source_pose = {m2m: source.matrix_world @ source.pose.bones[m2m].matrix for m2m, _ in pairs}

        pose = {}  # target pose matrices (armature space) as they will come out
        for bone in bones:
            parent_pose = pose[bone.parent.name] if bone.parent else Matrix.Identity(4)
            relative = rest_relative[bone.name]

            if bone.name in target_of:
                world_rotation = _world_rotation(source_pose[target_of[bone.name]]) @ offsets[bone.name]
                rotation = target_space_rotation @ world_rotation
            else:
                rotation = (parent_pose @ relative).to_quaternion()  # unmapped bones stay at rest

            if bone.name == hips:
                travel = (source_pose[target_of[hips]].to_translation() - source_hips_rest) * height_ratio
                location = to_target_space @ (target_hips_rest + travel)
                wanted = Matrix.LocRotScale(location, rotation, None)
                basis = relative.inverted() @ parent_pose.inverted() @ wanted
                location_keys.append(basis.to_translation())
                basis_rotation = basis.to_quaternion()
            else:
                basis_rotation = relative.to_quaternion().inverted() @ parent_pose.to_quaternion().inverted() @ rotation
                basis = basis_rotation.to_matrix().to_4x4()

            if bone.name in rotation_keys:
                keys = rotation_keys[bone.name]
                if keys and keys[-1].dot(basis_rotation) < 0:
                    basis_rotation.negate()  # keep keys in one hemisphere so they blend smoothly
                keys.append(basis_rotation.normalized())
            pose[bone.name] = parent_pose @ relative @ basis

    action = _write_action(target, entry, mirrored, frames, rotation_keys, hips, location_keys)
    action[apply.ID_PROPERTY] = entry["id"]
    action[apply.FPS_PROPERTY] = source_action[apply.FPS_PROPERTY]
    action[apply.MIRRORED_PROPERTY] = mirrored
    action[TARGET_PROPERTY] = target.data.name
    return action


def _write_action(target, entry, mirrored, frames, rotation_keys, hips, location_keys):
    name = f"{entry['name']} (Mixamo{', mirrored' if mirrored else ''})"
    action = bpy.data.actions.new(name)
    slot = action.slots.new(id_type="OBJECT", name=target.name)
    strip = action.layers.new("Animation Lab").strips.new(type="KEYFRAME")
    channelbag = strip.channelbag(slot, ensure=True)

    def add_curve(data_path, index, values):
        curve = channelbag.fcurves.new(data_path, index=index)
        curve.keyframe_points.add(len(frames))
        coordinates = [value for frame, key in zip(frames, values) for value in (frame, key)]
        curve.keyframe_points.foreach_set("co", coordinates)
        for point in curve.keyframe_points:
            point.interpolation = "LINEAR"
        curve.update()

    for bone_name, keys in rotation_keys.items():
        group = f'pose.bones["{bone_name}"]'
        for index in range(4):
            add_curve(f"{group}.rotation_quaternion", index, [key[index] for key in keys])
    for index in range(3):
        add_curve(f'pose.bones["{hips}"].location', index, [key[index] for key in location_keys])
    return action


def get_action(context, entry, target, scene_fps, match_scene_fps=True, mirrored=False):
    """The converted action for this armature: reused when it was already made for the same
    armature, frame rate and mirroring."""
    target_fps = scene_fps if match_scene_fps else entry["fps"]
    for action in bpy.data.actions:
        if action.get(apply.ID_PROPERTY) == entry["id"] and action.get(TARGET_PROPERTY) == target.data.name \
                and action.get(apply.FPS_PROPERTY) == target_fps \
                and bool(action.get(apply.MIRRORED_PROPERTY, False)) == mirrored:
            return action
    return convert(context, entry, target, scene_fps, match_scene_fps, mirrored)


def uses_mixamo_mode(entry, armature_object):
    return entry is not None and entry["skeleton"] == SKELETON and is_mixamo(armature_object)


def describe(armature_object):
    matching, total = matching_bones(armature_object)
    return f"Mixamo rig: {matching}/{total} bones, converted"


def action_for(context, entry, armature_object, scene_fps, match_scene_fps=True, mirrored=False):
    """The action to play on this armature: converted for a Mixamo armature, otherwise the
    library animation itself."""
    if uses_mixamo_mode(entry, armature_object):
        return get_action(context, entry, armature_object, scene_fps, match_scene_fps, mirrored)
    return apply.get_action(entry, scene_fps, match_scene_fps, mirrored)


def can_play_on(entry, armature_object):
    """True when the animation can be applied to (or previewed on) this armature."""
    if armature_object is None or armature_object.type != "ARMATURE" or entry is None:
        return False
    return uses_mixamo_mode(entry, armature_object) or \
        apply.compatibility(armature_object, library.skeleton(entry["skeleton"])).ok

