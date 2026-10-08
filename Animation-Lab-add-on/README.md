# Animation Lab

A Blender add-on that brings the [Mesh2Motion](https://mesh2motion.org/) animation library into Blender: browse the animations, import a rig, and apply animations to an armature or push them into the NLA Editor.

**Status:** AL1 done (the animation library). The add-on itself (panels, buttons) comes in AL3–AL5. Plan and reports are in [`../docs/animation-lab/`](../docs/animation-lab/).

## Folder layout

```
Animation-Lab-add-on/
├── animation_lab/            the add-on package
│   └── library/              built by tools/build_library (not in git)
│       ├── <skeleton>.blend  one rig + all its animations as actions, marked as assets
│       ├── catalog.json      one entry per animation
│       └── blender_assets.cats.txt
├── tools/build_library/      builds the library from mesh2motion-app/static
└── tests/                    run inside Blender
```

## Build the library

Needs Blender 4.2 or newer (tested with 4.5 LTS) and the `mesh2motion-app` folder next to this one.

```bash
tools/build_library/build.sh            # all 9 skeletons, about 6 seconds
tools/build_library/build.sh human,fox  # only some
```

Blender is found from `$BLENDER`, then `blender` on the PATH, then `/Applications/Blender.app`.

## Test

```bash
tests/run_tests.sh
```

The tests check that every clip of the web app is in the library, that each library holds only a clean rig, that every action is ready to use, that the catalog is valid, and that the motion matches the web app (every joint within a quarter of a millimetre).

## How the library is made

- Each animation file is imported at its **own frame rate** (24, 30 or 60 fps, detected from the file), so every key lands on a whole frame. The rate is stored on each action (`animation_lab_fps`) and in the catalog.
- Before importing, each animation file gets the **rig's rest pose** and only the channels the **web app** plays: rotations, the position of one tracking bone (pelvis, hips or head), and root position for clips ending in `RM`. So the actions move the rig exactly as the web app does.
- Categories come from the clip names, using the rules in `tools/build_library/categories.json`.

## Licenses

- Add-on code: GPL-3.0-or-later (Blender's requirement for add-ons)
- Animations and rigs: CC0, from Mesh2Motion
