"""Builds the Animation Lab library: one .blend per skeleton plus catalog.json.

Runs inside Blender:

    blender -b --factory-startup --python build_library.py -- \
        --static ../../../mesh2motion-app/static --out ../../animation_lab/library [--only human,fox]

Usually started through build.sh, which finds Blender and fills in the paths.

For each skeleton it imports the rig GLB (keeping only the armature), then every animation
GLB of that skeleton. Each animation GLB is first rewritten by glb_patch so it carries the
rig's rest pose and only the channels the web app plays; that way the actions reproduce the
web app's motion on the rig. The glTF importer creates one action per clip; those actions are
kept, re-pointed at the clean rig, given a fake user and marked as assets, and everything
else the import brought in (preview meshes, materials, the duplicate armature) is removed.
"""

import argparse
import json
import os
import re
import shutil
import sys
import tempfile
import time
import uuid

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from catalog_rules import category_for, clip_slug, load_rules, tags_for  # noqa: E402
from glb_info import pack_rate  # noqa: E402
from glb_patch import is_root_motion_clip, patch_animation_glb  # noqa: E402
from skeletons import SKELETONS  # noqa: E402

CATALOG_FORMAT_VERSION = 1
# custom property on every action: the frame rate its keys were made at
FPS_PROPERTY = "animation_lab_fps"
ROOT_CATALOG = "Animation Lab"
CATALOG_UUID_NAMESPACE = uuid.UUID("6f1f6a52-5b4d-4bb7-9a37-0a1d1c3e9b10")

# rig and animation files should share the exact rest pose; more than this is reported (meters)
REST_POSE_TOLERANCE = 0.0001


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(description="Build the Animation Lab library")
    parser.add_argument("--static", required=True, help="mesh2motion-app/static folder")
    parser.add_argument("--out", required=True, help="output library folder")
    parser.add_argument("--only", default="", help="comma separated skeleton keys to build")
    return parser.parse_args(argv)


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def set_scene_fps(fps):
    # the glTF importer turns key times into frames with the scene rate, so this has to match
    # the rate the clips were keyed at for every key to land on a whole frame
    scene = bpy.context.scene
    scene.render.fps = fps
    scene.render.fps_base = 1.0


def import_glb(path):
    """Imports a GLB and returns the objects and actions it created."""
    objects_before = set(bpy.data.objects)
    actions_before = set(bpy.data.actions)
    bpy.ops.import_scene.gltf(filepath=path)
    new_objects = [obj for obj in bpy.data.objects if obj not in objects_before]
    new_actions = [action for action in bpy.data.actions if action not in actions_before]
    return new_objects, new_actions


def only_armature(objects, source):
    armatures = [obj for obj in objects if obj.type == "ARMATURE"]
    if len(armatures) != 1:
        raise RuntimeError(f"{source}: expected 1 armature, found {len(armatures)}")
    return armatures[0]


def remove_objects(objects):
    for obj in objects:
        bpy.data.objects.remove(obj, do_unlink=True)


def action_fcurves(action):
    """F-curves of a single-slot action, through the layered action API (Blender 4.4+)."""
    curves = []
    for layer in action.layers:
        for strip in layer.strips:
            for channelbag in strip.channelbags:
                curves.extend(channelbag.fcurves)
    return curves


def bone_of(curve):
    return curve.data_path.split('"')[1] if curve.data_path.startswith('pose.bones["') else None


def remove_curves_for_missing_bones(action, rig_bones):
    """Drops keys for bones the rig does not have. Returns the names of those bones."""
    missing = set()
    for layer in action.layers:
        for strip in layer.strips:
            for channelbag in strip.channelbags:
                for curve in list(channelbag.fcurves):
                    bone = bone_of(curve)
                    if bone is not None and bone not in rig_bones:
                        missing.add(bone)
                        channelbag.fcurves.remove(curve)
    return missing


def max_rest_offset(rig, other_armature):
    """Largest distance between matching bone heads of two armatures at rest (meters)."""
    offset = 0.0
    for bone in rig.data.bones:
        other = other_armature.data.bones.get(bone.name)
        if other is not None:
            here = rig.matrix_world @ bone.head_local
            there = other_armature.matrix_world @ other.head_local
            offset = max(offset, (here - there).length)
    return offset


def remove_import_leftovers():
    """Everything the imports and renders brought in that the library does not need."""
    # the glTF importer files objects it skips under an empty collection of this name
    for collection in [collection for collection in bpy.data.collections if collection.name.startswith("glTF_not_exported")]:
        bpy.data.collections.remove(collection)
    for image in [image for image in bpy.data.images if image.type == "RENDER_RESULT"]:
        bpy.data.images.remove(image)
    # meshes, materials and images nothing uses any more
    bpy.data.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)


def catalog_uuid(path):
    return str(uuid.uuid5(CATALOG_UUID_NAMESPACE, path))


def preview_video(static_dir, skeleton, clip_name):
    relative = f"{skeleton.preview_folder}/dark_{clip_name}.mp4"
    return relative if os.path.isfile(os.path.join(static_dir, "animpreviews", relative)) else None


