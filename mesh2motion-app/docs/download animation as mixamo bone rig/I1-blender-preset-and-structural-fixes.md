# Implementation Phase I1: Blender preset + structural fixes

**Status:** Done, not committed (branch `feature/blender-fbx-preset`)
**Date:** 2026-10-06
**Design:** [05-root-cause-and-feature-design.md](05-root-cause-and-feature-design.md) §4.3, §4.4, §6

## What I1 had to deliver

| Item | Root cause fixed |
|---|---|
| Add **Blender** to the FBX coordinate presets (Unreal · Unity · **Blender**) | RC3 (100× too small), RC4 (turned 180°) |
| Full FBX: bones must not hang off the Mesh | RC2 (Blender imported nothing) |
| Skeleton-only: rest pose = bind pose, not the frame on screen | RC5 |
| Mixamo renaming must find bones that sit beside the mesh | RC9 (tracks dropped) |
| Warn when GLB + Skeleton only is picked | RC1 (66 empties) |

---

## 1. Code changes

### New files (`src/lib/processes/export-to-file/`)
| File | Purpose |
|---|---|
| `FbxExportPresetOptions.ts` | `fbx_exporter_options_for_preset()` maps the UI preset to exporter options. **Blender → `{ preset: 'blender', axisForward: '-Z' }`**: meters + `UnitScaleFactor 100`, Y-up, Front/Coord sign **+1** (same declaration as Mixamo). Unreal/Unity are passed through unchanged. |
| `FbxBoneHierarchyService.ts` | `lift_bones_out_of_meshes(scene)` temporarily re-parents any bone whose parent is a mesh onto the mesh's parent (world transform kept with `attach()`), and returns a restore function. Runs only for FBX. GLB is untouched. |
| `ExportRestPoseService.ts` | `apply_bind_pose(skinned_meshes)` poses the bones at the pose that leaves the skin undeformed, worked out from `bindMatrix` / `boneInverses` and the bind mode, and returns a restore function. Stays correct when the model was scaled after binding (Retarget page), which native `Skeleton.pose()` gets wrong. |

### Changed files
| File | Change |
|---|---|
| `DownloadSettings.ts` | `FbxExportPreset.Blender = 'blender'` added (Unreal stays the default, so existing behaviour is unchanged). GLB-skeleton warning visibility logic. |
| `DOMUtilities.ts` | Warning note under **Contents**: *"A GLB without the mesh has no skin, so Blender imports the bones as empties. Use FBX to get an armature."* |
| `styles.css` | FBX preset grid now 3 columns (was 2, so a third button would wrap). `.download-settings-note` style. |
| `ExportBoneNamingService.ts` | Renames bones via `skinned_mesh.skeleton.bones` **and** the mesh subtree, so bones beside the mesh are renamed too. |
| `StepExportToFile.ts` (Create page) | Uses `fbx_exporter_options_for_preset()`; lifts bones out of meshes around the FBX export; applies the bind pose for skeleton-only exports. Everything is restored afterwards. |
| `StepExportRetargetedAnimations.ts` (Retarget page) | Same three changes. |

### Tests added (16 new; suite 113 → **129, all passing**)
| Test file | What it proves |
|---|---|
| `FbxExportPresetOptions.test.ts` | Unreal/Unity unchanged; a Blender export **parsed back with the repo's FBX parser** has `UnitScaleFactor 100` and Up/Front/Coord = Y+/Z+/X+ (Mixamo's declaration) |
| `FbxBoneHierarchyService.test.ts` | Bone lifted beside the mesh with an identical world matrix; restore gives the exact original parent and local transform; bones already beside the mesh are left alone; **a parsed FBX has no `LimbNode` whose parent is a `Mesh`** |
| `ExportRestPoseService.test.ts` | Mid-animation skeleton → bind pose, checked with three.js's own `applyBoneTransform` (mesh undeformed); still correct after the model is scaled ×0.01 post-bind; restore gives the previous pose back |
| `ExportBoneNamingService.test.ts` | Bones beside the mesh are renamed; **tracks survive the export cleanup** (they were all dropped before); names restored |
| `DownloadSettings.test.ts` | Real popup markup: presets are `unreal, unity, blender`, default Unreal; Blender is picked up when selected; GLB warning appears only for GLB + Skeleton |

Other checks: `vite build` ✅ · ESLint on changed/new files: no new findings · `tsc`: no new errors (the repo already has 82 pre-existing ones in untouched code).

---

## 2. Verified in Blender (4.5.12, headless, default import)

Exports were produced through the **new** pipeline, using the repo's code in the same order as the updated `StepExportToFile`, with the preview **mid-animation** (`Idle_FoldArms` at 0.8 s) when Download is "clicked".

| ID | Settings | Before I1 (Phase 4) | **After I1** |
|---|---|---|---|
| B5 | Full · Default · **Blender** · Create-page layout | Nothing / 2 empties (E4, your `exported-model.fbx`) | **1 Armature (66 bones) + 1 Mesh (Armature modifier, 63 vertex groups), 0 empties**, 1.65 m, upright, left hand at +X like Mixamo ✅ |
| B2 | Skeleton · Mixamo · **Blender** · mid-animation | 1.6 cm, turned 180°, rest = animation frame (your `idles.fbx`) | 1 Armature, real size, upright, faces like Mixamo. **Rest pose identical to the true T-pose: max 0.0000° / 0.0001 cm difference over 66 bones** ✅ |
| B3 | Full · Mixamo · Blender · Retarget layout (bones beside mesh) | 198 → **3** tracks (E6) | **198 tracks kept**, Armature + Mesh ✅ |
| B4 | Full · Mixamo · **Unity** · Create-page layout | Nothing (E4) | Armature + Mesh ✅ (still 1.7 cm: the Unity preset itself is unchanged on purpose) |

---

## 3. What I1 does **not** do yet (planned)

| Still open | Planned in |
|---|---|
| Bone names `mixamorigHips` (no colon) and the extra `root` bone | I2 |
| Mixamo bone axes (the NLA mismatch of ~25%) | I2 + I3 |
| Mixamo cm units on the armature (scale 0.01) for Mixamo-compatible files | I4 |
| "FBX + Blender + Mixamo" routed to the new Mixamo export | I5 |

So **after I1**, a Blender-preset download imports as a proper armature, at the right size and facing the right way, with a correct T-pose rest. It does **not yet** line up with Mixamo clips in the NLA Editor; that's I2–I4.

## 4. Notes and observations
- **Unreal and Unity are unchanged** (except that they also benefit from the structural fixes). In Blender they still import tiny, which is expected: use the new **Blender** preset for Blender.
- Existing behaviour I left alone (outside I1's scope): on the Retarget page, a skeleton-only export moves the root bone into the export scene with `add()`, which drops any scale the app applied to the imported model.
- The preset button labels show the raw values (`unreal`, `unity`, `blender`), the same as before. I didn't change label styling.

## 5. Please check in the app (manual)
1. `npm run dev` → **Use Your Model** (`/create.html`) → finish the steps up to the animation list.
2. Download options: **FBX 7.4** · FBX Preset **blender** · Contents **Default** → Download.
3. In Blender: *File → Import → FBX* (default settings). Expect **one Armature + your mesh**, normal size, standing upright, animation playing.
4. Repeat with Contents **Skeleton + Animations**: expect one Armature in a T-pose rest, even if the preview was mid-animation.
5. Pick **GLB** + **Skeleton + Animations**: the warning note should appear.
