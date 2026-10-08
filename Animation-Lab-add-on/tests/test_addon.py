"""Tests for the installed Animation Lab add-on. Run through tests/run_addon_tests.sh, which
installs the built zip into a throwaway Blender user folder first.

Background mode never draws panels, so the panel is drawn into a checking layout that fails
on unknown icons, properties and operators, the mistakes that would otherwise only show up
as a broken sidebar in a real window.
"""

import importlib
import math
import os
import sys
import tempfile
import types
import unittest

import addon_utils
import bpy
from mathutils import Quaternion, Vector

MODULE = "bl_ext.user_default.animation_lab"
# a real Mixamo character, only on the developer's machine (Mixamo files are not in the repo)
Y_BOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "mesh2motion-app", "docs",
                     "download animation as mixamo bone rig", "Y Bot.fbx")
EXPECTED_ANIMATIONS = 251
EXPECTED_SKELETONS = 9

VALID_ICONS = set(bpy.types.UILayout.bl_rna.functions["label"].parameters["icon"].enum_items.keys())


class CheckingLayout:
    """Stands in for bpy.types.UILayout and checks every call a panel makes."""

    def __init__(self, test, calls=None):
        self.test = test
        self.calls = calls if calls is not None else []

    def _icon(self, icon):
        self.test.assertIn(icon, VALID_ICONS, f"unknown icon {icon!r}")

    def label(self, text="", icon="NONE", **_kwargs):
        self._icon(icon)
        self.test.assertIsInstance(text, str)
        self.calls.append(("label", text))

    def prop(self, data, property_name, icon="NONE", **_kwargs):
        self._icon(icon)
        self.test.assertIn(property_name, data.bl_rna.properties.keys(), f"no property {property_name!r}")
        self.calls.append(("prop", property_name))

    def operator(self, idname, icon="NONE", text=None, depress=False, **_kwargs):
        self._icon(icon)
        category, name = idname.split(".")
        self.test.assertTrue(hasattr(getattr(bpy.ops, category), name), f"no operator {idname!r}")
        self.calls.append(("operator", idname, text))
        if depress:
            self.calls.append(("pressed", text))
        return OperatorButton(self.test, getattr(getattr(bpy.ops, category), name), self.calls)

    def template_icon(self, icon_value=0, scale=1.0):
        self.test.assertGreater(icon_value, 0, "template_icon needs a loaded icon")
        self.calls.append(("template_icon", icon_value))

    def box(self):
        return CheckingLayout(self.test, self.calls)

    def grid_flow(self, **_kwargs):
        return CheckingLayout(self.test, self.calls)

    def column(self, **_kwargs):
        return CheckingLayout(self.test, self.calls)

    def row(self, **_kwargs):
        return CheckingLayout(self.test, self.calls)


class OperatorButton:
    """What layout.operator() returns: checks every property the panel sets on the button."""

    def __init__(self, test, operator, calls):
        object.__setattr__(self, "_test", test)
        object.__setattr__(self, "_names", set(operator.get_rna_type().properties.keys()))
        object.__setattr__(self, "_calls", calls)

    def __setattr__(self, name, value):
        self._test.assertIn(name, self._names, f"operator has no property {name!r}")
        self._calls.append(("set", name, value))


class DrawingAs:
    """Calls a draw method as `owner` would, but with a checking layout."""

    def __init__(self, owner, layout):
        self._owner = owner
        self.layout = layout

    def __getattr__(self, name):
        return getattr(self._owner, name)


def draw(test, draw_function, owner=None):
    layout = CheckingLayout(test)
    draw_function(DrawingAs(owner, layout) if owner is not None else types.SimpleNamespace(layout=layout), bpy.context)
    return layout.calls


