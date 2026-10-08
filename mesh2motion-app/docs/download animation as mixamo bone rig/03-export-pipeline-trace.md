# Phase 3: Following the Mesh2Motion FBX export path in the code

**Status:** Done (code reading only; nothing run yet, see Phase 4)
**Date:** 2026-10-06
**Previous phases:** [01-mesh2motion-skeleton.md](01-mesh2motion-skeleton.md) · [02-reference-mixamo-fbx-anatomy.md](02-reference-mixamo-fbx-anatomy.md)

## Goal

Follow the code from the **Download** button to the bytes of the `.fbx` file, and find where the output differs from the Mixamo checklist in Phase 2. Phase 2 showed that Blender makes a bone **only** when the FBX `Model` sub-type is `"LimbNode"`.

---

## 1. The export path, step by step

Both pages use the same steps. Retarget uses `StepExportRetargetedAnimations`, and Create uses `StepExportToFile`. The two files are near copies of each other.

```
[Download button]
      │
      ▼
DownloadSettings  (src/lib/processes/export-to-file/DownloadSettings.ts)
  bone naming: Default | Mixamo      (default = Default)
  contents:    Full    | Skeleton    (default = Full)
  format:      GLB     | FBX         (default = GLB)
  FBX preset:  Unreal  | Unity       (default = Unreal  ← first enum value)
      │
      ▼
(Retarget page only) AnimationRetargetService.retarget_animation_clip()
  └─ builds new tracks named "<TARGET bone name>.quaternion|position|scale",
     baked at 30 fps                (src/retarget/AnimationRetargetService.ts:136-201, 274-286)
      │
      ▼
ExportBoneNamingService.apply_download_settings()       ← "Bone Naming Pattern: Mixamo"
  ├─ renames Bones found by skinned_mesh.traverse() using MixamoMapper
  │    (pelvis → mixamorigHips, … NO colon)
  └─ renames animation track names the same way
      │
      ▼
ExportHierarchyService.collect_objects_to_export()
  ├─ Full:     the top-most ancestor of the skinned mesh + of each root bone
  └─ Skeleton: only the root bone(s)
      │
      ▼
ExportAnimationCleanupService.clean_clips_for_export()
  └─ DROPS every track whose node name is not found in the export hierarchy
      │
      ▼
FbxTextureCompatibilityService   (texture flipY fix, not relevant here)
      │
      ▼
new FBXExporter().parseAsync(scene, { preset, includeAnimations: true, animations, onlyVisible: false, embedTextures: true })
  (node_modules/@comfyorg/fbx-exporter-three v1.0.1)
      │
      ▼
<file>.fbx  (binary, FBX 7400)
```

Evidence: `src/retarget/steps/StepExportRetargetedAnimations.ts:41-155` and `src/lib/processes/export-to-file/StepExportToFile.ts:43-196`.

---

## 2. Inside the FBX library (`@comfyorg/fbx-exporter-three` 1.0.1)

| Question | Answer | Evidence |
|---|---|---|
| How is a `THREE.Bone` written? | `Model … "LimbNode"` ✅ | `dist/data/SceneCollector.js:16-26`, `dist/builders/objects/model.js:101-111` (`if (object.isBone) return 'LimbNode'`) |
| Is a Skeleton NodeAttribute written? | Yes: `NodeAttribute "LimbNode"`, `TypeFlags "Skeleton"`, Size 33 ✅ | `dist/builders/objects/bone.js:21-31` |
| How is a `Group` / `Object3D` written? | `Model … "Null"` plus `NodeAttribute "Null"` → **an Empty in Blender** | `model.js:110`, `model.js:163-172` |
| BindPose / Skin / Clusters? | Yes, for each SkinnedMesh (Full export) ✅ | `dist/FBXWriter.js:176-190`, `dist/builders/objects/skin.js` |
| Bone rest rotation | Written as `Lcl Rotation` (Euler, ZYX order). **No `PreRotation`** like Mixamo uses | `model.js:85-88,123-147` |
| Animation | Quaternion tracks → `Lcl Rotation` Euler-degree curves; position → `Lcl Translation`; scale → `Lcl Scaling`. Tracks are matched to nodes **by name** | `dist/data/animationCollector.js:80-213` |
| Tracks with no matching node | Silently skipped | `animationCollector.js:105-108` |
| Bone names | `object.name` written as-is (already colon-free, see §4) | `model.js:119` |
| FBX version | **7400** | `dist/constants.js:4` |
| Frame rate in header | `settings.fps ?? 24`. Mesh2Motion never passes `fps` | `dist/builders/header.js:75` |
| **Unit scale** | `UnitScaleFactor = preset.unitScale` | `header.js:74,85` |
| **Axes** | `UpAxis/FrontAxis` from preset; data is **not** rotated (`bakeSpaceTransform:false`) | `dist/data/transforms.js:54-60`, `header.js:77-82` |

