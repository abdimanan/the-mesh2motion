# Phase 2: Taking apart the reference Mixamo FBX (the target)

**Status:** Done
**Date:** 2026-10-06
**File examined:** `docs/download animation as mixamo bone rig/T-Pose.fbx` (266,864 bytes)
**Previous phase:** [01-mesh2motion-skeleton.md](01-mesh2motion-skeleton.md)

## Goal

Find out exactly **what is inside a real Mixamo FBX** that makes Blender build a proper **armature with bones**, and turn that into a checklist for the new feature.

## How it was examined

1. **A small binary FBX reader script** (Python, standard library only, kept in the session scratchpad and not in the repo). It decodes the binary FBX into its node tree: header, settings, objects, connections and animation.
2. **Blender 4.5.12 LTS in headless mode** (`/Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python …`). It imports the file with Blender's built-in FBX importer and reports what objects get created.
3. **Reading Blender's own FBX importer source code** (`/Applications/Blender.app/Contents/Resources/4.5/scripts/addons_core/io_scene_fbx/import_fbx.py`) to find the exact rule Blender uses to decide **"bone or empty"**.

---

## 1. Where the file came from

The FBX header says it was made by **Mixamo**, as a **skeleton plus motion only** file:

| Field | Value |
|---|---|
| `Original\|ApplicationVendor` | `Mixamo, Inc.` |
| `Original\|ApplicationName` | `mixamo.com` |
| `Original\|FileName` | `MotionOnlyScene; Retargeted Clip; Motion Sequence; 1 motions; Skeleton mixamorig:Hips` |
| `Creator` | `FBX SDK/FBX Plugins version 2020.2` |
| Created | 2026-10-06 13:13:55 |

✅ This answers an open question: `T-Pose.fbx` **is a real Mixamo download**, exported **"Without Skin"** (no mesh). It is the **target** we want to match.

---

## 2. File-level facts

| Item | Value | Notes |
|---|---|---|
| Encoding | **Binary** (`Kaydara FBX Binary`) | |
| FBX version | **7700** (FBX 2019/2020) | Mesh2Motion's UI offers "FBX 7.4" (7400). Blender reads both, so the version is **not** what decides bones vs empties. |
| Up axis | **Y** (`UpAxis=1`, sign +1) | |
| Front axis | **Z** (`FrontAxis=2`, sign +1) | |
| Coord axis | **X** (`CoordAxis=0`, sign +1) | Standard right-handed, Y-up (Maya style) |
| `UnitScaleFactor` | **1** | 1 unit = **1 centimeter**. All positions are in cm, e.g. Hips at 99.79 high. |
| Frame rate | **24 fps** (`TimeMode = 11`) | |
| Animation length | 1 frame (0 → 1/24 s) | It's a T-pose "clip": 2 keys per curve |

---

## 3. What objects the file contains

| Object class | Sub-type | Count |
|---|---|---|
| `Model` | **`LimbNode`** | **65** (one per bone) |
| `NodeAttribute` | `LimbNode` with `TypeFlags: "Skeleton"` | **65** (one per bone) |
| `AnimationStack` | `mixamo.com` | 1 |
| `AnimationLayer` | `Layer0` | 1 |
| `AnimationCurveNode` | T (translation) ×1, R (rotation) ×53 | 54 |
| `AnimationCurve` | | 315 |
| `Geometry` / `Mesh` | | **0** (no mesh) |
| `Deformer` (Skin / Cluster) | | **0** (no skin weights) |
| `Pose` (BindPose) | | **0** (no bind pose) |

**Important:** a real Mixamo "Without Skin" file has **no mesh, no skin, and no bind pose**. Blender still builds a perfect armature from it. So **BindPose and skin clusters are *not* required** for bones to appear.

---

## 4. How a single bone is written

Each bone is **two objects linked together**:

```
NodeAttribute: <id>, "\x00\x01NodeAttribute", "LimbNode"
    TypeFlags: "Skeleton"

Model: <id>, "mixamorig:Hips\x00\x01Model", "LimbNode"      <- the 3rd value is the key
    Version: 232
    Properties70:
        P: "PreRotation",   "Vector3D", ..., 0, -0.0002, 0.005   (joint orient, degrees)
        P: "RotationActive","bool", ..., 1
        P: "ScalingMax",    "Vector3D", ..., 0, 0, 0
        P: "DefaultAttributeIndex", "int", ..., 0
        P: "Lcl Translation","Lcl Translation", "", "A+", 0, 99.7919, 0   (cm)
        P: "Lcl Rotation",  "Lcl Rotation", "", "A+", ~0, ~0, ~0  (only on some bones)
    Shading: True
    Culling: "CullingOff"

Connections:
    C: "OO", <NodeAttribute id>, <Model id>      attribute -> bone
    C: "OO", <child Model id>, <parent Model id> bone -> parent bone
    C: "OO", <Hips Model id>, 0                  Hips -> scene root
```

