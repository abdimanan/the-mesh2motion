# Implementation Phase I4: Mixamo skeleton + animation download for Blender

**Status:** Done, not committed (branch `feature/blender-fbx-preset`)
**Date:** 2026-10-06
**Previous:** [I3](I3-animation-converter.md)

## Your feedback

> *"These are two downloads I made just now … and Y Bot.fbx is a Mixamo character with T-pose. Let's focus on the skeleton plus animation instead of uploading characters for now, because it's not matching the other skeletons in the animation layers."*

### What your two downloads showed (`example of what i got/`)
| File | What it is | Why it didn't match |
|---|---|---|
| `exported-ch.fbx` | Full export (2 meshes + skeleton), Blender preset | Written by the **I1** code: correct size and axes (UnitScaleFactor 100, axis signs +1), but still the **Mesh2Motion skeleton**: `mixamorigHips` (no colon), the extra `root` bone, Mesh2Motion bone axes |
| `exported-model.fbx` | Skeleton + animation (`Bow`), Blender preset | Same: Mesh2Motion skeleton, so the actions can't drive a Mixamo armature correctly |

That was expected: the I2/I3 converter wasn't connected to the Download button yet. **I4 connects it.**

### What `Y Bot.fbx` showed
`Y Bot.fbx` (Mixamo character + skin, 30 fps) has **exactly the same skeleton as `T-Pose.fbx`**. In Blender: **0.000° rotation and ≤ 0.009 cm joint difference over all 65 bones**. The I3 file played on the Y Bot armature with **≤ 0.005 cm** difference. So the **standard Mixamo skeleton (Y Bot)** is the right target, and **no character upload is needed**.

---

## 1. What the app does now

In the download popup (Create page, and the Explore page, which shares the same code):

| File Format | FBX Preset | Bone Naming Pattern | Result |
|---|---|---|---|
| FBX 7.4 | **blender** | **Mixamo** | 🆕 **Standard Mixamo skeleton (Y Bot) + your selected animations**, converted onto it. No mesh. A note in the popup says so. |
| FBX 7.4 | blender | Default | Your mesh/skeleton at Blender size and orientation (I1) |
| FBX 7.4 | unreal / unity | any | unchanged |

The note shown when the new mode is active:
> *Mixamo skeleton + animations: the standard Mixamo skeleton (Y Bot) with your animations, no mesh. The actions line up with Mixamo clips in Blender's NLA Editor.*

The **Retarget page** switches this mode off on purpose. Its export writes the uploaded character's own skeleton, and you asked to leave character uploads aside for now. There, FBX + blender + Mixamo behaves as in I1.

### How to use it
1. `npm run dev` → **Use Your Model** (or Explore) → pick your animations.
2. Download options: **FBX 7.4**, FBX Preset **blender**, Bone Naming **Mixamo** (the note appears) → **Download**.
3. Blender: import `Y Bot.fbx` (or your Mixamo clips), then import the download.
4. Select the **Y Bot armature** → Action Editor → choose `…|<clip name>` → push down into the **NLA Editor** next to your Mixamo strips.

---

## 2. Verified end to end

The **real `StepExportToFile.export()`** (the code the Download button calls) was run on the full Mesh2Motion human with real clips (Walk, Idle_A, Jog, Punch_Jab). The skeleton used the Create-page layout and the preview was **mid-animation**. The file was then imported in Blender 4.5 **next to your `Y Bot.fbx`**:

| Check | Result |
|---|---|
| Objects in the download | **1 Armature**, no empties, no mesh |
| Armature object | scale **0.01**, rotation **X 90°**, identical to Y Bot |
| Bone names | **65/65 identical to Y Bot**, no extra bones, root `mixamorig:Hips` |
| Rest pose vs Y Bot | **0.000°** max difference |
| Actions | Idle_A, Jog, Punch_Jab, Walk (30 fps) |
| Curves that bind to the Y Bot armature as is | **520/520** for every action |
| **Y Bot playing each action vs the download's own armature** | **≤ 0.005 cm** for hands, feet, head, hips, in all 4 actions |

Sample of exactly that download: `mesh2motion-app-download_mixamo-skeleton-for-blender_4-clips.fbx` (this folder).

---

## 3. Code

### New
| File | Purpose |
|---|---|
| `mixamo/MixamoStandardSkeleton.ts` | The standard Mixamo skeleton: 65 joint positions (cm) and rest rotations, measured from your `T-Pose.fbx` (identical to Y Bot). Replaces the I2 test fixture, so there's one copy at higher precision. |
| `StepExportToFile.test.ts` | Runs the real export step with the new mode: one `.fbx` saved, 65 `mixamorig:` bones, one take, and **the Mesh2Motion skeleton is not renamed or moved** |

### Changed
| File | Change |
|---|---|
| `mixamo/MixamoRigBuilder.ts` | `build_standard_mixamo()` and `build_from_world_transforms()`. `build_from_mixamo_skeleton()` now uses the latter. |
| `mixamo/MixamoFbxExportService.ts` | Defaults to the **standard Mixamo skeleton**. A rebuilt or adopted rig can still be passed in. |
| `DownloadSettings.ts` | `is_mixamo_blender_export()`: FBX + Blender + Mixamo naming + Human skeleton. Note visibility. `set_mixamo_blender_export_supported()` for pages that can't do it. |
| `DOMUtilities.ts` | The note in the popup |
| `StepExportToFile.ts` | Early branch → `export_mixamo_for_blender()` → `MixamoFbxExportService.export()`. Builds fresh bones, so nothing in the scene is touched. |
| `retarget/retarget.ts` | Switches the mode off on the Retarget page |

### Tests: 6 new, suite 146 → **152, all passing**
- Standard skeleton built exactly as stored; fresh bones every call
- The mode is on only for FBX + Blender + Mixamo on Human; off when any option differs, for other skeletons, and on pages that switch it off; the note follows
- The real export step writes the Mixamo file and leaves the scene untouched

Other checks: `vite build` ✅ · ESLint: no new findings (the one error is the existing `(error: any)` in `export_glb`) · `tsc`: no new errors.

---

## 4. Notes
- **Licensing:** `MixamoStandardSkeleton.ts` puts numbers derived from Mixamo's skeleton (65 joint positions and rotations; no mesh, no animation) into the **app code**. That's fine for your local use. Before contributing this upstream to the Mesh2Motion project, the maintainers should decide whether that's acceptable under Mixamo/Adobe's terms.
- **Proportions:** the Mixamo character keeps its own proportions and posture. Mesh2Motion's motion is transferred as a change from rest (arms and legs within ~1°, spine/neck ~9° straighter: Mixamo's posture, as measured in I3).
- **Removed fingers** (simplified hands): those Mixamo finger bones exist but stay at rest.
- **Mirrored clips** export as separate actions, like before.

## 5. Next
**I5 (polish), proposed:** fps option (24/30), action naming, a skeleton+animation-only option for the **Retarget page** using its Mesh2Motion source skeleton, and an Explore-page check.
**I6:** your NLA Editor check on a download from the running app, plus the docs update (`docs/COMMANDS.md` / README section).