The presets defined in the library (`dist/data/transforms.js:54-60`):

| Preset | Up | Forward | unitScale | Offered in Mesh2Motion UI? |
|---|---|---|---|---|
| `unreal` | **Z** | X | **1** | ✅ **default** |
| `unity` | Y | Z | **1** | ✅ |
| `blender` | Y | Z | **100** | ❌ commented out in `DownloadSettings.ts:19-25` |
| `maya` | Y | Z | 100 | ❌ |
| `threejs` | Y | Z | 1 | ❌ |

### ✅ So the library does write real bones
The main hypothesis from Phase 2 ("the library writes bones as `Null`") is **wrong for `THREE.Bone` objects**: they come out as `LimbNode` with a Skeleton attribute. Bones would only become empties if the objects handed to the exporter **were not `THREE.Bone`** (plain `Group`/`Object3D`), or if Blender read the file in a way that hides the bones. That points to the problems below.

---

## 3. Problems found in the export path

### 🔴 Problem A: wrong units. The skeleton is exported 100× too small
- three.js and all Mesh2Motion rigs work in **meters** (Phase 1: human ≈ 1.64 m tall).
- Both presets offered in the UI (`unreal`, `unity`) write **`UnitScaleFactor = 1`**, and in FBX that means **1 unit = 1 cm**. The position values are **not** multiplied by 100.
- Blender therefore reads a **1.64 cm tall** skeleton. Mixamo, by contrast, writes the Hips at `99.79` (cm), and Blender applies 0.01 to get meters (Phase 2).
- **What you'd see in Blender:** the armature is tiny and practically invisible at normal zoom, while any **Null objects** (see Problem C) still show up as normal-size **axes empties**. This fits the symptom "no bones, only axes" very well.
- The library's `blender` and `maya` presets (unitScale 100) exist but are **commented out** in `DownloadSettings.ts:19-25`.
- Note: even with `unitScale: 100`, the library only writes the header value (`bake=false`). It doesn't scale the data. Whether Blender then shows the right size has to be **tested in Phase 4**.

### 🔴 Problem B: the default FBX preset declares the wrong "up" axis
- The **default** preset is **Unreal**, because it's the first value in the enum (`DOMUtilities.ts:353-355`, `DownloadSettings.ts:19-25`).
- Unreal declares **Z-up / X-forward** in the header, but the data is still three.js **Y-up** (no baking).
- Blender respects the header, so the skeleton comes in **rotated** (lying down or turned), on top of being 100× too small.
- Mixamo uses **Y-up / Z-front / X-coord** (Phase 2).

### 🟠 Problem C: extra `Null` objects in the hierarchy
- In a **Full** export, `ExportHierarchyService` moves the **top-most ancestor** of the mesh and bones into the export scene (`ExportHierarchyService.ts:27-35,66-74`). That's usually a loader `Group` (e.g. the GLB "Scene"/"Armature" node, or FBX root groups).
- Every non-Bone node (`Group`/`Object3D`) is written as **`Model "Null"`**, and Blender shows each one as an **Empty (axes)**.
- A Null **directly above** the bones becomes the Armature object, which is fine. Any **other** Nulls stay as empties.
- Mixamo has **no Null nodes at all**: `mixamorig:Hips` hangs straight off the scene root (Phase 2).

### 🟠 Problem D: Mixamo names have no colon (`mixamorigHips` instead of `mixamorig:Hips`)
- `MixamoMapper` maps to `mixamorigHips` (`src/retarget/bone-automap/MixamoMapper.ts:15-…`).
- Even names that started as `mixamorig:Hips` lose the colon on import, because three.js strips `: . / [ ]` (Phase 1), and the exporter writes `object.name` as-is.
- **Result:** the file is **not name-compatible** with real Mixamo files, retargeting presets or tools that expect `mixamorig:`.
- Also, `Hips` is not the top bone: Mesh2Motion keeps its extra **`root`** bone above `pelvis`/`mixamorigHips` (Phase 1). The Mixamo name table doesn't map `root`, so it stays named `root`.

