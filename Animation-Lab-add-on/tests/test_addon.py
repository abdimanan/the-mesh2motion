"""Tests for the installed Animation Lab add-on. Run through tests/run_addon_tests.sh, which
installs the built zip into a throwaway Blender user folder first.

Background mode never draws panels, so the panel is drawn into a checking layout that fails
on unknown icons, properties and operators, the mistakes that would otherwise only show up
as a broken sidebar in a real window.
"""

import importlib
import os
import sys
import tempfile
import types
import unittest

import addon_utils
import bpy

MODULE = "bl_ext.user_default.animation_lab"
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
        addon_utils.disable(MODULE, default_set=True)
        self.assertFalse(hasattr(bpy.types, "ANIMLAB_PT_library"))
        self.assertFalse(hasattr(bpy.context.window_manager, "animation_lab"))

        addon_utils.enable(MODULE, default_set=True)
        self.assertTrue(hasattr(bpy.types, "ANIMLAB_PT_library"))
        self.assertTrue(hasattr(bpy.context.window_manager, "animation_lab"))


if __name__ == "__main__":
    result = unittest.main(argv=["test_addon"], exit=False, verbosity=2).result
    sys.exit(0 if result.wasSuccessful() else 1)
