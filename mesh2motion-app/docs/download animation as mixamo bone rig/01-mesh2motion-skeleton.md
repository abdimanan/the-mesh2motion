# Phase 1: What the Mesh2Motion skeleton is (the source side)

**Status:** Done
**Date:** 2026-10-06
**Plan:** [00-investigation-plan.md](00-investigation-plan.md)

## Questions this phase answers

1. On `http://localhost:5173/retarget/index.html`, what is the **"Mesh2Motion Skeleton"** and what kind of bones does it have?
2. What does **"Import your rig and map the bones to continue"** mean?
3. How do Mesh2Motion bones relate to Mixamo bones?

---

## 1. How the Retarget page works

The page is called **"Use Your Rigged Model"** and is marked **Experimental** in the UI. It has two columns:

| Left column: **Mesh2Motion Skeleton** | ⇨ | Right column: **Your 3D Rig Model** |
|---|---|---|
| The **source**. A built-in skeleton chosen from a dropdown (Human by default). All of Mesh2Motion's animations were made for this skeleton. | | The **target**. The rigged model **you upload** (`.glb`, `.fbx` or `.zip`). It must contain a **SkinnedMesh**, meaning a mesh bound to bones. |

"**Import your rig and map the bones to continue**" means:

1. Upload your own rigged character (right column).
2. Tell the app which of **your** bones matches each **Mesh2Motion** bone. You can drag bones by hand or press **Auto-Map** / **✨Mixamo**.
3. Press **Continue**. The app then *retargets* the Mesh2Motion animations onto **your** skeleton so you can preview and download them.

So the downloaded file is **your uploaded model, with your skeleton, carrying the retargeted animations**. It is *not* the Mesh2Motion skeleton itself. This matters for later phases.

Evidence:
- `src/retarget/index.html:43-161`: page layout, "Mesh2Motion Skeleton" (source) and "Your 3D Rig Model" (target)
- `src/retarget/steps/StepLoadSourceSkeleton.ts:41-49`: Human rig is loaded automatically
- `src/retarget/steps/StepLoadTargetModel.ts:94-145`: upload accepts glb/fbx/zip
- `src/retarget/RetargetUtils.ts:115-134`: the upload is rejected with "No SkinnedMeshes found in file" if it has no skinned mesh

Special case: if the uploaded rig uses **exactly the same bone names** as the Mesh2Motion skeleton (meaning it is a Mesh2Motion rig you skinned in Blender), the app skips mapping and shows *"No bone mapping needed…"* (`src/retarget/retarget.ts:180-205`, `src/retarget/bone-automap/Mesh2MotionMapper.ts`). The UI tooltip says this is the **main stable workflow**.

---

## 2. The skeleton types in the dropdown

The dropdown is filled from a single list, `src/lib/RigConfig.ts`. Each entry points to a **rig file** (bones only, no mesh) and to one or more **animation files**. All of them are glTF binary files (`.glb`) exported from Blender (`Khronos glTF Blender I/O v5.1.18`).

| Dropdown | Rig file | Bones | First bones | Animation file(s) |
|---|---|---|---|---|
| **Human** (default) | `static/rigs/rig-human.glb` | **66** | root, pelvis, spine_01, spine_02, spine_03, neck_01, head | `human-base-animations.glb` (87 clips), `human-addon-animations.glb`, `human-mocap-animations.glb` |
| Fox | `rigs/rig-fox.glb` | 49 | root, Hips, Spine_1, Spine_2… | `fox-animations.glb` |
| Bird | `rigs/rig-bird.glb` | 55 | root, hips, spine_0… | `bird-animations.glb` |
| Dragon | `rigs/rig-dragon.glb` | 99 | root, hips, spine_0… | `dragon-animations.glb` |
| Kaiju | `rigs/rig-kaiju.glb` | 58 | root, Hips, Spine_1… | `kaiju-animations.glb` |
| Spider | `rigs/rig-spider.glb` | 56 | root, hips, spine_1… | `spider-animations.glb` |
| Snake | `rigs/rig-snake.glb` | 28 | root, head, head_tip… | `snake-animations.glb` |
| Fish | `rigs/rig-shark.glb` | 33 | root, pelvis, tail_1… | `shark-animations.glb` |
| Horse | `rigs/rig-horse.glb` | 56 | root, hips, spine_1… | `horse-animations.glb` |

The Blender source files for these rigs and animations are in the other repo, `../mesh2motion-assets/rigs`. The page links to it ("View M2M rigs from GitHub").