How each bone is described:
- **Model sub-type = `"LimbNode"`.** This is what makes it a bone (see section 6).
- **Name = `mixamorig:Hips`.** In binary FBX the stored string is `mixamorig:Hips` + `\x00\x01` + `Model`, a "Name::Class" pair. **The colon is part of the bone name.**
- **Bone orientation is stored in `PreRotation`** (Maya "joint orient") on 47 of 65 bones. `Lcl Rotation` is ~0 in the rest pose. This is the standard Maya / Mixamo style.
- **Bones point along local +Y.** Children are offset mostly along +Y, e.g. Spine → Spine1 `T=(0, 11.73, 0)`.
- **No extra "Armature" node:** `mixamorig:Hips` is connected **directly to the scene root (0)**. Blender creates the `Armature` object itself.
- The `NodeAttribute` uses the template defaults `Size = 100` and `LimbLength = 1`.

### Hierarchy (first levels)
```
(scene root)
└─ mixamorig:Hips            T=(0, 99.79, 0)  cm
   ├─ mixamorig:Spine → Spine1 → Spine2 → (Neck → Head → HeadTop_End,
   │                                       LeftShoulder → LeftArm → LeftForeArm → LeftHand → fingers 1-4,
   │                                       RightShoulder → … )
   ├─ mixamorig:LeftUpLeg → LeftLeg → LeftFoot → LeftToeBase → LeftToe_End
   └─ mixamorig:RightUpLeg → RightLeg → RightFoot → RightToeBase → RightToe_End
```
65 bones in total. These are exactly the 65 Mixamo names mapped from Mesh2Motion in Phase 1.

---

## 5. How the animation is written

| Item | Value |
|---|---|
| AnimationStack | `mixamo.com`. Blender names the action `Armature\|mixamo.com\|Layer0` |
| AnimationLayer | `Layer0` |
| Rotation curves | 53 `R` curve nodes connected to the `Lcl Rotation` property of **52 bones** (X/Y/Z **Euler, degrees**) |
| Translation curves | **1** `T` curve node, on `Lcl Translation` of **Hips only** (root motion) |
| Scale curves | none |
| Keys | 2 keys per curve (frame 0 and frame 1 at 24 fps) |
| Connection types | `OO` curveNode → layer, `OO` layer → stack, `OP` curve → curveNode (`d\|X`, `d\|Y`, `d\|Z`), `OP` curveNode → Model (`Lcl Rotation` / `Lcl Translation`) |
| Takes section | `Take: "mixamo.com"` with `LocalTime` / `ReferenceTime` |

So Mixamo animation means **Euler rotation curves on every bone, plus translation only on Hips**. It's attached to the **bones' own `Lcl Rotation` / `Lcl Translation` properties**.

---

## 6. ⭐ The key finding: Blender's "bone or empty" rule

From Blender's FBX importer, `import_fbx.py` line 3397:

```python
# Note: 'Root' "bones" are handled as (armature) objects.
is_bone = fbx_obj.props[2] in {b'LimbNode', b'Limb'}
```

And from `find_armatures()` (lines 2473-2496):

```python
if child.is_bone:
    needs_armature = True
...
if self.fbx_type in {b'Null', b'Root'}:
    self.is_armature = True      # an empty parent becomes the Armature object
else:
    armature = FbxImportHelperNode(...)   # otherwise Blender inserts a new "Armature"
    armature.fbx_name = "Armature"
```

**In plain words:**

- Blender turns an FBX `Model` into a **bone only if its sub-type is `"LimbNode"`** (or the old `"Limb"`).
- A `Model` whose sub-type is **`"Null"`** becomes an **Empty**: the "axes" you see in Blender.
- The `NodeAttribute: Skeleton`, BindPose and skin clusters are **not** used to make this decision. When present they only refine the bone rest positions.
- An empty (`Null`/`Root`) directly above the bones becomes the Armature object. If there is none, Blender adds an `Armature` object itself, as it did with this Mixamo file.

➡️ **Main hypothesis for Phases 3–4:** if Mesh2Motion's FBX export writes bones as `Model … "Null"` (or anything other than `"LimbNode"`), Blender will import every bone as an **Empty with axes**, which is exactly the problem you're seeing.

---

## 7. What Blender actually creates from `T-Pose.fbx`

Headless import with default settings:

