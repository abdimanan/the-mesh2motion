"""Renders a thumbnail for every animation in the Animation Lab library. Runs after build_library.py.

    blender -b --factory-startup --python render_thumbnails.py -- \
        --static ../../../mesh2motion-app/static --library ../../animation_lab/library [--only human]

For each skeleton it opens the library, borrows the skinned model from the web app's animation
files, poses it at the most telling moment of each clip and renders it with Workbench:
256x256, transparent background, so the images work on dark and light Blender themes.

Each image is written to library/thumbnails/<skeleton>/<id>.png, stored in the .blend as the
asset preview of the action (Blender's Asset Browser shows it), and recorded in catalog.json.
The borrowed model, camera and images are removed again before the library is saved.
"""

import argparse
import json
import math
import os
import shutil
import sys
import tempfile
import time

import bpy
import numpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from build_library import remove_import_leftovers  # noqa: E402
from glb_patch import write_model_only_glb  # noqa: E402
from skeletons import SKELETONS  # noqa: E402

THUMBNAIL_SIZE = 256
ICON_SIZE = 32
THUMBNAILS_FOLDER = "thumbnails"
RIG_THUMBNAIL = "_rig.png"

# three-quarter view from the character's front right, slightly from above.
# The glTF importer turns the characters to face Blender's -Y.
CAMERA_YAW = math.radians(35)
CAMERA_PITCH = math.radians(12)
FRAME_MARGIN = 1.12
# frames looked at when choosing the pose to show
POSE_SAMPLES = 30
# a borrowed model is only used when its armature matches the rig this closely (meters)
REST_POSE_TOLERANCE = 0.0001


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(description="Render Animation Lab thumbnails")
    parser.add_argument("--static", required=True, help="mesh2motion-app/static folder")
    parser.add_argument("--library", required=True, help="library folder made by build_library.py")
    parser.add_argument("--only", default="", help="comma separated skeleton keys")
    return parser.parse_args(argv)


def max_rest_offset(rig, armature):
    offset = 0.0
    for bone in rig.data.bones:
        other = armature.data.bones.get(bone.name)
        if other is not None:
            offset = max(offset, ((rig.matrix_world @ bone.head_local) - (armature.matrix_world @ other.head_local)).length)
    return offset


def borrow_model(skeleton, static_dir, rig, work_dir):
    """Imports the skinned model of the first animation file whose armature matches the rig,
    and binds it to the rig. Returns the model's mesh objects.

    The human base pack was authored on a slightly different armature, so for the human the
    model comes from the addon pack instead.
    """
    for animation_pack in skeleton.packs:
        # import the model without the clips: the library already holds actions of the same names
        model_path = os.path.join(work_dir, f"model-{animation_pack.file}")
        write_model_only_glb(os.path.join(static_dir, "animations", animation_pack.file), model_path)

        objects_before = set(bpy.data.objects)
        actions_before = set(bpy.data.actions)
        bpy.ops.import_scene.gltf(filepath=model_path)
        imported = [obj for obj in bpy.data.objects if obj not in objects_before]
        if set(bpy.data.actions) != actions_before:
            raise RuntimeError(f"{animation_pack.file}: importing the model changed the library's actions")

        armature = next(obj for obj in imported if obj.type == "ARMATURE")
        skinned = [obj for obj in imported if obj.type == "MESH" and any(mod.type == "ARMATURE" for mod in obj.modifiers)]

        if skinned and max_rest_offset(rig, armature) <= REST_POSE_TOLERANCE:
            for mesh in skinned:
                world = mesh.matrix_world.copy()
                mesh.parent = rig
                mesh.matrix_world = world
                for modifier in mesh.modifiers:
                    if modifier.type == "ARMATURE":
                        modifier.object = rig
            for obj in imported:
                if obj not in skinned:
                    bpy.data.objects.remove(obj, do_unlink=True)
            return skinned

        for obj in imported:
            bpy.data.objects.remove(obj, do_unlink=True)

    raise RuntimeError(f"{skeleton.key}: no animation file has a skinned model that matches the rig")


