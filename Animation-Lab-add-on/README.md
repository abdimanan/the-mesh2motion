# Animation Lab

A Blender add-on that brings the [Mesh2Motion](https://mesh2motion.org/) animation library into Blender: browse the animations, import a rig, and apply animations to an armature or push them into the NLA Editor.

**Status:** AL1 (library), AL2 (thumbnails) and AL3 (installable add-on with its sidebar tab) done. Browsing and applying animations come in AL4–AL5. Plan and reports are in [`../docs/animation-lab/`](../docs/animation-lab/).

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
