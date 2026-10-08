# Investigation Plan: "Download as Mixamo bone rig" (FBX)

**Status:** Investigation complete (phases 1–5: [01](01-mesh2motion-skeleton.md), [02](02-reference-mixamo-fbx-anatomy.md), [03](03-export-pipeline-trace.md), [04](04-reproduce-and-diff.md), [05](05-root-cause-and-feature-design.md)). Implementation: I1 done ([I1](I1-blender-preset-and-structural-fixes.md)), I2 done ([I2](I2-mixamo-rig-builder.md)), I3 done ([I3](I3-animation-converter.md)), I4 done ([I4](I4-mixamo-skeleton-download-for-blender.md)); I5 (polish) next.
**Date:** 2026-10-06

## The problem

On the Retarget page (`http://localhost:5173/retarget/index.html`):

1. The app shows **"Import your rig and map the bones to continue"** and has a **Mesh2Motion Skeleton** option. We need to know what these skeletons are and what bones they contain.
2. The download settings offer **File Format: FBX 7.4** and **Bone Naming Pattern: Mixamo**.
3. **What goes wrong:** when the downloaded FBX is opened in Blender, it does **not** behave like a real Mixamo file. Instead of an **armature with bones**, you only get **empties/axes** carrying the animation. That means you can't use it as a normal rig.

**Reference file:** `docs/download animation as mixamo bone rig/T-Pose.fbx`

A quick first look at the reference file (only enough to plan, not the investigation itself):
- It is a **binary FBX** (`Kaydara FBX Binary`).
- It has about 65 bones. Each one is a `Model` of type **`LimbNode`**, and **`NodeAttribute` objects of type `Skeleton`** are present.
- The bones are named **`mixamorig:Hips`, `mixamorig:Spine` …** (prefix `mixamorig` plus a **colon**).

**Starting idea, to be proven or disproven:** the app's FBX export (the library `@comfyorg/fbx-exporter-three`) writes the bones in a form that Blender doesn't recognise as an armature. For example: `Null` nodes instead of `LimbNode`, no `Skeleton` node attributes, no `Pose`/BindPose, or no skin clusters. So Blender's FBX importer turns them into empties. A naming difference might also matter: `mixamorig_` vs `mixamorig:`.

## Questions to confirm with the user before Phase 4

- Is `T-Pose.fbx` a file **downloaded from Mixamo**, which is the *target* we want to match? Or is it a file **downloaded from Mesh2Motion**, which is the *broken* output? Right now I assume it is the **Mixamo reference**, because it already has real `LimbNode` bones.
- If it is the Mixamo reference, I also need a broken **Mesh2Motion download** to compare against. I'll make one myself in Phase 4, but if you already have one, please put it in this folder.
- Which Mixamo export setting is the target: **"With Skin"** (mesh plus armature) or **"Without Skin"** (armature only)?

## Tools

| Tool | What it's for |
|---|---|
| Source code reading (`src/retarget`, `src/lib/processes/export-to-file`, `src/lib/io/fbx`) | Follow how the skeleton and the export work |
| `node_modules/@comfyorg/fbx-exporter-three` | See exactly what the FBX writer outputs |
| A small FBX dump script, kept in the scratchpad (not in the repo), possibly reusing the repo's own parser in `src/lib/io/fbx` | Turn binary FBX into a readable tree: Objects, Connections, Pose, Deformers, AnimationStack |
| Blender in headless mode (`/Applications/Blender.app/Contents/MacOS/Blender -b --python …`) | Check how Blender actually imports each file: armature vs empties, number of bones, actions |
| The running app (`npm run dev`) | Make a real "FBX 7.4 + Mixamo naming" download to compare |

## The 5 phases

Each phase ends with its own Markdown report in this folder. We stop after each phase so you can review before the next one starts.

### Phase 1: What the Mesh2Motion skeleton is (the source side)
**Report:** `01-mesh2motion-skeleton.md`

- Read the retarget page: `src/retarget/index.html`, `retarget.ts`, `steps/StepLoadTargetModel.ts`.
- Work out what the **"Mesh2Motion Skeleton"** choices are: the rig files in `static/rigs`, and the skeleton types (human, quadruped, bird, etc.).
- List the Mesh2Motion human bone names and the hierarchy. Note bone count, rest pose and scale/units.
- Explain what "Import your rig and map the bones" means: target rig vs source animations, and how `bone-automap` / `MixamoMapper` match bones.