The **Bone Naming Pattern** option (Default / **Mixamo**) is shown **only for the Human skeleton** (`src/lib/processes/export-to-file/DownloadSettings.ts:64-90`). So the Mixamo feature we're investigating only applies to Human.

---

## 3. The Human skeleton: what type of bones these are

### Short answer
The Mesh2Motion Human skeleton is a **standard game-style humanoid skeleton**. Its bone names follow the **Unreal Engine Mannequin naming convention** (`pelvis`, `spine_01`, `clavicle_l`, `upperarm_l`, `lowerarm_l`, `thigh_l`, `calf_l`, `ball_l`…). In the file they are ordinary **glTF skin joints**. Once loaded in the app, each one is a three.js **`THREE.Bone`**.

It is **not** a Mixamo skeleton. It does, however, have **the same layout as Mixamo, bone for bone** (see section 4).

### Facts about it
| Property | Value |
|---|---|
| Format | glTF binary (`.glb`), exported from Blender |
| Total bones | **66**: `root` plus 65 body bones |
| Mesh in rig file | None (bones only). The display mesh is in `static/models/model-human.glb` |
| Units | **Meters** (glTF standard). Height to `head_leaf` is about **1.64 m** |
| Up axis | **Y-up** (glTF standard). The `root` bone has a −90° X rotation, which is left over from Blender's Z-up armature |
| Rest pose | **T-pose**. Arms are horizontal: `upperarm_l` y=1.446, `hand_l` y=1.439, hand x=0.75 |
| Hierarchy root | `Armature` (empty node) → `root` → `pelvis` |
| Bone name style | lowercase, `_l` / `_r` suffix, `_leaf` for end bones |

### Full Human bone hierarchy (66 bones)
```
Armature            (empty node, not a bone)
└─ root
   └─ pelvis
      ├─ spine_01
      │  └─ spine_02
      │     └─ spine_03
      │        ├─ neck_01
      │        │  └─ head
      │        │     └─ head_leaf
      │        ├─ clavicle_l
      │        │  └─ upperarm_l
      │        │     └─ lowerarm_l
      │        │        └─ hand_l
      │        │           ├─ index_01_l → index_02_l → index_03_l → index_04_leaf_l
      │        │           ├─ middle_01_l → middle_02_l → middle_03_l → middle_04_leaf_l
      │        │           ├─ pinky_01_l → pinky_02_l → pinky_03_l → pinky_04_leaf_l
      │        │           ├─ ring_01_l → ring_02_l → ring_03_l → ring_04_leaf_l
      │        │           └─ thumb_01_l → thumb_02_l → thumb_03_l → thumb_04_leaf_l
      │        └─ clavicle_r
      │           └─ upperarm_r → lowerarm_r → hand_r → (same 5 fingers, _r)
      ├─ thigh_l → calf_l → foot_l → ball_l → ball_leaf_l
      └─ thigh_r → calf_r → foot_r → ball_r → ball_leaf_r
```

The animation file `human-base-animations.glb` uses **the same 66 joints**. Its clips animate rotation, translation and scale. Only one bone per rig is allowed position (translation) keys, plus root; for Human that is `pelvis` (`RigConfig.ts`, `position_tracking_bone_name`).

---

## 4. Mesh2Motion Human compared with Mixamo

The app has a fixed table in `src/retarget/bone-automap/MixamoMapper.ts` that maps each Mesh2Motion bone to a Mixamo bone.

**Result: the 65 body bones map 1:1 onto the 65 bones in your reference `T-Pose.fbx`.** I compared the table's names with the names inside the FBX and they match exactly: no missing and no extra bones. Only `root` has no Mixamo equivalent, because Mixamo's top bone is `Hips`.

| Mesh2Motion | Mixamo (in `T-Pose.fbx`) |
|---|---|
| root | *(no equivalent)* |
| pelvis | mixamorig:Hips |
| spine_01 / spine_02 / spine_03 | mixamorig:Spine / Spine1 / Spine2 |
| neck_01 / head / head_leaf | mixamorig:Neck / Head / HeadTop_End |
| clavicle_l / upperarm_l / lowerarm_l / hand_l | mixamorig:LeftShoulder / LeftArm / LeftForeArm / LeftHand |
| thigh_l / calf_l / foot_l / ball_l / ball_leaf_l | mixamorig:LeftUpLeg / LeftLeg / LeftFoot / LeftToeBase / LeftToe_End |
| thumb_01_l … thumb_04_leaf_l | mixamorig:LeftHandThumb1 … LeftHandThumb4 |
| index / middle / ring / pinky `_01…_04_leaf_l` | mixamorig:LeftHandIndex / Middle / Ring / Pinky `1…4` |
| *(right side is the same with `_r` → `Right…`)* | |

