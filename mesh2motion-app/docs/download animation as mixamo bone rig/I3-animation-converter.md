# Implementation Phase I3: Animation converter (plus the core of I4)

**Status:** Done, not committed (branch `feature/blender-fbx-preset`)
**Date:** 2026-10-06
**Design:** [05-root-cause-and-feature-design.md](05-root-cause-and-feature-design.md) §4.2 · previous: [I2](I2-mixamo-rig-builder.md)

## Why this phase changed shape

After I2 you reported: *"I tried but it did not work for me. Use T-Pose.fbx to animate if you can."*

The most likely reason option C failed: the **Retarget page only accepts files with a mesh** ("No SkinnedMeshes found in file", `RetargetUtils.validate_skinned_mesh_has_bones`), and `T-Pose.fbx` is a skeleton-only Mixamo download. So I built the converter to work with **any** target skeleton, including **the skeleton inside your `T-Pose.fbx`**, and pulled the FBX writing (the core of I4) forward so you get files to use in Blender now.

---

## 1. Files for you to try (in this folder)

| File | Contents |
|---|---|
| `mesh2motion-on-mixamo-T-Pose-skeleton_4-clips.fbx` (0.7 MB) | Walk, Idle_A, Jog, Punch_Jab |
| `mesh2motion-on-mixamo-T-Pose-skeleton_all-87-base-clips.fbx` (13.7 MB) | all 87 Mesh2Motion base animations |

Both are **on your `T-Pose.fbx` skeleton**: same 65 bones, same names (`mixamorig:Hips` …), same rest pose and axes, same cm units, same axis declaration. Blender imports them exactly like a Mixamo "Without Skin" file.

### How to use them in Blender's NLA Editor
1. *File → Import → FBX* → `T-Pose.fbx` (or your Mixamo character / Mixamo clips as you normally do). This is the armature you animate.
2. *File → Import → FBX* → `mesh2motion-on-mixamo-T-Pose-skeleton_4-clips.fbx`. This brings in a second armature and actions named like `Armature.001|Walk`.
3. Select **your Mixamo armature** → *Dope Sheet → Action Editor* → pick `…|Walk`. It plays on the Mixamo armature directly, with no renaming.
4. *Push Down* to put it in the **NLA Editor** as a strip, next to your Mixamo action strips, and blend as usual.
5. You can delete the imported Mesh2Motion armature afterwards. To keep its actions when saving, push them to NLA strips first or press the **shield** (fake user) icon on each action.