```
Object types: {'ARMATURE': 1}
ARMATURE object='Armature' bones=65 roots=['mixamorig:Hips'] scale=(0.01, 0.01, 0.01) rot=(1.5708, 0, 0)
   mixamorig:Hips           world head=(+0.000,+0.000,+0.998)
   mixamorig:Head           world head=(-0.000,+0.003,+1.601)
   mixamorig:HeadTop_End    world head=(-0.000,-0.063,+1.786)
   mixamorig:LeftHand       world head=(+0.738,+0.062,+1.436)
   mixamorig:LeftToe_End    world head=(+0.094,-0.213,+0.031)
   action: Armature|mixamo.com|Layer0
EMPTY count: 0
ACTION 'Armature|mixamo.com|Layer0' frame_range=(1.0, 2.0) fcurves=520
scene fps: 24
```

- **1 Armature object, 65 bones, 0 empties.** ✅
- Bone names keep the colon: `mixamorig:Hips`.
- The armature object has **scale 0.01** (cm → m) and **rotation X = 90°** (Y-up → Blender's Z-up). The character stands about **1.79 m** tall.
- One action, `Armature|mixamo.com|Layer0`, with 520 F-curves.
- Hands are at height 1.436 m with the arms straight out: a **T-pose**. This matches the Mesh2Motion Human rest pose from Phase 1 (hand at 1.439 m).

---

## 8. ✅ Checklist: what our new export must contain to match Mixamo

| # | Requirement | Mixamo value | Required for bones in Blender? |
|---|---|---|---|
| 1 | Every bone is a `Model` with sub-type **`"LimbNode"`** | yes | **YES, this is the decisive one** |
| 2 | One `NodeAttribute` (`"LimbNode"`, `TypeFlags: "Skeleton"`) per bone, linked `OO` to its Model | yes | Recommended (standard, other tools expect it) |
| 3 | Bone parent links: `OO child → parent`; the root bone links to scene root `0` | `mixamorig:Hips → 0` | Yes |
| 4 | Bone names `mixamorig:<Name>` **with colon**, the 65 standard names | yes | For Mixamo compatibility |
| 5 | Hips is the top bone (no extra `root` bone) | yes | For Mixamo compatibility |
| 6 | Units in **cm** (`UnitScaleFactor = 1`), Y-up, Z-front, X-coord | yes | For matching scale/orientation |
| 7 | Rest orientation in `PreRotation`, `Lcl Rotation` ≈ 0 at rest | yes | Optional (matching style) |
| 8 | Animation: 1 AnimationStack + 1 Layer; `Lcl Rotation` curves (Euler °) on bones; `Lcl Translation` curve on Hips | yes | Yes, for the animation to play on the bones |
| 9 | Frame rate 24 or 30 fps, set in `GlobalSettings.TimeMode` | 24 fps | Should match the source clips |
| 10 | Mesh + Skin Deformer + Clusters + BindPose | **absent** (Without Skin) | Only needed for a "With Skin" export |
| 11 | FBX version | 7700 | 7400 is fine; Blender reads both |

## Findings

1. **`T-Pose.fbx` is a genuine Mixamo "Without Skin" download** (`mixamo.com`, `MotionOnlyScene`). It contains **65 bones, all `Model` sub-type `LimbNode`**, with `NodeAttribute Skeleton`, and no mesh, skin or bind pose.
2. **Blender's rule is simple:** a Model becomes a **bone only if its sub-type is `LimbNode` (or `Limb`)**. `Null` Models become **empties**. Skin and BindPose are optional.
3. Mixamo names keep the **colon** (`mixamorig:Hips`). Units are **cm**, the axes are Y-up, and the frame rate is **24 fps**.
4. Mixamo animation = **Euler `Lcl Rotation` curves on 52 bones plus `Lcl Translation` on Hips**, in a stack called `mixamo.com`.
5. Blender imports it as **one Armature with 65 bones and one action**, standing ~1.79 m tall in a T-pose.

## Evidence
- FBX dump of `T-Pose.fbx`: header (`Original|ApplicationName = mixamo.com`), `GlobalSettings`, `Definitions` (65 Model, 65 NodeAttribute, no Pose/Deformer/Geometry), `Connections`.
- Blender headless import output (section 7).
- Blender importer source: `/Applications/Blender.app/Contents/Resources/4.5/scripts/addons_core/io_scene_fbx/import_fbx.py:3397` (bone rule), `:2473-2496` (armature creation), `:3443-3462` (BindPose is optional extra data).

## Open questions (for Phase 3 and 4)
1. Does `@comfyorg/fbx-exporter-three` write `THREE.Bone` as `Model … "LimbNode"` or as `"Null"`? (Phase 3, code reading.)
2. What names does the export actually write: `mixamorigHips` or `mixamorig:Hips`? (Phase 3/4.)
3. Does the export write the animation curves onto the bone Models (`Lcl Rotation`), and in what units and axes? (Phase 3/4.)
4. Still to confirm: what you uploaded as "Your 3D Rig Model" before downloading (Phase 4 needs to reproduce your exact case).
