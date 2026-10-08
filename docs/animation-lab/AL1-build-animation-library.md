# AL1: Build the animation library

**Status:** ✅ Done
**Date:** 2026-10-08
**Feasibility study:** [00-animation-lab-feasibility.md](00-animation-lab-feasibility.md)

## Goal

Turn the Mesh2Motion web library into **Blender-native libraries** for the add-on:
- read the animation and rig **GLB** files from `mesh2motion-app/static/`
- prepare one clean **rig** per skeleton
- save every animation as a Blender **action**, in one **`.blend` per skeleton**
- generate **`catalog.json`** describing every animation

## Result

| Skeleton | Actions | Bones | `.blend` size |
|---|---|---|---|
| Human | **178** (base 87, addon 75, mocap 16) | 66 | 17.0 MB |
| Fox | 14 | 49 | 1.0 MB |
| Horse | 14 | 56 | 1.5 MB |
| Kaiju | 10 | 58 | 1.9 MB |
| Spider | 10 | 56 | 0.8 MB |
| Snake | 8 | 28 | 0.5 MB |
| Fish | 7 | 33 | 0.4 MB |
| Bird | 5 | 55 | 0.2 MB |
| Dragon | 5 | 99 | 0.5 MB |
| **Total** | **251** | | **23 MB** |

- **Build time:** about 6 seconds for everything (`tools/build_library/build.sh`)
- **Build warnings:** none
- **Tests:** 9/9 passing (`tests/run_tests.sh`)
- **Motion vs the web app:** every joint within **0.095 mm**

### Categories (generated from clip names, none left uncategorised)
| Category | Clips | Examples |
|---|---|---|
| Locomotion | 48 | Walk, Jog, Run_Stealth, Crouch_Walk, Flying Forward, Swim… |
| Idle | 34 | Idle_A, Idle_FoldArms, Crouch_Idle, Sleeping, Meditate… |
| Combat | 34 | Punch_Jab, Sword_Attack, Melee_Hook, Defend, Kick… |
| Acrobatics | 32 | Backflip, Climb Ladder, Roll, Dodge_left, Ledge Hang… |
| Emotes | 26 | Dance Charleston, Greeting, Head Nod, Victory, Cheer… |
| Weapons & Magic | 25 | Bow Release, Pistol_Shoot, Spell_Simple, Two-hand Blast, Golf… |
| Reactions | 23 | Death_A, Hit_Head, Hit_Knockback, Dizzy… |
| Interaction | 20 | Chest_Open, Chop_Tree, Farm_Harvest, Sitting_Idle, Push… |
| Poses | 9 | Rest Pose (one per skeleton) |

Other catalog facts: **15** root-motion clips; **251/251** linked to their web-app preview video; frame rates **24 fps (197 clips), 30 fps (38), 60 fps (16)**.

---

## What we found while building (and fixed)

### 1. The packs use three different frame rates
The plan assumed 30 fps for everything. Reading the key times in the files showed otherwise:

| Rate | Packs |
|---|---|
| 24 fps | human base, human addon, bird, dragon, fish (shark), snake, spider |
| 30 fps | fox, horse, kaiju |
| 60 fps | human mocap |

Many clips are keyed on every other frame, so the "most common gap between keys" is misleading. The build therefore uses **the smallest standard rate at which every key of the file lands on a whole frame** (`glb_info.pack_rate`). Each pack is imported at its own rate. The rate is stored on each action as the custom property **`animation_lab_fps`** and in the catalog, so the add-on can play every clip at the right speed in any scene (AL5).

### 2. The human base pack was authored on a slightly different armature
Its armature's rest pose differs from the human rig by up to **34 mm** (spine, neck, calves). The addon and mocap packs match the rig exactly. Imported as is, base clips came out **2–6° off** on the rig (measured).

**What the web app does** (`AnimationUtility.clean_track_data`): it plays a clip on the rig by setting each bone's local transform straight from the keys, and keeps only:
- rotation keys
- position keys of one **tracking bone** (pelvis for Human/Fish, hips for most animals, head for Snake)
- root position keys, only for clips whose name ends in **`rm`** (root motion)

**The fix** (`glb_patch.py`): before importing, each animation file is rewritten so its joints carry **the rig's rest pose**, in the node transforms *and* the inverse bind matrices (Blender's importer builds the rest pose from the latter), and only the channels the web app plays are kept. Blender then builds actions that move the rig **exactly like the web app**.