The clips are 30 fps (Mixamo's default download rate).

---

## 2. Verified in Blender (4.5.12, headless)

One scene: your Mixamo `T-Pose.fbx` armature + our file. Our **Walk** action is assigned **directly to the Mixamo armature** (the NLA workflow), and the result is compared:

| Measure | Phase 4 (original export) | **On your T-Pose skeleton** | Rebuilt skeleton (option A, no Mixamo file) |
|---|---|---|---|
| Objects created | 1 armature (wrong names) | **1 Armature** | 1 Armature |
| Armature object scale / rotation | 1.0 / 90° turned | **0.01 / X 90° (= Mixamo)** | 0.01 / X 90° |
| Bone names identical to Mixamo | 0 / 65 | **65 / 65** | 65 / 65 |
| Walk curves that bind to the Mixamo armature as is | 0 (needs renaming) | **520 / 520** | 520 / 520 |
| **Mixamo armature playing our Walk vs our own armature** | 24.6 % off (max 43.5 %) | **0.00 %: identical** | 5.8 % (proportions only) |
| Is it still the original Mesh2Motion walk? (limb directions on the Mixamo armature vs the original) | n/a | **arms/legs ~1°**, foot 3.8°, spine/neck 9.3° | same |
| 87-clip file | n/a | **87 actions, 0 curves that fail to bind** | n/a |

The 9.3° on spine and neck isn't an error. It's the **posture difference** between the two rest poses: Mixamo's spine and neck are straighter than Mesh2Motion's. The converter keeps each bone's *change* from rest identical, so the Mixamo character keeps its own posture while doing the Mesh2Motion motion. That's how Mixamo itself retargets between characters.

---

## 3. Code

### New files (`src/lib/processes/export-to-file/mixamo/`)
| File | Purpose |
|---|---|
| `MixamoAnimationConverter.ts` | Converts Mesh2Motion clips onto a Mixamo rig. For each frame (30 fps): forward kinematics of the Mesh2Motion skeleton from its **bind pose** and the clip's own interpolants → `W_mix = W_m2m · O` with constant rest offset `O` → `local = W_parent⁻¹ · W_mix`. Hips carries root motion, **scaled by the hip-height ratio** so feet stay grounded on taller or shorter characters. End bones aren't keyed (like Mixamo). Quaternion hemisphere is kept continuous. Tracks are bound by **bone uuid** so the `:` in Mixamo names survives. |
| `MixamoFbxExportService.ts` | `export(source_meshes, clips, { target_rig?, fps? })`: build (option A) or take a target rig (option C), convert, and write the FBX with Mixamo's header: `unitScale 1` (data in cm), Y-up, Front/Coord **+1**, 30 fps, one take per clip, no Nulls. |
| `mixamo-test-helpers.ts` | Test helpers: the real Mesh2Motion rig bound to a mesh, and a clip with arm/leg/spine motion plus root motion |

### Changed
| File | Change |
|---|---|
| `MixamoRigBuilder.ts` | New `build_from_mixamo_skeleton(bones)` **adopts an existing Mixamo skeleton** as is (e.g. loaded from `T-Pose.fbx`). Accepts `mixamorig:Hips`, `mixamorigHips` (three.js strips the colon) and `mixamorig1:Hips`. Shared assembly code with the rule-based build. |

### Tests: 9 new, suite 137 → **146, all passing**
| Test | Proves |
|---|---|
| Converter, same proportions | Every one of the 65 joints of the converted rig lands **within 0.05 cm** of the Mesh2Motion joint (×100) at 3 sample times. Rotations and root motion are correct end to end through `AnimationMixer`. |
| Converter, different skeleton (Mixamo proportions) | Every animated bone's world rotation change equals its Mesh2Motion bone's, **within 0.25°** (float32 key precision) |
| Root motion | Hips travel = Mesh2Motion pelvis travel × hip-height ratio |
| Clip layout | 52 rotation tracks + 1 Hips position track, uuid-bound, 31 keys for 1 s at 30 fps, name and duration kept |
| Export service | 65 `LimbNode` named `mixamorig:*` with colon, 0 Nulls; **Hips is the only child of the scene root**; UnitScaleFactor 1, Y+/Z+/X+, TimeMode 30 fps; one AnimationStack per clip; rotation curves on 52 bones, translation on Hips only, no scale curves |
| Adopting a loaded Mixamo skeleton | Same positions and rotations for all 65 bones, whatever the name style |

Checks: ESLint clean on all new files · `tsc` no new errors · `vite build` unaffected (nothing wired to the UI yet).

---

## 4. What's left

| Phase | Work |
|---|---|
| **I4** (mostly done here) | Remaining: decide the fps option, and name the take/actions sensibly |
| **I5: UI** | In the download popup: **FBX + Blender + Mixamo naming** → `MixamoFbxExportService`. Add a **"Mixamo skeleton" upload** (skeleton-only FBX such as `T-Pose.fbx` or your Mixamo character) so the app can export onto **your exact skeleton** (option C) instead of the rebuilt one (option A). That also fixes the Retarget page refusing skeleton-only files. |
| **I6** | Your manual NLA check, the docs update, and a final Blender verification of files downloaded from the running app |

## 5. Please check
Import `T-Pose.fbx`, then `mesh2motion-on-mixamo-T-Pose-skeleton_4-clips.fbx`, assign `…|Walk` to the **Mixamo** armature and push it to the NLA. Let me know if it lines up with your Mixamo clips the way you expect. If you did something else when it "did not work", tell me what you tried so I can cover that case too.
