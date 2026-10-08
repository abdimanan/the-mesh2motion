# Implementation Phase I2: Mixamo rig builder

**Status:** Done, not committed (branch `feature/blender-fbx-preset`)
**Date:** 2026-10-06
**Design:** [05-root-cause-and-feature-design.md](05-root-cause-and-feature-design.md) §2, §4.2

## What I2 had to deliver

A function that turns the Mesh2Motion human skeleton into a **Mixamo-convention skeleton**: 65 bones named `mixamorig:<Name>`, `Hips` as the only root, every bone oriented the way Mixamo's auto-rigger orients it, and positions in **cm**. This is the skeleton the animations will be converted onto in I3.

---

## 1. Code

### New files (`src/lib/processes/export-to-file/mixamo/`)
| File | Purpose |
|---|---|
| `MixamoBoneOrientationRules.ts` | The 65 Mixamo bones (parents always before children), the **aim** of each bone's Y axis, and the **roll** rule. Also the list of required core bones. |
| `MixamoRigBuilder.ts` | `build_from_mesh2motion(skinned_meshes)` uses the bind pose, so it works mid-animation. `build_from_mesh2motion_joints(world positions)` and `build_from_joint_positions(Mixamo-named positions)` are the pure core. Returns `{ root_bone, bones, rest_world_rotations, source_bone_names }`. |
| `mixamo-reference-tpose.fixture.ts` | **Derived numbers only**: 65 joint positions and rest rotations measured from your Mixamo `T-Pose.fbx`. Used only by the test that checks the rule. The Mixamo file itself isn't in the code. |
| `MixamoRigBuilder.test.ts` | 8 tests (see §3) |

### Changed
| File | Change |
|---|---|
| `ExportRestPoseService.ts` | The bind-pose maths from I1 is now exposed as `bind_world_matrices()`, so the builder reads joint positions from the same tested code. `apply_bind_pose()` behaves exactly as before. |

---

## 2. The orientation rule (final)

Measured in the Mixamo file's frame (Y up, character faces +Z, +X = character's left; the same frame three.js uses):

| Bones | Y axis aims at | Roll |
|---|---|---|
| Hips, Spine2, Neck, Head, HeadTop_End | world up | X → +X |
| Spine, Spine1 | child | X → +X |
| Left Shoulder/Arm/ForeArm/fingers | child | X → −Z (back) |
| Left Hand | Middle1 → Index1 → Ring1 → forearm direction (first that exists) | X → −Z |
| Right side | same | X → +Z (front) |
| UpLeg, Leg, Foot | child | **Z → +Z (forward)** |
| ToeBase | child | X → −X |
| End bones (finger 4, Toe_End) | keep the parent's orientation | n/a |

One refinement during I2: with "X sideways" the **foot** came out 2.6° off. Mixamo actually keeps the leg's **Z axis facing forward**, so the leg rule now sets the roll with Z (0.0° fit). The rule can set the roll with either axis.

Missing bones (hand variants *ThumbAndIndex*, *SimplifiedHand*, *SingleBone*) are skipped together with their descendants. The hand then aims down whatever finger is left. If a **core** bone is missing (spine, arms, legs…), the builder throws a clear error naming the bones.

---

## 3. Results

### Unit tests: 8 new, suite 129 → **137, all passing**
| Test | Result |
|---|---|
| Rule reproduces Mixamo's axes from Mixamo's joint positions | **52/52 animated bones under 2°: max 1.08° (ToeBase), mean 0.09°** |
| Joints placed exactly where given | < 0.001 cm |
| Hierarchy | 65 bones, all `mixamorig:` names, parents exactly as Mixamo's, Hips the only root |
| Removed fingers (ThumbAndIndex) | middle/ring/pinky left out, hand aims down the index finger |
| Missing core bone | throws, naming `LeftForeArm` |
| Real Mesh2Motion rig (`static/rigs/rig-human.glb`) | 65 bones, `pelvis → Hips`, `hand_l → LeftHand`, **no `root` bone**, Hips at 91.7 cm, left hand at +75 cm |
| Mesh2Motion bones get **Mixamo** axes | left arm X → back, right arm X → front, leg X → character's right (Mesh2Motion had 90°/180° rolls there) |
| Built mid-animation | identical to the rest-pose build (bind pose used) |

