"""Opens the Animation Lab tab in a real Blender window, takes a screenshot and quits.

Thumbnails only exist when Blender has a window, so this is the one check of how the panel
really looks. Started by tests/take_ui_screenshot.sh, not by the automated tests.

    blender --python ui_screenshot.py -- <output.png> [search text] [apply]

With "apply" it also imports the Human rig, applies Walk to it and shows a frame mid-stride.
"""
import sys
import traceback

import bpy

OUT = sys.argv[sys.argv.index("--") + 1]
ARGS = sys.argv[sys.argv.index("--") + 1:]
SEARCH = ARGS[1] if len(ARGS) > 1 else ""
APPLY = len(ARGS) > 2 and ARGS[2] == "apply"
steps = {"n": 0}
# never leave a window open: give up after this many steps
MAX_STEPS = 12


def view3d():
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == "VIEW_3D":
                return window, area
    return None, None


def tick():
    """Runs one step; any error is printed and Blender quits, so no window is left open."""
    try:
        next_interval = step()
    except Exception:  # noqa: BLE001
        print("UI SCREENSHOT FAILED")
        traceback.print_exc()
        next_interval = None
    if next_interval is None or steps["n"] >= MAX_STEPS:
        bpy.ops.wm.quit_blender()
        return None
    return next_interval


def step():
    steps["n"] += 1
    window, area = view3d()
    if area is None:
        return 0.5
    if steps["n"] == 1:
        area.spaces.active.show_region_ui = True
        state = bpy.context.window_manager.animation_lab
        state.skeleton = "human"
        state.search = SEARCH
        state.selected = "human/walk"
        if APPLY:
            with bpy.context.temp_override(window=window, area=area):
                for obj in list(bpy.data.objects):
                    bpy.data.objects.remove(obj)
                bpy.ops.animation_lab.import_rig()
                bpy.ops.animation_lab.apply_animation(mode="ACTION")
                bpy.context.scene.frame_set(20)
            window_region = next(region for region in area.regions if region.type == "WINDOW")
            with bpy.context.temp_override(window=window, area=area, region=window_region):
                bpy.ops.view3d.view_selected()
        return 0.5
    if steps["n"] == 2:
        for region in area.regions:
            if region.type == "UI":
                try:
                    region.active_panel_category = "Animation Lab"
                except Exception as error:  # noqa: BLE001
                    print("TAB", error)
        area.tag_redraw()
        return 1.5
    if steps["n"] == 3:
        area.tag_redraw()
        return 1.5
    if steps["n"] == 4:
        with bpy.context.temp_override(window=window, area=area):
            bpy.ops.screen.screenshot(filepath=OUT)
        print("SCREENSHOT", OUT)
    return None


bpy.app.timers.register(tick, first_interval=1.0)