def setup_render(scene):
    camera = bpy.data.objects.new("Animation Lab Thumbnail Camera", bpy.data.cameras.new("Animation Lab Thumbnail Camera"))
    camera.data.type = "ORTHO"
    camera.data.clip_end = 1000
    scene.collection.objects.link(camera)
    scene.camera = camera

    render = scene.render
    render.engine = "BLENDER_WORKBENCH"
    render.resolution_x = render.resolution_y = THUMBNAIL_SIZE
    render.resolution_percentage = 100
    render.film_transparent = True
    render.image_settings.file_format = "PNG"
    render.image_settings.color_mode = "RGBA"
    # lossless; only makes the files smaller, at the cost of a slower write
    render.image_settings.compression = 100

    shading = scene.display.shading
    shading.light = "STUDIO"
    shading.color_type = "TEXTURE"  # the web app's own textures
    shading.show_cavity = True
    shading.show_object_outline = True
    scene.display.render_aa = "8"
    return camera


def camera_rotation():
    toward_camera = Vector((
        math.sin(CAMERA_YAW) * math.cos(CAMERA_PITCH),
        -math.cos(CAMERA_YAW) * math.cos(CAMERA_PITCH),
        math.sin(CAMERA_PITCH),
    ))
    return (-toward_camera).to_track_quat("-Z", "Y")


def frame_camera(camera, meshes, rotation):
    """Points the orthographic camera so the posed model fills the image."""
    depsgraph = bpy.context.evaluated_depsgraph_get()
    to_camera = numpy.array(rotation.inverted().to_matrix())
    chunks = []
    for mesh in meshes:
        # every vertex: thin parts like spider legs are easy to miss with a sample
        evaluated = mesh.evaluated_get(depsgraph)
        data = evaluated.to_mesh()
        local = numpy.empty(len(data.vertices) * 3, dtype=numpy.float64)
        data.vertices.foreach_get("co", local)
        world = numpy.array(evaluated.matrix_world)
        points = local.reshape(-1, 3) @ world[:3, :3].T + world[:3, 3]
        chunks.append(points @ to_camera.T)
        evaluated.to_mesh_clear()

    points = numpy.concatenate(chunks)
    low, high = points.min(axis=0), points.max(axis=0)
    centre = Vector(((low[0] + high[0]) / 2, (low[1] + high[1]) / 2, high[2] + 10))
    camera.rotation_euler = rotation.to_euler()
    camera.location = rotation @ centre
    camera.data.ortho_scale = max(high[0] - low[0], high[1] - low[1]) * FRAME_MARGIN


def body_shape(rig):
    """Joint positions relative to the root, so travelling through the scene does not count."""
    origin = rig.matrix_world @ rig.pose.bones[0].head
    return [(rig.matrix_world @ bone.head) - origin for bone in rig.pose.bones]


