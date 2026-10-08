"""Reads the keyframe rate of the clips in a GLB file. No Blender needed."""

import json
import struct

STANDARD_RATES = [12, 15, 24, 25, 30, 48, 50, 60, 120]
# how far a key may sit from a whole frame and still count as on it (in frames)
FRAME_TOLERANCE = 0.01


def _read_glb(path):
    with open(path, "rb") as glb_file:
        data = glb_file.read()
    json_length = struct.unpack("<I", data[12:16])[0]
    document = json.loads(data[20:20 + json_length])
    binary_offset = 20 + json_length
    binary_length = struct.unpack("<I", data[binary_offset:binary_offset + 4])[0]
    return document, data[binary_offset + 8:binary_offset + 8 + binary_length]


def _key_times(document, binary, accessor_index):
    accessor = document["accessors"][accessor_index]
    view = document["bufferViews"][accessor["bufferView"]]
    offset = view.get("byteOffset", 0) + accessor.get("byteOffset", 0)
    return struct.unpack(f"<{accessor['count']}f", binary[offset:offset + 4 * accessor["count"]])


def all_key_times(path):
    document, binary = _read_glb(path)
    times = set()
    for animation in document.get("animations", []):
        for sampler in animation["samplers"]:
            times.update(_key_times(document, binary, sampler["input"]))
    return times


def pack_rate(path):
    """The frame rate the pack was keyed at.

    Clips are often keyed on every other frame, so the most common gap between keys is
    misleading. Instead this is the smallest standard rate at which every key of every clip
    in the file lands on a whole frame.
    """
    times = all_key_times(path)
    for rate in STANDARD_RATES:
        if all(abs(time * rate - round(time * rate)) < FRAME_TOLERANCE for time in times):
            return rate
    raise ValueError(f"{path}: keys do not line up with any standard frame rate")