**This is good news for the feature.** No bones need to be invented or merged. A Mixamo-style skeleton can be built straight from the Mesh2Motion Human skeleton by renaming bones and dropping or merging `root`.

### ⚠️ A naming detail that matters for later phases
| Where | How the Hips bone is spelled |
|---|---|
| Real Mixamo FBX (`T-Pose.fbx`) | `mixamorig:Hips`, **with a colon** |
| Mesh2Motion's Mixamo table | `mixamorigHips`, **no colon** |

The colon is missing because **three.js strips `:` `.` `/` `[` `]` from every node name** when it loads a file (`PropertyBinding.sanitizeNodeName`). See `node_modules/three/src/animation/PropertyBinding.js:3-4,185-189`, also used in `src/lib/io/fbx/FBXTreeParser.ts:938,975`. So inside the app a Mixamo rig is always seen as `mixamorigHips`. If the export also writes `mixamorigHips`, the file won't be name-compatible with real Mixamo animations or tools that expect `mixamorig:`. This is a **possible secondary issue**. Phase 3 will check what names are actually written, and Phase 4 will confirm in Blender.

---

## 5. How auto-mapping chooses a method

`src/retarget/bone-automap/BoneAutoMapper.ts` picks one of three strategies for **your uploaded rig**:

1. **Mixamo rig detected:** any bone name contains `mixamorig`, or at least 80% of the core Mixamo names are present. It uses the exact `MixamoMapper` table above.
2. **Rigify rig detected:** it uses the `RigifyMapper` table.
3. **Anything else:** exact names first, then "canonical slots" (joint type, side and position in chain), then loose name matching.

If the uploaded rig already *is* a Mesh2Motion rig, no mapping is needed at all.

---

## Findings

1. **"Mesh2Motion Skeleton" is the source skeleton.** All the animations are authored on it. There are 9 types; **Human** is the default and the only one where "Mixamo bone naming" is offered.
2. **The Human bones** are a 66-bone, **Unreal-Mannequin-style** humanoid skeleton (`root/pelvis/spine_01/clavicle_l/upperarm_l…`). They're stored as glTF skin joints, use meters and Y-up, and sit in a **T-pose**.
3. **It lines up 1:1 with Mixamo.** All 65 body bones have a direct Mixamo equivalent, matching the 65 bones of your `T-Pose.fbx`. Only `root` is extra.
4. **The retarget page exports *your uploaded rig*,** not the Mesh2Motion skeleton. What gets written depends on the skeleton in your upload, plus any renaming the app applies.
5. **The colon problem.** Inside three.js, Mixamo names lose their colon (`mixamorig:Hips` → `mixamorigHips`), and the app's Mixamo table uses the colon-less form.
6. Nothing in Phase 1 explains the "**empties instead of bones in Blender**" problem by itself. The source skeleton is a proper armature. The cause must be in the **export step** (Phase 3) or in the FBX structure that gets written (Phases 2 and 4).

## Evidence (files)
- `src/retarget/index.html`: page layout and texts
- `src/retarget/retarget.ts`: page controller, Mesh2Motion rig detection
- `src/retarget/steps/StepLoadSourceSkeleton.ts`: loads the source rig GLB
- `src/retarget/steps/StepLoadTargetModel.ts`: loads the user's rig; must contain a SkinnedMesh
- `src/lib/RigConfig.ts`: the list of skeleton types, rig files and animation files
- `src/lib/processes/export-to-file/DownloadSettings.ts`: Bone Naming Pattern is Human-only
- `src/retarget/bone-automap/MixamoMapper.ts`: Mesh2Motion → Mixamo name table
- `src/retarget/bone-automap/BoneAutoMapper.ts`: auto-map strategy choice
- `static/rigs/rig-human.glb`: inspected with a small GLB reader script (kept in the scratchpad, not in the repo)

## Open questions (for the next phases)
1. On the Retarget page, **what did you upload as "Your 3D Rig Model"** before downloading? Was it a Mixamo character, a Mesh2Motion rig, or something else? Since the download carries *your* skeleton, this affects what we expect in the file.
2. Does the "empties instead of bones" problem also happen on the **"Use Your Model" (`/create.html`) page**, which exports the Mesh2Motion skeleton itself? Phase 3 will check whether both pages share the same FBX export code (they both use `@comfyorg/fbx-exporter-three`).
3. Was `T-Pose.fbx` downloaded **from Mixamo** (the target we want to match)? It looks like a skeleton-only "Without Skin" file. Phase 2 will confirm.