### 🟠 Problem E: Mixamo renaming can silently delete the animation (Retarget page)
- `ExportBoneNamingService.rename_bones_to_mixamo()` only finds bones via `skinned_mesh.traverse()`, meaning bones that are **children of the mesh** (`ExportBoneNamingService.ts:27-43`).
- On the Retarget page, uploaded rigs usually have their bones as **siblings** of the mesh, not children. The code comment in `ExportHierarchyService.ts:8-13` says exactly that.
- But **all** animation tracks are renamed to Mixamo names (`ExportBoneNamingService.ts:45-51`).
- Then `ExportAnimationCleanupService` **drops every track whose bone name can't be found** (`ExportAnimationCleanupService.ts:28-40`).
- **Likely result** (when the uploaded rig is a Mesh2Motion-named rig loaded from GLB/FBX): the bones keep their old names, the tracks get Mixamo names, the tracks are deleted, and the **exported animation is empty or partial**. This needs confirming in Phase 4.
- The renaming only applies to **Mesh2Motion bone names** (the table keys). If you uploaded a **Mixamo** rig, its bones already have (colon-less) Mixamo names and the setting does nothing to them.

### 🟡 Problem F: minor format differences from Mixamo
| Item | Mesh2Motion export | Mixamo |
|---|---|---|
| FBX version | 7400 | 7700 |
| Frame rate in header | 24 fps (default; never set) while retarget bakes at **30 fps** | 24 fps |
| Rest orientation | `Lcl Rotation` | `PreRotation` (+ `Lcl Rotation` ≈ 0) |
| Root of hierarchy | Null(s) → `root` bone → `mixamorigHips` | `mixamorig:Hips` → scene root |
| Animation stacks | one stack per exported clip | one stack `mixamo.com` |
| Bone NodeAttribute Size | 33 | 100 (template default) |

None of these alone should turn bones into empties, but they matter for a file that's "exactly like Mixamo".

---

## 4. Answers to the Phase 2 open questions

| Question | Answer from the code |
|---|---|
| Does the library write `THREE.Bone` as `LimbNode` or `Null`? | **`LimbNode`** (with Skeleton attribute). Non-bone groups become `Null`. |
| What names are written? | Whatever `object.name` is. For Mixamo naming that's **`mixamorigHips`** (no colon). The extra `root` bone stays `root`. |
| Are animation curves written onto the bone Models? | Yes. `OP` curveNode → bone `Lcl Rotation`/`Lcl Translation`/`Lcl Scaling`, Euler degrees, matched **by name**. Tracks with no matching node are silently dropped. |
| Units / axes? | **Unit scale 1 (cm) with meter data → 100× too small.** Default preset Unreal declares **Z-up** with Y-up data. |

---

## 5. Ranked suspects for "Blender shows axes, not bones"

| Rank | Suspect | Why it fits | To confirm in Phase 4 |
|---|---|---|---|
| 1 | **Problem A + B: unit scale 1 and Unreal axes** | The skeleton becomes ~1.6 cm and rotated, so it's practically invisible next to normal-size empties | Export a file, import it in Blender, measure armature size and orientation |
| 2 | **Problem C: Null groups exported as empties** | These are exactly the "axes" objects you'd see | Count `Null` vs `LimbNode` models in the exported file; list Blender objects |
| 3 | Bones that aren't `THREE.Bone` in the export scene | Would come out as `Null` → empties | Check the exported file's Model sub-types |
| 4 | **Problem E: animation tracks dropped** | The download "has no usable animation" | Count AnimationCurveNodes in the export |

## Findings

1. Both pages share the same FBX path: **DownloadSettings → (retarget) → bone renaming → hierarchy collection → animation cleanup → `@comfyorg/fbx-exporter-three`**.
2. The FBX library **does** write `THREE.Bone` as `LimbNode` with a Skeleton attribute, plus skin, clusters and BindPose. It is **not** obviously broken at the bone level.
3. **The units are wrong:** both offered presets write `UnitScaleFactor = 1` (cm) while the data is in meters, so the skeleton is **100× too small** in Blender. The `blender` preset (×100) is commented out.
4. **The default preset is Unreal**, which declares **Z-up** without rotating the data, so the skeleton is mis-oriented in Blender.
5. Loader **Groups** are exported as `Null` models → **empties with axes** in Blender. Mixamo files have none.
6. Mixamo naming gives **`mixamorigHips`** (no colon), keeps an extra **`root`** bone, and on the Retarget page can **delete the animation tracks**, because bones that are siblings of the mesh are never renamed.

## Open questions for Phase 4
1. Does Blender really show a ~1.6 cm, rotated armature plus normal-size empties? (Make an export and import it in Blender headless.)
2. Do any exported bones come out as `Null`?
3. How many animation curves survive with Mixamo naming on the Retarget page?
4. Does exporting with `preset: 'blender'` (unitScale 100) give the correct size in Blender, or must the data itself be scaled ×100?
5. Still needed: **what rig did you upload** on the Retarget page, and which settings did you pick (Full/Skeleton, Unreal/Unity)? Phase 4 will test the common combinations either way.
