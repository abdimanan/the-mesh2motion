# Animation Lab

A Blender add-on that brings the [Mesh2Motion](https://mesh2motion.org/) animation library into Blender: browse the animations, import a rig, and apply animations to an armature or push them into the NLA Editor.

**Status:** MVP complete (AL1–AL5), plus AL6 (viewport preview) and AL7 (Mixamo mode). Plan and reports are in [`../docs/animation-lab/`](../docs/animation-lab/).

## Folder layout

```
Animation-Lab-add-on/
├── animation_lab/            the add-on package (what Blender installs)
│   ├── blender_manifest.toml
│   ├── __init__.py, ui.py, properties.py, preferences.py, operators.py, previews.py, library.py
│   └── library/              built by tools/build_library (not in git)
│       ├── <skeleton>.blend  one rig + all its animations as actions, marked as assets
│       ├── catalog.json      one entry per animation
│       ├── thumbnails/       256x256 PNG per animation and per rig
│       └── blender_assets.cats.txt
├── tools/build_library/      builds the library from mesh2motion-app/static
├── tools/package_addon.sh    builds dist/animation_lab-<version>.zip
├── dist/                     the installable zip (not in git)
└── tests/                    run inside Blender
```

## Install in Blender

Needs Blender 4.4 or newer.

```bash
tools/package_addon.sh        # builds the library and dist/animation_lab-0.1.0.zip (about 45 MB)
```

Then in Blender: drag the zip into the Blender window, or *Edit → Preferences → Get Extensions → ⌄ (top right) → Install from Disk…*. Open the 3D Viewport sidebar (**N**) and pick the **Animation Lab** tab.

## Using the browser

- Pick a **skeleton** (Human, Fox, Horse…), type in **Search** (matches names, categories and tags; every word must match, e.g. `sword attack`), and pick a **category**.
- Thumbnails are shown a page at a time; use ◀ ▶ to page. Click an animation's name to select it.
- **Selected Animation** shows a larger preview, category, pack, length, frames, frame rate, root motion and tags.

## Previewing

Select an animation and click **Preview**: it loops in the viewport, on the active armature when it matches the skeleton (so you see it on your own character), otherwise on a temporary rig at the 3D cursor. Click other animations to switch. **Stop Preview** puts everything back: the armature's action and pose, the scene's preview range and frame, and removes the temporary rig. The preview also stops by itself before saving, before opening another file, when you apply an animation, and when the add-on is disabled.

## Using an animation

1. **Import Rig** adds the skeleton's Mesh2Motion rig at the 3D cursor (or select your own Mesh2Motion-rigged armature).
2. Select an animation in the browser. The panel shows whether the active armature matches ("Human Rig: 66/66 bones match").
3. **Apply** sets it as the armature's action. **Push to NLA** adds it as a strip at the current frame (on the "Animation Lab" track, or a new track when that spot is taken).
4. Tick **Mirror** first to get it with left and right swapped.

Animations are copied into your file (not linked), so it keeps working without the add-on. Applying the same animation again reuses the copy. Clips are retimed to play at their real speed at your scene's frame rate. Armatures with other bone names are refused with a message.

## Mixamo characters (Mixamo mode)

Select a **Mixamo armature** (e.g. Y Bot or any character downloaded from Mixamo) and apply or preview a **Human** animation: the panel shows "Mixamo rig: 65/65 bones, converted" and the animation is converted onto that armature. Every Mixamo bone turns exactly like its Mesh2Motion bone (Mixamo's bones have different axes, so the keys can't just be renamed), and the hips carry the movement scaled to the character's height. The result is a normal action on your armature, so it can be mixed with Mixamo clips in the NLA Editor. Names like `mixamorig:Hips`, `mixamorig1:Hips`, `mixamorig_Hips` or plain `Hips` are recognised. No Mixamo data ships with the add-on: the conversion uses your armature.

*Edit → Preferences → Add-ons → Animation Lab*: thumbnail size, animations per page, and **Match Scene Frame Rate** (on by default; off keeps a clip's own frames).

## Build the library

Needs Blender 4.2 or newer (tested with 4.5 LTS) and the `mesh2motion-app` folder next to this one.

```bash
tools/build_library/build.sh                    # all 9 skeletons + thumbnails, about 25 seconds
tools/build_library/build.sh human,fox          # only some
SKIP_THUMBNAILS=1 tools/build_library/build.sh  # library only, about 6 seconds
```

Blender is found from `$BLENDER`, then `blender` on the PATH, then `/Applications/Blender.app`.

## Test

```bash
tests/run_tests.sh          # the library (inside Blender)
tests/run_addon_tests.sh    # packages the add-on, installs it into a throwaway Blender user
                            # folder and tests the installed copy; your own Blender is not touched
tests/take_ui_screenshot.sh shot.png [search] [apply]   # manual: opens Blender with a window for
                                                        # a few seconds and screenshots the tab;
                                                        # "apply" imports the rig and applies Walk; "preview" previews Walk;
                                                        # "mixamo" applies Walk to the local Y Bot
```

The tests check that every clip of the web app is in the library, that each library holds only a clean rig, that every action is ready to use, that the catalog is valid, that the motion matches the web app (every joint within a quarter of a millimetre), and that every thumbnail shows the whole model.

## How the library is made

- Each animation file is imported at its **own frame rate** (24, 30 or 60 fps, detected from the file), so every key lands on a whole frame. The rate is stored on each action (`animation_lab_fps`) and in the catalog.
- Before importing, each animation file gets the **rig's rest pose** and only the channels the **web app** plays: rotations, the position of one tracking bone (pelvis, hips or head), and root position for clips ending in `RM`. So the actions move the rig exactly as the web app does.
- Categories come from the clip names, using the rules in `tools/build_library/categories.json`.
- **Thumbnails** are rendered in Blender (Workbench, 256x256, transparent background) with the web app's own textured models, posed at the clip's most telling frame: the one whose pose differs most from the clip's first frame. They're saved as PNGs and as the actions' asset previews.

## Licenses

- Add-on code: GPL-3.0-or-later (Blender's requirement for add-ons)
- Animations and rigs: CC0, from Mesh2Motion
