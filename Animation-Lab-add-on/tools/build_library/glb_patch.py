"""Rewrites an animation GLB so Blender imports it the way the web app plays it. No Blender needed.

The web app (AnimationUtility.clean_track_data) plays a clip on the skeleton's rig by
setting each bone's local transform straight from the keys, and it keeps only:
- rotation keys
- position keys of the skeleton's position tracking bone (pelvis, hips or head)
- position keys of the root bone, only for clips whose name ends in "rm" (root motion)

Blender's glTF importer instead keys every channel relative to the armature stored in the
same file. Some animation files were authored on an armature whose rest pose differs from
the rig (the human base pack by up to 34 mm), which tilts limbs by several degrees once the
action is played on the rig. So before importing, the joints of the animation file get the
rig's rest pose and the channels the web app drops are removed. The importer then builds
actions that reproduce the web app's motion on the rig.
"""

import json
import struct

GLB_MAGIC = 0x46546C67
JSON_CHUNK = 0x4E4F534A
# the binary chunk starts with an 8 byte header (length, type) before its data
BINARY_DATA_START = 8


def _read(path):
    with open(path, "rb") as glb_file:
        data = glb_file.read()
    json_length = struct.unpack("<I", data[12:16])[0]
    document = json.loads(data[20:20 + json_length])
    return document, data[20 + json_length:]  # binary chunk with its header, untouched


def _write(path, document, binary_chunk):
    json_bytes = json.dumps(document, separators=(",", ":")).encode("utf-8")
    json_bytes += b" " * ((4 - len(json_bytes) % 4) % 4)
    total_length = 12 + 8 + len(json_bytes) + len(binary_chunk)
    with open(path, "wb") as glb_file:
        glb_file.write(struct.pack("<III", GLB_MAGIC, 2, total_length))
        glb_file.write(struct.pack("<II", len(json_bytes), JSON_CHUNK))
        glb_file.write(json_bytes)
        glb_file.write(binary_chunk)


def _accessor_data_offset(document, accessor_index):
    accessor = document["accessors"][accessor_index]
    view = document["bufferViews"][accessor["bufferView"]]
    if view.get("byteStride", 64) != 64:
        raise ValueError("interleaved inverse bind matrices are not supported")
    return view.get("byteOffset", 0) + accessor.get("byteOffset", 0)


def _inverse_bind_matrices(document, binary_chunk):
    """Raw 64 byte inverse bind matrix of every joint, by joint name."""
    matrices = {}
    for skin in document.get("skins", []):
        if "inverseBindMatrices" not in skin:
            continue
        data_offset = _accessor_data_offset(document, skin["inverseBindMatrices"])
        for joint_slot, node_index in enumerate(skin["joints"]):
            start = BINARY_DATA_START + data_offset + joint_slot * 64
            matrices.setdefault(document["nodes"][node_index].get("name"), binary_chunk[start:start + 64])
    return matrices


def _rest_transforms(document):
    """Local rest transform of every named node: translation, rotation, scale."""
    rests = {}
    for node in document.get("nodes", []):
        if "name" in node:
            rests[node["name"]] = {
                key: node[key] for key in ("translation", "rotation", "scale", "matrix") if key in node
            }
    return rests


def is_root_motion_clip(clip_name):
    # the web app checks the lower-case name: clip_name.toLowerCase().endsWith('rm')
    return clip_name.lower().endswith("rm")


def kept_channel(target_path, node_name, clip_name, position_bone, root_bone):
    if target_path == "rotation":
        return True
    if target_path != "translation":
        return False  # scale and morph weights are dropped by the web app
    if node_name.lower() == position_bone.lower():
        return True
    return node_name == root_bone and is_root_motion_clip(clip_name)


def patch_animation_glb(animation_path, rig_path, out_path, position_bone):
    """Writes out_path: the animation file with the rig's rest pose and the web app's channels.

    Returns a summary dict: how many rest transforms changed and channels were dropped.
    """
    document, binary_chunk = _read(animation_path)
    rig_document, rig_binary = _read(rig_path)
    rig_rests = _rest_transforms(rig_document)
    rig_nodes = rig_document.get("nodes", [])
    rig_joint_names = set()
    for skin in rig_document.get("skins", []):
        rig_joint_names.update(rig_nodes[index].get("name") for index in skin["joints"])

    # the root bone is the joint whose parent is not a joint
    parent_name = {rig_nodes[child].get("name"): node.get("name") for node in rig_nodes for child in node.get("children", [])}
    root_bone = next((name for name in sorted(rig_joint_names) if parent_name.get(name) not in rig_joint_names), None)

    # Blender's importer builds the armature rest pose from the skin's inverse bind matrices,
    # so those have to match the rig as well, not only the node transforms
    rig_bind = _inverse_bind_matrices(rig_document, rig_binary)
    binary_chunk = bytearray(binary_chunk)
    for skin in document.get("skins", []):
        if "inverseBindMatrices" not in skin:
            continue
        data_offset = _accessor_data_offset(document, skin["inverseBindMatrices"])
        for joint_slot, node_index in enumerate(skin["joints"]):
            matrix = rig_bind.get(document["nodes"][node_index].get("name"))
            if matrix is not None:
                start = BINARY_DATA_START + data_offset + joint_slot * 64
                binary_chunk[start:start + 64] = matrix
    binary_chunk = bytes(binary_chunk)

    rests_changed = 0
    for node in document.get("nodes", []):
        rig_rest = rig_rests.get(node.get("name"))
        if rig_rest is None or node.get("name") not in rig_joint_names:
            continue
        before = {key: node.get(key) for key in ("translation", "rotation", "scale", "matrix")}
        for key in ("translation", "rotation", "scale", "matrix"):
            node.pop(key, None)
        node.update(rig_rest)
        if before != {key: node.get(key) for key in ("translation", "rotation", "scale", "matrix")}:
            rests_changed += 1

    channels_dropped = 0
    nodes = document.get("nodes", [])
    for animation in document.get("animations", []):
        clip_name = animation.get("name", "")
        kept = []
        for channel in animation["channels"]:
            target = channel["target"]
            node_name = nodes[target["node"]].get("name", "") if "node" in target else ""
            if node_name in rig_joint_names and kept_channel(target["path"], node_name, clip_name, position_bone, root_bone):
                kept.append(channel)
            else:
                channels_dropped += 1
        animation["channels"] = kept

    _write(out_path, document, binary_chunk)
    return {"rests_changed": rests_changed, "channels_dropped": channels_dropped, "root_bone": root_bone}