def build_skeleton(skeleton, static_dir, out_dir, rules, catalog_paths, work_dir):
    reset_scene()
    report = {"skeleton": skeleton.key, "warnings": [], "notes": []}

    rig_path = os.path.join(static_dir, "rigs", skeleton.rig_file)
    rig_objects, _ = import_glb(rig_path)
    rig = only_armature(rig_objects, skeleton.rig_file)
    remove_objects([obj for obj in rig_objects if obj is not rig])
    rig.name = skeleton.rig_name
    rig.data.name = skeleton.rig_name
    rig_bones = {bone.name for bone in rig.data.bones}

    rigs_catalog = f"{ROOT_CATALOG}/{skeleton.display_name}"
    catalog_paths.add(rigs_catalog)
    rig.asset_mark()
    rig.asset_data.catalog_id = catalog_uuid(rigs_catalog)
    rig.asset_data.description = f"Mesh2Motion {skeleton.display_name} rig. Apply the {skeleton.display_name} animations to it."
    rig.asset_data.author = "Mesh2Motion"
    rig.asset_data.license = "CC0-1.0"

    entries = []
    action_names = set()

    clips_per_fps = {}

    for animation_pack in skeleton.packs:
        source = os.path.join(static_dir, "animations", animation_pack.file)
        fps = pack_rate(source)
        set_scene_fps(fps)

        patched = os.path.join(work_dir, f"{skeleton.key}-{animation_pack.file}")
        patch = patch_animation_glb(source, rig_path, patched, skeleton.position_bone)
        if patch["rests_changed"]:
            report["notes"].append(f"{animation_pack.file}: {patch['rests_changed']} joints put on the rig's rest pose")
        if patch["duplicates_dropped"]:
            report["notes"].append(f"{animation_pack.file}: {patch['duplicates_dropped']} duplicate channels dropped")
        imported_objects, imported_actions = import_glb(patched)
        imported_armature = only_armature(imported_objects, animation_pack.file)

        rest_offset = max_rest_offset(rig, imported_armature)
        if rest_offset > REST_POSE_TOLERANCE:
            report["warnings"].append(f"{animation_pack.file}: rest pose differs from the rig by {rest_offset * 1000:.2f} mm")

        for action in imported_actions:
            # keep the action when its importer armature is deleted below
            action.use_fake_user = True

            clip_name = action.name
            if clip_name in action_names or re.search(r"\.\d{3}$", clip_name):
                clip_name = re.sub(r"\.\d{3}$", "", clip_name)
                action.name = f"{clip_name} ({animation_pack.pack})"
                report["warnings"].append(f"duplicate clip name '{clip_name}' in {animation_pack.file}, saved as '{action.name}'")
            action_names.add(action.name)

            # the importer named the slot after its own armature object; point it at the rig
            for slot in action.slots:
                slot.name_display = rig.name

            missing_bones = remove_curves_for_missing_bones(action, rig_bones)
            if missing_bones:
                report["notes"].append(f"{action.name}: dropped keys for bones the rig does not have: {sorted(missing_bones)}")

            action[FPS_PROPERTY] = fps
            clips_per_fps[fps] = clips_per_fps.get(fps, 0) + 1

            frame_start, frame_end = action.frame_range
            start, end = round(frame_start), round(frame_end)
            if abs(frame_start - start) > 1e-3:
                report["warnings"].append(f"{action.name}: starts between frames ({frame_start:.3f})")

            root_motion = is_root_motion_clip(clip_name)
            category = category_for(clip_name, rules)
            tags = tags_for(clip_name, skeleton.key, animation_pack.pack, root_motion)

            action_catalog = f"{ROOT_CATALOG}/{skeleton.display_name}/{category}"
            catalog_paths.add(action_catalog)
            action.asset_mark()
            action.asset_data.catalog_id = catalog_uuid(action_catalog)
            action.asset_data.description = f"{clip_name}: Mesh2Motion {skeleton.display_name} animation ({animation_pack.pack} pack)"
            action.asset_data.author = "Mesh2Motion"
            action.asset_data.license = "CC0-1.0"
            for tag in tags:
                action.asset_data.tags.new(tag, skip_if_exists=True)

            entries.append({
                "id": f"{skeleton.key}/{clip_slug(action.name)}",
                "name": clip_name,
                "action": action.name,
                "skeleton": skeleton.key,
                "pack": animation_pack.pack,
                "category": category,
                "tags": tags,
                "frame_start": start,
                "frame_end": end,
                "fps": fps,
                "duration": round((end - start) / fps, 3),
                "root_motion": root_motion,
                "blend_file": skeleton.blend_file,
                "thumbnail": None,
                "app_preview_video": preview_video(static_dir, skeleton, clip_name),
            })

        remove_objects(imported_objects)

    remove_import_leftovers()

    # the library opens at the rate most of its clips were made at
    set_scene_fps(max(clips_per_fps, key=clips_per_fps.get))

    blend_path = os.path.join(out_dir, skeleton.blend_file)
    # saving over an existing file makes Blender keep the old one as .blend1
    for stale in (blend_path, blend_path + "1"):
        if os.path.exists(stale):
            os.remove(stale)
    bpy.ops.wm.save_as_mainfile(filepath=blend_path, compress=True, check_existing=False)

    report.update({
        "actions": len(entries),
        "bones": len(rig_bones),
        "bone_names": [bone.name for bone in rig.data.bones],
        "blend_bytes": os.path.getsize(blend_path),
    })
    return entries, report


