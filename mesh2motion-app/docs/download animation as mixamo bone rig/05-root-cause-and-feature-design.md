# Phase 5: Root cause and design of the new feature

**Status:** Done. This is the design for the implementation task.
**Date:** 2026-10-06
**Previous phases:** [01](01-mesh2motion-skeleton.md) · [02](02-reference-mixamo-fbx-anatomy.md) · [03](03-export-pipeline-trace.md) · [04](04-reproduce-and-diff.md)

## The user's goal

> Download **the skeleton plus the animations** from Mesh2Motion as an FBX that works in **Blender** **exactly like a Mixamo file**, so the actions can be mixed with real Mixamo animations in the **NLA Editor**. Add **Blender** to the coordinate presets, next to Unreal and Unity.

### Assumptions (change these if they're wrong)
| Topic | Assumption |
|---|---|
| Contents | **Skeleton + animation** (like Mixamo "Without Skin") is the main output. "With Skin" (mesh too) is a later extension. |
| Skeleton types | **Human only**, the only skeleton with a Mixamo mapping. The option is hidden for other skeletons, as Bone Naming already is. |
| Clips per file | Several clips in one FBX, **one AnimationStack per clip**, which gives one Blender action per clip. |
| Pages | **Create page** (`/create.html`) first. The **Retarget page** only when the source is the Mesh2Motion Human skeleton (that's already the case). |

---

## 1. Root cause summary

The problem isn't one bug. It's **five independent problems** that all have to be fixed for the file to behave like Mixamo:

| Layer | Root cause | Confirmed in |
|---|---|---|
| **A. Structure** | GLB skeleton-only has no skin, so Blender makes **empties** (RC1). Create-page Full FBX puts the bones **under the Mesh**, so Blender **drops everything** (RC2). Mixamo renaming **drops tracks** when the bones aren't under the mesh (RC9). | Phase 4 §2, §3 (E4, E6), user files |
| **B. Space** | `UnitScaleFactor=1` with meter data makes it **100× too small** (RC3). The Unreal preset declares Z-up (lies down); Unity/`blender` write Front/Coord sign **−1** (turned 180° vs Mixamo) (RC4). Location keys in m vs Mixamo cm (RC8). | Phase 4 §3 (E1–E3, E8), §4 |
| **C. Names** | `mixamorigHips` (colon stripped by three.js) plus an extra `root` bone (RC6). | Phase 1 §4, Phase 4 §4 |
| **D. Rest pose** | Skeleton-only writes the **current animation frame** as the rest pose (RC5). | User file `exported-model idles.fbx` |
| **E. Bone axes** | Mesh2Motion bone axes differ from Mixamo on **38/65 bones** (arms rolled 90°, legs 180°). Keyframes are bone-relative, so the motion is ~**25% of body height off** on a Mixamo rig (RC7). | Phase 4 §4 (E8), Phase 5 §2 below |

**A preset alone fixes only part of layer B.** Layers A, C, D and E need new export logic.

---

## 2. Key discovery: Mixamo's bone axes follow a rule

Measured on `T-Pose.fbx` (in the file's Y-up frame; the character faces +Z, and +X is the character's left):

| Bones | Local **Y** axis (along the bone) | Local **X** | Local **Z** |
|---|---|---|---|
| Hips, Neck, Head | **world up** (exactly 0.0°) | +X | +Z (forward) |
| Spine, Spine1, Spine2 | towards the child (Spine2 ≈ world up) | +X | +Z (forward) |
| HeadTop_End, *_End, finger tips (4) | same as parent | | |
| LeftShoulder / Arm / ForeArm | towards the child | −Z (back) | **−Y (down)** |
| RightShoulder / Arm / ForeArm | towards the child | +Z (front) | **−Y (down)** |
| Left/RightHand | towards **Middle1** | like the forearm | like the forearm |
| Fingers 1–3 | towards the child | like the hand (thumb ≈ 30° rolled) | |
| Up leg, Leg | towards the child (down) | **−X** | +Z (forward) |
| Foot, ToeBase | towards the child (forward) | −X | **+Y (up)** |

Measured: Y points at the chosen target with a mean deviation of 2.6°. The only exceptions are the ones in the table (Hips/Neck/Head up, Hand to the middle finger).

**Why this matters:** Mixamo's auto-rigger computes these axes **from the character's joint positions**. So we can build a **Mixamo-convention skeleton from Mesh2Motion's own joint positions**. That works for the default human **and** for skeletons the user edited on the Create page, and it means **no Mixamo data has to be copied into the app**.

For comparison, the Mesh2Motion export (E8) puts the left arm at X=−Y / Z=+Z (90° roll) and the legs at X=+X / Z=−Z (180° roll), which is exactly where the NLA mismatch comes from.

---

## 3. Options considered

| # | Option | Fixes | Verdict |
|---|---|---|---|
| 1 | **Add a "Blender" preset only** (`unitScale:100`, `axisForward:'-Z'`) | B (size, direction) | Necessary, **not sufficient**. Phase 4 E8 still has a 24.6% motion mismatch. |
| 2 | Rename bones with a colon only | C | Not sufficient (E). |
| 3 | **Build a Mixamo-convention rig and convert the animation into it, then export with the existing FBX library** | A, B, C, D, E | ✅ **Recommended** |
| 4 | Write our own FBX writer | A–E | Not needed. The library already writes correct `LimbNode`s, Skeleton attributes and curves (Phase 3). More code to maintain. |
| 5 | Blender-side Python script to convert after import | E | Fallback only: an extra manual step for the user. |
| 6 | Embed Mixamo's exact bone table (from `T-Pose.fbx`) | E (default proportions only) | ❌ Breaks for edited skeletons, and copies Mixamo data. The rule (option 3) is better. |

### Why the existing FBX library can be reused (option 3)
- It writes any `THREE.Bone` as `LimbNode` plus a Skeleton NodeAttribute (Phase 3 §2).
- It accepts option overrides: `{ unitScale: 1, axisUp: 'Y', axisForward: '-Z' }`. These give `UpAxis Y(+1)`, `FrontAxis Z(+1)`, `CoordAxis X(+1)`, which is **identical to Mixamo** (verified in E8: header Front/Coord sign +1).
- Bone names **can contain `:`** if tracks are bound by **uuid** instead of name. The library resolves track nodes with `PropertyBinding.findNode()`, which matches `node.uuid`. `PropertyBinding` can't parse `:` in a track name, but it can parse a uuid. (This **must be checked with a unit test first**.)
- Rest transforms: for a skeleton-only export the library writes each bone's local transform, so we just have to hand it a skeleton **posed at the rest pose**.

---

## 4. Recommended design

### 4.1 Output contract: "Mixamo-compatible FBX (Blender)"
The file must import into Blender (default FBX settings) **exactly like a Mixamo "Without Skin" download**:

| Item | Required value |
|---|---|
| Objects in Blender | **1 Armature**, **0 empties**, **65 bones** |
| Bone names | `mixamorig:Hips` … `mixamorig:RightToe_End` (the 65 standard names, with colon) |
| Top bone | `mixamorig:Hips` connected straight to the scene root. **No `root` bone, no Null.** |
| Bone axes | Mixamo convention (§2), built from the Mesh2Motion joint positions |
| Rest pose | Mesh2Motion **T-pose / bind pose**, never the current frame |
| Units | **cm** in the data, `UnitScaleFactor = 1`. Blender object scale **0.01**, the same as a Mixamo import. |
| Axes | `UpAxis=Y(+1)`, `FrontAxis=Z(+1)`, `CoordAxis=X(+1)`. Blender object rotation **X=90°**, the same as Mixamo. |
| Animation | One AnimationStack per clip. `Lcl Rotation` on every bone, `Lcl Translation` on **Hips only** (cm). No scale curves. |
| Frame rate | The clip's own rate (Mesh2Motion clips: 30 fps; Mixamo: 24/30). Header `TimeMode` matches. |
| FBX version | 7400 (the library default). Blender reads it like Mixamo's 7700. |

### 4.2 New modules (all in `src/lib/processes/export-to-file/mixamo/`)

```
MixamoBoneOrientationRules.ts    the §2 rule table (aim target + roll reference per Mixamo bone)
MixamoRigBuilder.ts              M2M skeleton (bind pose) ──► new THREE.Bone hierarchy, Mixamo names/axes, cm
MixamoAnimationConverter.ts      M2M AnimationClip ──► clip on the Mixamo rig (bone-space re-expression)
MixamoFbxExportService.ts        orchestrates: build rig → convert clips → FBXExporter with Mixamo header options
```

**MixamoRigBuilder**
1. Read the Mesh2Motion bones **at their bind pose**, using `skeleton.boneInverses` (not the current pose, which fixes RC5). `RetargetUtils` already has bind-pose recovery code that can be reused.
2. For each of the 65 Mixamo bones, take the matching Mesh2Motion joint's world position (`MixamoMapper` table, reversed). Fold the Mesh2Motion `root` bone into Hips.
3. Compute the world rotation from the rule: **Y = aim direction** (child, world up, or middle finger), **Z (or X) = roll reference** orthogonalised against Y.
4. Create a new `THREE.Bone` tree (Hips at the top). Local transform = parentWorld⁻¹ · world, with positions × **100** (cm).
5. Name each bone `mixamorig:<Name>`.

**MixamoAnimationConverter** (the core maths)
For every keyframe time *t* in the clip:
1. Pose the Mesh2Motion skeleton with the clip at *t*. Use a private `AnimationMixer` on a clone so the on-screen preview isn't touched.
2. For each Mixamo bone *b* with Mesh2Motion source *s*:
   `W_mix(b,t) = W_m2m(s,t) · O_b`, where `O_b = W_m2m_rest(s)⁻¹ · W_mix_rest(b)` is a constant per-bone offset.
3. Local rotation: `L(b,t) = W_mix(parent(b),t)⁻¹ · W_mix(b,t)`, written as a quaternion track (the library turns it into Euler curves).
4. Hips translation: the Mesh2Motion pelvis world position at *t*, root motion included, expressed in the Hips parent space (scene root) × 100.
5. Bind tracks by **bone uuid**, so colon names survive.

Result: when Blender plays the action on **any** Mixamo-convention armature, each bone gets the same world rotation as on the Mesh2Motion skeleton. Only proportions differ, which is the normal behaviour when mixing Mixamo clips between characters.

### 4.3 Coordinate preset: add **Blender**
`FbxExportPreset` gets a third value, `Blender`, shown in the UI as **Unreal | Unity | Blender**.

| Preset | Library options passed | Used for |
|---|---|---|
| Unreal | unchanged (`preset:'unreal'`) | existing behaviour |
| Unity | unchanged (`preset:'unity'`) | existing behaviour |
| **Blender** (normal export) | `{ preset:'blender', axisForward:'-Z' }`: meters + `UnitScaleFactor 100`, Front/Coord +1 | correct size and facing in Blender (verified E8: 1.73 m, faces like Mixamo) |
| **Blender + Mixamo bone naming** (Human) | goes through **MixamoFbxExportService**: cm data, `{ unitScale:1, axisUp:'Y', axisForward:'-Z' }` | **the Mixamo-compatible file for the NLA Editor** |

UI rule: when **FBX + Blender + Mixamo naming** is selected on the Human skeleton, show a short note: *"Mixamo-compatible: bone names and axes match Mixamo so actions can be mixed in Blender's NLA Editor."*

### 4.4 Fixes to the existing path (bundled, low risk)
| Fix | Where | Root cause |
|---|---|---|
| Full FBX: export the mesh and the root bone as **siblings** under one Group (temporarily re-parent, then restore) | `ExportHierarchyService` / `StepExportToFile.export()` | RC2 |
| Skeleton-only: reset the bones to the **bind pose** before export, then restore | `StepExportToFile`, `StepExportRetargetedAnimations` | RC5 |
| Rename bones **wherever they are** (walk `skeleton.bones`, not `skinned_mesh.traverse()`) | `ExportBoneNamingService.rename_bones_to_mixamo` | RC9 |
| GLB + Skeleton-only: show a warning ("GLB has no skin without a mesh, so Blender shows empties; use FBX") or grey it out | `DownloadSettings` UI | RC1 |

Not changed without testing in those engines: the **Unity** and **Unreal** presets. The Unity front-axis sign (−1) may also be wrong for Unity, but this task targets Blender, so that's only noted here.

---

## 5. Acceptance tests

**Automated (Vitest, run in CI):**
1. `MixamoRigBuilder`: 65 bones, exact Mixamo names with colon, Hips is the root, no `root` bone, Hips height ≈ Mesh2Motion pelvis height × 100 (cm).
2. Orientation rule: build the rig from **Mixamo's own joint positions** (numbers taken from `T-Pose.fbx`) and compare with Mixamo's rest axes. **Every bone ≤ 2°.**
3. `MixamoAnimationConverter`: for sampled frames, the world rotation of every Mixamo bone equals the Mesh2Motion bone's world rotation × the constant offset (≤ 0.1°). Hips world position matches × 100.
4. FBX contents (parse the written bytes with the repo's own FBX parser): 65 `LimbNode` Models, 0 `Null`, UpAxis/Front/Coord = Y+/Z+/X+, UnitScaleFactor 1, one stack per clip, no scale curves, curves on all 65 bones, translation only on Hips.
5. Regressions: the existing Unreal/Unity exports are byte-identical to before. Full FBX now has mesh and bones as siblings.

**Blender (headless script, run by hand or in a dev check):**
6. Import gives **1 Armature, 65 bones, 0 empties**, object scale 0.01, rotation X=90°.
7. Import together with `T-Pose.fbx`: **65/65 names identical**, rest-axis difference **≤ 2° on every bone**.
8. **NLA transfer:** play the exported Walk on the Mixamo armature. Pose mismatch **≤ 6%** (proportions only; the Phase 4 baseline rest offset was 5.7%), down from **24.6%** today.
9. Manual: in Blender's NLA Editor, push a Mesh2Motion action and a Mixamo action onto the same Mixamo armature and blend between them. Both play correctly.

> ⚠️ `T-Pose.fbx` is a Mixamo download. Mixamo's terms may not allow redistributing it in a public repo. Automated tests should use **only the derived numbers** (joint positions and axes) or keep the file local and out of git. Decide before committing.

---

## 6. Implementation plan: 6 phases

| Phase | Work | Output | Done when |
|---|---|---|---|
| **I1. Blender preset + structural fixes** | Add `Blender` to `FbxExportPreset` + UI (`{preset:'blender', axisForward:'-Z'}`). Fix RC2 (siblings), RC5 (bind pose), RC9 (rename via `skeleton.bones`). GLB skeleton-only warning. | Working "Blender" preset: correct size and facing; Full FBX no longer empty | Tests 5, 6 (normal export) pass; your files no longer import empty or tiny |
| **I2. Mixamo rig builder** | `MixamoBoneOrientationRules` + `MixamoRigBuilder` | Mixamo-convention skeleton from any M2M human skeleton | Tests 1, 2 pass |
| **I3. Animation converter** | `MixamoAnimationConverter` (bone-space re-expression, Hips root motion in cm, uuid-bound tracks; first a spike to prove uuid binding + colon names work in the FBX library) | Converted clips | Test 3 passes |
| **I4. Mixamo FBX export service** | `MixamoFbxExportService`: build → convert → `FBXExporter` with Mixamo header options; one stack per clip | Mixamo-compatible `.fbx` bytes | Test 4 passes; Blender tests 6–7 pass |
| **I5. UI + page wiring** | Create page and Retarget page: FBX + Blender + Mixamo naming routes to the new service; info note; Human-only visibility | Feature usable from the Download button | Clicking Download on both pages gives the new file |
| **I6. Blender verification + docs** | Headless Blender NLA test (8), your manual NLA check (9), update `docs/COMMANDS.md` / README section, clean up | Verified feature + documentation | Tests 8, 9 pass; you confirm in the NLA Editor |

Each implementation phase gets its own short report in this folder (`I1-…md` … `I6-…md`), the same way as the investigation, with a stop after each one for your review.

## Findings
1. The "axes only / no bones" problem has **two structural causes**: GLB skeleton-only has no skin, and the Create-page Full FBX puts the bones under the mesh. Small size and wrong orientation come from the **presets** (units and axis signs).
2. The NLA mismatch comes from **names** (colon and `root`) and, more fundamentally, from **different bone axes** on 38 of 65 bones. Fixing it means **converting the animation into Mixamo-convention bones**.
3. Mixamo's bone axes follow a **simple, measurable rule**, so the Mixamo skeleton can be rebuilt from Mesh2Motion's joint positions with no copied Mixamo data.
4. The existing FBX library is good enough. The new work is a **rig builder + animation converter** in front of it, plus a **Blender preset** and three small fixes.
5. Estimated effort: **6 implementation phases**. I1 alone already fixes your empties/tiny/rotated problems for normal exports. I2–I4 deliver the NLA-compatible Mixamo file.

## Evidence
- Phase 4 measurements (E1–E8, user files)
- Mixamo axis survey (Blender headless on `T-Pose.fbx`): Hips/Neck/Head Y = world up (0.0°), Hand Y → Middle1 (0.0°), others Y → child (mean 2.6°), roll per chain as in the §2 table
- Library behaviour: `@comfyorg/fbx-exporter-three/dist/data/transforms.js` (option overrides), `dist/constants.js` `RIGHT_HAND_AXES["Y|-Z"]` → front/coord sign +1, `dist/data/animationCollector.js:103-108` (`findNode` by name or uuid)