### 3. Smaller things
- **Dragon** clips animated a `DRV_root` bone that isn't in the rig. Those keys are dropped.
- **Scale keys** are dropped (the web app ignores them).
- **Root motion** follows the web app's rule (name ends in `rm`), so the catalog matches what the user sees in the app.
- Blender kept `.blend1` backups when rebuilding. The build now removes the old file first.
- Two category misfires (Dance Body Roll → Acrobatics, Crouch_Idle → Locomotion) were fixed with early rules.

---

## What was built

```
Animation-Lab-add-on/
├── README.md
├── .gitignore                       library outputs are built, not committed
├── animation_lab/library/           (generated)
│   ├── human.blend … horse.blend    rig + actions, marked as assets
│   ├── catalog.json
│   └── blender_assets.cats.txt      lets Blender's Asset Browser show the library too
├── tools/build_library/
│   ├── build.sh                     one command: finds Blender, builds everything
│   ├── build_library.py             runs inside Blender
│   ├── skeletons.py                 skeleton list, mirrors the web app's RigConfig.ts
│   ├── glb_info.py                  detects each file's frame rate
│   ├── glb_patch.py                 rig rest pose + web app channels
│   ├── catalog_rules.py             names → ids, words, categories, tags
│   └── categories.json              editable category rules
└── tests/
    ├── run_tests.sh
    └── test_library.py
```

### Inside each `.blend`
- **One armature**, named `<Skeleton> Rig` (e.g. `Human Rig`), marked as an asset (author Mesh2Motion, license CC0-1.0)
- **Every clip as an action**: fake user (kept when unassigned), marked as an asset with catalog `Animation Lab/<Skeleton>/<Category>`, tags, description, author and license, slot bound to the rig, `animation_lab_fps` property
- Nothing else: no meshes, materials or images

### A catalog entry
```json
{
  "id": "human/walk", "name": "Walk", "action": "Walk",
  "skeleton": "human", "pack": "base", "category": "Locomotion",
  "tags": ["walk", "human", "base"],
  "frame_start": 0, "frame_end": 40, "fps": 24, "duration": 1.667,
  "root_motion": false, "blend_file": "human.blend",
  "thumbnail": null, "app_preview_video": "human/dark_Walk.mp4"
}
```
`thumbnail` is filled in AL2.

---

## Tests (`tests/run_tests.sh`, inside Blender): 9/9 ✅

| Test | Checks |
|---|---|
| Skeleton list matches the web app | `skeletons.py` vs `RigConfig.ts`: rig files, animation files, tracking bone. A skeleton added to the web app fails this test until it's added here. |
| Frame rates | Detection gives 24 / 60 / 30 fps for human base / mocap / fox |
| Every clip is in the library | 251 total; per skeleton, `.blend` actions = GLB clips = catalog entries |
| Each library holds only a clean rig | 1 armature, bone count = rig GLB joints, 0 meshes/images/materials, rig marked as asset |
| Actions are ready to use | fake user, asset with a catalog id from `blender_assets.cats.txt`, fps property = catalog, whole-frame start, frame range = catalog, every curve's bone exists, no scale curves, a slot binds to the rig |
| **Motion matches the web app** | Independent of the build: plays the **original** GLB clips with the web app's rules using plain glTF maths and compares every joint with the library rig posed by Blender. 4 clips per pack × 4 frames, all 9 skeletons. **Worst: 0.095 mm** (limit 0.25 mm; the rig files themselves disagree with themselves by up to 0.027 mm at rest, from float rounding). |
| Catalog entries are valid | unique ids, files and actions exist, no uncategorised clips, root motion rule, preview video files exist |
| Category rules | sample names land in the right categories |

---

## Deviations from the plan
| Plan | Done instead | Why |
|---|---|---|
| Everything at 30 fps | Each pack at its own rate, stored per action | The files are 24, 30 and 60 fps |
| Import the GLBs as they are | Patch them first (rig rest pose, web app channels) | Otherwise base clips are 2–6° off and extra channels play that the web app ignores |
| Root motion detected from root travel | Web app rule: name ends in `rm` | Matches what the user sees in the app |
| Category "Weapons" | "Weapons & Magic" | Spells, blasts and levitation belong together |

## Notes for later phases
- **AL2:** thumbnails go into `catalog.json` (`thumbnail`), and as asset previews in the `.blend` files.
- **AL5:** when applying a clip, use its `animation_lab_fps` to play it at the right speed (scene fps or NLA strip scale).
- **Release (AL8):** the library isn't in git; the release zip is built from `build.sh`.
