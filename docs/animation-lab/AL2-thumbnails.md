# AL2: Thumbnails

**Status:** ✅ Done
**Date:** 2026-10-08
**Previous:** [AL1-build-animation-library.md](AL1-build-animation-library.md)

## Goal

One preview image per animation for the add-on's browser grid (AL4), and as the preview Blender's own **Asset Browser** shows.

## Result

| | |
|---|---|
| Images | **260**: 251 animations + 9 rigs (at rest) |
| Size | 256×256 PNG, **transparent background** (works on dark and light Blender themes) |
| Look | The web app's own textured models (mannequin, fox, horse, dragon…), Workbench studio lighting, cavity and outline, 3/4 front view |
| Pose | Picked automatically: the clip's **most telling frame** |
| Where | `animation_lab/library/thumbnails/<skeleton>/<id>.png`, path in `catalog.json` (`thumbnail`), and stored in the `.blend` as the action's **asset preview** |
| Time | ~17 s for all (full build with library: ~25 s) |
| Tests | **10/10 passing** |

Command: `tools/build_library/build.sh` now builds the library and then the thumbnails. `SKIP_THUMBNAILS=1` skips them.

## How it works (`tools/build_library/render_thumbnails.py`)

For each skeleton:
1. Open the library `.blend` built in AL1.
2. **Borrow the model:** import the skinned model from the first animation file whose armature matches the rig (for the human, the addon pack, because the base pack's armature differs). A copy of the GLB **without its animations** is imported, so the importer can't touch the library's actions. The model is bound to the library rig.
3. For every animation:
   - assign the action and play it at its own frame rate
   - **choose the frame** whose pose differs most from the clip's first frame (joint positions measured from the root, so walking forward doesn't count). That gives the punch fully thrown, the body on the floor at the end of a death, mid-stride for walks. Ties go to the frame nearest the middle.
   - **frame the camera** on every vertex of the posed model (orthographic, 12% margin)
   - render, save the PNG, and store it as the action's asset preview (256×256 image + 32×32 icon)
4. Render the **rig at rest** as the skeleton's thumbnail.
5. Remove the borrowed model, camera, render image and leftovers, then save the library.

## Visual check

I reviewed a contact sheet of 24 thumbnails: the 6 with the least visible model, plus a spread across categories and skeletons.
- **Humans:** walk mid-stride, jog, sitting, climbing, bow release, backflip upside down, punch, golf follow-through, swimming flat, knockback mid-fall, rig in T-pose.
- **Animals:** running fox, rearing horse, kaiju attack, gliding dragon and bird, biting shark, spider at rest.
- The lowest coverage (4.9%) are long thin creatures (snake, spider, dragon with wings spread). They're complete and recognisable, just wide.

## Problems found and fixed

| Problem | Fix |
|---|---|
| The first pose choice measured distance from the **T-pose**, so a death clip showed the character standing | Measure difference from the clip's **own first frame** |
| Importing the model into the library made Blender's glTF importer **collide with the library's same-named actions** | Import a copy of the GLB with its animations removed (`glb_patch.write_model_only_glb`); the build fails if actions change |
| A thumbnail was **cut off** (spider legs): framing used every 7th vertex | Frame on every vertex (numpy, still fast) |
| **AL1 bug:** `build.sh human` replaced the whole catalog with the human entries | Partial builds now keep the other skeletons' entries; asset catalogs are written for the whole catalog |
| **AL1 hidden errors:** "F-Curve … already exists" during the library build | `Sword_Regular_C_RM` (human base) lists every channel twice with the same keys; the patcher now drops duplicates. Earlier output filtering had hidden these errors. |
| Leftovers saved in the libraries (`Render Result` image, empty `glTF_not_exported` collection) | Removed before saving (`remove_import_leftovers`) |

Dropping the duplicate channels also tightened the motion check against the web app from 0.095 mm to **0.029 mm**.

## Tests added or extended
| Test | Checks |
|---|---|
| **Thumbnails show the model** (new) | All 260 PNGs: 256×256, RGBA, at least 3% of pixels visible (smallest: 4.9%), and **nothing on the image border** (no cropping) |
| Library holds only a clean rig | + no cameras, collections or textures; rig has no action assigned; rig has a 256×256 preview |
| Actions are ready to use | + every action has a 256×256 asset preview |
| Catalog entries are valid | + every `thumbnail` file exists |

## Catalog changes
- `animations[].thumbnail`: `"thumbnails/human/walk.png"` (was `null` in AL1)
- `skeletons[].thumbnail`: the rig at rest, e.g. `"thumbnails/human/_rig.png"`

## Not in git
Thumbnails are build output (like the `.blend` files) and are listed in `Animation-Lab-add-on/.gitignore`.