End bones aren't part of the 2° check, because Mixamo never animates them (52 of 65 bones carry keys in a Mixamo clip). The thumb tips differ by 17°. Every other end bone is ≤ 1.1°.

### Blender check (preview of I4)
I exported just the built skeleton (no animation yet) with Mixamo's header settings (cm, `UnitScaleFactor 1`, Y-up, Front/Coord +1) and imported it next to your `T-Pose.fbx`:

| Check | Mixamo `T-Pose.fbx` | Built from Mesh2Motion | |
|---|---|---|---|
| Objects | 1 Armature | 1 Armature | ✅ |
| Armature object | scale 0.01, rotation X 90° | scale 0.01, rotation X 90° | ✅ identical |
| Bone names | 65 | **65/65 identical** | ✅ |
| Roots | `mixamorig:Hips` | `mixamorig:Hips` | ✅ |
| Animated bones with rest axes > 10° off | n/a | **7/52** (Phase 4 with Mesh2Motion axes: 38/65) | much closer |
| Mean rest-axis difference | n/a | **5.0°** | |
| Largest | n/a | Shoulders 26.9°, Spine 14.0°, Index2 11.9° | see §4 |

---

## 4. Finding: what's left is body proportions, not the rule

The rule reproduces Mixamo's axes to about 1° **when given Mixamo's joints**. The 5° mean / 27° shoulder difference above appears only because the **Mesh2Motion body has different proportions** from the default Mixamo character. For example, Mesh2Motion's collarbones point at a different angle, and since a bone's Y axis points at its child, that angle becomes the bone's axis. Two different Mixamo characters differ in exactly the same way.

**Why it matters for the NLA Editor:** Blender applies keyframes relative to each bone's rest. A clip made on skeleton A and played on skeleton B is off by the rest difference between A and B. That's true for any two characters, Mixamo or not. So for mixing with Mixamo clips, the best result comes from exporting onto the **same skeleton the Mixamo clips use**.

### Options for the target skeleton (decision for I3)
| Option | How | Accuracy on your Mixamo character | Notes |
|---|---|---|---|
| **A. Rebuilt from Mesh2Motion** (what I2 does now) | rule applied to Mesh2Motion joints | close (mean ~5°, shoulders ~27°) | No Mixamo data in the app. Works on the Create page with edited skeletons. |
| **B. Default Mixamo skeleton axes** | use the measured Mixamo rotations as the rest | exact for the default Mixamo proportions only | Puts Mixamo-derived numbers into **product** code (licensing question). Still off for other characters. |
| **C. Your own Mixamo character** (Retarget page) | upload your Mixamo character FBX on the Retarget page; export onto **that** skeleton, with names restored to `mixamorig:` | **exact for that character** | Best for NLA mixing with Mixamo clips downloaded for the same character. Needs I3 to accept any target skeleton, which is planned anyway. |

**Recommendation:** keep **A** for the Create page, and add **C** on the Retarget page. I'll write the I3 converter against a generic target skeleton (the `MixamoRig` shape), so A and C share the same code, and B can be added later if you decide the licensing is fine.

---

## 5. Checks
- `vitest`: 137/137 ✅
- ESLint on new/changed files: clean ✅
- `tsc`: no new errors (81, all pre-existing in untouched files) ✅
- Nothing in the UI changes in I2. The builder isn't wired to a button until I4/I5.

## Next: I3, animation converter
Re-express every keyframe of a Mesh2Motion clip in the target skeleton's bone axes (`W_mix = W_m2m · O`, `L = W_parent⁻¹ · W_mix`), carry Hips root motion in cm, and bind the tracks by bone uuid so the `:` in the names survives the FBX exporter. Success measure: the Phase 4 NLA test, where the pose mismatch drops from 24.6% to only what the proportions explain.
