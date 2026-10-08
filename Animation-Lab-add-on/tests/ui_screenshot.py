"""Opens the Animation Lab tab in a real Blender window, takes a screenshot and quits.

Thumbnails only exist when Blender has a window, so this is the one check of how the panel
really looks. Started by tests/take_ui_screenshot.sh, not by the automated tests.

    blender --python ui_screenshot.py -- <output.png> [search text]
"""
import bpy
import sys

OUT = sys.argv[sys.argv.index("--") + 1]
SEARCH = sys.argv[sys.argv.index("--") + 2] if len(sys.argv) > sys.argv.index("--") + 2 else ""
steps = {"n": 0}


def view3d():
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == "VIEW_3D":
                return window, area
    return None, None


def tick():
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
        return 0.5
    bpy.ops.wm.quit_blender()
    return None


bpy.app.timers.register(tick, first_interval=1.0)