class TestInstalledAddon(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.addon = importlib.import_module(MODULE)
        cls.library = importlib.import_module(MODULE + ".library")

    def test_installed_and_enabled(self):
        self.assertIn(MODULE, bpy.context.preferences.addons.keys())
        # the copy Blender installed, not the source folder
        user_folder = os.environ["BLENDER_USER_RESOURCES"]
        self.assertTrue(os.path.realpath(self.addon.__file__).startswith(os.path.realpath(user_folder)))

    def test_library_ships_inside_the_addon(self):
        library = self.library
        self.assertIsNone(library.load_error())
        self.assertEqual(len(library.animations()), EXPECTED_ANIMATIONS)
        self.assertEqual(len(library.skeletons()), EXPECTED_SKELETONS)
        for skeleton in library.skeletons():
            self.assertTrue(os.path.isfile(library.file_path(skeleton["blend_file"])), skeleton["key"])
            self.assertTrue(os.path.isfile(library.file_path(skeleton["thumbnail"])), skeleton["key"])
        for animation in library.animations():
            self.assertTrue(os.path.isfile(library.file_path(animation["thumbnail"])), animation["id"])

    def test_registered_types(self):
        for panel in ("ANIMLAB_PT_library", "ANIMLAB_PT_selection", "ANIMLAB_PT_skeleton"):
            self.assertTrue(hasattr(bpy.types, panel), panel)
            self.assertEqual(getattr(bpy.types, panel).bl_category, "Animation Lab")
        self.assertTrue(hasattr(bpy.context.window_manager, "animation_lab"))
        self.assertEqual(bpy.ops.animation_lab.reload_library(), {"FINISHED"})

    def test_skeleton_and_category_choices(self):
        state = bpy.context.window_manager.animation_lab
        properties = importlib.import_module(MODULE + ".properties")
        items = [item[0] for item in properties.skeleton_items(state, bpy.context)]
        self.assertEqual(len(items), EXPECTED_SKELETONS)
        self.assertEqual(items[0], "human")

        state.skeleton = "human"
        state.category = "Locomotion"
        self.assertEqual(state.category, "Locomotion")

        state.skeleton = "fox"
        self.assertEqual(state.category, "ALL", "changing skeleton resets the category")
        fox_categories = properties.category_items(state, bpy.context)
        self.assertEqual(fox_categories[0][1], "All categories (14)")

    def test_preferences(self):
        preferences = bpy.context.preferences.addons[MODULE].preferences
        self.assertEqual(preferences.thumbnail_scale, 4.5)
        calls = draw(self, type(preferences).draw, owner=preferences)
        self.assertIn(("label", f"{EXPECTED_ANIMATIONS} animations for {EXPECTED_SKELETONS} skeletons"), calls)

    def setUp(self):
        state = bpy.context.window_manager.animation_lab
        state.skeleton = "human"
        state.category = "ALL"
        state.search = ""
        state.selected = ""
        bpy.context.preferences.addons[MODULE].preferences.page_size = 12

    def selects(self, calls):
        return [call for call in calls if call[0] == "operator" and call[1] == "animation_lab.select_animation"]

    def test_panel_draws(self):
        calls = draw(self, bpy.types.ANIMLAB_PT_library.draw)
        self.assertIn(("label", "178 animations"), calls)
        self.assertIn(("label", "1 / 15"), calls)  # 178 animations, 12 per page
        self.assertEqual(len(self.selects(calls)), 12)
        self.assertIn(("prop", "search"), calls)

        # Blender hands out icon ids only when it has a UI, so in background mode the panel
        # leaves the picture out. What can be checked: the rig thumbnail was loaded in full.
        previews = importlib.import_module(MODULE + ".previews")
        thumbnail = self.library.file_path(self.library.animations("human")[0]["thumbnail"])
        previews.icon_id(thumbnail)
        self.assertEqual(tuple(previews._collection[thumbnail].image_size), (256, 256))
        if not bpy.app.background:
            self.assertIn("template_icon", [call[0] for call in calls], "the rig thumbnail is shown")
        self.assertIn(("prop", "skeleton"), calls)
        self.assertIn(("prop", "category"), calls)

    def test_search(self):
        library = self.library
        names = lambda results: {entry["name"] for entry in results}
        self.assertIn("Walk", names(library.search("human", None, "walk")))
        self.assertIn("Crouch_Walk", names(library.search("human", None, "walk")))
        self.assertEqual(names(library.search("human", None, "sword attack")) - {n for n in names(library.animations("human")) if "Sword" in n and "Attack" in n}, set())
        self.assertTrue(library.search("human", None, "sword attack"))
        self.assertEqual(len(library.search("human", None, "mocap")), 16)  # the pack name is a tag
        self.assertTrue(all(entry["category"] == "Locomotion" for entry in library.search("human", "Locomotion", "walk")))
        self.assertEqual(library.search("human", None, "no such animation"), [])
        self.assertEqual(len(library.search("fox")), 14)

    def test_browser_shows_the_search_results(self):
        state = bpy.context.window_manager.animation_lab
        state.search = "dance"
        calls = draw(self, bpy.types.ANIMLAB_PT_library.draw)
        shown = {call[2] for call in self.selects(calls)}
        self.assertTrue(shown)
        self.assertTrue(all("Dance" in name for name in shown), shown)

        state.search = "no such animation"
        calls = draw(self, bpy.types.ANIMLAB_PT_library.draw)
        self.assertIn(("label", "No animations match"), calls)

    def test_paging(self):
        state = bpy.context.window_manager.animation_lab
        self.assertEqual(bpy.ops.animation_lab.change_page(step=-1), {"FINISHED"})
        self.assertEqual(state.page, 0, "no page before the first")

        for _ in range(20):
            bpy.ops.animation_lab.change_page(step=1)
        self.assertEqual(state.page, 14, "no page after the last")
        calls = draw(self, bpy.types.ANIMLAB_PT_library.draw)
        self.assertIn(("label", "15 / 15"), calls)
        self.assertEqual(len(self.selects(calls)), 178 - 14 * 12)

        state.search = "walk"
        self.assertEqual(state.page, 0, "a new search starts at the first page")

        bpy.context.preferences.addons[MODULE].preferences.page_size = 4
        state.search = ""
        self.assertIn(("label", "1 / 45"), draw(self, bpy.types.ANIMLAB_PT_library.draw))

    def test_selecting_an_animation(self):
        state = bpy.context.window_manager.animation_lab
        calls = draw(self, bpy.types.ANIMLAB_PT_selection.draw)
        self.assertIn(("label", "Click an animation to select it"), calls)

        self.assertEqual(bpy.ops.animation_lab.select_animation(animation_id="human/walk"), {"FINISHED"})
        self.assertEqual(state.selected, "human/walk")
        calls = draw(self, bpy.types.ANIMLAB_PT_selection.draw)
        self.assertIn(("label", "Walk"), calls)
        self.assertIn(("label", "Locomotion · base pack"), calls)
        self.assertIn(("label", "1.67 s · 41 frames at 24 fps"), calls)

        state.search = "walk"
        browser = draw(self, bpy.types.ANIMLAB_PT_library.draw)
        self.assertEqual([call for call in browser if call[0] == "pressed"], [("pressed", "Walk")],
                         "the selected animation is drawn pressed, and only it")

        self.assertEqual(bpy.ops.animation_lab.select_animation(animation_id="human/nope"), {"CANCELLED"})
        self.assertEqual(state.selected, "human/walk")

        state.skeleton = "fox"
        self.assertEqual(state.selected, "", "changing skeleton clears the selection")

    def test_skeleton_panel(self):
        calls = draw(self, bpy.types.ANIMLAB_PT_skeleton.draw)
        self.assertIn(("label", "178 animations"), calls)
        self.assertIn(("label", "Human Rig, 66 bones"), calls)

    # --- AL5: importing rigs and applying animations -------------------------------------

    def clean_scene(self):
        preview = importlib.import_module(MODULE + ".preview")
        if preview.is_active():
            preview.stop(bpy.context)
        for obj in list(bpy.data.objects):
            bpy.data.objects.remove(obj)
        for action in list(bpy.data.actions):
            bpy.data.actions.remove(action)
        bpy.context.scene.render.fps = 24
        bpy.context.scene.render.fps_base = 1
        bpy.context.scene.frame_current = 1
        bpy.context.window_manager.animation_lab.mirror = False
        bpy.context.preferences.addons[MODULE].preferences.match_scene_fps = True

    def import_rig(self):
        self.assertEqual(bpy.ops.animation_lab.import_rig(), {"FINISHED"})
        return bpy.context.active_object

    def apply_selected(self, mode="ACTION"):
        return bpy.ops.animation_lab.apply_animation(mode=mode)

    def joints(self, rig, frame):
        bpy.context.scene.frame_set(frame)
        return {bone.name: rig.matrix_world @ bone.head for bone in rig.pose.bones}

    def lab_actions(self, animation_id):
        return [action for action in bpy.data.actions if action.get("animation_lab_id") == animation_id]

    def test_import_rig(self):
        self.clean_scene()
        bpy.context.scene.cursor.location = (1.0, 2.0, 0.0)
        rig = self.import_rig()

        self.assertEqual(rig.type, "ARMATURE")
        self.assertEqual(rig.name, "Human Rig")
        self.assertEqual(len(rig.data.bones), 66)
        self.assertEqual(tuple(rig.location), (1.0, 2.0, 0.0))
        self.assertIsNone(rig.asset_data, "appended rigs are not left marked as assets")
        self.assertIn(rig.name, bpy.context.scene.objects)
        self.assertTrue(rig.select_get())

        second = self.import_rig()
        self.assertNotEqual(second, rig)
        self.assertEqual(len([obj for obj in bpy.data.objects if obj.type == "ARMATURE"]), 2)
        bpy.context.scene.cursor.location = (0.0, 0.0, 0.0)

    def test_apply_as_active_action(self):
        self.clean_scene()
        rig = self.import_rig()
        bpy.ops.animation_lab.select_animation(animation_id="human/walk")

        self.assertEqual(self.apply_selected(), {"FINISHED"})
        action = rig.animation_data.action
        self.assertEqual(action.name, "Walk")
        self.assertIsNotNone(rig.animation_data.action_slot)
        self.assertEqual(action["animation_lab_fps"], 24)
        self.assertEqual(tuple(round(value) for value in action.frame_range), (0, 40))
        self.assertIsNone(action.asset_data)

        # the pose really changes over the clip
        self.assertNotEqual(self.joints(rig, 0)["hand_l"], self.joints(rig, 20)["hand_l"])

        self.assertEqual(self.apply_selected(), {"FINISHED"})
        self.assertEqual(len(self.lab_actions("human/walk")), 1, "applying again reuses the action")

    def test_animation_is_retimed_to_the_scene_frame_rate(self):
        self.clean_scene()
        bpy.ops.animation_lab.select_animation(animation_id="human/walk")
        at_24 = self.import_rig()
        self.apply_selected()

        bpy.context.scene.render.fps = 30
        at_30 = self.import_rig()
        self.apply_selected()

        action = at_30.animation_data.action
        self.assertEqual(action["animation_lab_fps"], 30)
        self.assertEqual(tuple(round(value) for value in action.frame_range), (0, 50))  # 40 frames at 24 = 50 at 30
        self.assertEqual(len(self.lab_actions("human/walk")), 2, "one copy per frame rate")

        # the same moment (0.833 s) is frame 20 at 24 fps and frame 25 at 30 fps
        offset = at_30.location - at_24.location
        expected = self.joints(at_24, 20)
        actual = self.joints(at_30, 25)
        worst = max((actual[name] - offset - expected[name]).length for name in expected)
        self.assertLess(worst, 1e-5)

    def test_frame_rate_matching_can_be_switched_off(self):
        self.clean_scene()
        bpy.context.preferences.addons[MODULE].preferences.match_scene_fps = False
        bpy.context.scene.render.fps = 30
        rig = self.import_rig()
        bpy.ops.animation_lab.select_animation(animation_id="human/walk")
        self.apply_selected()
        self.assertEqual(tuple(round(value) for value in rig.animation_data.action.frame_range), (0, 40))
        self.assertEqual(rig.animation_data.action["animation_lab_fps"], 24)

    def test_push_to_nla(self):
        self.clean_scene()
        rig = self.import_rig()
        bpy.ops.animation_lab.select_animation(animation_id="human/walk")

        bpy.context.scene.frame_current = 10
        self.assertEqual(self.apply_selected("NLA"), {"FINISHED"})
        tracks = rig.animation_data.nla_tracks
        self.assertEqual(len(tracks), 1)
        self.assertEqual(tracks[0].name, "Animation Lab")
        strip = tracks[0].strips[0]
        self.assertEqual(strip.frame_start, 10)
        self.assertEqual(strip.action.name, "Walk")
        self.assertIsNotNone(strip.action_slot)

        self.apply_selected("NLA")  # same spot: needs a new track
        self.assertEqual(len(tracks), 2)

        bpy.context.scene.frame_current = 100
        self.apply_selected("NLA")  # free spot on the first track
        self.assertEqual(len(tracks), 2)
        self.assertEqual(len(tracks[0].strips), 2)

    def test_mirror(self):
        self.clean_scene()
        apply = importlib.import_module(MODULE + ".apply")
        for animation_id in ("human/walk", "human/dodge_left_rm"):
            bpy.ops.animation_lab.select_animation(animation_id=animation_id)
            bpy.context.window_manager.animation_lab.mirror = False
            normal = self.import_rig()
            self.apply_selected()
            bpy.context.window_manager.animation_lab.mirror = True
            mirrored = self.import_rig()
            self.apply_selected()

            action = mirrored.animation_data.action
            self.assertTrue(action["animation_lab_mirrored"])
            self.assertTrue(action.name.endswith("(mirrored)"))

            start, end = (round(value) for value in action.frame_range)
            for frame in range(start, end + 1, max(1, (end - start) // 5)):
                left = self.joints(normal, frame)
                right = self.joints(mirrored, frame)
                for name, position in left.items():
                    reflected = Vector((-position.x, position.y, position.z))
                    self.assertLess((reflected - right[apply.mirror_bone_name(name)]).length, 0.0001,
                                    f"{animation_id} frame {frame}: {name}")
            for obj in (normal, mirrored):
                bpy.data.objects.remove(obj)

    def test_refuses_other_armatures(self):
        self.clean_scene()
        armature = bpy.data.objects.new("Some Rig", bpy.data.armatures.new("Some Rig"))
        bpy.context.collection.objects.link(armature)
        bpy.context.view_layer.objects.active = armature
        bpy.ops.animation_lab.select_animation(animation_id="human/walk")

        with self.assertRaises(RuntimeError):  # operator errors are raised when called from Python
            self.apply_selected()
        self.assertEqual(self.lab_actions("human/walk"), [], "nothing is added to the file")

    def test_apply_needs_an_animation_and_an_armature(self):
        self.clean_scene()
        self.assertFalse(bpy.ops.animation_lab.apply_animation.poll(), "no armature")
        self.import_rig()
        self.assertFalse(bpy.ops.animation_lab.apply_animation.poll(), "no animation selected")
        bpy.ops.animation_lab.select_animation(animation_id="human/walk")
        self.assertTrue(bpy.ops.animation_lab.apply_animation.poll())

    def test_selection_panel_with_an_armature(self):
        self.clean_scene()
        self.import_rig()
        bpy.ops.animation_lab.select_animation(animation_id="human/walk")
        calls = draw(self, bpy.types.ANIMLAB_PT_selection.draw)
        self.assertIn(("label", "Human Rig: 66/66 bones match"), calls)
        self.assertIn(("operator", "animation_lab.apply_animation", "Apply"), calls)
        self.assertIn(("set", "mode", "NLA"), calls)
        self.assertIn(("prop", "mirror"), calls)

    # --- AL6: previewing in the viewport ---------------------------------------------------

    def preview(self):
        return importlib.import_module(MODULE + ".preview")

    def test_preview_on_a_matching_armature_puts_everything_back(self):
        self.clean_scene()
        scene = bpy.context.scene
        rig = self.import_rig()
        user_pose = Quaternion((0.9, 0.1, 0.3, 0.0)).normalized()  # a pose the user set
        rig.pose.bones["upperarm_l"].rotation_quaternion = user_pose
        scene.use_preview_range = True  # Blender only keeps a set preview range reliably while it is on
        scene.frame_preview_start, scene.frame_preview_end = 5, 60
        scene.use_preview_range = False
        scene.frame_current = 7
        bpy.ops.animation_lab.select_animation(animation_id="human/walk")

        self.assertEqual(bpy.ops.animation_lab.preview_start(), {"FINISHED"})
        self.assertTrue(self.preview().is_active())
        self.assertEqual(self.preview().target(), rig, "plays on the user's armature")
        self.assertEqual(rig.animation_data.action.name, "Walk")
        self.assertTrue(scene.use_preview_range)
        self.assertEqual((scene.frame_preview_start, scene.frame_preview_end), (0, 40), "loops the clip")

        self.assertEqual(bpy.ops.animation_lab.preview_stop(), {"FINISHED"})
        self.assertFalse(self.preview().is_active())
        self.assertIsNone(rig.animation_data, "the rig had no animation before")
        self.assertLess(rig.pose.bones["upperarm_l"].rotation_quaternion.rotation_difference(user_pose).angle, 1e-5)
        self.assertFalse(scene.use_preview_range)
        self.assertEqual((scene.frame_preview_start, scene.frame_preview_end), (5, 60))
        self.assertEqual(scene.frame_current, 7)

    def test_preview_gives_back_the_previous_action(self):
        self.clean_scene()
        rig = self.import_rig()
        bpy.ops.animation_lab.select_animation(animation_id="human/jog")
        self.apply_selected()
        jog = rig.animation_data.action

        bpy.ops.animation_lab.select_animation(animation_id="human/walk")
        bpy.ops.animation_lab.preview_start()
        self.assertEqual(rig.animation_data.action.name, "Walk")
        bpy.ops.animation_lab.preview_stop()
        self.assertEqual(rig.animation_data.action, jog)
        self.assertIsNotNone(rig.animation_data.action_slot)

    def test_preview_without_an_armature_uses_a_temporary_rig(self):
        self.clean_scene()
        bpy.context.view_layer.objects.active = None
        bpy.ops.animation_lab.select_animation(animation_id="human/walk")

        bpy.ops.animation_lab.preview_start()
        temporary = self.preview().target()
        self.assertTrue(self.preview().is_temporary_rig())
        self.assertTrue(temporary.get("animation_lab_preview"))
        self.assertTrue(temporary.show_in_front)
        name, armature_data = temporary.name, temporary.data.name

        bpy.ops.animation_lab.preview_stop()
        self.assertNotIn(name, bpy.data.objects, "the temporary rig is removed")
        self.assertNotIn(armature_data, bpy.data.armatures)

    def test_clicking_another_animation_switches_the_preview(self):
        self.clean_scene()
        rig = self.import_rig()
        bpy.ops.animation_lab.select_animation(animation_id="human/walk")
        bpy.ops.animation_lab.preview_start()
        bpy.ops.animation_lab.select_animation(animation_id="human/jog")
        self.assertTrue(self.preview().is_active())
        self.assertEqual(rig.animation_data.action.name, "Jog")
        self.assertEqual(self.preview().animation_id(), "human/jog")

        bpy.context.window_manager.animation_lab.mirror = True
        bpy.ops.animation_lab.preview_start()
        self.assertEqual(rig.animation_data.action.name, "Jog (mirrored)")
        bpy.ops.animation_lab.preview_stop()

    def test_apply_ends_the_preview_and_keeps_the_animation(self):
        self.clean_scene()
        rig = self.import_rig()
        bpy.ops.animation_lab.select_animation(animation_id="human/walk")
        bpy.ops.animation_lab.preview_start()
        self.apply_selected()
        self.assertFalse(self.preview().is_active())
        self.assertEqual(rig.animation_data.action.name, "Walk", "not undone by the preview stopping")

    def test_preview_stops_before_saving(self):
        self.clean_scene()
        bpy.context.view_layer.objects.active = None
        bpy.ops.animation_lab.select_animation(animation_id="human/walk")
        bpy.ops.animation_lab.preview_start()
        name = self.preview().target().name
        self.preview()._stop_before_save()
        self.assertFalse(self.preview().is_active())
        self.assertNotIn(name, bpy.data.objects)

    def test_preview_controls_in_the_panel(self):
        self.clean_scene()
        self.import_rig()
        bpy.ops.animation_lab.select_animation(animation_id="human/walk")
        calls = draw(self, bpy.types.ANIMLAB_PT_selection.draw)
        self.assertIn(("operator", "animation_lab.preview_start", None), calls)

        bpy.ops.animation_lab.preview_start()
        calls = draw(self, bpy.types.ANIMLAB_PT_selection.draw)
        self.assertIn(("label", "Previewing on Human Rig"), calls)
        self.assertIn(("operator", "animation_lab.preview_stop", None), calls)
        bpy.ops.animation_lab.preview_stop()

    # --- AL7: Mixamo mode -------------------------------------------------------------------

    def mixamo(self):
        return importlib.import_module(MODULE + ".mixamo")

    def make_mixamo_rig(self, roll=False, prefix="mixamorig:"):
        """A Mixamo-style armature built from the library rig: Mixamo names, and with roll=True
        bones rolled so their axes differ the way Mixamo's differ from Mesh2Motion's."""
        rig = self.import_rig()
        rig.name = "Mixamo Test Rig"
        for m2m, mixamo_name in self.mixamo().MIXAMO_FROM_M2M.items():
            rig.data.bones[m2m].name = prefix + mixamo_name
        if roll:
            bpy.ops.object.mode_set(mode="EDIT")
            for bone in rig.data.edit_bones:
                if "Arm" in bone.name or "Hand" in bone.name or "Shoulder" in bone.name:
                    bone.roll += math.pi / 2
                elif "Leg" in bone.name or "Foot" in bone.name or "Toe" in bone.name:
                    bone.roll += math.pi
                elif "Spine" in bone.name or "Neck" in bone.name:
                    bone.roll += 0.5
            bpy.ops.object.mode_set(mode="OBJECT")
        return rig

    def assert_same_motion(self, target, source, frames, tolerance=1e-5):
        names = {m2m: mixamo_name for m2m, mixamo_name in self.mixamo().MIXAMO_FROM_M2M.items()}
        target_names = self.mixamo().mixamo_bones(target)
        for frame in frames:
            bpy.context.scene.frame_set(frame)
            for m2m, mixamo_name in names.items():
                expected = source.matrix_world @ source.pose.bones[m2m].head
                actual = target.matrix_world @ target.pose.bones[target_names[mixamo_name]].head
                self.assertLess((actual - expected).length, tolerance, f"frame {frame}: {mixamo_name}")

    def converted_on(self, target, animation_id="human/walk"):
        bpy.context.view_layer.objects.active = target
        bpy.ops.animation_lab.select_animation(animation_id=animation_id)
        self.assertEqual(self.apply_selected(), {"FINISHED"})
        return target.animation_data.action

    def test_mixamo_armatures_are_recognised(self):
        self.clean_scene()
        for prefix in ("mixamorig:", "mixamorig1:", "mixamorig_", "mixamorig", ""):
            rig = self.make_mixamo_rig(prefix=prefix)
            self.assertTrue(self.mixamo().is_mixamo(rig), repr(prefix))
            self.assertEqual(self.mixamo().matching_bones(rig), (65, 65), repr(prefix))
            bpy.data.objects.remove(rig)
        self.assertFalse(self.mixamo().is_mixamo(self.import_rig()), "a Mesh2Motion rig is not Mixamo")

    def test_converted_motion_on_a_mixamo_named_rig(self):
        self.clean_scene()
        source = self.import_rig()
        bpy.ops.animation_lab.select_animation(animation_id="human/walk")
        self.apply_selected()
        target = self.make_mixamo_rig()
        action = self.converted_on(target)
        self.assertEqual(action.name, "Walk (Mixamo)")
        self.assert_same_motion(target, source, range(0, 41, 4))

    def test_conversion_compensates_for_different_bone_axes(self):
        # the same joints but rolled bones: only a real per-bone conversion keeps the motion
        self.clean_scene()
        source = self.import_rig()
        bpy.ops.animation_lab.select_animation(animation_id="human/sword_attack")
        self.apply_selected()
        target = self.make_mixamo_rig(roll=True)
        self.converted_on(target, "human/sword_attack")
        self.assert_same_motion(target, source, range(0, 47, 5))

    def test_root_motion_on_a_mixamo_rig(self):
        self.clean_scene()
        source = self.import_rig()
        bpy.ops.animation_lab.select_animation(animation_id="human/dodge_left_rm")
        self.apply_selected()
        target = self.make_mixamo_rig(roll=True)
        self.converted_on(target, "human/dodge_left_rm")
        start, end = (round(value) for value in target.animation_data.action.frame_range)
        self.assert_same_motion(target, source, range(start, end + 1, 4))

    def test_mixamo_action_is_reused_and_mirrorable(self):
        self.clean_scene()
        target = self.make_mixamo_rig()
        first = self.converted_on(target)
        self.assertIs(self.converted_on(target), first, "converted once per armature")

        bpy.context.window_manager.animation_lab.mirror = True
        mirrored = self.converted_on(target)
        self.assertEqual(mirrored.name, "Walk (Mixamo, mirrored)")

        bpy.context.window_manager.animation_lab.mirror = False
        bpy.context.scene.frame_current = 30
        self.assertEqual(self.apply_selected("NLA"), {"FINISHED"})
        self.assertEqual(target.animation_data.nla_tracks[0].strips[0].action, first)

    def test_mixamo_mode_is_for_human_animations_only(self):
        self.clean_scene()
        target = self.make_mixamo_rig()
        bpy.context.view_layer.objects.active = target
        bpy.context.window_manager.animation_lab.skeleton = "fox"
        bpy.ops.animation_lab.select_animation(animation_id="fox/run")
        with self.assertRaises(RuntimeError):
            self.apply_selected()

    def test_preview_on_a_mixamo_rig(self):
        self.clean_scene()
        target = self.make_mixamo_rig()
        bpy.context.view_layer.objects.active = target
        bpy.ops.animation_lab.select_animation(animation_id="human/walk")
        bpy.ops.animation_lab.preview_start()
        self.assertEqual(self.preview().target(), target, "plays on the Mixamo rig itself")
        self.assertEqual(target.animation_data.action.name, "Walk (Mixamo)")
        bpy.ops.animation_lab.preview_stop()
        self.assertIsNone(target.animation_data)

    def test_panel_with_a_mixamo_rig(self):
        self.clean_scene()
        target = self.make_mixamo_rig()
        bpy.context.view_layer.objects.active = target
        bpy.ops.animation_lab.select_animation(animation_id="human/walk")
        calls = draw(self, bpy.types.ANIMLAB_PT_selection.draw)
        self.assertIn(("label", "Mixamo Test Rig: Mixamo rig: 65/65 bones, converted"), calls)

    @unittest.skipUnless(os.path.isfile(Y_BOT), "the Y Bot Mixamo character is only on the developer's machine")
    def test_mixamo_y_bot(self):
        self.clean_scene()
        bpy.context.scene.render.fps = 30
        objects_before = set(bpy.data.objects)
        bpy.ops.import_scene.fbx(filepath=Y_BOT)
        y_bot = next(obj for obj in bpy.data.objects if obj not in objects_before and obj.type == "ARMATURE")
        y_bot.animation_data.action = None
        for bone in y_bot.pose.bones:
            bone.matrix_basis.identity()

        source = self.import_rig()
        bpy.ops.animation_lab.select_animation(animation_id="human/walk")
        self.apply_selected()
        self.converted_on(y_bot)

        def world_rotation(obj, matrix):
            return (obj.matrix_world @ matrix).to_3x3().normalized().to_quaternion()

        rest_target = {bone.name: world_rotation(y_bot, bone.matrix_local) for bone in y_bot.data.bones}
        rest_source = {bone.name: world_rotation(source, bone.matrix_local) for bone in source.data.bones}
        worst = 0.0
        for frame in range(0, 51, 5):
            bpy.context.scene.frame_set(frame)
            for m2m, mixamo_name in self.mixamo().MIXAMO_FROM_M2M.items():
                bone = y_bot.pose.bones["mixamorig:" + mixamo_name]
                change_target = world_rotation(y_bot, bone.matrix) @ rest_target[bone.name].inverted()
                change_source = world_rotation(source, source.pose.bones[m2m].matrix) @ rest_source[m2m].inverted()
                angle = math.degrees(change_target.rotation_difference(change_source).angle) % 360
                worst = max(worst, min(angle, 360 - angle))  # q and -q are the same rotation
        self.assertLess(worst, 0.01, "every Y Bot bone turns exactly like its Mesh2Motion bone")

    def test_panel_draws_without_a_library(self):
        library = self.library
        real_folder = library.LIBRARY_DIR
        try:
            library.LIBRARY_DIR = tempfile.mkdtemp()
            library.reload()
            calls = draw(self, bpy.types.ANIMLAB_PT_library.draw)
            self.assertIn(("label", "Animation library not found"), calls)
            self.assertEqual(bpy.ops.animation_lab.reload_library(), {"CANCELLED"})
        finally:
            library.LIBRARY_DIR = real_folder
            library.reload()
        self.assertIsNone(library.load_error())

    def test_disable_and_enable_again(self):
        # a running preview on a temporary rig is cleaned up when the add-on is disabled
        bpy.context.view_layer.objects.active = None
        bpy.context.window_manager.animation_lab.selected = "human/walk"
        bpy.ops.animation_lab.preview_start()
        temporary_name = importlib.import_module(MODULE + ".preview").target().name

        addon_utils.disable(MODULE, default_set=True)
        self.assertNotIn(temporary_name, bpy.data.objects)
        self.assertFalse(hasattr(bpy.types, "ANIMLAB_PT_library"))
        self.assertFalse(hasattr(bpy.context.window_manager, "animation_lab"))

        addon_utils.enable(MODULE, default_set=True)
        self.assertTrue(hasattr(bpy.types, "ANIMLAB_PT_library"))
        self.assertTrue(hasattr(bpy.context.window_manager, "animation_lab"))


if __name__ == "__main__":
    result = unittest.main(argv=["test_addon"], exit=False, verbosity=2).result
    sys.exit(0 if result.wasSuccessful() else 1)
