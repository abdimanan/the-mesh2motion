"""Tests for the built Animation Lab library. Run inside Blender through tests/run_tests.sh.

The motion test is independent of the build: it plays the original GLB clips with the web
app's rules (rotation keys, plus the position bone, plus root for "rm" clips, applied to the
rig's rest pose) using plain glTF maths, and compares the joints with the library rig posed
by Blender at the same moments.
"""

import json
import os
import re
import struct
import sys
import unittest

import bpy
import numpy
from mathutils import Matrix, Quaternion, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ADDON_ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ADDON_ROOT, "tools", "build_library"))

from catalog_rules import category_for, clip_slug, load_rules, name_words  # noqa: E402
from glb_info import pack_rate  # noqa: E402
from skeletons import SKELETONS  # noqa: E402

LIBRARY_DIR = os.path.join(ADDON_ROOT, "animation_lab", "library")
STATIC_DIR = os.path.abspath(os.path.join(ADDON_ROOT, "..", "mesh2motion-app", "static"))
RIG_CONFIG = os.path.abspath(os.path.join(ADDON_ROOT, "..", "mesh2motion-app", "src", "lib", "RigConfig.ts"))

EXPECTED_TOTAL_CLIPS = 251
# Joints have to land within a quarter of a millimetre of where the web app puts them (meters).
# The rig files themselves disagree with themselves by up to 0.027 mm at rest (float rounding
# between their joint transforms and bind matrices), and long chains carry that a little
# further when animated: the measured worst case is 0.095 mm.
JOINT_TOLERANCE = 0.00025
MOTION_SAMPLE_CLIPS_PER_PACK = 4
MOTION_SAMPLE_FRAMES_PER_CLIP = 4
THUMBNAIL_SIZE = 256
# a thumbnail has to show the model: at least this share of its pixels visible...
MIN_THUMBNAIL_COVERAGE = 0.03
# ...and not cut off: pixels on the image border at most this opaque
MAX_BORDER_ALPHA = 0.05


def load_catalog():
    with open(os.path.join(LIBRARY_DIR, "catalog.json"), encoding="utf-8") as catalog_file:
        return json.load(catalog_file)


def open_library(skeleton):
    bpy.ops.wm.open_mainfile(filepath=os.path.join(LIBRARY_DIR, skeleton.blend_file))
    rig = bpy.data.objects[skeleton.rig_name]
    return rig


def action_fcurves(action):
    return [curve for layer in action.layers for strip in layer.strips
            for channelbag in strip.channelbags for curve in channelbag.fcurves]


class Glb:
    """Just enough glTF reading to play clips the way the web app (three.js) does."""

    def __init__(self, path):
        with open(path, "rb") as glb_file:
            data = glb_file.read()
        json_length = struct.unpack("<I", data[12:16])[0]
        self.document = json.loads(data[20:20 + json_length])
        self.binary = data[28 + json_length:]
        self.nodes = self.document["nodes"]

    def accessor(self, index):
        accessor = self.document["accessors"][index]
        view = self.document["bufferViews"][accessor["bufferView"]]
        width = {"SCALAR": 1, "VEC3": 3, "VEC4": 4, "MAT4": 16}[accessor["type"]]
        offset = view.get("byteOffset", 0) + accessor.get("byteOffset", 0)
        values = struct.unpack(f"<{accessor['count'] * width}f", self.binary[offset:offset + 4 * accessor["count"] * width])
        return [values[i:i + width] for i in range(0, len(values), width)] if width > 1 else list(values)

    def joint_names(self):
        return {self.nodes[index]["name"] for skin in self.document.get("skins", []) for index in skin["joints"]}

    def animation(self, name):
        return next(animation for animation in self.document["animations"] if animation["name"] == name)


def web_app_channels(glb, animation, joint_names, position_bone):
    """The channels the web app keeps (AnimationUtility.clean_track_data), by node name."""
    root_motion = animation["name"].lower().endswith("rm")
    root_names = {name for name in joint_names
                  if not any(glb.nodes[child]["name"] in joint_names and name == glb.nodes[child]["name"]
                             for node in glb.nodes if node.get("name") in joint_names for child in node.get("children", []))}
    channels = {}
    for channel in animation["channels"]:
        name = glb.nodes[channel["target"]["node"]].get("name")
        path = channel["target"]["path"]
        keep = path == "rotation" or (path == "translation" and (
            name.lower() == position_bone.lower() or (root_motion and name in root_names)))
        if name in joint_names and keep:
            sampler = animation["samplers"][channel["sampler"]]
            channels[(name, path)] = (glb.accessor(sampler["input"]), glb.accessor(sampler["output"]))
    return channels