def write_asset_catalogs(out_dir, catalog_paths):
    """blender_assets.cats.txt: lets Blender's Asset Browser show the library's catalogs."""
    paths = set()
    for path in catalog_paths:
        parts = path.split("/")
        paths.update("/".join(parts[:index]) for index in range(1, len(parts) + 1))

    lines = [
        "# This is an Asset Catalog Definition file for Blender.",
        "# Generated by Animation Lab tools/build_library. Do not edit by hand.",
        "",
        "VERSION 1",
        "",
    ]
    lines += [f"{catalog_uuid(path)}:{path}:{path.replace('/', '-')}" for path in sorted(paths)]

    with open(os.path.join(out_dir, "blender_assets.cats.txt"), "w", encoding="utf-8") as cats_file:
        cats_file.write("\n".join(lines) + "\n")


def main():
    args = parse_args()
    static_dir = os.path.abspath(args.static)
    out_dir = os.path.abspath(args.out)
    os.makedirs(out_dir, exist_ok=True)

    wanted = {key.strip() for key in args.only.split(",") if key.strip()}
    skeletons = [skeleton for skeleton in SKELETONS if not wanted or skeleton.key in wanted]
    rules = load_rules()

    started = time.time()
    catalog_paths = set()
    animations = []
    reports = []

    work_dir = tempfile.mkdtemp(prefix="animation-lab-build-")
    try:
        for skeleton in skeletons:
            entries, report = build_skeleton(skeleton, static_dir, out_dir, rules, catalog_paths, work_dir)
            animations += entries
            reports.append(report)
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)

    skeleton_entries = [
        {
            "key": skeleton.key,
            "display_name": skeleton.display_name,
            "rig": skeleton.rig_name,
            "blend_file": skeleton.blend_file,
            "bones": report["bones"],
            "animations": report["actions"],
            "thumbnail": None,
            # the add-on checks an armature against these before applying an animation
            "position_bone": skeleton.position_bone,
            "bone_names": report["bone_names"],
        }
        for skeleton, report in zip(skeletons, reports)
    ]

    # a partial build (--only) keeps the other skeletons' entries from the existing catalog
    catalog_path = os.path.join(out_dir, "catalog.json")
    built = {skeleton.key for skeleton in skeletons}
    if wanted and os.path.exists(catalog_path):
        with open(catalog_path, encoding="utf-8") as catalog_file:
            previous = json.load(catalog_file)
        skeleton_entries += [entry for entry in previous["skeletons"] if entry["key"] not in built]
        animations += [entry for entry in previous["animations"] if entry["skeleton"] not in built]

    order = {skeleton.key: index for index, skeleton in enumerate(SKELETONS)}
    skeleton_entries.sort(key=lambda entry: order[entry["key"]])
    animations.sort(key=lambda entry: (order[entry["skeleton"]], entry["name"].lower()))

    catalog = {
        "format_version": CATALOG_FORMAT_VERSION,
        "license": "CC0-1.0",
        "source": "Mesh2Motion (mesh2motion-app/static)",
        "skeletons": skeleton_entries,
        "animations": animations,
    }

    with open(catalog_path, "w", encoding="utf-8") as catalog_file:
        json.dump(catalog, catalog_file, indent=2, ensure_ascii=False)
        catalog_file.write("\n")

    # asset catalogs for every skeleton in the catalog, not only the ones just built
    display_names = {skeleton.key: skeleton.display_name for skeleton in SKELETONS}
    all_paths = {f"{ROOT_CATALOG}/{display_names[entry['key']]}" for entry in skeleton_entries}
    all_paths |= {f"{ROOT_CATALOG}/{display_names[entry['skeleton']]}/{entry['category']}" for entry in animations}
    write_asset_catalogs(out_dir, all_paths)

    # summary
    print("\n=== Animation Lab library build ===")
    for report in reports:
        print(f"{report['skeleton']:8s} {report['actions']:4d} actions  {report['bones']:3d} bones  {report['blend_bytes'] / 1e6:5.2f} MB")
        for warning in report["warnings"]:
            print(f"         WARNING {warning}")
        for note in report["notes"]:
            print(f"         note: {note}")

    categories = {}
    for entry in animations:
        categories.setdefault(entry["category"], []).append(entry["id"])
    print("categories: " + ", ".join(f"{name} {len(ids)}" for name, ids in sorted(categories.items())))
    uncategorised = categories.get(rules["fallback"], [])
    if uncategorised:
        print(f"{rules['fallback']} ({len(uncategorised)}): " + ", ".join(uncategorised))
    print(f"total: {len(animations)} animations in {time.time() - started:.1f} s -> {out_dir}")


if __name__ == "__main__":
    main()
