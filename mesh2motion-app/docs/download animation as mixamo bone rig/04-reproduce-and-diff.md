# Phase 4: Reproduce and compare side by side

**Status:** Done
**Date:** 2026-10-06
**Previous phases:** [01](01-mesh2motion-skeleton.md) · [02](02-reference-mixamo-fbx-anatomy.md) · [03](03-export-pipeline-trace.md)

## Goal (updated with the user's feedback)

> *"some of them are sized but it still doesn't match when I try to match it with Mixamo in the **NLA Editor** in Blender"*

So the bar is higher than "bones show up". The download must be usable **next to real Mixamo animations in Blender's NLA Editor**. In Blender, an action only drives another armature correctly when:

1. the **bone names are identical** (`mixamorig:Hips`, with colon),
2. every bone has the **same rest orientation / local axes** (keyframes are stored *relative to each bone's own axes*),
3. the **units** of the location keys match (Mixamo armatures are in cm with object scale 0.01), and
4. the character **faces the same way**.

This phase measures all four, on the user's real downloads and on controlled reproductions.

---

## 1. How the reproduction was done

| Piece | Method |
|---|---|
| Real downloads | `example of what i got/` (4 files provided by the user) |
| Controlled exports | A Node script (kept in the session scratchpad, not in the repo) that **imports the app's own unchanged export code**: `ExportBoneNamingService`, `ExportHierarchyService`, `ExportAnimationCleanupService` and `@comfyorg/fbx-exporter-three` with the **same `parseAsync` options** as `StepExportToFile.export_fbx()`. It follows the same order as `StepExportToFile.export()`. Input: `static/animations/human-base-animations.glb` (Mesh2Motion human rig, mesh and clips; textures stripped because Node has no image decoder). Clips exported: `Walk`, `Idle_A`. The root bone was placed **under the skinned mesh**, exactly as the Create page does it (`StepWeightSkin.ts:126`, `skinned_mesh.add(bones[0])`). |
| File inspection | The same binary FBX reader used in Phase 2 |
| Blender checks | Blender 4.5.12 LTS headless, default FBX/glTF import settings |
| NLA test | Import Mixamo `T-Pose.fbx` and the export into **one scene**. Compare bone names and rest orientations bone by bone. Then **play the exported `Walk` action on the Mixamo armature** (paths renamed to the colon names) and measure how far the hands, feet and head land from where the exported armature puts them (as % of body height, relative to the hips; 0% = identical motion). |

---

## 2. The user's real downloads

| File | What it is (from the FBX/GLB header) | What Blender creates |
|---|---|---|
| `exported-model.glb` | GLB, **Skeleton only**, Mixamo names, 0 skins, 0 meshes, 66 nodes, 1 clip (`Idle_A`) | **66 EMPTIES (axes)**, no armature ❌ |
| `exported-model idel.glb` | same as above | **66 EMPTIES (axes)** ❌ |
| `exported-model.fbx` | FBX, **Full** (mesh + skin), Mixamo names, **Unreal** preset (Z-up, unit 1). Hierarchy: `Skinned Mesh 0 [Mesh]` → `root [LimbNode]` → `mixamorigHips` … | **Nothing at all**: 0 objects, 0 actions ❌ |
| `exported-model idles.fbx` | FBX, **Skeleton only**, Mixamo names, **Unity** preset (unit 1, front sign −1). Clip `Idle_FoldArms` | 1 Armature, 66 bones, but **1.6 cm tall**, **turned 180°**, rest pose ≠ T-pose ⚠️ |

**All of the user's symptoms are reproduced from their own files.**

---

## 3. Controlled exports (same code as the app)

| ID | Settings | FBX content | Blender result |
|---|---|---|---|
| E1 | Skeleton · Mixamo · **Unreal** | 66 `LimbNode`, 0 Null, UpAxis=**Z**, Unit=1 | Armature 66 bones, **1.2 cm tall**, **lying down** (hips→head points along −X) |
| E2 | Skeleton · Mixamo · **Unity** | 66 `LimbNode`, Up=Y, Front sign **−1**, Unit=1 | Armature, **1.7 cm tall**, upright, **facing backwards vs Mixamo** |
| E3 | Skeleton · Mixamo · library `blender` preset *(not in UI)* | as E2 but Unit=**100** | Armature, **1.73 m** ✅ upright, **facing backwards vs Mixamo** |
| E4 | **Full** · Mixamo · Unity | `Scene [Null]` → `Armature [Null]` → `Mannequin [Mesh]` → `root [LimbNode]` …, Skin + 66 Clusters + BindPose | **Only 2 EMPTIES** (`Scene`, `Armature`). **Mesh and all 66 bones are silently dropped** ❌ |
| E5 | Skeleton · Default names · Unity | 66 `LimbNode` | Armature, 1.7 cm (baseline) |
| E6 | Full · Mixamo · Unity · bones **beside** the mesh (Retarget-page / GLB structure) | **Animation reduced from 198 tracks to 3** before export ❌ | Armature + Mesh + 1 empty |
| E7 | Full · Default names · `blender` preset · bones **beside** the mesh | `Mannequin [Mesh]` and `root [LimbNode]` are siblings | **Armature + Mesh** ✅ (+1 stray `Scene` empty) |
| E8 | Skeleton · Mixamo · `blender` preset + **`axisForward: '-Z'`** | Front/Coord sign **+1** (same as Mixamo), Unit=100 | Armature 1.73 m ✅ upright ✅ **facing the same way as Mixamo** ✅ |

Sample files saved in this folder:
- `mesh2motion-export-sample-full-mixamo-unity.fbx` (= E4, reproduces "nothing / only empties")
- `mesh2motion-export-sample-skeleton-mixamo.fbx` (= E3)

---

## 4. NLA / action-compatibility test against real Mixamo

| Measure | E2 (Unity, as shipped) | E3 (`blender` preset) | **E8 (`blender` + −Z forward)** | Target |
|---|---|---|---|---|
| Bone names identical to Mixamo | **0 / 65** | **0 / 65** | **0 / 65** | 65 / 65 |
| …identical after adding the colon | 65 / 65 | 65 / 65 | 65 / 65 | n/a |
| Faces the same way as Mixamo | ❌ (180° turned) | ❌ | ✅ | ✅ |
| Rest-pose joint offset (proportions only) | n/a | 38.4 % | **5.7 %** | small |
| Bones whose rest orientation differs > 10° | 63 / 65 | 61 / 65 | **38 / 65** | 0 |
| Mean rest-orientation difference | ~176° | 160° | **68°** | ~0° |
| Worst bones | legs, feet, fingers | hips, spine, head, hands (180°) | **both legs 180°, finger tips 180°** | n/a |
| **Pose mismatch when the exported Walk drives the Mixamo armature** | 25.8 % (max 55 %) | 25.8 % (max 55 %) | **24.6 % (max 43.5 %)** | ~0 % |
| Hips location key units | m (×0.01 armature) | m | **m** (armature scale 1) | **cm** (armature scale 0.01) |

**How to read this:**
- Fixing scale and facing direction (E8) makes the skeleton **look** right. The rest-pose offset of 5.7% is just the Mesh2Motion body being slightly shorter (1.73 m vs 1.79 m).
- But the **animation still lands about 25% of body height off** when played on a Mixamo armature, because **38 of the 65 bones have different local axes** from Mixamo's bones. Both legs, for example, have their axes rotated 180° around the bone. Blender applies keyframes in each bone's *own* axes, so the same numbers bend the Mixamo leg a different way.
- **This is why the NLA Editor doesn't match, even when the size looks right.**
- Also, Mixamo's armature is in **cm with object scale 0.01**, while our export is in **m with scale 1**. A Hips movement of 0.05 (5 cm) in our action would move a Mixamo Hips by only **0.05 cm**, so root motion is ~100× too small on a Mixamo character.

---

## 5. Root causes, confirmed

| # | Root cause | Evidence | Effect the user sees |
|---|---|---|---|
| **RC1** | **GLB "Skeleton only" exports bones with no skin.** glTF only treats nodes as joints when a `skin` references them. Without a mesh there's no skin, so the bones are plain nodes. | User GLBs: `joints=0 meshes=0`. Blender: **66 EMPTIES** | "Only axes with animation" |
| **RC2** | **Create-page Full FBX puts the root bone *under the mesh* Model.** Blender's importer then silently drops the mesh **and** the skeleton. | E4 and the user's `exported-model.fbx`: `Mesh → root LimbNode`. Blender: 0–2 objects, no error. E7 (bones beside the mesh) works. | Nothing, or only empties |
| **RC3** | **Unit scale:** both UI presets write `UnitScaleFactor=1` (cm) while the data is in **meters**. | E1/E2/user file: armature **1.2–1.7 cm** tall | Skeleton "missing" or tiny |
| **RC4** | **Axis declaration:** Unreal declares Z-up without rotating the data (character lies down). Unity/`blender` write Front/Coord **sign −1** vs Mixamo's **+1** (character turned 180°). | E1 lying down; E2/E3 180° vs Mixamo; E8 fixed with `axisForward:'-Z'` | Wrong orientation in Blender |
| **RC5** | **Skeleton-only rest pose = the frame currently on screen.** With no skin there's no bind matrix, so the exporter writes each bone's *current* local transform as its rest. | User `idles.fbx`: Hips rest rot `(99.7, 0, −13.3)` vs rig T-pose `(104.5, 0, 0)`, Spine1 `1.0` vs `−8.9` | Rest pose is a random animation frame, not a T-pose |
| **RC6** | **Names:** `mixamorigHips` (no colon) plus an extra `root` bone above Hips. | 0/65 names identical to Mixamo | NLA actions don't bind to a Mixamo armature (or the reverse) |
| **RC7** | **Bone local axes differ from Mixamo's** for 38/65 bones (legs and fingers worst). | E8: 24.6% pose mismatch with scale and direction already fixed | Even with names fixed, the motion is wrong on a Mixamo rig |
| **RC8** | **Location units:** export is m on an armature of scale 1; Mixamo is cm on scale 0.01. | Hips pose location units compared in Blender | Root motion ~100× off between rigs |
| **RC9** | **Mixamo renaming drops tracks** when the bones aren't children of the mesh (Retarget page, GLB rigs). | E6: 198 → **3** tracks per clip | Download has (almost) no animation |
| minor | FBX 7400 vs 7700; header 24 fps while retarget bakes at 30 fps; scale curves on every bone; `Lcl Rotation` instead of `PreRotation`; one stack per clip vs Mixamo's `mixamo.com` | FBX dumps | Cosmetic / tool-specific |

---

## 6. What this means for the new feature

To get a download that behaves **exactly like a Mixamo file in Blender's NLA Editor**, adding a "Blender" coordinate preset alone isn't enough. That would fix **RC3**, and half of **RC4** if it also sets `axisForward:'-Z'`. The export also has to:

1. **Always write a real armature**: FBX `LimbNode` bones hanging off the scene root (or a single Null), never under a Mesh (RC1, RC2).
2. **Use Mixamo's exact names** `mixamorig:<Name>`, with **Hips as the top bone** (merge or drop Mesh2Motion's `root`) (RC6).
3. **Use Mixamo's rest orientations** (bone local axes) and write the rest pose from the **T-pose / bind pose**, never the current frame (RC5, RC7).
4. **Convert each animation into those Mixamo bone axes**: re-express every keyframe from Mesh2Motion bone space into Mixamo bone space (RC7).
5. Write in **cm with `UnitScaleFactor=1`**, Y-up, Front/Coord sign **+1**, exactly like Mixamo, so Blender gives the armature scale 0.01 and rotation X=90°, the same as a Mixamo import (RC3, RC4, RC8).
6. Rename bones **wherever they live** (not only under the mesh) so no tracks are dropped (RC9).