def web_app_joint_positions(rig_glb, channels, time):
    """World joint positions (glTF space, meters) with the clip's keys applied at an exact key time."""
    positions = {}

    def visit(index, parent_matrix):
        node = rig_glb.nodes[index]
        name = node.get("name")
        translation = Vector(node.get("translation", (0, 0, 0)))
        x, y, z, w = node.get("rotation", (0, 0, 0, 1))
        rotation = Quaternion((w, x, y, z))
        scale = Vector(node.get("scale", (1, 1, 1)))

        for (channel_name, path), (times, values) in channels.items():
            if channel_name != name:
                continue
            key = min(range(len(times)), key=lambda i: abs(times[i] - time))
            if path == "translation":
                translation = Vector(values[key])
            else:
                x, y, z, w = values[key]
                rotation = Quaternion((w, x, y, z))

        world = parent_matrix @ Matrix.LocRotScale(translation, rotation, scale)
        if name is not None:
            positions[name] = world.to_translation()
        for child in node.get("children", []):
            visit(child, world)

    scene = rig_glb.document["scenes"][rig_glb.document.get("scene", 0)]
    for root in scene["nodes"]:
        visit(root, Matrix.Identity(4))
    return positions


def gltf_to_blender(vector):
    # Blender's glTF importer turns glTF's Y up into Blender's Z up
    return Vector((vector.x, -vector.z, vector.y))


class TestCatalogRules(unittest.TestCase):
    def test_name_words(self):
        self.assertEqual(name_words("Sword_Attack_RM"), ["sword", "attack", "rm"])
        self.assertEqual(name_words("LayToIdle"), ["lay", "to", "idle"])
        self.assertEqual(clip_slug("Bow Pull Back"), "bow_pull_back")

    def test_categories(self):
        rules = load_rules()
        self.assertEqual(category_for("Idle_Sword", rules), "Idle")
        self.assertEqual(category_for("Sword_Attack", rules), "Combat")
        self.assertEqual(category_for("Head Nod", rules), "Emotes")
        self.assertEqual(category_for("Eating", rules), "Interaction")
        self.assertEqual(category_for("Walk", rules), "Locomotion")
        self.assertEqual(category_for("Dance Body Roll", rules), "Emotes")
        self.assertEqual(category_for("Crouch_Idle", rules), "Idle")
        self.assertEqual(category_for("Crouch_Walk", rules), "Locomotion")


class TestSourceData(unittest.TestCase):
    def test_skeleton_list_matches_the_web_app(self):
        with open(RIG_CONFIG, encoding="utf-8") as config_file:
            config = config_file.read()

        entries = re.findall(r"rig_file: '([^']+)'.*?animation_files: \[([^\]]*)\].*?position_tracking_bone_name: '([^']+)'", config, re.S)
        web_app = {
            os.path.basename(rig): ([os.path.basename(file) for file in re.findall(r"'([^']+)'", files)], bone)
            for rig, files, bone in entries
        }
        ours = {"rigs/" + skeleton.rig_file: skeleton for skeleton in SKELETONS}

        self.assertEqual(len(web_app), len(SKELETONS), "a skeleton was added to or removed from the web app")
        for skeleton in SKELETONS:
            animation_files, position_bone = web_app[skeleton.rig_file]
            self.assertEqual([pack.file for pack in skeleton.packs], animation_files, skeleton.key)
            self.assertEqual(skeleton.position_bone, position_bone, skeleton.key)
        self.assertTrue(ours)

    def test_frame_rates(self):
        rates = {pack.file: pack_rate(os.path.join(STATIC_DIR, "animations", pack.file))
                 for skeleton in SKELETONS for pack in skeleton.packs}
        self.assertEqual(rates["human-base-animations.glb"], 24)
        self.assertEqual(rates["human-mocap-animations.glb"], 60)
        self.assertEqual(rates["fox-animations.glb"], 30)