**Result:** a clear answer to "what type of bones are those", with the full bone list.

### Phase 2: Taking apart the reference Mixamo FBX (the target)
**Report:** `02-reference-mixamo-fbx-anatomy.md`

- Dump `T-Pose.fbx` into a readable tree.
- Record the things that make it a "real rig":
  - FBX version and header
  - `GlobalSettings`: up/front axis and **UnitScaleFactor** (cm)
  - `Model` types (`LimbNode`, `Mesh`, `Null`) and the **`NodeAttribute: Skeleton`** objects
  - the **`Pose` (BindPose)** section
  - **`Deformer` Skin plus `SubDeformer` Clusters** (TransformLink matrices)
  - the `Connections` graph
  - `AnimationStack`, `AnimationLayer` and `AnimationCurveNode` (T/R/S)
  - bone naming (`mixamorig:` prefix) and the root setup (`Armature`/`Hips`)
- Import it into Blender headless and record the result: one Armature object, N bones, mesh with armature modifier, actions.

**Result:** a checklist of the FBX features that Blender needs in order to build an armature.

### Phase 3: Following the Mesh2Motion FBX export path in the code
**Report:** `03-export-pipeline-trace.md`

- `src/lib/DOMUtilities.ts` (download settings UI) → `DownloadSettings.ts` → `retarget/steps/StepExportRetargetedAnimations.ts` and `StepExportToFile.ts`.
- `ExportBoneNamingService.ts` and `MixamoMapper.ts`: what names come out exactly (`mixamorig_X`, `mixamorigX`, `mixamorig:X`?), whether every bone is mapped, and whether track names match the bones.
- `ExportHierarchyService.ts`, `GlbSkinCleanupService.ts`, `FbxTextureCompatibilityService.ts`: how the scene is re-parented or cleaned before export.
- **Inside `@comfyorg/fbx-exporter-three`:** how it writes `THREE.Bone` / `Object3D` (LimbNode or Null?), whether it writes `NodeAttribute Skeleton`, `Pose`, Skin/Clusters, and what unit scale and axis it uses.
- Write down the order of operations, plus any place where the skinned mesh or skeleton gets dropped or turned into plain objects.

**Result:** a map of the export path with suspected weak points marked.

### Phase 4: Reproduce and compare side by side
**Report:** `04-reproduce-and-diff.md`

- Run the app, retarget an animation onto a rig, and download it as **FBX 7.4 + Mixamo naming**. Save it here as `mesh2motion-export-sample.fbx`.
- Dump it with the same tool as in Phase 2.
- Make a **comparison table, Mixamo vs Mesh2Motion**: model types, Skeleton attributes, BindPose, clusters, names, hierarchy, units/axes, animation curves.
- Import both into Blender headless and record the outcome (armature vs empties) as evidence.
- If useful, also test the GLB export path, to see whether the problem is only with FBX.

**Result:** proof of exactly what is missing or different, plus the Blender import results.

### Phase 5: Root cause and design of the new feature
**Report:** `05-root-cause-and-feature-design.md`

- State the root cause(s), backed by Phases 2–4.
- Compare the ways to fix it, with pros and cons:
  1. patch or extend `@comfyorg/fbx-exporter-three` (LimbNode, Skeleton attributes, BindPose, clusters)
  2. write our own small FBX writer for skeleton + skin + animation
  3. fix how the scene is prepared before export (if the library already supports bones and the input is the problem)
  4. other options (e.g. a Blender-side conversion script, as a fallback only)
- Recommend one, and lay out the implementation plan for the **next task**: a download that produces an FBX matching Mixamo's structure, with an armature of `mixamorig:` bones. Include the option for with or without skin.
- Define the acceptance tests:
  - Blender imports it as **one armature** with the expected bone count and names.
  - The animation plays on the bones.
  - The mesh deforms when skin is included.
  - Optional: re-importing it into Mesh2Motion works.

**Result:** a ready-to-build feature spec.

## Ground rules
- Don't change the app source during the investigation (Phases 1–5). Changes start in the feature task.
- Throw-away scripts go in the session scratchpad, not the repo. Only the Markdown reports and sample FBX files are added to this folder.
- Each report ends with **Findings**, **Evidence** (file paths / line numbers / command output) and **Open questions**.