Phase 5 turns this into a concrete design.

## Evidence
- User files: `example of what i got/*.fbx|*.glb` (header: `Creator: @comfyorg/fbx-exporter-three - 1.0.0`)
- Blender outputs quoted in sections 2–4 (Blender 4.5.12 LTS, default import settings)
- FBX dumps: hierarchy, GlobalSettings axis signs (`T-Pose.fbx`: Front/Coord sign +1; exports: −1)
- Code: `StepWeightSkin.ts:123-130` (root bone under mesh), `StepExportToFile.ts`, `@comfyorg/fbx-exporter-three/dist/FBXWriter.js:118-140` (bind matrix only for skinned bones), `dist/constants.js` (`RIGHT_HAND_AXES["Y|Z"]` → sign −1)
- Throw-away scripts (scratchpad, not in repo): GLB texture stripper, Node export reproduction, FBX analyzer, Blender comparison/NLA test

## Open questions for Phase 5
1. Should the Mixamo download include the **mesh** ("With Skin") as well as the skeleton-only version? (Mixamo offers both. The NLA use case needs skeleton + animation, which is what Mixamo's "Without Skin" gives.)
2. Should the feature be **only for the Human skeleton** (the only one with a Mixamo mapping)? I assume yes.
3. One stack per clip (current) or one file per clip like Mixamo? Blender handles multiple stacks fine (one action each).