class TestLibrary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = load_catalog()
        cls.entries_by_skeleton = {}
        for entry in cls.catalog["animations"]:
            cls.entries_by_skeleton.setdefault(entry["skeleton"], []).append(entry)

    def test_every_clip_is_in_the_library(self):
        self.assertEqual(len(self.catalog["animations"]), EXPECTED_TOTAL_CLIPS)

        for skeleton in SKELETONS:
            clips_in_glbs = sum(len(Glb(os.path.join(STATIC_DIR, "animations", pack.file)).document["animations"])
                                for pack in skeleton.packs)
            open_library(skeleton)
            self.assertEqual(len(bpy.data.actions), clips_in_glbs, skeleton.key)
            self.assertEqual(len(self.entries_by_skeleton[skeleton.key]), clips_in_glbs, skeleton.key)

    def test_each_library_holds_only_a_clean_rig(self):
        for skeleton in SKELETONS:
            rig = open_library(skeleton)
            rig_glb = Glb(os.path.join(STATIC_DIR, "rigs", skeleton.rig_file))

            self.assertEqual([obj.type for obj in bpy.data.objects], ["ARMATURE"], skeleton.key)
            self.assertEqual(len(rig.data.bones), len(rig_glb.joint_names()), skeleton.key)
            for leftovers in ("meshes", "images", "materials", "cameras", "collections", "textures"):
                self.assertEqual(len(getattr(bpy.data, leftovers)), 0, f"{skeleton.key}: {leftovers} left in the library")
            self.assertIsNone(rig.animation_data, f"{skeleton.key}: the rig should not have an action assigned")
            self.assertIsNotNone(rig.asset_data, f"{skeleton.key}: rig is not marked as an asset")
            self.assertEqual(tuple(rig.preview.image_size), (THUMBNAIL_SIZE, THUMBNAIL_SIZE), f"{skeleton.key}: rig preview")

    def test_actions_are_ready_to_use(self):
        catalog_ids = self.asset_catalog_ids()

        for skeleton in SKELETONS:
            rig = open_library(skeleton)
            bones = {bone.name for bone in rig.data.bones}
            entries = {entry["action"]: entry for entry in self.entries_by_skeleton[skeleton.key]}

            for action in bpy.data.actions:
                entry = entries[action.name]
                label = f"{skeleton.key}/{action.name}"
                self.assertTrue(action.use_fake_user, label)
                self.assertIsNotNone(action.asset_data, label)
                self.assertIn(action.asset_data.catalog_id, catalog_ids, label)
                self.assertEqual(action["animation_lab_fps"], entry["fps"], label)
                self.assertIsNotNone(action.preview, f"{label}: no asset preview")
                self.assertEqual(tuple(action.preview.image_size), (THUMBNAIL_SIZE, THUMBNAIL_SIZE), label)

                start, end = action.frame_range
                self.assertAlmostEqual(start, round(start), places=3, msg=label)
                self.assertEqual(round(start), entry["frame_start"], label)
                self.assertEqual(round(end), entry["frame_end"], label)

                for curve in action_fcurves(action):
                    self.assertTrue(curve.data_path.startswith('pose.bones["'), label)
                    self.assertIn(curve.data_path.split('"')[1], bones, label)
                    # the web app plays rotations, the position bone and root motion only
                    self.assertFalse(curve.data_path.endswith(".scale"), label)

                rig.animation_data_create().action = action
                self.assertIsNotNone(rig.animation_data.action_slot, f"{label}: no slot binds to the rig")

    def test_motion_matches_the_web_app(self):
        worst = 0.0

        for skeleton in SKELETONS:
            rig = open_library(skeleton)
            rig_glb = Glb(os.path.join(STATIC_DIR, "rigs", skeleton.rig_file))
            joint_names = rig_glb.joint_names()

            for pack in skeleton.packs:
                pack_glb = Glb(os.path.join(STATIC_DIR, "animations", pack.file))
                fps = pack_rate(os.path.join(STATIC_DIR, "animations", pack.file))
                bpy.context.scene.render.fps = fps
                animations = pack_glb.document["animations"]
                step = max(1, len(animations) // MOTION_SAMPLE_CLIPS_PER_PACK)

                for animation in animations[::step][:MOTION_SAMPLE_CLIPS_PER_PACK]:
                    channels = web_app_channels(pack_glb, animation, joint_names, skeleton.position_bone)
                    # moments where every kept channel has a key, so no interpolation is involved
                    shared_times = set.intersection(*(set(round(t * fps) for t in times) for times, _ in channels.values()))
                    frames = sorted(shared_times)
                    frames = frames[::max(1, len(frames) // MOTION_SAMPLE_FRAMES_PER_CLIP)][:MOTION_SAMPLE_FRAMES_PER_CLIP]

                    action = bpy.data.actions[animation["name"]]
                    rig.animation_data_create().action = action

                    for frame in frames:
                        bpy.context.scene.frame_set(frame)
                        expected = web_app_joint_positions(rig_glb, channels, frame / fps)
                        for bone in rig.pose.bones:
                            actual = rig.matrix_world @ bone.head
                            distance = (actual - gltf_to_blender(expected[bone.name])).length
                            worst = max(worst, distance)
                            self.assertLess(distance, JOINT_TOLERANCE,
                                            f"{skeleton.key}/{animation['name']} frame {frame}: {bone.name} is {distance * 1000:.3f} mm off")

        print(f"\n  motion check: worst joint difference from the web app {worst * 1000:.4f} mm")

    def test_catalog_entries_are_valid(self):
        rules = load_rules()
        ids = [entry["id"] for entry in self.catalog["animations"]]
        self.assertEqual(len(ids), len(set(ids)), "catalog ids must be unique")

        for skeleton in SKELETONS:
            open_library(skeleton)
            for entry in self.entries_by_skeleton[skeleton.key]:
                self.assertEqual(entry["blend_file"], skeleton.blend_file)
                self.assertIn(entry["action"], bpy.data.actions, entry["id"])
                self.assertIn(entry["pack"], [pack.pack for pack in skeleton.packs])
                self.assertNotEqual(entry["category"], rules["fallback"], f"{entry['id']} has no category rule")
                self.assertGreaterEqual(entry["frame_end"], entry["frame_start"])
                self.assertEqual(entry["root_motion"], entry["name"].lower().endswith("rm"))
                self.assertTrue(os.path.isfile(os.path.join(LIBRARY_DIR, entry["thumbnail"])), entry["id"])
                if entry["app_preview_video"] is not None:
                    self.assertTrue(os.path.isfile(os.path.join(STATIC_DIR, "animpreviews", entry["app_preview_video"])))

    def test_thumbnails_show_the_model(self):
        paths = [entry["thumbnail"] for entry in self.catalog["animations"]]
        paths += [entry["thumbnail"] for entry in self.catalog["skeletons"]]
        self.assertEqual(len(paths), EXPECTED_TOTAL_CLIPS + len(SKELETONS))

        lowest_coverage = 1.0
        for relative_path in paths:
            image = bpy.data.images.load(os.path.join(LIBRARY_DIR, relative_path))
            self.assertEqual(tuple(image.size), (THUMBNAIL_SIZE, THUMBNAIL_SIZE), relative_path)
            self.assertEqual(image.channels, 4, f"{relative_path}: needs a transparent background")

            pixels = numpy.empty(THUMBNAIL_SIZE * THUMBNAIL_SIZE * 4, dtype=numpy.float32)
            image.pixels.foreach_get(pixels)
            alpha = pixels.reshape(THUMBNAIL_SIZE, THUMBNAIL_SIZE, 4)[:, :, 3]
            bpy.data.images.remove(image)

            coverage = float((alpha > 0.5).mean())
            lowest_coverage = min(lowest_coverage, coverage)
            border = numpy.concatenate([alpha[0], alpha[-1], alpha[:, 0], alpha[:, -1]])
            self.assertGreater(coverage, MIN_THUMBNAIL_COVERAGE, f"{relative_path}: the model barely shows")
            self.assertLess(float(border.max()), MAX_BORDER_ALPHA, f"{relative_path}: the model is cut off at the edge")

        print(f"\n  thumbnails: {len(paths)} checked, smallest model coverage {lowest_coverage:.1%}")

    @staticmethod
    def asset_catalog_ids():
        with open(os.path.join(LIBRARY_DIR, "blender_assets.cats.txt"), encoding="utf-8") as cats_file:
            return {line.split(":")[0] for line in cats_file if re.match(r"^[0-9a-f-]{36}:", line)}


if __name__ == "__main__":
    result = unittest.main(argv=["test_library"], exit=False, verbosity=2).result
    sys.exit(0 if result.wasSuccessful() else 1)