def telling_frame(scene, rig, action):
    """The frame whose pose differs most from the clip's first frame: the punch fully thrown,
    the body on the ground at the end of a death. Ties go to the frame nearest the middle."""
    start, end = (round(value) for value in action.frame_range)
    scene.frame_set(start)
    first = body_shape(rig)

    best_frame, best_score = start, -1.0
    for frame in range(start, end + 1, max(1, (end - start) // POSE_SAMPLES)):
        scene.frame_set(frame)
        score = sum((now - then).length for now, then in zip(body_shape(rig), first))
        score -= abs(frame - (start + end) / 2) * 1e-6
        if score > best_score:
            best_frame, best_score = frame, score
    return best_frame


def render_to(scene, path):
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)


def set_preview(datablock, png_path):
    """Stores the image as the datablock's asset preview (and its small icon)."""
    image = bpy.data.images.load(png_path)
    icon = image.copy()
    icon.scale(ICON_SIZE, ICON_SIZE)

    preview = datablock.preview_ensure()
    preview.image_size = (image.size[0], image.size[1])
    preview.image_pixels_float = image.pixels[:]
    preview.icon_size = (ICON_SIZE, ICON_SIZE)
    preview.icon_pixels_float = icon.pixels[:]

    bpy.data.images.remove(icon)
    bpy.data.images.remove(image)


def clear_pose(rig):
    for bone in rig.pose.bones:
        bone.matrix_basis = Matrix.Identity(4)


def render_skeleton(skeleton, static_dir, library_dir, entries, work_dir):
    blend_path = os.path.join(library_dir, skeleton.blend_file)
    bpy.ops.wm.open_mainfile(filepath=blend_path)
    scene = bpy.context.scene
    library_fps = scene.render.fps
    library_engine = scene.render.engine
    rig = bpy.data.objects[skeleton.rig_name]

    meshes = borrow_model(skeleton, static_dir, rig, work_dir)
    camera = setup_render(scene)
    rotation = camera_rotation()
    out_dir = os.path.join(library_dir, THUMBNAILS_FOLDER, skeleton.key)
    os.makedirs(out_dir, exist_ok=True)

    animation_data = rig.animation_data_create()
    for entry in entries:
        action = bpy.data.actions[entry["action"]]
        animation_data.action = action
        scene.render.fps = action.get("animation_lab_fps", library_fps)

        scene.frame_set(telling_frame(scene, rig, action))
        frame_camera(camera, meshes, rotation)

        file_name = entry["id"].split("/", 1)[1] + ".png"
        path = os.path.join(out_dir, file_name)
        render_to(scene, path)
        set_preview(action, path)
        entry["thumbnail"] = f"{THUMBNAILS_FOLDER}/{skeleton.key}/{file_name}"

    # the rig itself, at rest
    animation_data.action = None
    clear_pose(rig)
    scene.frame_set(scene.frame_start)
    frame_camera(camera, meshes, rotation)
    rig_path = os.path.join(out_dir, RIG_THUMBNAIL)
    render_to(scene, rig_path)
    set_preview(rig, rig_path)

    # leave the library as build_library.py made it, plus the previews
    for obj in meshes + [camera]:
        bpy.data.objects.remove(obj, do_unlink=True)
    rig.animation_data_clear()
    scene.render.fps = library_fps
    scene.render.engine = library_engine
    remove_import_leftovers()

    for stale in (blend_path, blend_path + "1"):
        if os.path.exists(stale):
            os.remove(stale)
    bpy.ops.wm.save_as_mainfile(filepath=blend_path, compress=True, check_existing=False)

    return f"{THUMBNAILS_FOLDER}/{skeleton.key}/{RIG_THUMBNAIL}"


def main():
    args = parse_args()
    static_dir = os.path.abspath(args.static)
    library_dir = os.path.abspath(args.library)
    catalog_path = os.path.join(library_dir, "catalog.json")

    with open(catalog_path, encoding="utf-8") as catalog_file:
        catalog = json.load(catalog_file)

    wanted = {key.strip() for key in args.only.split(",") if key.strip()}
    skeletons = [skeleton for skeleton in SKELETONS if not wanted or skeleton.key in wanted]

    started = time.time()
    rendered = 0
    work_dir = tempfile.mkdtemp(prefix="animation-lab-thumbnails-")
    for skeleton in skeletons:
        entries = [entry for entry in catalog["animations"] if entry["skeleton"] == skeleton.key]
        rig_thumbnail = render_skeleton(skeleton, static_dir, library_dir, entries, work_dir)
        for skeleton_entry in catalog["skeletons"]:
            if skeleton_entry["key"] == skeleton.key:
                skeleton_entry["thumbnail"] = rig_thumbnail
        rendered += len(entries) + 1
        print(f"thumbnails: {skeleton.key:8s} {len(entries) + 1:4d} images")

    with open(catalog_path, "w", encoding="utf-8") as catalog_file:
        json.dump(catalog, catalog_file, indent=2, ensure_ascii=False)
        catalog_file.write("\n")
    shutil.rmtree(work_dir, ignore_errors=True)

    print(f"thumbnails: {rendered} images in {time.time() - started:.1f} s -> {os.path.join(library_dir, THUMBNAILS_FOLDER)}")


if __name__ == "__main__":
    main()
